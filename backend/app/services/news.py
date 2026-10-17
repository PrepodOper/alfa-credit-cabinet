"""Персонализированная новостная лента.

Релевантность считается по трём сигналам: отрасль клиента, стадия его
кредитного пути и профиль обслуживания в банке. Лента — часть продукта:
новости объясняют изменения условий, напоминают о сроках и подсказывают
следующие шаги, а не просто транслируют общий поток.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models import Application, Company, NewsItem, User

CATEGORY_LABELS = {
    "bank": "Альфа-Банк",
    "market": "Рынок",
    "support": "Поддержка бизнеса",
    "product": "Продукты",
    "education": "База знаний",
}


def client_stage(db: Session, company: Company) -> str:
    apps = db.query(Application).filter(Application.company_id == company.id).all()
    statuses = {a.status for a in apps}
    if "funded" in statuses:
        return "funded"
    if statuses & {"submitted", "validation", "scoring", "manual_review", "client_info_provided",
                   "info_requested", "offer_formed"}:
        return "in_process"
    if "offer_issued" in statuses:
        return "has_offer"
    return "new"


STAGE_LABELS = {
    "new": "Новый клиент",
    "in_process": "Заявка в работе",
    "has_offer": "Есть предложение",
    "funded": "Действующий кредит",
}


def _score_item(item: NewsItem, company: Company, stage: str) -> tuple[int, list[str]]:
    score = 0
    relevance: list[str] = []
    industries = json.loads(item.industries_json or "[]")
    stages = json.loads(item.stage_tags_json or "[]")
    if "all" in industries:
        score += 1
    elif company.industry in industries:
        score += 4
        relevance.append(f"Ваша отрасль: {company.industry}")
    if company.okved_risk and "risk_okved" in industries:
        score += 2
    if stage in stages:
        score += 3
        relevance.append(f"Стадия: {STAGE_LABELS.get(stage, stage)}")
    if company.has_alfa_account and item.category == "bank":
        score += 2
        relevance.append("Вы клиент Альфа-Банка")
    if not company.has_alfa_account and "new_client" in stages:
        score += 2
        relevance.append("Старт работы с банком")
    if company.collateral_available and "collateral" in stages:
        score += 1
    # лёгкий бонус за свежесть
    age_days = max(0, (datetime.utcnow() - item.published_at).days)
    score += max(0, 3 - age_days // 3)
    return score, relevance


def build_feed(db: Session, user: User, company: Company | None, limit: int = 20, category: str | None = None) -> list[dict[str, Any]]:
    items = db.query(NewsItem).all()
    stage = client_stage(db, company) if company else "new"
    seen: set[int] = set()
    ranked: list[dict[str, Any]] = []
    for item in items:
        if category and category != "all" and item.category != category:
            continue
        seen.add(item.id)
        score, relevance = _score_item(item, company, stage)
        ranked.append({
            "id": item.id,
            "title": item.title,
            "summary": item.summary,
            "body": item.body,
            "category": item.category,
            "category_label": CATEGORY_LABELS.get(item.category, item.category),
            "source": item.source,
            "reading_time_min": item.reading_time_min,
            "published_at": item.published_at,
            "relevance": relevance,
            "is_personal": score >= 4,
            "relevance_score": score,
        })
    ranked.sort(key=lambda x: (x["relevance_score"], x["published_at"]), reverse=True)
    return ranked[:limit]


def feed_context(company: Company | None, stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "stage_label": STAGE_LABELS.get(stage, stage),
        "industry": company.industry if company else "",
        "has_alfa_account": company.has_alfa_account if company else False,
    }
