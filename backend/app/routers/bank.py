from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, ApplicationEvent, User
from ..schemas import (ApplicationDetailOut, BankDecisionRequest, PipelineResponse, TaskOut,
                       TasksResponse)
from ..security import require_role
from ..serializers import application_out, client_snapshot, event_out
from ..services.pipeline import decline_application, form_offer
from ..services.scoring import scoring_from_application
from ..services.workflow import (BANK_ACTION_STATUSES, SLA_HOURS_MANUAL, STATUS_LABELS, add_event,
                                 move, sla_info)

router = APIRouter(prefix="/bank", tags=["bank-office"])

QUEUE = {"manual_review", "client_info_provided"}
WAITING = {"submitted", "validation", "scoring", "info_requested", "offer_issued", "offer_accepted", "signing"}
DECIDED = {"funded", "declined", "expired"}


def _bucket(status: str) -> str:
    if status in QUEUE:
        return "queue"
    if status in WAITING:
        return "waiting"
    return "decided"


def _task(app: Application) -> TaskOut:
    remaining, state = sla_info(app)
    return TaskOut(
        id=app.id, number=app.number, status=app.status, product_name=app.product.name,
        company_name=app.company.short_name or app.company.name, amount=app.amount,
        term_months=app.term_months, score=app.score, risk_class=app.risk_class,
        pd_percent=app.pd_percent, created_at=app.created_at, submitted_at=app.submitted_at,
        sla_minutes=remaining, sla_state=state,
    )


@router.get("/tasks", response_model=TasksResponse)
def tasks(tab: str = Query("queue", pattern="^(queue|waiting|decided|all)$"),
          search: str = "",
          user: User = Depends(require_role("bank")), db: Session = Depends(get_db)):
    apps = db.query(Application).order_by(Application.updated_at.desc()).all()
    counts = {"queue": 0, "waiting": 0, "decided": 0}
    items = []
    for a in apps:
        bucket = _bucket(a.status)
        counts[bucket] += 1
        if tab != "all" and bucket != tab:
            continue
        if search:
            needle = search.lower()
            haystack = f"{a.number} {a.company.short_name} {a.company.name} {a.company.inn}".lower()
            if needle not in haystack:
                continue
        items.append(_task(a))
    if tab == "queue":
        items.sort(key=lambda t: (t.sla_state == "overdue", t.sla_minutes if t.sla_minutes is not None else 10**9))
    counts["manual_review"] = sum(1 for a in apps if a.status == "manual_review")
    counts["info"] = sum(1 for a in apps if a.status in {"info_requested", "client_info_provided"})
    return TasksResponse(items=items, counts=counts)


@router.get("/applications/{app_id}", response_model=ApplicationDetailOut)
def bank_application(app_id: int, user: User = Depends(require_role("bank")), db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    data = application_out(app, include_history=True)
    all_events = [event_out(e) for e in app.events]
    data["events"] = all_events
    data["client"] = client_snapshot(app.company)
    data["scoring"] = scoring_from_application(app)
    return ApplicationDetailOut(**data)


@router.post("/applications/{app_id}/decision", response_model=ApplicationDetailOut)
def decide(app_id: int, payload: BankDecisionRequest,
           user: User = Depends(require_role("bank")), db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    if app.status not in BANK_ACTION_STATUSES:
        raise HTTPException(status_code=409, detail="Заявка не находится в очереди на решение")

    scoring = scoring_from_application(app) or {}
    product = app.product

    if payload.action == "request_info":
        if not payload.comment.strip():
            raise HTTPException(status_code=422, detail="Опишите, какие уточнения нужны клиенту")
        app.decision_comment = payload.comment
        move(db, app, "info_requested", title="Банк запросил уточнения",
             comment=payload.comment, actor_type="bank", actor_name=user.full_name,
             payload={"requested": payload.comment})
        db.commit()
        db.refresh(app)
        return bank_application(app_id, user, db)

    if payload.action == "decline":
        reasons = payload.decline_reasons or ["Решение андеррайтера: кредитный риск выше допустимого"]
        decline_application(db, app, reasons, comment=payload.comment or "; ".join(reasons),
                            actor_type="bank", actor_name=user.full_name)
        add_event(db, app, event_type="decision", title="Решение принято андеррайтером",
                  comment="Отрицательное решение", actor_type="bank", actor_name=user.full_name,
                  visible_to_client=True)
        db.commit()
        db.refresh(app)
        return bank_application(app_id, user, db)

    # approve / counter_offer
    amount = payload.offer_amount or scoring.get("recommended_amount") or app.amount
    rate = payload.offer_rate if payload.offer_rate is not None else (scoring.get("recommended_rate") or product.base_rate)
    term = payload.offer_term_months or scoring.get("recommended_term_months") or app.term_months

    if not (product.min_amount <= amount <= product.max_amount):
        raise HTTPException(status_code=422, detail="Сумма вне лимитов продукта")
    if not (product.min_term_months <= term <= product.max_term_months):
        raise HTTPException(status_code=422, detail="Срок вне лимитов продукта")
    if not (product.base_rate - 2.0 <= rate <= product.max_rate):
        raise HTTPException(status_code=422,
                            detail=f"Ставка должна быть в диапазоне {product.base_rate - 2:.1f}–{product.max_rate:.1f}%")

    is_counter = payload.action == "counter_offer" or amount < app.amount or rate > (product.base_rate + 2)
    if payload.action == "counter_offer":
        is_counter = True
    comment = payload.comment or (
        f"Решение андеррайтера: {'контрпредложение' if is_counter else 'одобрение'} "
        f"на сумму {amount:,.0f} ₽, ставка {rate}%, срок {term} мес.".replace(",", " ")
    )
    form_offer(db, app, amount=amount, rate=rate, term_months=term, comment=comment,
               is_counter_offer=is_counter, actor_type="bank", actor_name=user.full_name)
    add_event(db, app, event_type="decision", title="Решение принято андеррайтером",
              comment=comment, actor_type="bank", actor_name=user.full_name,
              payload={"action": payload.action, "amount": amount, "rate": rate, "term_months": term})
    db.commit()
    db.refresh(app)
    return bank_application(app_id, user, db)


@router.get("/pipeline", response_model=PipelineResponse)
def pipeline(user: User = Depends(require_role("bank")), db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    stage_keys = ["submitted", "validation", "scoring", "manual_review", "info_requested",
                  "client_info_provided", "offer_issued", "signing", "funded", "declined"]
    statuses = []
    for key in stage_keys:
        count = sum(1 for a in apps if a.status == key)
        amount = sum(a.amount for a in apps if a.status == key)
        statuses.append({"status": key, "label": STATUS_LABELS[key], "count": count, "amount": amount})

    since = datetime.utcnow() - timedelta(days=30)
    decided = [a for a in apps if a.decision_at and a.decision_at >= since]
    return PipelineResponse(
        statuses=statuses,
        total=len(apps),
        in_progress=sum(1 for a in apps if _bucket(a.status) != "decided"),
        approved_30d=sum(1 for a in decided if a.status not in {"declined", "expired"}),
        declined_30d=sum(1 for a in decided if a.status == "declined"),
    )


@router.get("/metrics")
def metrics(user: User = Depends(require_role("bank")), db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    decided = [a for a in apps if a.decision_at and a.submitted_at]
    auto = [a for a in decided if a.score is not None and not (a.events and any(
        e.actor_type == "bank" and e.event_type == "decision" for e in a.events))]
    manual = [a for a in apps if any(e.actor_type == "bank" and e.event_type == "decision" for e in a.events)]
    durations = [(a.decision_at - a.submitted_at).total_seconds() / 60 for a in decided]
    portfolio = sum(a.offer_amount or 0 for a in apps if a.status in {"funded", "signed"})
    queue = [a for a in apps if a.status in QUEUE]
    breaches = sum(1 for a in queue if (sla_info(a)[0] or 0) < 0)
    decline_rate = (sum(1 for a in decided if a.status == "declined") / len(decided) * 100) if decided else 0
    return {
        "total": len(apps),
        "in_queue": len(queue),
        "avg_decision_minutes": round(sum(durations) / len(durations), 1) if durations else 0,
        "auto_share": round(len(auto) / len(decided) * 100, 1) if decided else 0,
        "manual_share": round(len(manual) / len(apps) * 100, 1) if apps else 0,
        "decline_rate": round(decline_rate, 1),
        "portfolio": portfolio,
        "sla_breaches": breaches,
        "sla_hours": SLA_HOURS_MANUAL,
        "queue_by_status": {s: sum(1 for a in apps if a.status == s) for s in sorted(QUEUE)},
    }
