import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { money, moneyShort, percent, statusMeta, timeAgo } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import StatusPill from '../components/StatusPill.jsx';

const TABS = [
  { key: 'queue', label: 'Очередь' },
  { key: 'waiting', label: 'В работе' },
  { key: 'decided', label: 'Решения' },
  { key: 'all', label: 'Все' },
];

function slaText(minutes, state) {
  if (minutes === null || minutes === undefined) return '—';
  if (minutes < 0) return `просрочено ${Math.abs(Math.round(minutes / 60))} ч`;
  if (minutes < 60) return `${minutes} мин`;
  return `${Math.round(minutes / 60)} ч`;
}

export default function BankQueue() {
  const [tab, setTab] = useState('queue');
  const [search, setSearch] = useState('');
  const [data, setData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    let alive = true;
    const params = new URLSearchParams({ tab, search });
    Promise.all([api(`/bank/tasks?${params}`), api('/bank/metrics')])
      .then(([tasks, m]) => {
        if (!alive) return;
        setData(tasks);
        setMetrics(m);
      })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [tab, search]);

  return (
    <div className="page page-wide">
      <div className="page-head">
        <div>
          <h1>Очередь заявок</h1>
          <p>
            Рабочее место андеррайтера: заявки, которым нужно решение, карточка клиента,
            результаты скоринга и полная история процесса.
          </p>
        </div>
        <span className="pill pill-dark"><Icon name="shield" size={13} /> Роль: андеррайтер МСБ</span>
      </div>

      {error && <div className="banner banner-danger" style={{ marginBottom: 16 }}><Icon name="alert" size={16} />{error}</div>}

      <div className="grid grid-4" style={{ marginBottom: 16 }}>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">В очереди</div>
            <div className="stat-icon" style={{ background: 'var(--red-soft)', color: 'var(--red)' }}><Icon name="files" size={17} /></div>
          </div>
          <div className="stat-value">{metrics?.in_queue ?? '—'}</div>
          <div className={`stat-hint ${metrics?.sla_breaches ? 'red' : ''}`}>
            {metrics?.sla_breaches ? `${metrics.sla_breaches} с нарушением SLA` : `SLA ${metrics?.sla_hours ?? 4} ч соблюдается`}
          </div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Среднее решение</div>
            <div className="stat-icon"><Icon name="clock" size={17} /></div>
          </div>
          <div className="stat-value">{metrics?.avg_decision_minutes ?? '—'} <span style={{ fontSize: 14, fontWeight: 500 }}>мин</span></div>
          <div className="stat-hint">от отправки до решения</div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Автоматические решения</div>
            <div className="stat-icon"><Icon name="bolt" size={17} /></div>
          </div>
          <div className="stat-value">{percent(metrics?.auto_share ?? 0)}</div>
          <div className="stat-hint">доля без участия человека</div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Портфель выдан</div>
            <div className="stat-icon"><Icon name="wallet" size={17} /></div>
          </div>
          <div className="stat-value">{metrics ? moneyShort(metrics.portfolio) : '—'}</div>
          <div className="stat-hint">доля отказов {percent(metrics?.decline_rate ?? 0)}</div>
        </div>
      </div>

      <div className="card">
        <div className="row-between wrap" style={{ padding: '14px 16px', gap: 12 }}>
          <div className="bank-tabs">
            {TABS.map((t) => (
              <button key={t.key} className={`bank-tab ${tab === t.key ? 'active' : ''}`} onClick={() => setTab(t.key)}>
                {t.label}
                {t.key !== 'all' && <span className="count-chip">{data?.counts?.[t.key] ?? 0}</span>}
              </button>
            ))}
          </div>
          <div className="input-group" style={{ width: 300, maxWidth: '100%' }}>
            <input
              className="input" placeholder="Поиск по номеру, компании, ИНН" value={search}
              onChange={(e) => setSearch(e.target.value)} style={{ paddingLeft: 38 }}
            />
            <span style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--muted-2)' }}>
              <Icon name="search" size={16} />
            </span>
          </div>
        </div>

        {!data ? (
          <div style={{ padding: 20 }}>{[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 46, marginBottom: 10 }} />)}</div>
        ) : data.items.length === 0 ? (
          <div className="empty">
            <div className="empty-icon"><Icon name="checkCircle" size={24} /></div>
            <h3>Очередь пуста</h3>
            <p>Новые заявки появятся здесь автоматически после скоринга.</p>
          </div>
        ) : (
          <div>
            <div className="queue-row" style={{ background: '#fafbfc', cursor: 'default', borderTop: '1px solid var(--line-2)' }}>
              <span className="tiny muted">Клиент / заявка</span>
              <span className="tiny muted">Продукт и сумма</span>
              <span className="tiny muted">Скоринг</span>
              <span className="tiny muted">SLA</span>
              <span className="tiny muted">Статус</span>
              <span />
            </div>
            {data.items.map((t) => (
              <div key={t.id} className="queue-row" onClick={() => navigate(`/bank/applications/${t.id}`)}>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 650 }}>{t.company_name}</div>
                  <div className="tiny muted" style={{ marginTop: 2 }}>{t.number} · {timeAgo(t.submitted_at || t.created_at)}</div>
                </div>
                <div>
                  <div style={{ fontSize: 13.5, fontWeight: 600 }}>{money(t.amount)}</div>
                  <div className="tiny muted" style={{ marginTop: 2 }}>{t.product_name} · {t.term_months} мес.</div>
                </div>
                <div className="row gap-8">
                  <span className={`pill ${t.risk_class === 'A' ? 'pill-green' : t.risk_class === 'B' ? 'pill-teal' : t.risk_class === 'C' ? 'pill-amber' : 'pill-red'}`}>
                    {t.score ?? '—'}
                  </span>
                  <span className="tiny muted">{t.risk_class || ''}</span>
                </div>
                <div className={`sla ${t.sla_state}`}>
                  {slaText(t.sla_minutes, t.sla_state)}
                </div>
                <div><StatusPill status={t.status} /></div>
                <Icon name="chevronRight" size={16} style={{ color: 'var(--muted-2)' }} />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="row gap-16 mt-16 wrap">
        <span className="tiny muted row gap-8"><Icon name="info" size={14} /> Ручное рассмотрение включается для пограничного риск-класса и крупных сумм.</span>
        <span className="tiny muted row gap-8"><Icon name="clock" size={14} /> SLA на решение андеррайтера — 4 часа.</span>
      </div>
    </div>
  );
}
