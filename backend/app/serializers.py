"""Преобразование ORM-моделей в контракты API."""
from __future__ import annotations

import json
from typing import Any

from .models import Application, Company, Document, NewsItem, Product
from .services.scoring import scoring_from_application
from .services.workflow import PROGRESS, STATUS_LABELS, next_action


def _json_list(value: str | None) -> list:
    try:
        return json.loads(value or "[]")
    except json.JSONDecodeError:
        return []


def product_out(p: Product) -> dict[str, Any]:
    return {
        "id": p.id, "code": p.code, "name": p.name, "tagline": p.tagline,
        "description": p.description, "min_amount": p.min_amount, "max_amount": p.max_amount,
        "min_term_months": p.min_term_months, "max_term_months": p.max_term_months,
        "base_rate": p.base_rate, "max_rate": p.max_rate,
        "min_business_age_months": p.min_business_age_months,
        "requires_collateral": p.requires_collateral,
        "purposes": _json_list(p.purposes_json), "features": _json_list(p.features_json),
        "documents": _json_list(p.documents_json),
        "icon": p.icon, "badge": p.badge,
    }


def company_brief(c: Company) -> dict[str, Any]:
    return {
        "id": c.id, "name": c.name, "short_name": c.short_name, "legal_form": c.legal_form,
        "inn": c.inn, "ogrn": c.ogrn, "industry": c.industry, "region": c.region,
        "founded_date": c.founded_date, "employees_count": c.employees_count,
        "revenue_avg_monthly": c.revenue_avg_monthly, "has_alfa_account": c.has_alfa_account,
    }


def document_out(d: Document) -> dict[str, Any]:
    return {
        "id": d.id, "doc_type": d.doc_type, "title": d.title, "filename": d.filename,
        "size_kb": d.size_kb, "status": d.status, "comment": d.comment,
        "uploaded_by_role": d.uploaded_by_role, "created_at": d.created_at,
    }


def event_out(e) -> dict[str, Any]:
    try:
        payload = json.loads(e.payload_json) if e.payload_json else None
    except json.JSONDecodeError:
        payload = None
    return {
        "id": e.id, "event_type": e.event_type, "from_status": e.from_status, "to_status": e.to_status,
        "title": e.title, "comment": e.comment, "actor_type": e.actor_type, "actor_name": e.actor_name,
        "visible_to_client": e.visible_to_client, "payload": payload, "created_at": e.created_at,
    }


def offer_payload(app: Application) -> dict[str, Any] | None:
    if app.offer_amount is None:
        return None
    return {
        "amount": app.offer_amount,
        "rate": app.offer_rate,
        "term_months": app.offer_term_months,
        "monthly_payment": app.offer_monthly_payment,
        "comment": app.offer_comment,
        "is_counter_offer": app.is_counter_offer,
        "expires_at": app.offer_expires_at,
        "accepted_at": app.offer_accepted_at,
        "requested_amount": app.amount,
        "requested_term_months": app.term_months,
    }


def application_out(app: Application, include_history: bool = False) -> dict[str, Any]:
    data = {
        "id": app.id,
        "number": app.number,
        "status": app.status,
        "status_label": STATUS_LABELS.get(app.status, app.status),
        "product": product_out(app.product),
        "company_name": app.company.short_name or app.company.name,
        "amount": app.amount,
        "term_months": app.term_months,
        "purpose": app.purpose,
        "purpose_details": app.purpose_details,
        "score": app.score,
        "risk_class": app.risk_class,
        "pd_percent": app.pd_percent,
        "required_docs": _json_list(app.required_docs_json),
        "offer": offer_payload(app),
        "decision_comment": app.decision_comment,
        "decline_reasons": _json_list(app.decline_reasons_json),
        "signature_docs": _json_list(app.signature_docs_json),
        "credit_account": app.credit_account,
        "created_at": app.created_at,
        "submitted_at": app.submitted_at,
        "decision_at": app.decision_at,
        "funded_at": app.funded_at,
        "next_action": next_action(app),
        "progress_percent": PROGRESS.get(app.status, 0),
    }
    if include_history:
        data["events"] = [event_out(e) for e in app.events if e.visible_to_client]
        data["documents"] = [document_out(d) for d in app.documents]
        data["scoring"] = scoring_from_application(app)
    return data


def client_snapshot(company: Company) -> dict[str, Any]:
    from .services.registry import bki_snapshot, company_snapshot, registry_snapshot
    return {
        "company": company_snapshot(company),
        "bki": bki_snapshot(company),
        "registry": registry_snapshot(company),
        "dynamics": _json_list(company.monthly_dynamics_json),
        "collateral_available": company.collateral_available,
        "collateral_desc": company.collateral_desc,
        "okved_name": company.okved_name,
        "director_name": company.director_name,
        "alfa_client_since": company.alfa_client_since,
    }


def news_out(n: NewsItem) -> dict[str, Any]:
    return {
        "id": n.id, "title": n.title, "summary": n.summary, "body": n.body,
        "category": n.category, "source": n.source, "reading_time_min": n.reading_time_min,
        "published_at": n.published_at,
    }
