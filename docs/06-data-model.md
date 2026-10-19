# 06 · Модель данных

## ER-диаграмма

```mermaid
erDiagram
    COMPANY ||--o{ USER : "сотрудники"
    COMPANY ||--|| CREDIT_PROFILE : "БКИ (мок)"
    COMPANY ||--|| REGISTRY_INFO : "ЕГРЮЛ/ФНС (мок)"
    COMPANY ||--o{ APPLICATION : "заявки"
    USER ||--o{ APPLICATION : "создаёт"
    PRODUCT ||--o{ APPLICATION : "по продукту"
    APPLICATION ||--o{ DOCUMENT : "документы"
    APPLICATION ||--o{ APPLICATION_EVENT : "журнал"
    PRODUCT }o--|| NEWS_ITEM : "рекомендации по продукту"

    COMPANY {
      int id PK
      string name
      string short_name
      string legal_form "ООО | ИП"
      string inn "10-12 цифр"
      string ogrn
      string kpp
      string industry
      string okved_code
      string okved_name
      bool okved_risk
      string region
      string city
      string address
      date founded_date
      int employees_count
      string director_name
      float revenue_avg_monthly
      float revenue_12m
      float net_profit_12m
      float existing_monthly_payments
      float account_turnover_monthly
      bool has_alfa_account
      date alfa_client_since
      bool collateral_available
      string collateral_desc
      text monthly_dynamics_json "6 мес.: выручка/прибыль"
      datetime created_at
    }

    USER {
      int id PK
      string email UK
      string password_hash "PBKDF2-SHA256"
      string full_name
      string role "client | bank"
      string position
      string phone
      int company_id FK
      datetime created_at
    }

    CREDIT_PROFILE {
      int id PK
      int company_id FK
      int bki_score
      int active_loans
      float total_debt
      float monthly_payments
      int max_delay_days_12m
      bool has_current_overdue
      int delinquencies_12m
      int inquiries_6m
      text summary
      datetime updated_at
    }

    REGISTRY_INFO {
      int id PK
      int company_id FK
      string status
      bool tax_debt
      bool fns_violations
      bool mass_address
      bool director_changed_recently
      text founders_json
      int employees_reported
      datetime last_update
      string source
    }

    PRODUCT {
      int id PK
      string code UK
      string name
      string tagline
      text description
      float min_amount
      float max_amount
      int min_term_months
      int max_term_months
      float base_rate
      float max_rate
      int min_business_age_months
      bool requires_collateral
      float min_monthly_turnover
      text purposes_json
      text features_json
      text documents_json
      string icon
      string badge
      int sort_order
      bool is_active
    }

    APPLICATION {
      int id PK
      string number UK
      int user_id FK
      int company_id FK
      int product_id FK
      float amount
      int term_months
      string purpose
      string purpose_details
      string status "14 состояний"
      int score
      string risk_class
      float pd_percent
      text scoring_json "факторы и рекомендации"
      text required_docs_json
      float offer_amount
      float offer_rate
      int offer_term_months
      float offer_monthly_payment
      text offer_comment
      bool is_counter_offer
      datetime offer_expires_at
      text decision_comment
      text decline_reasons_json
      text signature_docs_json
      string credit_account
      datetime created_at
      datetime submitted_at
      datetime decision_at
      datetime offer_accepted_at
      datetime signed_at
      datetime funded_at
      datetime updated_at
    }

    DOCUMENT {
      int id PK
      int application_id FK
      string doc_type
      string title
      string filename
      int size_kb
      string status "uploaded | verified | rejected"
      string comment
      string uploaded_by_role
      datetime created_at
    }

    APPLICATION_EVENT {
      int id PK
      int application_id FK
      string event_type "created | status_change | scoring | data_enrichment | decision | documents_signed | document_uploaded"
      string from_status
      string to_status
      string title
      text comment
      string actor_type "system | client | bank"
      string actor_name
      bool visible_to_client
      text payload_json
      datetime created_at
    }

    NEWS_ITEM {
      int id PK
      string title
      text summary
      text body
      string category "bank | market | support | product | education"
      text industries_json
      text stage_tags_json
      string source
      int reading_time_min
      datetime published_at
    }
```

## Решения по модели данных

1. **События вместо `status_history`-поля.** `application_events` — единственный источник истории:
   статус меняется вместе с записью события в одной операции (`workflow.move`). Это даёт аудит,
   ленту для клиента и материал для аналитики без денормализации.
2. **`offer_*` в заявке, а не отдельная таблица.** В MVP одна активная оферта на заявку; при развитии
   (несколько раундов контрпредложений) выделяется `offers` с историей.
3. **JSON-поля для справочников** (`purposes_json`, `features_json`, `scoring_json`) — гибкость MVP;
   при росте нормализуются в справочники и таблицу `scoring_runs` с версией модели.
4. **Моки внешних источников — отдельные таблицы** (`credit_profiles`, `registry_infos`), а не поля
   компании: в проде заменяются кэшем ответов внешних API с TTL и историей запросов.
5. **Деньги — `float` для демо.** В проде: `NUMERIC(15,2)`/минорные единицы, чтобы исключить
   ошибки округления.
6. **Индексы:** `users.email`, `applications.number`, `applications.status`; для продакшена
   добавить составные (`company_id, created_at`) и (`status, updated_at`).

## Миграция на PostgreSQL

Модель использует только переносимые типы. Достаточно:
1. `DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db`;
2. ввести Alembic (`alembic init`, autogenerate) и перенести `create_all` в миграции;
3. заменить `JSON`-строки на `JSONB` при необходимости индексации по содержимому.
