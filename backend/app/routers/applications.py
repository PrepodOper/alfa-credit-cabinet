import json
import logging
import random
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..models import Application, Document, Product, User
from ..schemas import (ApplicationCreate, ApplicationDetailOut, ApplicationOut, DocumentCreate,
                       DocumentOut, InfoProvideRequest, OfferAcceptRequest)
from ..security import require_role
from ..serializers import application_out, document_out, offer_payload
from ..services.pipeline import (AUTO_STATUSES, application_lock, decline_application,
                                 hand_over_to_manual_review, process_application)
from ..services.schedule import payment_schedule
from ..services.workflow import STATUS_LABELS, add_event, move

logger = logging.getLogger("credit.pipeline")

router = APIRouter(prefix="/applications", tags=["applications"])

SIGN_DOCS = [
    {"code": "individual_terms", "title": "Индивидуальные условия кредитного договора", "pages": 5},
    {"code": "general_terms", "title": "Общие условия кредитного договора", "pages": 12},
    {"code": "schedule", "title": "График платежей", "pages": 1},
    {"code": "consent", "title": "Согласие на обработку данных и запрос в БКИ", "pages": 2},
]


def _gen_number(db: Session) -> str:
    while True:
        number = f"ALF-{datetime.utcnow():%y%m%d}-{random.randint(1000, 9999)}"
        if not db.query(Application).filter(Application.number == number).first():
            return number


def _get_client_app(db: Session, user: User, app_id: int) -> Application:
    app = db.get(Application, app_id)
    if app is None or app.company_id != user.company_id:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return app


def _expire_if_needed(db: Session, app: Application) -> None:
    if app.status == "offer_issued" and app.offer_expires_at and app.offer_expires_at < datetime.utcnow():
        move(db, app, "expired", title="Срок действия предложения истёк",
             comment="Предложение аннулировано. Можно подать новую заявку с актуальными условиями.")
        db.commit()


def run_pipeline(app_id: int) -> None:
    """Фоновый прогон конвейера.

    Гарантии:
    - на одну заявку одновременно работает только один прогон (пер-заявочный замок);
    - повторный прогон по уже обработанной заявке — no-op (проверка статуса внутри);
    - если автоматика упала, заявка НЕ зависает: она уходит андеррайтеру с описанием
      причины, поэтому «пропавших» заявок в очереди не бывает.
    """
    lock = application_lock(app_id)
    if not lock.acquire(blocking=False):
        # Параллельный прогон этой же заявки уже идёт — второй не нужен.
        return
    db = SessionLocal()
    try:
        app = db.get(Application, app_id)
        if app and app.status in AUTO_STATUSES:
            process_application(db, app)
    except Exception as exc:  # pragma: no cover - защита от падения фоновой задачи
        db.rollback()
        logger.exception("Конвейер не смог обработать заявку %s", app_id)
        _fallback_to_manual_review(app_id, exc)
    finally:
        db.close()
        lock.release()


def _fallback_to_manual_review(app_id: int, exc: Exception) -> None:
    """Технический сбой конвейера → ручное рассмотрение вместо «потерянной» заявки."""
    db = SessionLocal()
    try:
        app = db.get(Application, app_id)
        if app is None or app.status not in AUTO_STATUSES:
            return
        reason = (
            "Автоматическая обработка не завершилась (техническая ошибка конвейера). "
            "Заявка передана андеррайтеру, чтобы клиент не ждал повторного прогона. "
            f"Детали для поддержки: {type(exc).__name__}: {str(exc)[:200]}"
        )
        hand_over_to_manual_review(
            db, app, reason,
            title="Автоматическая проверка прервана — заявка у андеррайтера",
        )
    except Exception:  # pragma: no cover - последний рубеж
        db.rollback()
        logger.exception("Не удалось передать заявку %s в ручное рассмотрение", app_id)
    finally:
        db.close()


@router.get("", response_model=list[ApplicationOut])
def list_applications(user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    apps = (db.query(Application).filter(Application.company_id == user.company_id)
            .order_by(Application.created_at.desc()).all())
    for a in apps:
        _expire_if_needed(db, a)
    return [ApplicationOut(**application_out(a)) for a in apps]


@router.post("", response_model=ApplicationOut, status_code=201)
def create_application(payload: ApplicationCreate, background: BackgroundTasks,
                       user: User = Depends(require_role("client")),
                       db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.code == payload.product_code, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    if not (product.min_amount <= payload.amount <= product.max_amount):
        raise HTTPException(
            status_code=422,
            detail=f"Сумма должна быть от {product.min_amount:,.0f} до {product.max_amount:,.0f} ₽".replace(",", " "),
        )
    if not (product.min_term_months <= payload.term_months <= product.max_term_months):
        raise HTTPException(
            status_code=422,
            detail=f"Срок должен быть от {product.min_term_months} до {product.max_term_months} месяцев",
        )
    if not payload.purpose:
        raise HTTPException(status_code=422, detail="Укажите цель финансирования")

    app = Application(
        number=_gen_number(db),
        user_id=user.id,
        company_id=user.company_id,
        product_id=product.id,
        amount=payload.amount,
        term_months=payload.term_months,
        purpose=payload.purpose,
        purpose_details=payload.purpose_details,
        status="draft",
        required_docs_json=product.documents_json or "[]",
    )
    db.add(app)
    db.flush()
    add_event(db, app, event_type="created", title="Заявка создана", to_status="draft",
              actor_type="client", actor_name=user.full_name,
              payload={"product": product.name, "amount": app.amount, "term_months": app.term_months})
    if payload.submit:
        app.status = "submitted"
        app.submitted_at = datetime.utcnow()
        add_event(db, app, event_type="status_change", title="Заявка отправлена в банк",
                  from_status="draft", to_status="submitted", actor_type="client", actor_name=user.full_name)
        db.commit()
        background.add_task(run_pipeline, app.id)
    else:
        db.commit()
    db.refresh(app)
    return ApplicationOut(**application_out(app))


@router.get("/{app_id}", response_model=ApplicationDetailOut)
def get_application(app_id: int, user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    _expire_if_needed(db, app)
    data = application_out(app, include_history=True)
    return ApplicationDetailOut(**data)


@router.post("/{app_id}/submit", response_model=ApplicationDetailOut)
def submit_application(app_id: int, background: BackgroundTasks,
                       user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    if app.status != "draft":
        raise HTTPException(status_code=409, detail="Отправить можно только черновик заявки")
    # Атомарный переход draft → submitted: двойной клик или повтор запроса
    # не создадут второй прогон конвейера по той же заявке.
    now = datetime.utcnow()
    updated = (db.query(Application)
               .filter(Application.id == app.id, Application.status == "draft")
               .update({"status": "submitted", "submitted_at": now, "updated_at": now},
                       synchronize_session=False))
    if not updated:
        db.rollback()
        raise HTTPException(status_code=409, detail="Заявка уже отправлена")
    db.commit()
    db.refresh(app)
    add_event(db, app, event_type="status_change", title="Заявка отправлена в банк",
              from_status="draft", to_status="submitted", actor_type="client", actor_name=user.full_name)
    db.commit()
    background.add_task(run_pipeline, app.id)
    db.refresh(app)
    return ApplicationDetailOut(**application_out(app, include_history=True))


@router.get("/{app_id}/schedule")
def application_schedule(app_id: int, user: User = Depends(require_role("client")),
                         db: Session = Depends(get_db)):
    """График платежей по фактическим условиям предложения."""
    app = _get_client_app(db, user, app_id)
    if not app.offer_amount or not app.offer_term_months:
        raise HTTPException(status_code=404, detail="График появится после формирования предложения")
    moment = app.funded_at or app.offer_accepted_at or app.decision_at
    start = moment.date() if moment else None
    data = payment_schedule(app.offer_amount, app.offer_rate or 0.0, app.offer_term_months, start)
    return {"application_id": app.id, "number": app.number, **data}


@router.post("/{app_id}/offer/accept", response_model=ApplicationDetailOut)
def accept_offer(app_id: int, payload: OfferAcceptRequest,
                 user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    _expire_if_needed(db, app)
    if app.status != "offer_issued":
        raise HTTPException(status_code=409, detail="Предложение уже неактуально")
    if not payload.accept:
        decline_application(db, app, ["Клиент отказался от предложения банка"],
                            comment=payload.comment or "Клиент отклонил предложение",
                            actor_type="client", actor_name=user.full_name)
        db.commit()
        db.refresh(app)
        return ApplicationDetailOut(**application_out(app, include_history=True))

    now = datetime.utcnow()
    app.offer_accepted_at = now
    docs = [{**d, "signed": False} for d in SIGN_DOCS]
    app.signature_docs_json = json.dumps(docs, ensure_ascii=False)
    move(db, app, "signing", title="Предложение принято, документы готовы к подписанию",
         comment="Проверьте условия и подпишите пакет документов.",
         actor_type="client", actor_name=user.full_name,
         payload={"offer": offer_payload(app)})
    db.commit()
    db.refresh(app)
    return ApplicationDetailOut(**application_out(app, include_history=True))


@router.post("/{app_id}/sign", response_model=ApplicationDetailOut)
def sign_documents(app_id: int, user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    if app.status != "signing":
        raise HTTPException(status_code=409, detail="Подписание недоступно в текущем статусе")
    now = datetime.utcnow()
    docs = json.loads(app.signature_docs_json or "[]")
    for d in docs:
        d["signed"] = True
        d["signed_at"] = now.isoformat()
    app.signature_docs_json = json.dumps(docs, ensure_ascii=False)
    app.signed_at = now
    add_event(db, app, event_type="documents_signed", title="Документы подписаны (УКЭП, демо)",
              actor_type="client", actor_name=user.full_name,
              comment="Пакет документов подписан усиленной квалифицированной электронной подписью.")

    app.credit_account = f"40817810{random.randint(10**11, 10**12 - 1)}"
    app.funded_at = now
    app.status = "signed"
    add_event(db, app, event_type="status_change", title="Документы подписаны",
              from_status="signing", to_status="signed", actor_type="system",
              actor_name="Кредитный конвейер")
    move(db, app, "funded", title="Кредит выдан",
         comment=f"Средства зачислены на расчётный счёт {app.credit_account}.",
         payload={"credit_account": app.credit_account, "amount": app.offer_amount})
    db.commit()
    db.refresh(app)
    return ApplicationDetailOut(**application_out(app, include_history=True))


@router.post("/{app_id}/info", response_model=ApplicationDetailOut)
def provide_info(app_id: int, payload: InfoProvideRequest,
                 user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    if app.status != "info_requested":
        raise HTTPException(status_code=409, detail="Банк не запрашивал уточнения по этой заявке")
    if not payload.comment.strip() and not payload.fields:
        raise HTTPException(status_code=422, detail="Опишите, что уточняется, или заполните поля")
    details = payload.comment.strip()
    if payload.fields:
        details += "\n" + "\n".join(f"{k}: {v}" for k, v in payload.fields.items())
    move(db, app, "client_info_provided", title="Клиент предоставил уточнения",
         comment=details, actor_type="client", actor_name=user.full_name,
         payload={"fields": payload.fields})
    db.commit()
    db.refresh(app)
    return ApplicationDetailOut(**application_out(app, include_history=True))


@router.post("/{app_id}/documents", response_model=DocumentOut, status_code=201)
def upload_document(app_id: int, payload: DocumentCreate,
                    user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    app = _get_client_app(db, user, app_id)
    if app.status in {"funded", "declined", "expired"}:
        raise HTTPException(status_code=409, detail="Заявка закрыта — загрузка документов недоступна")
    doc = Document(application_id=app.id, doc_type=payload.doc_type, title=payload.title,
                   filename=payload.filename or f"{payload.doc_type}.pdf", size_kb=payload.size_kb or 120,
                   status="uploaded", uploaded_by_role="client")
    db.add(doc)
    add_event(db, app, event_type="document_uploaded", title=f"Загружен документ: {payload.title}",
              comment="Документ получен и будет проверен банком.",
              actor_type="client", actor_name=user.full_name)
    db.commit()
    db.refresh(doc)
    return DocumentOut(**document_out(doc))
