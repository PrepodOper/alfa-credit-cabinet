from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(190), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(190), nullable=False)
    role = Column(String(20), nullable=False, default="client")  # client | bank
    position = Column(String(120), default="")
    phone = Column(String(40), default="")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    company = relationship("Company", back_populates="users")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    short_name = Column(String(120), default="")
    legal_form = Column(String(20), default="ООО")  # ООО | ИП
    inn = Column(String(12), default="")
    ogrn = Column(String(20), default="")
    kpp = Column(String(20), default="")
    industry = Column(String(120), default="")
    okved_code = Column(String(20), default="")
    okved_name = Column(String(255), default="")
    okved_risk = Column(Boolean, default=False)
    region = Column(String(120), default="")
    city = Column(String(120), default="")
    address = Column(String(255), default="")
    founded_date = Column(Date, default=date.today)
    employees_count = Column(Integer, default=0)
    director_name = Column(String(190), default="")
    phone = Column(String(40), default="")
    email = Column(String(190), default="")
    revenue_avg_monthly = Column(Float, default=0.0)
    revenue_12m = Column(Float, default=0.0)
    net_profit_12m = Column(Float, default=0.0)
    existing_monthly_payments = Column(Float, default=0.0)
    account_turnover_monthly = Column(Float, default=0.0)
    has_alfa_account = Column(Boolean, default=False)
    alfa_client_since = Column(Date, nullable=True)
    collateral_available = Column(Boolean, default=False)
    collateral_desc = Column(String(255), default="")
    monthly_dynamics_json = Column(Text, default="[]")  # последние 6 месяцев: выручка/прибыль
    created_at = Column(DateTime, default=utcnow)

    users = relationship("User", back_populates="company")
    credit_profile = relationship("CreditProfile", back_populates="company", uselist=False)
    registry_info = relationship("RegistryInfo", back_populates="company", uselist=False)


class CreditProfile(Base):
    """Мок-выгрузка из бюро кредитных историй (БКИ)."""

    __tablename__ = "credit_profiles"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True, nullable=False)
    bki_score = Column(Integer, default=600)
    active_loans = Column(Integer, default=0)
    total_debt = Column(Float, default=0.0)
    monthly_payments = Column(Float, default=0.0)
    max_delay_days_12m = Column(Integer, default=0)
    has_current_overdue = Column(Boolean, default=False)
    delinquencies_12m = Column(Integer, default=0)
    inquiries_6m = Column(Integer, default=0)
    summary = Column(Text, default="")
    updated_at = Column(DateTime, default=utcnow)

    company = relationship("Company", back_populates="credit_profile")


class RegistryInfo(Base):
    """Мок-выгрузка из ЕГРЮЛ/ЕГРИП и сервиса ФНС «Прозрачный бизнес»."""

    __tablename__ = "registry_infos"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), unique=True, nullable=False)
    status = Column(String(60), default="Действующий")
    tax_debt = Column(Boolean, default=False)
    fns_violations = Column(Boolean, default=False)
    mass_address = Column(Boolean, default=False)
    director_changed_recently = Column(Boolean, default=False)
    founders_json = Column(Text, default="[]")
    employees_reported = Column(Integer, default=0)
    last_update = Column(DateTime, default=utcnow)
    source = Column(String(120), default="ЕГРЮЛ / ФНС «Прозрачный бизнес» (мок)")

    company = relationship("Company", back_populates="registry_info")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    code = Column(String(40), unique=True, nullable=False)
    name = Column(String(190), nullable=False)
    tagline = Column(String(255), default="")
    description = Column(Text, default="")
    min_amount = Column(Float, default=100_000)
    max_amount = Column(Float, default=3_000_000)
    min_term_months = Column(Integer, default=6)
    max_term_months = Column(Integer, default=24)
    base_rate = Column(Float, default=19.5)
    max_rate = Column(Float, default=25.5)
    min_business_age_months = Column(Integer, default=6)
    requires_collateral = Column(Boolean, default=False)
    min_monthly_turnover = Column(Float, default=0.0)
    purposes_json = Column(Text, default="[]")
    features_json = Column(Text, default="[]")
    documents_json = Column(Text, default="[]")
    icon = Column(String(40), default="wallet")
    badge = Column(String(60), default="")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    number = Column(String(40), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    amount = Column(Float, nullable=False)
    term_months = Column(Integer, nullable=False)
    purpose = Column(String(190), default="")
    purpose_details = Column(String(500), default="")
    status = Column(String(30), default="draft", index=True)
    score = Column(Integer, nullable=True)
    risk_class = Column(String(4), nullable=True)
    pd_percent = Column(Float, nullable=True)
    scoring_json = Column(Text, default="")
    required_docs_json = Column(Text, default="[]")
    offer_amount = Column(Float, nullable=True)
    offer_rate = Column(Float, nullable=True)
    offer_term_months = Column(Integer, nullable=True)
    offer_monthly_payment = Column(Float, nullable=True)
    offer_comment = Column(Text, default="")
    is_counter_offer = Column(Boolean, default=False)
    offer_expires_at = Column(DateTime, nullable=True)
    decision_comment = Column(Text, default="")
    decline_reasons_json = Column(Text, default="[]")
    signature_docs_json = Column(Text, default="[]")
    credit_account = Column(String(40), default="")
    created_at = Column(DateTime, default=utcnow)
    submitted_at = Column(DateTime, nullable=True)
    decision_at = Column(DateTime, nullable=True)
    offer_accepted_at = Column(DateTime, nullable=True)
    signed_at = Column(DateTime, nullable=True)
    funded_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User")
    company = relationship("Company")
    product = relationship("Product")
    documents = relationship("Document", back_populates="application", cascade="all, delete-orphan")
    events = relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan",
                          order_by="ApplicationEvent.id")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    doc_type = Column(String(60), default="other")
    title = Column(String(190), default="")
    filename = Column(String(255), default="")
    size_kb = Column(Integer, default=0)
    status = Column(String(30), default="uploaded")  # uploaded | verified | rejected
    comment = Column(String(255), default="")
    uploaded_by_role = Column(String(20), default="client")
    created_at = Column(DateTime, default=utcnow)

    application = relationship("Application", back_populates="documents")


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    event_type = Column(String(40), default="status_change")
    from_status = Column(String(30), default="")
    to_status = Column(String(30), default="")
    title = Column(String(255), default="")
    comment = Column(Text, default="")
    actor_type = Column(String(20), default="system")  # system | client | bank
    actor_name = Column(String(190), default="Кредитный конвейер")
    visible_to_client = Column(Boolean, default=True)
    payload_json = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    application = relationship("Application", back_populates="events")


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    summary = Column(Text, default="")
    body = Column(Text, default="")
    category = Column(String(40), default="market")  # bank | market | support | product | education
    industries_json = Column(Text, default="[]")
    stage_tags_json = Column(Text, default="[]")
    source = Column(String(120), default="Альфа-Банк")
    reading_time_min = Column(Integer, default=3)
    published_at = Column(DateTime, default=utcnow)
