"""Синтетические демонстрационные данные.

Все компании, ИНН, сотрудники и финансовые показатели — вымышленные.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import (Application, ApplicationEvent, Company, CreditProfile, Document, NewsItem,
                     Product, RegistryInfo, User)
from .security import hash_password
from .services.scoring import annuity_payment

DEMO_PASSWORD = "demo1234"


def _money(x: float) -> float:
    return round(float(x), 2)


def seed_database(db: Session) -> None:
    if db.query(Product).count() > 0:
        return

    # ------------------------------------------------------------------ products
    products = [
        Product(
            code="working_capital", name="Оборотный кредит",
            tagline="Пополнить оборотные средства и закрыть кассовые разрывы",
            description="Классический кредит на текущую деятельность: закупка товара, выплаты поставщикам, "
                        "зарплаты и другие операционные задачи. Решение автоматическое — по анкете и данным банка.",
            min_amount=300_000, max_amount=3_000_000, min_term_months=6, max_term_months=24,
            base_rate=18.9, max_rate=24.9, min_business_age_months=6, requires_collateral=False,
            min_monthly_turnover=0,
            purposes_json=json.dumps(["Закупка товара", "Оборотные средства", "Зарплаты и налоги",
                                      "Маркетинг и продвижение"], ensure_ascii=False),
            features_json=json.dumps(["Решение за 5 минут", "Без залога", "Досрочное погашение без комиссии",
                                      "График платежей в кабинете"], ensure_ascii=False),
            documents_json=json.dumps(["Анкета заявки", "Устав (или паспорт для ИП)",
                                       "Справка об оборотах, если счёта в Альфа-Банке нет"], ensure_ascii=False),
            icon="refresh", badge="Хит", sort_order=1,
        ),
        Product(
            code="express", name="Экспресс-кредит",
            tagline="До 1 млн ₽ по упрощённой анкете — для микробизнеса",
            description="Быстрое финансирование небольших сумм. Подходит, чтобы закрыть срочную потребность "
                        "без подготовки большого пакета документов.",
            min_amount=50_000, max_amount=1_000_000, min_term_months=3, max_term_months=12,
            base_rate=21.9, max_rate=27.9, min_business_age_months=3, requires_collateral=False,
            min_monthly_turnover=0,
            purposes_json=json.dumps(["Оборотные средства", "Оборудование", "Ремонт", "Маркетинг"],
                                     ensure_ascii=False),
            features_json=json.dumps(["Только 3 документа", "Деньги на счёт в день обращения",
                                      "Без залога и поручителей"], ensure_ascii=False),
            documents_json=json.dumps(["Анкета", "Паспорт руководителя"], ensure_ascii=False),
            icon="bolt", badge="Быстро", sort_order=2,
        ),
        Product(
            code="investment", name="Инвестиционный кредит",
            tagline="До 15 млн ₽ на оборудование, помещения и расширение",
            description="Финансирование развития бизнеса: покупка оборудования и транспорта, ремонт "
                        "и покупка помещений, запуск новых направлений. Требует залога и финансовой отчётности.",
            min_amount=1_000_000, max_amount=15_000_000, min_term_months=12, max_term_months=60,
            base_rate=16.5, max_rate=22.5, min_business_age_months=12, requires_collateral=True,
            min_monthly_turnover=0,
            purposes_json=json.dumps(["Оборудование", "Недвижимость", "Расширение производства", "Транспорт"],
                                      ensure_ascii=False),
            features_json=json.dumps(["До 60 месяцев", "Ставка ниже на 2 п.п. при залоге",
                                      "Индивидуальный график платежей", "Отсрочка платежей до 6 месяцев"],
                                     ensure_ascii=False),
            documents_json=json.dumps(["Анкета", "Финансовая отчётность за 12 месяцев",
                                       "Документы на залог", "Бизнес-план проекта"], ensure_ascii=False),
            icon="building", badge="До 15 млн", sort_order=3,
        ),
        Product(
            code="overdraft", name="Овердрафт",
            tagline="Возобновляемая кредитная линия для ежедневных расчётов",
            description="Кредитная линия к расчётному счёту в Альфа-Банке: закрывает короткие кассовые "
                        "разрывы, проценты начисляются только за фактическое использование лимита.",
            min_amount=100_000, max_amount=1_500_000, min_term_months=6, max_term_months=12,
            base_rate=19.5, max_rate=25.5, min_business_age_months=6, requires_collateral=False,
            min_monthly_turnover=500_000,
            purposes_json=json.dumps(["Кассовый разрыв", "Платежи поставщикам", "Зарплаты"], ensure_ascii=False),
            features_json=json.dumps(["Проценты только за фактическое использование", "Возобновляемый лимит",
                                      "Требуется расчётный счёт в Альфа-Банке"], ensure_ascii=False),
            documents_json=json.dumps(["Анкета", "Договор банковского счёта"], ensure_ascii=False),
            icon="card", badge="Для клиентов банка", sort_order=4,
        ),
    ]
    db.add_all(products)
    db.flush()

    # ------------------------------------------------------------------ companies
    vesna = Company(
        name='Общество с ограниченной ответственностью «Кофейня Весна»', short_name="Кофейня «Весна»",
        legal_form="ООО", inn="7704123456", ogrn="1217700123456", kpp="770401001",
        industry="Общественное питание", okved_code="56.10", okved_name="Деятельность ресторанов и кафе",
        okved_risk=False, region="г. Москва", city="Москва", address="ул. Большая Никитская, 14с1",
        founded_date=date(2021, 4, 12), employees_count=14, director_name="Соколова Анна Петровна",
        phone="+7 (495) 123-45-67", email="hello@vesna-coffee.ru",
        revenue_avg_monthly=1_850_000, revenue_12m=22_200_000, net_profit_12m=2_109_000,
        existing_monthly_payments=65_000, account_turnover_monthly=1_600_000,
        has_alfa_account=True, alfa_client_since=date(2022, 2, 1),
        collateral_available=True, collateral_desc="Оборудование кухни, 1,4 млн ₽",
        monthly_dynamics_json=json.dumps([
            {"month": "май", "revenue": 1_680_000, "profit": 190_000},
            {"month": "июн", "revenue": 1_720_000, "profit": 205_000},
            {"month": "июл", "revenue": 1_880_000, "profit": 240_000},
            {"month": "авг", "revenue": 1_910_000, "profit": 255_000},
            {"month": "сен", "revenue": 1_970_000, "profit": 268_000},
            {"month": "окт", "revenue": 2_040_000, "profit": 282_000},
        ], ensure_ascii=False),
    )
    stroi = Company(
        name='Индивидуальный предприниматель Морозов Пётр Сергеевич', short_name="ИП Морозов П.С. «СтройМастер»",
        legal_form="ИП", inn="502734567890", ogrn="323500012345678",
        industry="Строительство", okved_code="43.21", okved_name="Производство электромонтажных работ",
        okved_risk=False, region="Московская область", city="Красногорск",
        address="ул. Центральная, 8, офис 3",
        founded_date=date(2023, 9, 5), employees_count=8, director_name="Морозов Пётр Сергеевич",
        phone="+7 (916) 555-21-08", email="petr@stroymaster.ru",
        revenue_avg_monthly=720_000, revenue_12m=8_640_000, net_profit_12m=604_800,
        existing_monthly_payments=130_000, account_turnover_monthly=500_000,
        has_alfa_account=False,
        collateral_available=False,
        monthly_dynamics_json=json.dumps([
            {"month": "май", "revenue": 690_000, "profit": 48_000},
            {"month": "июн", "revenue": 705_000, "profit": 52_000},
            {"month": "июл", "revenue": 725_000, "profit": 50_000},
            {"month": "авг", "revenue": 740_000, "profit": 55_000},
            {"month": "сен", "revenue": 710_000, "profit": 47_000},
            {"month": "окт", "revenue": 760_000, "profit": 58_000},
        ], ensure_ascii=False),
    )
    tehnopark = Company(
        name='Общество с ограниченной ответственностью «ТехноПарк»', short_name="ООО «ТехноПарк»",
        legal_form="ООО", inn="7801456789", ogrn="1247800098765", kpp="780101001",
        industry="ИТ и связь", okved_code="62.01", okved_name="Разработка компьютерного программного обеспечения",
        okved_risk=False, region="г. Санкт-Петербург", city="Санкт-Петербург",
        address="Невский проспект, 92",
        founded_date=date(2024, 6, 20), employees_count=11, director_name="Ветров Илья Андреевич",
        phone="+7 (812) 400-11-22", email="finance@tehnopark.dev",
        revenue_avg_monthly=1_200_000, revenue_12m=14_400_000, net_profit_12m=432_000,
        existing_monthly_payments=320_000, account_turnover_monthly=900_000,
        has_alfa_account=True, alfa_client_since=date(2024, 8, 1),
        collateral_available=False,
        monthly_dynamics_json=json.dumps([
            {"month": "май", "revenue": 1_310_000, "profit": 52_000},
            {"month": "июн", "revenue": 1_270_000, "profit": 44_000},
            {"month": "июл", "revenue": 1_220_000, "profit": 36_000},
            {"month": "авг", "revenue": 1_180_000, "profit": 30_000},
            {"month": "сен", "revenue": 1_150_000, "profit": 25_000},
            {"month": "окт", "revenue": 1_130_000, "profit": 22_000},
        ], ensure_ascii=False),
    )
    db.add_all([vesna, stroi, tehnopark])
    db.flush()

    profiles = [
        CreditProfile(company_id=vesna.id, bki_score=794, active_loans=1, total_debt=640_000,
                      monthly_payments=65_000, max_delay_days_12m=0, has_current_overdue=False,
                      delinquencies_12m=0, inquiries_6m=1,
                      summary="Дисциплинированный заёмщик: 1 действующий кредит, просрочек нет."),
        CreditProfile(company_id=stroi.id, bki_score=592, active_loans=2, total_debt=1_450_000,
                      monthly_payments=130_000, max_delay_days_12m=21, has_current_overdue=False,
                      delinquencies_12m=2, inquiries_6m=3,
                      summary="Умеренный риск: 2 кредита, две просрочки до 21 дня за год."),
        CreditProfile(company_id=tehnopark.id, bki_score=521, active_loans=3, total_debt=3_800_000,
                      monthly_payments=320_000, max_delay_days_12m=38, has_current_overdue=False,
                      delinquencies_12m=3, inquiries_6m=5,
                      summary="Повышенный риск: высокая долговая нагрузка, систематические задержки."),
    ]
    registries = [
        RegistryInfo(company_id=vesna.id, status="Действующий", tax_debt=False, fns_violations=False,
                     mass_address=False, director_changed_recently=False,
                     founders_json=json.dumps([{"name": "Соколова Анна Петровна", "share": 70},
                                               {"name": "Григорьев Олег Ильич", "share": 30}],
                                              ensure_ascii=False), employees_reported=14),
        RegistryInfo(company_id=stroi.id, status="Действующий", tax_debt=False, fns_violations=False,
                     mass_address=False, director_changed_recently=False,
                     founders_json=json.dumps([{"name": "Морозов Пётр Сергеевич", "share": 100}],
                                              ensure_ascii=False), employees_reported=8),
        RegistryInfo(company_id=tehnopark.id, status="Действующий", tax_debt=False, fns_violations=False,
                     mass_address=False, director_changed_recently=True,
                     founders_json=json.dumps([{"name": "Ветров Илья Андреевич", "share": 60},
                                               {"name": "ООО «Инвест-Софт»", "share": 40}],
                                              ensure_ascii=False), employees_reported=11),
    ]
    db.add_all(profiles + registries)
    db.flush()

    # ------------------------------------------------------------------ users
    users = [
        User(email="ivan@vesna.ru", password_hash=hash_password(DEMO_PASSWORD),
             full_name="Соколова Анна Петровна", role="client", position="Собственник и генеральный директор",
             phone="+7 (495) 123-45-67", company_id=vesna.id),
        User(email="petr@stroymaster.ru", password_hash=hash_password(DEMO_PASSWORD),
             full_name="Морозов Пётр Сергеевич", role="client", position="Индивидуальный предприниматель",
             phone="+7 (916) 555-21-08", company_id=stroi.id),
        User(email="anna@tehnopark.ru", password_hash=hash_password(DEMO_PASSWORD),
             full_name="Ветров Илья Андреевич", role="client", position="Генеральный директор",
             phone="+7 (812) 400-11-22", company_id=tehnopark.id),
        User(email="underwriter@alfabank.ru", password_hash=hash_password(DEMO_PASSWORD),
             full_name="Кузнецов Дмитрий Олегович", role="bank", position="Андеррайтер МСБ"),
        User(email="manager@alfabank.ru", password_hash=hash_password(DEMO_PASSWORD),
             full_name="Егорова Мария Викторовна", role="bank", position="Клиентский менеджер МСБ"),
    ]
    db.add_all(users)
    db.flush()

    # ------------------------------------------------------------------ демонстрационная история
    working = next(p for p in products if p.code == "working_capital")
    seeded_app = Application(
        number="ALF-KL-260914",
        user_id=users[0].id, company_id=vesna.id, product_id=working.id,
        amount=640_000, term_months=12, purpose="Закупка товара",
        purpose_details="Закупка кофе и расходных материалов на сезон",
        status="funded", score=690, risk_class="B", pd_percent=2.4,
        offer_amount=640_000, offer_rate=18.4, offer_term_months=12,
        offer_monthly_payment=round(annuity_payment(640_000, 18.4, 12), 2),
        decision_comment="Одобрено автоматически",
        credit_account="40817810099910004321",
        created_at=datetime.utcnow() - timedelta(days=35),
        submitted_at=datetime.utcnow() - timedelta(days=35),
        decision_at=datetime.utcnow() - timedelta(days=35, minutes=-4),
        offer_accepted_at=datetime.utcnow() - timedelta(days=35, minutes=-9),
        signed_at=datetime.utcnow() - timedelta(days=35, minutes=-14),
        funded_at=datetime.utcnow() - timedelta(days=35, minutes=-16),
    )
    db.add(seeded_app)
    db.flush()
    db.add_all([
        ApplicationEvent(application_id=seeded_app.id, event_type="created", title="Заявка создана",
                         to_status="draft", actor_type="client", actor_name="Соколова Анна Петровна",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=20)),
        ApplicationEvent(application_id=seeded_app.id, event_type="status_change", title="Заявка отправлена в банк",
                         from_status="draft", to_status="submitted", actor_type="client",
                         actor_name="Соколова Анна Петровна",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=19)),
        ApplicationEvent(application_id=seeded_app.id, event_type="status_change", title="Скоринг завершён",
                         from_status="scoring", to_status="offer_issued", actor_type="system",
                         actor_name="Кредитный конвейер", comment="Балл 690/1000, риск-класс B",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=14)),
        ApplicationEvent(application_id=seeded_app.id, event_type="offer_issued", title="Предложение сформировано",
                         actor_type="system", actor_name="Кредитный конвейер",
                         comment="Сумма 640 000 ₽, ставка 18,4%, срок 12 мес.",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=14)),
        ApplicationEvent(application_id=seeded_app.id, event_type="status_change", title="Клиент принял предложение",
                         from_status="offer_issued", to_status="offer_accepted", actor_type="client",
                         actor_name="Соколова Анна Петровна",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=10)),
        ApplicationEvent(application_id=seeded_app.id, event_type="status_change", title="Документы подписаны",
                         from_status="offer_accepted", to_status="signed", actor_type="client",
                         actor_name="Соколова Анна Петровна",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=8)),
        ApplicationEvent(application_id=seeded_app.id, event_type="status_change", title="Кредит выдан",
                         from_status="signed", to_status="funded", actor_type="system",
                         actor_name="Кредитный конвейер",
                         comment="Средства зачислены на расчётный счёт 40817810099910004321",
                         created_at=datetime.utcnow() - timedelta(days=35, minutes=6)),
    ])
    db.add(Document(application_id=seeded_app.id, doc_type="charter", title="Устав ООО «Кофейня Весна»",
                    filename="ustav_vesna.pdf", size_kb=1240, status="verified", uploaded_by_role="client",
                    created_at=datetime.utcnow() - timedelta(days=35, minutes=18)))
    db.add(Document(application_id=seeded_app.id, doc_type="financials", title="Оборотно-сальдовая ведомость",
                    filename="osv_2026.xlsx", size_kb=86, status="verified", uploaded_by_role="client",
                    created_at=datetime.utcnow() - timedelta(days=35, minutes=17)))

    # ------------------------------------------------------------------ news
    now = datetime.utcnow()
    news = [
        dict(title="Ставки по кредитам для МСП в октябре 2026: что изменилось", category="market",
             summary="Разбираем динамику ставок для малого бизнеса и что она означает для заёмщиков с разным риском.",
             body="Ключевая ставка стабилизировалась, и банки постепенно пересматривают условия по кредитам МСП. "
                  "Для заёмщиков с положительной историей снижение может составить 0,5–1,5 п.п. "
                  "Обратите внимание: итоговая ставка зависит не только от рынка, но и от риск-профиля, "
                  "залога и продукта.",
             industries_json=json.dumps(["all"], ensure_ascii=False), stage_tags_json=json.dumps(["new", "in_process", "has_offer"], ensure_ascii=False),
             source="Альфа-Банк · Аналитика МСБ", reading_time_min=4, published_at=now - timedelta(hours=3)),
        dict(title="Альфа-Банк снизил ставку по «Оборотному кредиту» для общепита", category="bank",
             summary="Сезонное предложение для кафе и ресторанов: ставка от 17,9% при подаче заявки до 15 ноября.",
             body="Для компаний отрасли «Общественное питание» доступна скидка 1 п.п. к базовой ставке по "
                  "«Оборотному кредиту». Предложение действует для действующих клиентов банка при подтверждённых "
                  "оборотах от 1 млн ₽ в месяц.",
             industries_json=json.dumps(["Общественное питание"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Альфа-Банк", reading_time_min=2, published_at=now - timedelta(hours=9)),
        dict(title="Сезонный спад в общепите: как подготовить денежный поток к ноябрю", category="education",
             summary="Три приёма, которые помогают кафе сохранить ликвидность в низкий сезон.",
             body="Планируйте закупки на основе скользящей средней за 6 недель, зафиксируйте поставщиков с "
                  "отсрочкой и держите резерв на 2 недели расходов. Если разрыв всё же возникает, овердрафт "
                  "дешевле, чем краткосрочный кредит на полную сумму.",
             industries_json=json.dumps(["Общественное питание"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "has_offer", "funded"], ensure_ascii=False),
             source="Альфа-Банк · База знаний", reading_time_min=5, published_at=now - timedelta(days=1, hours=2)),
        dict(title="Субсидированные программы для МСП в 2026 году", category="support",
             summary="Кто может получить льготный кредит по госпрограмме и какие документы понадобятся.",
             body="В 2026 году сохраняются программы льготного кредитования для приоритетных отраслей: "
                  "производство, логистика, общепит, ИТ. Банк проверяет соответствие требованиям программы "
                  "на этапе обработки заявки — отдельный пакет документов обычно не нужен.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Минэкономразвития · обзор", reading_time_min=6, published_at=now - timedelta(days=1, hours=7)),
        dict(title="Что банк проверяет при выдаче кредита: 7 факторов", category="education",
             summary="Почему одинаковый платёж по-разному влияет на решение для разных продуктов.",
             body="Банк смотрит на финансовую устойчивость, долговую нагрузку, кредитную историю, срок ведения "
                  "бизнеса, обороты по счёту, соответствие продукту и деловую репутацию. Итоговое решение "
                  "принимается по совокупности факторов, а не по одному показателю.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Альфа-Банк · База знаний", reading_time_min=6, published_at=now - timedelta(days=2)),
        dict(title="Заявка на овердрафт теперь занимает 7 минут", category="product",
             summary="Обновили сценарий: лимит рассчитывается автоматически по оборотам за последние 6 месяцев.",
             body="Предпринимателям больше не нужно прикладывать справки об оборотах — банк использует данные "
                  "расчётного счёта. Предварительный лимит показывается до подачи заявки.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "funded"], ensure_ascii=False),
             source="Альфа-Банк · Продукты", reading_time_min=3, published_at=now - timedelta(days=2, hours=5)),
        dict(title="Строительному бизнесу: кредит на технику под залог", category="product",
             summary="До 15 млн ₽ на спецтехнику и оборудование со ставкой от 16,5%.",
             body="Залогом может выступать приобретаемая техника. Первоначальный взнос — от 15%, срок — до 60 "
                  "месяцев, возможна отсрочка первого платежа до 3 месяцев.",
             industries_json=json.dumps(["Строительство"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Альфа-Банк · Продукты", reading_time_min=3, published_at=now - timedelta(days=3, hours=2)),
        dict(title="ФНС обновила сервис сверки ЕНС для малого бизнеса", category="support",
             summary="Как быстро проверить задолженность и избежать неприятных сюрпризов при рассмотрении заявки.",
             body="В личном кабинете ФНС появился расширенный отчёт по единому налоговому счёту. "
                  "Проверьте отсутствие задолженности перед подачей заявки — это один из автоматических "
                  "стоп-факторов при скоринге.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="ФНС России", reading_time_min=2, published_at=now - timedelta(days=3, hours=8)),
        dict(title="Как снизить долговую нагрузку перед новой заявкой", category="education",
             summary="Что можно сделать уже сейчас, чтобы повысить шансы на одобрение.",
             body="Закройте мелкие дорогие кредиты, реструктурируйте платежи неравномерным графиком, "
                  "подтвердите стабильную выручку выпиской. Нагрузка до 40% выручки воспринимается как "
                  "комфортная, выше 60% — как повышенный риск.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["in_process"], ensure_ascii=False),
             source="Альфа-Банк · База знаний", reading_time_min=4, published_at=now - timedelta(days=4)),
        dict(title="Что происходит с заявкой на этапе скоринга", category="bank",
             summary="Заглядываем внутрь конвейера: какие данные участвуют в оценке и сколько это занимает.",
             body="Система проверяет полноту анкеты, подтягивает данные БКИ, ЕГРЮЛ и ФНС, считает балльную оценку "
                  "и передаёт заявку в кредитную логику. Автоматическое решение занимает минуты; сложные "
                  "случаи уходят андеррайтеру.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["in_process"], ensure_ascii=False),
             source="Альфа-Банк · Кредитный конвейер", reading_time_min=3, published_at=now - timedelta(days=4, hours=6)),
        dict(title="Ключевая ставка и кредиты МСП: куда движется рынок", category="market",
             summary="Мнение аналитиков: чего ждать бизнесу в четвёртом квартале.",
             body="Смягчение денежно-кредитной политики отражается на стоимости фондирования с задержкой "
                  "1–2 квартала. Бизнесу с инвестиционными планами выгоднее фиксировать ставку сейчас, "
                  "а не ждать дальнейшего снижения.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "has_offer"], ensure_ascii=False),
             source="Альфа-Банк · Аналитика МСБ", reading_time_min=5, published_at=now - timedelta(days=5)),
        dict(title="Оборудование в лизинг или кредит: что выбрать", category="education",
             summary="Сравнение двух способов финансирования инвестиций для малого бизнеса.",
             body="Лизинг ускоряет получение техники и сохраняет оборотный капитал, но итоговая переплата "
                  "обычно выше. Кредит даёт владение активом и возможность залога для следующих займов.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Альфа-Банк · База знаний", reading_time_min=5, published_at=now - timedelta(days=5, hours=9)),
        dict(title="Альфа-Банк выдал более 1 трлн рублей кредитов малому бизнесу", category="bank",
             summary="Историческая веха и что она значит для клиентов: скорость решений и новые продукты.",
             body="Более 1 трлн рублей кредитов малому бизнесу — результат развития цифрового конвейера. "
                  "Средняя скорость принятия решения по типовым заявкам сократилась до нескольких минут.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "has_offer", "funded"], ensure_ascii=False),
             source="Альфа-Банк · Новости", reading_time_min=2, published_at=now - timedelta(days=6)),
        dict(title="ИТ-компаниям: кредит на разработку и закупку оборудования", category="product",
             summary="Как финансировать hardware и команду, не размывая доли инвесторов.",
             body="Для ИТ-компаний доступны кредитные продукты без залога при подтверждённых контрактах. "
                  "Банк учитывает выручку по договорам подряда и регулярные поступления.",
             industries_json=json.dumps(["ИТ и связь"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process"], ensure_ascii=False),
             source="Альфа-Банк · Продукты", reading_time_min=3, published_at=now - timedelta(days=6, hours=10)),
        dict(title="Как пройти верификацию документов с первого раза", category="education",
             summary="Четыре частые ошибки в документах, из-за которых сдвигается решение по заявке.",
             body="Проверьте срок действия документов, читаемость сканов, совпадение подписей и отсутствие "
                  "устаревших редакций устава. Файлы лучше загружать в PDF или XLSX без пароля.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["info_requested"], ensure_ascii=False),
             source="Альфа-Банк · База знаний", reading_time_min=4, published_at=now - timedelta(days=7)),
        dict(title="Что делать после одобрения: пошаговый чек-лист", category="support",
             summary="Проверьте условия, подпишите документы и убедитесь, что счёт готов к зачислению.",
             body="1. Сверьте сумму, ставку и график платежей. 2. Убедитесь, что реквизиты верны. "
                  "3. Подпишите документы в кабинете. 4. Проверьте поступление средств. 5. Настройте напоминание "
                  "о первом платеже.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["has_offer"], ensure_ascii=False),
             source="Альфа-Банк · Поддержка", reading_time_min=3, published_at=now - timedelta(days=8)),
        dict(title="Отсрочка платежей по кредиту: когда банк может её предоставить", category="support",
             summary="Условия и порядок обращения за кредитными каникулами для малого бизнеса.",
             body="Отсрочка доступна при временном снижении выручки. Решение принимается индивидуально; "
                  "в кабинете можно оставить заявку и приложить подтверждающие документы.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["funded"], ensure_ascii=False),
             source="Альфа-Банк · Поддержка", reading_time_min=3, published_at=now - timedelta(days=9)),
        dict(title="Розничной торговле: кредитная линия под сезонный запас", category="product",
             summary="Гибкий лимит под закупку товара к высокому сезону.",
             body="Возобновляемая линия позволяет выбирать лимит частями по мере закупок и платить проценты "
                  "только за использованную сумму.",
             industries_json=json.dumps(["Розничная торговля", "Общественное питание"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "has_offer"], ensure_ascii=False),
             source="Альфа-Банк · Продукты", reading_time_min=3, published_at=now - timedelta(days=10)),
        dict(title="Пять цифровых сервисов для предпринимателя этой осенью", category="product",
             summary="Сервисы, которые снимают рутину: от аналитики до подготовки документов.",
             body="В подборке — инструменты для контроля денежного потока, электронного документооборота, "
                  "проверки контрагентов и подготовки заявок. Все они доступны в экосистеме банка.",
             industries_json=json.dumps(["all"], ensure_ascii=False),
             stage_tags_json=json.dumps(["new", "in_process", "funded"], ensure_ascii=False),
             source="Альфа-Банк · Дайджест", reading_time_min=4, published_at=now - timedelta(days=11)),
    ]
    db.add_all([NewsItem(**item) for item in news])

    db.commit()
