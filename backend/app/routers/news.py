from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import get_current_user
from ..services.news import build_feed, feed_context, client_stage

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def news_feed(category: str = Query("all"), limit: int = Query(20, ge=1, le=50),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = user.company
    if company is None:
        return {"context": {"stage": "staff"}, "items": []}
    items = build_feed(db, user, company, limit=limit, category=category)
    stage = client_stage(db, company)
    return {"context": feed_context(company, stage), "items": items}
