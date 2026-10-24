from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------- auth ----------
class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    position: str = ""

    class Config:
        from_attributes = True


class CompanyBrief(BaseModel):
    id: int
    name: str
    short_name: str = ""
    legal_form: str = "ООО"
    inn: str = ""
    ogrn: str = ""
    industry: str = ""
    region: str = ""
    founded_date: Optional[date] = None
    employees_count: int = 0
    revenue_avg_monthly: float = 0
    has_alfa_account: bool = False

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserOut
    company: Optional[CompanyBrief] = None


# ---------- products ----------
class ProductOut(BaseModel):
    id: int
    code: str
    name: str
    tagline: str = ""
    description: str = ""
    min_amount: float
    max_amount: float
    min_term_months: int
    max_term_months: int
    base_rate: float
    max_rate: float
    min_business_age_months: int
    requires_collateral: bool
    purposes: list[str] = []
    features: list[str] = []
    documents: list[str] = []
    icon: str = "wallet"
    badge: str = ""

    class Config:
        from_attributes = True


class EligibilityOut(BaseModel):
    product_code: str
    eligible: bool
    estimated_rate: float
    reasons: list[str] = []
    checks: list[dict[str, Any]] = []


# ---------- scoring ----------
class FactorOut(BaseModel):
    code: str
    title: str
    value: str
    points: float
    max_points: float
    impact: str  # positive | neutral | negative


class ScoringOut(BaseModel):
    score: int
    risk_class: str
    pd_percent: float
    decision: str
    factors: list[FactorOut] = []
    hard_stops: list[str] = []
    recommended_amount: Optional[float] = None
    recommended_term_months: Optional[int] = None
    recommended_rate: Optional[float] = None
    monthly_payment: Optional[float] = None
    debt_load_percent: Optional[float] = None
    explanation: str = ""


# ---------- applications ----------
ApplicationStatus = Literal[
    "draft", "submitted", "validation", "scoring", "manual_review",
    "info_requested", "offer_formed", "offer_issued", "offer_accepted",
    "client_info_provided", "signing", "signed", "funded", "declined", "expired",
]


class ApplicationCreate(BaseModel):
    product_code: str
    amount: float = Field(gt=0)
    term_months: int = Field(gt=0, le=120)
    purpose: str = ""
    purpose_details: str = ""
    submit: bool = True


class OfferAcceptRequest(BaseModel):
    accept: bool
    comment: str = ""


class InfoProvideRequest(BaseModel):
    comment: str = ""
    fields: dict[str, Any] = {}


class DocumentCreate(BaseModel):
    doc_type: str = "other"
    title: str
    filename: str = ""
    size_kb: int = 0


class ApplicationEventOut(BaseModel):
    id: int
    event_type: str
    from_status: str = ""
    to_status: str = ""
    title: str = ""
    comment: str = ""
    actor_type: str = "system"
    actor_name: str = ""
    visible_to_client: bool = True
    payload: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: int
    doc_type: str
    title: str
    filename: str = ""
    size_kb: int = 0
    status: str
    comment: str = ""
    uploaded_by_role: str = "client"
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationOut(BaseModel):
    id: int
    number: str
    status: str
    status_label: str = ""
    product: ProductOut
    company_name: str
    amount: float
    term_months: int
    purpose: str = ""
    purpose_details: str = ""
    score: Optional[int] = None
    risk_class: Optional[str] = None
    pd_percent: Optional[float] = None
    required_docs: list[str] = []
    offer: Optional[dict[str, Any]] = None
    decision_comment: str = ""
    decline_reasons: list[str] = []
    signature_docs: list[dict[str, Any]] = []
    credit_account: str = ""
    created_at: datetime
    submitted_at: Optional[datetime] = None
    decision_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None
    next_action: str = ""
    progress_percent: int = 0


class ApplicationDetailOut(ApplicationOut):
    events: list[ApplicationEventOut] = []
    documents: list[DocumentOut] = []
    scoring: Optional[ScoringOut] = None
    client: Optional[dict[str, Any]] = None
    # График платежей по фактическим условиям предложения (сводка + строки).
    schedule: Optional[dict[str, Any]] = None


# ---------- back office ----------
class TaskOut(BaseModel):
    id: int
    number: str
    status: str
    product_name: str
    company_name: str
    amount: float
    term_months: int
    score: Optional[int] = None
    risk_class: Optional[str] = None
    pd_percent: Optional[float] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    sla_minutes: Optional[int] = None
    sla_state: str = "ok"


class TasksResponse(BaseModel):
    items: list[TaskOut]
    counts: dict[str, int]


class BankDecisionRequest(BaseModel):
    action: Literal["approve", "counter_offer", "request_info", "decline"]
    comment: str = ""
    offer_amount: Optional[float] = None
    offer_rate: Optional[float] = None
    offer_term_months: Optional[int] = None
    decline_reasons: list[str] = []


class PipelineResponse(BaseModel):
    statuses: list[dict[str, Any]]
    total: int
    in_progress: int
    approved_30d: int
    declined_30d: int


# ---------- news ----------
class NewsOut(BaseModel):
    id: int
    title: str
    summary: str
    body: str = ""
    category: str
    source: str
    reading_time_min: int
    published_at: datetime
    relevance: list[str] = []
    is_personal: bool = False

    class Config:
        from_attributes = True


# ---------- analytics ----------
class DashboardOut(BaseModel):
    company: dict[str, Any]
    stats: dict[str, Any]
    active_application: Optional[ApplicationOut] = None
    recommendations: list[dict[str, Any]] = []
    credit_meter: dict[str, Any] = {}


# ---------- company profile ----------
class CompanyUpdate(BaseModel):
    """Правка профиля компании клиентом.

    Регистрационные данные (название, ИНН, ОГРН, КПП, дата регистрации, форма)
    меняются только через ЕГРЮЛ и здесь недоступны — это явное ограничение модели.
    """
    model_config = ConfigDict(extra="forbid")

    # контакты и адрес
    phone: Optional[str] = Field(default=None, max_length=40)
    email: Optional[str] = Field(default=None, max_length=190)
    region: Optional[str] = Field(default=None, max_length=120)
    city: Optional[str] = Field(default=None, max_length=120)
    address: Optional[str] = Field(default=None, max_length=255)
    director_name: Optional[str] = Field(default=None, max_length=190)

    # деятельность
    industry: Optional[str] = Field(default=None, max_length=120)
    okved_code: Optional[str] = Field(default=None, max_length=20)
    okved_name: Optional[str] = Field(default=None, max_length=255)
    employees_count: Optional[int] = Field(default=None, ge=0, le=100_000)

    # финансы (в рублях)
    revenue_avg_monthly: Optional[float] = Field(default=None, ge=0, le=100_000_000_000)
    revenue_12m: Optional[float] = Field(default=None, ge=0, le=1_200_000_000_000)
    net_profit_12m: Optional[float] = Field(default=None, ge=-1_200_000_000_000, le=1_200_000_000_000)
    existing_monthly_payments: Optional[float] = Field(default=None, ge=0, le=100_000_000_000)
    account_turnover_monthly: Optional[float] = Field(default=None, ge=0, le=100_000_000_000)

    # залог
    collateral_available: Optional[bool] = None
    collateral_desc: Optional[str] = Field(default=None, max_length=255)

    @field_validator("email")
    @classmethod
    def _email_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return value
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Некорректный email")
        return value.strip()

    @field_validator("phone")
    @classmethod
    def _phone_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return value
        digits = sum(ch.isdigit() for ch in value)
        if digits < 10:
            raise ValueError("Телефон должен содержать не меньше 10 цифр")
        return value.strip()


class CompanyChangeOut(BaseModel):
    id: int
    field: str
    field_label: str = ""
    old_value: str = ""
    new_value: str = ""
    user_name: str = ""
    created_at: datetime

    class Config:
        from_attributes = True
