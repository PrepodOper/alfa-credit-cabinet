import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { dateShort, money, moneyShort, percent } from '../lib/format.js';
import Icon from '../components/Icons.jsx';

function RevenueChart({ data = [] }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.revenue)) * 1.1;
  return (
    <div>
      <div className="row" style={{ alignItems: 'flex-end', gap: 14, height: 150, padding: '10px 4px 0' }}>
        {data.map((d) => {
          const h = Math.round((d.revenue / max) * 100);
          const p = Math.round((d.profit / max) * 100);
          return (
            <div key={d.month} className="col" style={{ flex: 1, alignItems: 'center', justifyContent: 'flex-end', height: '100%', gap: 4 }}>
              <div className="tiny muted" style={{ fontSize: 10 }}>{moneyShort(d.revenue).replace(' ₽', '')}</div>
              <div style={{ width: '100%', maxWidth: 44, height: `${h}%`, borderRadius: '8px 8px 4px 4px', background: 'linear-gradient(180deg,#ff8a80,#ef3124)', position: 'relative' }}>
                <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: `${Math.max(4, (p / h) * 100)}%`, background: 'rgba(255,255,255,0.35)', borderRadius: '0 0 4px 4px' }} />
              </div>
            </div>
          );
        })}
      </div>
      <div className="row mt-8" style={{ gap: 14, padding: '0 4px' }}>
        {data.map((d) => (
          <div key={d.month} className="tiny muted" style={{ flex: 1, textAlign: 'center' }}>{d.month}</div>
        ))}
      </div>
      <div className="row gap-16 mt-12">
        <span className="row gap-8 tiny muted"><span style={{ width: 10, height: 10, borderRadius: 3, background: 'var(--red)' }} /> Выручка</span>
        <span className="row gap-8 tiny muted"><span style={{ width: 10, height: 10, borderRadius: 3, background: 'rgba(239,49,36,0.35)' }} /> Прибыль</span>
      </div>
    </div>
  );
}

function CheckRow({ ok, title, detail }) {
  return (
    <div className="row gap-12" style={{ padding: '9px 0', alignItems: 'flex-start' }}>
      <span style={{
        width: 22, height: 22, borderRadius: 7, display: 'grid', placeItems: 'center', flex: '0 0 auto',
        background: ok ? 'var(--green-soft)' : 'var(--red-soft)', color: ok ? 'var(--green)' : 'var(--red-600)',
      }}>
        <Icon name={ok ? 'check' : 'x'} size={13} />
      </span>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{title}</div>
        <div className="tiny muted" style={{ marginTop: 2 }}>{detail}</div>
      </div>
    </div>
  );
}

export default function Company() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api('/company').then(setData).catch((e) => setError(e.message));
  }, []);

  if (!data) {
    return (
      <div className="page">
        {error ? <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div> : <div className="skeleton" style={{ height: 400 }} />}
      </div>
    );
  }

  const { requisites: r, financials: f, company: snapshot } = data;
  const bki = snapshot.bki || {};
  const reg = snapshot.registry || {};

  return (
    <div className="page">
      <div className="row-between wrap" style={{ alignItems: 'flex-start', gap: 16 }}>
        <div className="row gap-16" style={{ alignItems: 'flex-start' }}>
          <div className="avatar red" style={{ width: 54, height: 54, borderRadius: 16, fontSize: 15 }}>
            {r.legal_form === 'ИП' ? 'ИП' : 'ООО'}
          </div>
          <div>
            <h1 style={{ fontSize: 25, letterSpacing: '-0.025em' }}>{r.short_name}</h1>
            <p className="muted small mt-8">{r.name}</p>
            <div className="row gap-8 mt-12 wrap">
              <span className="tag">ИНН {r.inn}</span>
              <span className="tag">ОГРН {r.ogrn}</span>
              <span className="tag"><Icon name="building" size={12} /> {r.industry}</span>
              <span className="tag"><Icon name="user" size={12} /> {r.employees_count} сотрудников</span>
              {r.has_alfa_account && <span className="pill pill-green"><span className="dot" /> Клиент Альфа-Банка</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-4 mt-24">
        <div className="card stat">
          <div className="stat-label">Средняя выручка</div>
          <div className="stat-value">{moneyShort(f.revenue_avg_monthly)}</div>
          <div className="stat-hint">в месяц · 12 мес. {moneyShort(f.revenue_12m)}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Прибыль за 12 мес.</div>
          <div className="stat-value">{moneyShort(f.net_profit_12m)}</div>
          <div className="stat-hint green">рентабельность {percent((f.net_profit_12m / f.revenue_12m) * 100)}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Платежи по кредитам</div>
          <div className="stat-value">{moneyShort(f.existing_monthly_payments)}</div>
          <div className="stat-hint">в месяц</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Обороты по счёту</div>
          <div className="stat-value">{moneyShort(f.account_turnover_monthly)}</div>
          <div className="stat-hint">{percent((f.account_turnover_monthly / Math.max(f.revenue_avg_monthly, 1)) * 100)} от выручки</div>
        </div>
      </div>

      <div className="mt-16" style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 16, alignItems: 'start' }}>
        <div className="col gap-16">
          <div className="card card-pad">
            <div className="card-head">
              <div className="card-title">Динамика выручки и прибыли</div>
              <span className="tiny muted">последние 6 месяцев</span>
            </div>
            <RevenueChart data={f.dynamics} />
          </div>

          <div className="card card-pad">
            <div className="card-title" style={{ marginBottom: 6 }}>Реквизиты и регистрационные данные</div>
            <div className="grid grid-2" style={{ gap: '0 28px' }}>
              <div>
                <div className="kv"><span>Организационная форма</span><b>{r.legal_form}</b></div>
                <div className="kv"><span>ИНН</span><b>{r.inn}</b></div>
                <div className="kv"><span>ОГРН</span><b>{r.ogrn}</b></div>
                {r.kpp && <div className="kv"><span>КПП</span><b>{r.kpp}</b></div>}
                <div className="kv"><span>Дата регистрации</span><b>{dateShort(r.founded_date)}</b></div>
                <div className="kv"><span>Основной ОКВЭД</span><b style={{ maxWidth: 220 }}>{r.okved_code} · {r.okved_name}</b></div>
              </div>
              <div>
                <div className="kv"><span>Руководитель</span><b>{r.director_name}</b></div>
                <div className="kv"><span>Адрес</span><b style={{ maxWidth: 240 }}>{r.city}, {r.address}</b></div>
                <div className="kv"><span>Телефон</span><b>{r.phone}</b></div>
                <div className="kv"><span>Email</span><b>{r.email}</b></div>
                <div className="kv"><span>Залоговое имущество</span><b>{snapshot.collateral_available ? snapshot.collateral_desc : 'нет'}</b></div>
                <div className="kv"><span>Клиент банка с</span><b>{r.alfa_client_since ? dateShort(r.alfa_client_since) : '—'}</b></div>
              </div>
            </div>
          </div>

          <div className="card card-pad">
            <div className="card-head">
              <div>
                <div className="card-title">Кредитная история</div>
                <div className="tiny muted mt-8">по данным БКИ · мок-интеграция</div>
              </div>
              <span className={`pill ${bki.bki_score >= 700 ? 'pill-green' : bki.bki_score >= 600 ? 'pill-amber' : 'pill-red'}`}>
                Скор БКИ {bki.bki_score}
              </span>
            </div>
            <div className="grid grid-3" style={{ gap: 12 }}>
              <div className="metric-mini"><span>Действующие кредиты</span><b>{bki.active_loans}</b></div>
              <div className="metric-mini"><span>Общий долг</span><b>{moneyShort(bki.total_debt)}</b></div>
              <div className="metric-mini"><span>Платёж в месяц</span><b>{moneyShort(bki.monthly_payments)}</b></div>
              <div className="metric-mini"><span>Макс. просрочка</span><b>{bki.max_delay_days_12m} дн.</b></div>
              <div className="metric-mini"><span>Просрочки за 12 мес.</span><b>{bki.delinquencies_12m}</b></div>
              <div className="metric-mini"><span>Запросы за 6 мес.</span><b>{bki.inquiries_6m}</b></div>
            </div>
            <p className="small muted mt-16" style={{ lineHeight: 1.5 }}>{bki.summary}</p>
          </div>
        </div>

        <div className="col gap-16">
          <div className="card card-pad">
            <div className="row gap-8">
              <Icon name="shield" size={18} style={{ color: 'var(--green)' }} />
              <div className="card-title">Проверка в ЕГРЮЛ и ФНС</div>
            </div>
            <div className="tiny muted mt-8">{reg.source}</div>
            <div className="mt-8">
              <CheckRow ok={reg.status === 'Действующий'} title="Статус компании" detail={reg.status} />
              <CheckRow ok={!reg.tax_debt} title="Задолженность по налогам" detail={reg.tax_debt ? 'Обнаружена задолженность ЕНС' : 'Задолженности нет'} />
              <CheckRow ok={!reg.mass_address} title="Адрес регистрации" detail={reg.mass_address ? 'Признан массовым' : 'Признаков массовости нет'} />
              <CheckRow ok={!reg.fns_violations} title="Нарушения ФНС" detail={reg.fns_violations ? 'Есть нарушения' : 'Нарушений не найдено'} />
              <CheckRow ok={!reg.director_changed_recently} title="Смена руководителя" detail={reg.director_changed_recently ? 'Руководитель менялся менее года назад' : 'Изменений нет'} />
            </div>
          </div>

          <div className="card card-pad">
            <div className="card-title">Учредители</div>
            <div className="mt-8">
              {(reg.founders || []).map((founder) => (
                <div key={founder.name} className="kv" style={{ padding: '10px 0' }}>
                  <span>{founder.name}</span><b>{founder.share}%</b>
                </div>
              ))}
            </div>
          </div>

          <div className="card card-pad" style={{ background: 'linear-gradient(160deg,#f7f9ff,#fff)' }}>
            <div className="row gap-8">
              <Icon name="sparkles" size={17} style={{ color: 'var(--blue)' }} />
              <div className="card-title">Что влияет на ваш лимит</div>
            </div>
            <div className="col gap-12 mt-12">
              {[
                ['Финансовая устойчивость', 'рентабельность и динамика выручки'],
                ['Долговая нагрузка', 'платежи по кредитам к выручке'],
                ['Кредитная история', 'дисциплина и просрочки по БКИ'],
                ['Обороты по счёту', 'стабильность денежного потока'],
              ].map(([t, d], i) => (
                <div key={t} className="row gap-12" style={{ alignItems: 'flex-start' }}>
                  <span className="avatar" style={{ width: 24, height: 24, fontSize: 11, background: 'var(--blue-soft)', color: 'var(--blue)' }}>{i + 1}</span>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{t}</div>
                    <div className="tiny muted">{d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
