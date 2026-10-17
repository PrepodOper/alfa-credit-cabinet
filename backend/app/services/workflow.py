"""Модель состояний заявки, SLA и журнал событий."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..models import Application, ApplicationEvent, User

STATUS_LABELS: dict[str, str] = {
    "draft": "Черновик",
    "submitted": "Заявка отправлена",
    "validation": "Проверка данных",
    "scoring": "Скоринг и оценка риска",
    "manual_review": "Ручное рассмотрение",
    "info_requested": "Запрошены уточнения",
    "client_info_provided": "Уточнения получены",
    "offer_formed": "Условия сформированы",
    "offer_issued": "Предложение готово",
    "offer_accepted": "Предложение принято",
    "signing": "Подписание документов",
    "signed": "Документы подписаны",
    "funded": "Кредит выдан",
    "declined": "Отказ",
    "expired": "Предложение истекло",
}

# Прогресс клиентского пути в процентах для прогресс-бара.
PROGRESS: dict[str, int] = {
    "draft": 5,
    "submitted": 15,
    "validation": 25,
    "scoring": 40,
    "manual_review": 55,
    "info_requested": 55,
    "client_info_provided": 60,
    "offer_formed": 70,
    "offer_issued": 75,
    "offer_accepted": 85,
    "signing": 90,
    "signed": 95,
    "funded": 100,
    "declined": 100,
    "expired": 100,
}

ACTIVE_STATUSES = {"submitted", "validation", "scoring", "manual_review", "info_requested",
                   "client_info_provided", "offer_formed", "offer_issued", "offer_accepted", "signing", "signed"}

BANK_ACTION_STATUSES = {"manual_review", "client_info_provided"}
IN_PROGRESS_STATUSES = {"submitted", "validation", "scoring", "manual_review", "info_requested",
                        "client_info_provided", "offer_formed", "offer_issued", "offer_accepted", "signing"}

SLA_HOURS_MANUAL = 4


def add_event(
    db: Session,
    app: Application,
    *,
    title: str,
    event_type: str = "status_change",
    from_status: str = "",
    to_status: str = "",
    comment: str = "",
    actor_type: str = "system",
    actor_name: str = "Кредитный конвейер",
    visible_to_client: bool = True,
    payload: dict[str, Any] | None = None,
) -> ApplicationEvent:
    import json

    event = ApplicationEvent(
        application_id=app.id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        title=title,
        comment=comment,
        actor_type=actor_type,
        actor_name=actor_name,
        visible_to_client=visible_to_client,
        payload_json=json.dumps(payload or {}, ensure_ascii=False, default=str) if payload else "",
    )
    db.add(event)
    return event


def move(
    db: Session,
    app: Application,
    to_status: str,
    *,
    title: str | None = None,
    comment: str = "",
    actor_type: str = "system",
    actor_name: str = "Кредитный конвейер",
    visible_to_client: bool = True,
    payload: dict[str, Any] | None = None,
    event_type: str = "status_change",
) -> ApplicationEvent:
    from_status = app.status
    app.status = to_status
    app.updated_at = datetime.utcnow()
    return add_event(
        db, app,
        title=title or STATUS_LABELS.get(to_status, to_status),
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        actor_type=actor_type,
        actor_name=actor_name,
        visible_to_client=visible_to_client,
        payload=payload,
    )


def next_action(app: Application) -> str:
    if app.status == "draft":
        return "Заполните заявку и отправьте её в банк"
    if app.status in {"submitted", "validation", "scoring", "manual_review", "client_info_provided", "offer_formed"}:
        return "Ожидайте решения банка — обычно это занимает несколько минут"
    if app.status == "info_requested":
        return "Банк запросил уточнения — ответьте, чтобы продолжить рассмотрение"
    if app.status == "offer_issued":
        return "Проверьте условия предложения и примите решение"
    if app.status in {"offer_accepted", "signing"}:
        return "Подпишите документы, чтобы получить финансирование"
    if app.status == "signed":
        return "Документы подписаны, средства будут перечислены на счёт"
    if app.status == "funded":
        return "Кредит выдан — деньги зачислены на расчётный счёт"
    if app.status == "declined":
        return "Можно подать новую заявку с другими параметрами"
    return ""


def sla_info(app: Application) -> tuple[int | None, str]:
    if app.status not in BANK_ACTION_STATUSES or not app.submitted_at:
        return None, "none"
    deadline = app.submitted_at + timedelta(hours=SLA_HOURS_MANUAL)
    remaining = int((deadline - datetime.utcnow()).total_seconds() // 60)
    if remaining < 0:
        return remaining, "overdue"
    if remaining <= 60:
        return remaining, "warning"
    return remaining, "ok"


def actor_for(user: User) -> tuple[str, str]:
    if user.role == "bank":
        return "bank", user.full_name
    return "client", user.full_name
