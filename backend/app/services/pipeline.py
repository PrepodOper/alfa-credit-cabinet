"""Обработка заявки кредитным конвейером (автоматическая ветка)."""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Application
from .scoring import (annuity_payment, calculate_scoring, declined_reasons, requires_manual_review,
                      scoring_to_json)
from .workflow import add_event, move


def _stage(name: str) -> None:
    """Пауза, имитирующая длительность этапа обработки.

    Длительность берётся из профиля TIMING_PROFILE и умножается на DEMO_DELAY_SCALE,
    поэтому на защите показ остаётся быстрым, а в «правдоподобном» режиме — реалистичным.
    """
    seconds = settings.stage_seconds.get(name, 0.0) * settings.demo_delay_scale
    if seconds > 0:
        time.sleep(seconds)


def form_offer(
    db: Session,
    app: Application,
    *,
    amount: float,
    rate: float,
    term_months: int,
    comment: str = "",
    is_counter_offer: bool = False,
    actor_name: str = "Кредитный конвейер",
    actor_type: str = "system",
) -> None:
    app.offer_amount = round(amount, 2)
    app.offer_rate = round(rate, 1)
    app.offer_term_months = term_months
    app.offer_monthly_payment = round(annuity_payment(app.offer_amount, app.offer_rate, term_months), 2)
    app.offer_comment = comment
    app.is_counter_offer = is_counter_offer
    app.offer_expires_at = datetime.utcnow() + timedelta(hours=settings.offer_ttl_hours)
    app.required_docs_json = app.product.documents_json or "[]"
    app.decision_at = app.decision_at or datetime.utcnow()
    move(
        db, app, "offer_issued",
        title="Предложение сформировано" if not is_counter_offer else "Сформировано контрпредложение",
        comment=comment or (
            f"Сумма {app.offer_amount:,.0f} ₽, ставка {app.offer_rate}%, срок {term_months} мес., "
            f"платёж {app.offer_monthly_payment:,.0f} ₽/мес.".replace(",", " ")
        ),
        actor_type=actor_type, actor_name=actor_name,
        payload={
            "amount": app.offer_amount, "rate": app.offer_rate, "term_months": term_months,
            "monthly_payment": app.offer_monthly_payment, "is_counter_offer": is_counter_offer,
        },
    )


def decline_application(
    db: Session,
    app: Application,
    reasons: list[str],
    *,
    comment: str = "",
    actor_type: str = "system",
    actor_name: str = "Кредитный конвейер",
) -> None:
    app.decline_reasons_json = json.dumps(reasons, ensure_ascii=False)
    app.decision_comment = comment
    app.decision_at = datetime.utcnow()
    move(
        db, app, "declined",
        title="Принято отрицательное решение",
        comment=comment or "; ".join(reasons),
        actor_type=actor_type, actor_name=actor_name,
        payload={"reasons": reasons},
    )


def process_application(db: Session, app: Application) -> Application:
    """Прогон заявки по автоматической ветке конвейера.

    Шаги: проверка полноты → обогащение данными (БКИ, ЕГРЮЛ, ФНС) → скоринг →
    маршрутизация (авто-решение / ручное рассмотрение / отказ).
    """
    from .registry import bki_snapshot, registry_snapshot

    _stage("validation")
    move(db, app, "validation", title="Проверка полноты и корректности данных",
         comment="Анкета заполнена, обязательные поля и параметры продукта проверены.")
    db.commit()

    _stage("enrichment")
    bki = bki_snapshot(app.company)
    registry = registry_snapshot(app.company)
    add_event(
        db, app, event_type="data_enrichment",
        title="Данные обогащены из внешних источников",
        comment="Получены сведения из БКИ, ЕГРЮЛ/ЕГРИП и сервиса ФНС «Прозрачный бизнес».",
        payload={"bki": bki, "registry": registry},
    )
    db.commit()

    _stage("scoring")
    move(db, app, "scoring", title="Скоринг и оценка кредитного риска",
         comment="Рассчитывается балльная оценка и риск-класс заявки.")
    db.commit()

    result = calculate_scoring(app.company, app.product, app.amount, app.term_months)
    app.score = result["score"]
    app.risk_class = result["risk_class"]
    app.pd_percent = result["pd_percent"]
    app.scoring_json = scoring_to_json(result)

    add_event(
        db, app, event_type="scoring",
        title="Скоринг завершён",
        comment=result["explanation"],
        payload={"score": result["score"], "risk_class": result["risk_class"],
                 "pd_percent": result["pd_percent"], "decision": result["decision"]},
    )
    db.commit()

    _stage("decision")
    if result["decision"] == "declined":
        decline_application(db, app, declined_reasons(result), comment=result["explanation"])
        db.commit()
        return app

    if requires_manual_review(result, app.amount):
        app.required_docs_json = app.product.documents_json or "[]"
        move(
            db, app, "manual_review",
            title="Заявка передана на ручное рассмотрение",
            comment=(
                f"Балл {result['score']}/1000, риск-класс {result['risk_class']}. "
                "Заявка требует проверки андеррайтером: параметры или риск-профиль находятся в пограничной зоне."
            ),
            payload={"score": result["score"], "risk_class": result["risk_class"],
                     "queue_reason": "Пограничный риск-класс или крупная сумма"},
        )
        db.commit()
        return app

    # Автоматическое одобрение: риск-классы A и B.
    form_offer(
        db, app,
        amount=min(app.amount, result["recommended_amount"] or app.amount),
        rate=result["recommended_rate"] or app.product.base_rate,
        term_months=app.term_months,
        comment=(
            f"Автоматическое решение: балл {result['score']}/1000, риск-класс {result['risk_class']}, "
            f"PD≈{result['pd_percent']:.1f}%. Ставка рассчитана по риск-профилю."
        ),
    )
    db.commit()
    return app
