import { useEffect, useState } from 'react';
import { api } from '../lib/api.js';
import { money, moneyShort, percent } from '../lib/format.js';
import Icon from '../components/Icons.jsx';

const RULES = [
  { cls: 'A', range: '800–1000', pd: '0,9%', decision: 'Автоматическое одобрение', rate: '−1,0 п.п.' },
  { cls: 'B', range: '680–799', pd: '2,4%', decision: 'Авто; ручное при сумме ≥ 1,5 млн ₽', rate: 'базовая' },
  { cls: 'C', range: '550–679', pd: '5,8%', decision: 'Ручное рассмотрение, контрпредложение', rate: '+1,5 п.п.' },
  { cls: 'D', range: '420–549', pd: '12,5%', decision: 'Ручное; контрпредложение при нагрузке ≤ 65%', rate: '+3,0 п.п.' },
  { cls: 'E', range: '0–419', pd: '24,0%', decision: 'Отказ', rate: '—' },
];

const PIPELINE_STEPS = [
  { icon: 'files', title: 'Подача', text: 'Анкета и параметры продукта, согласие на проверки' },
  { icon: 'shield', title: 'Проверки', text: 'Полнота данных, БКИ, ЕГРЮЛ, ФНС' },
  { icon: 'chart', title: 'Скоринг', text: 'Балльная модель, риск-класс, PD' },
  { icon: 'users', title: 'Решение', text: 'Автоматически или андеррайтером' },
  { icon: 'checkCircle', title: 'Выдача', text: 'Предложение, документы, зачисление' },
];

export default function BankAnalytics() {
  const [metrics, setMetrics] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api('/bank/metrics'), api('/bank/pipeline')])
      .then(([m, p]) => { setMetrics(m); setPipeline(p); })
      .catch((e) => setError(e.message));
  }, []);

  const maxCount = Math.max(1, ...(pipeline?.statuses || []).map((s) => s.count));

  return (
    <div className="page page-wide">
      <div className="page-head">
        <div>
          <h1>Аналитика конвейера</h1>
          <p>Как распределяются заявки, где подключается андеррайтер и какие правила формируют кредитное решение.</p>
        </div>
        <span className="pill pill-dark"><Icon name="chart" size={13} /> Метрики в реальном времени</span>
      </div>

      {error && <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div>}

      <div className="grid grid-4">
        <div className="card stat">
          <div className="stat-label">Всего заявок</div>
          <div className="stat-value">{metrics?.total ?? '—'}</div>
          <div className="stat-hint">{metrics?.in_queue ?? 0} в очереди андеррайтера</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Среднее время решения</div>
          <div className="stat-value">{metrics?.avg_decision_minutes ?? '—'} <span style={{ fontSize: 14, fontWeight: 500 }}>мин</span></div>
          <div className="stat-hint">SLA ручного этапа — {metrics?.sla_hours ?? 4} ч</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Автоматизация</div>
          <div className="stat-value">{percent(metrics?.auto_share ?? 0)}</div>
          <div className="stat-hint">решений без участия человека</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Портфель выдан</div>
          <div className="stat-value">{metrics ? moneyShort(metrics.portfolio) : '—'}</div>
          <div className="stat-hint red">доля отказов {percent(metrics?.decline_rate ?? 0)}</div>
        </div>
      </div>

      <div className="mt-16" style={{ display: 'grid', gridTemplateColumns: '1.35fr 1fr', gap: 16, alignItems: 'start' }}>
        <div className="card card-pad">
          <div className="row-between">
            <div>
              <div className="card-title">Воронка статусов</div>
              <div className="tiny muted mt-8">распределение заявок по этапам процесса</div>
            </div>
            <span className="pill pill-gray">в работе: {pipeline?.in_progress ?? '—'}</span>
          </div>
          <div className="funnel mt-16">
            {(pipeline?.statuses || []).map((s) => (
              <div key={s.status} className="funnel-row">
                <span className="funnel-label">{s.label}</span>
                <div className="funnel-bar">
                  <div className="funnel-fill" style={{ width: `${(s.count / maxCount) * 100}%`, opacity: s.count ? 1 : 0 }} />
                </div>
                <span className="funnel-count">{s.count}</span>
              </div>
            ))}
          </div>
          <div className="divider" />
          <div className="row gap-24 wrap">
            <div className="row gap-8 tiny muted"><Icon name="checkCircle" size={14} style={{ color: 'var(--green)' }} /> Одобрено за 30 дней: {pipeline?.approved_30d ?? 0}</div>
            <div className="row gap-8 tiny muted"><Icon name="x" size={14} style={{ color: 'var(--red)' }} /> Отказов за 30 дней: {pipeline?.declined_30d ?? 0}</div>
          </div>
        </div>

        <div className="card card-pad">
          <div className="card-title">Нагрузка и SLA</div>
          <div className="col gap-12 mt-16">
            <div className="metric-mini"><span>В очереди на решение</span><b>{metrics?.in_queue ?? 0}</b></div>
            <div className="metric-mini"><span>Нарушения SLA</span><b className={metrics?.sla_breaches ? 'text-red' : 'text-green'}>{metrics?.sla_breaches ?? 0}</b></div>
            <div className="metric-mini"><span>Доля ручных решений</span><b>{percent(metrics?.manual_share ?? 0)}</b></div>
          </div>
          <div className="divider" />
          <div className="tiny muted" style={{ lineHeight: 1.55 }}>
            В ручное рассмотрение уходят заявки риск-класса C, суммы от 1,5 млн ₽ для класса B
            и контрпредложения класса D. Остальные решения принимаются автоматически в рамках правил продукта.
          </div>
        </div>
      </div>

      <div className="card card-pad mt-16">
        <div className="row-between">
          <div>
            <div className="card-title">Модель кредитного решения</div>
            <div className="tiny muted mt-8">риск-класс определяется балльной оценкой, условия и маршрут — правилами конвейера</div>
          </div>
          <span className="pill pill-teal"><span className="dot" /> Прозрачная логика</span>
        </div>
        <div className="scroll-x mt-16">
          <table className="data-table">
            <thead>
              <tr>
                <th>Класс</th>
                <th>Диапазон баллов</th>
                <th>Ожидаемый PD</th>
                <th>Маршрут решения</th>
                <th>Корректировка ставки</th>
              </tr>
            </thead>
            <tbody>
              {RULES.map((r) => (
                <tr key={r.cls}>
                  <td>
                    <span className={`pill ${r.cls === 'A' ? 'pill-green' : r.cls === 'B' ? 'pill-teal' : r.cls === 'C' ? 'pill-amber' : r.cls === 'D' ? 'pill-orange' : 'pill-red'}`}>
                      {r.cls}
                    </span>
                  </td>
                  <td className="mono">{r.range}</td>
                  <td>{r.pd}</td>
                  <td>{r.decision}</td>
                  <td>{r.rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card card-pad mt-16">
        <div className="card-title" style={{ marginBottom: 16 }}>Путь заявки в конвейере</div>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(5, minmax(0,1fr))', gap: 12 }}>
          {PIPELINE_STEPS.map((s, i) => (
            <div key={s.title} className="card card-pad-sm" style={{ background: '#fafbfc', borderStyle: 'dashed' }}>
              <div className="row-between">
                <div className="stat-icon" style={{ background: '#fff' }}><Icon name={s.icon} size={17} /></div>
                <span className="tiny muted">0{i + 1}</span>
              </div>
              <div style={{ fontSize: 13.5, fontWeight: 650, marginTop: 10 }}>{s.title}</div>
              <div className="tiny muted" style={{ marginTop: 4, lineHeight: 1.4 }}>{s.text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
