import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api.js';
import { dateShort, dateTime, money, moneyShort, percent, riskClassLabel } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import StatusPill from '../components/StatusPill.jsx';
import ScoreRing from '../components/ScoreRing.jsx';
import { useToast } from '../components/Toast.jsx';
import PaymentSchedule from '../components/PaymentSchedule.jsx';

const ACTIONS = [
  { key: 'approve', label: 'Одобрить', icon: 'check', tone: 'green' },
  { key: 'counter_offer', label: 'Контрпредложение', icon: 'refresh', tone: 'amber' },
  { key: 'request_info', label: 'Запросить уточнения', icon: 'alert', tone: 'blue' },
  { key: 'decline', label: 'Отказать', icon: 'x', tone: 'red' },
];

const DECLINE_REASONS = [
  'Долговая нагрузка выше допустимой',
  'Недостаточная кредитная история',
  'Финансовые показатели нестабильны',
  'Не подтверждено обеспечение по продукту',
  'Сомнительные данные в ЕГРЮЛ / ФНС',
  'Не соответствует требованиям продукта',
];

function MiniBars({ data = [] }) {
  if (!data.length) return null;
  const max = Math.max(...data.map((d) => d.revenue));
  return (
    <div className="row" style={{ alignItems: 'flex-end', gap: 8, height: 56 }}>
      {data.map((d) => (
        <div key={d.month} title={`${d.month}: ${money(d.revenue)}`} style={{ flex: 1, height: `${Math.round((d.revenue / max) * 100)}%`, background: 'linear-gradient(180deg,#ff9287,#ef3124)', borderRadius: 5, minHeight: 8 }} />
      ))}
    </div>
  );
}

function Check({ ok, label, detail }) {
  return (
    <div className="row gap-8" style={{ padding: '6px 0', alignItems: 'flex-start' }}>
      <Icon name={ok ? 'checkCircle' : 'alert'} size={15} style={{ color: ok ? 'var(--green)' : 'var(--red-600)', flex: '0 0 auto', marginTop: 1 }} />
      <div>
        <div style={{ fontSize: 12.5, fontWeight: 600 }}>{label}</div>
        {detail && <div className="tiny muted">{detail}</div>}
      </div>
    </div>
  );
}

export default function BankApplication() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState('');
  const [action, setAction] = useState('approve');
  const [amount, setAmount] = useState('');
  const [rate, setRate] = useState('');
  const [term, setTerm] = useState('');
  const [comment, setComment] = useState('');
  const [reasons, setReasons] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api(`/bank/applications/${id}`);
      setApp(data);
      setError('');
      const s = data.scoring || {};
      setAmount(String(Math.round(s.recommended_amount ?? data.amount)));
      setRate(String(s.recommended_rate ?? data.product.base_rate));
      setTerm(String(s.recommended_term_months ?? data.term_months));
    } catch (e) {
      setError(e.message);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  const scoring = app?.scoring;
  const client = app?.client;
  const canDecide = ['manual_review', 'client_info_provided'].includes(app?.status);
  const conditionsChanged = app ? (Number(amount) !== app.amount || Number(term) !== app.term_months) : false;
  const riskTone = useMemo(() => ({ A: 'pill-green', B: 'pill-teal', C: 'pill-amber', D: 'pill-orange', E: 'pill-red' }), []);

  if (!app) {
    return (
      <div className="page">
        {error ? <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div> : <div className="skeleton" style={{ height: 480 }} />}
      </div>
    );
  }

  async function submitDecision() {
    setBusy(true);
    setError('');
    const body = { action, comment };
    if (action === 'approve' || action === 'counter_offer') {
      body.offer_amount = Number(amount);
      body.offer_rate = Number(rate);
      body.offer_term_months = Number(term);
    }
    if (action === 'decline') body.decline_reasons = reasons;
    try {
      await api(`/bank/applications/${app.id}/decision`, { method: 'POST', body });
      toast.push(action === 'decline' ? 'Отрицательное решение зафиксировано' : action === 'request_info' ? 'Запрос уточнений отправлен клиенту' : 'Решение сохранено, предложение сформировано');
      setComment('');
      setReasons([]);
      await load();
    } catch (e) {
      setError(e.message);
      toast.push(e.message, 'error');
    } finally {
      setBusy(false);
    }
  }

  const c = client?.company || {};
  const bki = client?.bki || {};
  const reg = client?.registry || {};
  const offer = app.offer;
  const disabled = !canDecide || busy ||
    ((action === 'approve' || action === 'counter_offer') && (!amount || !rate || !term)) ||
    (action === 'request_info' && !comment.trim()) ||
    (action === 'decline' && reasons.length === 0) ||
    (action === 'approve' && !conditionsChanged && ['C', 'D'].includes(app?.risk_class) && !comment.trim());

  return (
    <div className="page page-wide">
      <Link to="/bank" className="row gap-8 small muted" style={{ marginBottom: 16, fontWeight: 600 }}>
        <Icon name="arrowLeft" size={16} /> К очереди заявок
      </Link>

      <div className="row-between wrap" style={{ alignItems: 'flex-start', gap: 16, marginBottom: 18 }}>
        <div>
          <div className="row gap-12 wrap">
            <h1 style={{ fontSize: 24, letterSpacing: '-0.02em' }}>{c.name?.replace('Общество с ограниченной ответственностью ', 'ООО ').replace('Индивидуальный предприниматель ', 'ИП ')}</h1>
            <StatusPill status={app.status} />
          </div>
          <p className="muted small mt-8">
            Заявка № {app.number} · {app.product.name} · {money(app.amount)} на {app.term_months} мес. · отправлена {dateTime(app.submitted_at)}
          </p>
        </div>
        <div className="row gap-8">
          <button className="btn btn-secondary btn-sm" onClick={load}><Icon name="refresh" size={15} /> Обновить</button>
          <button className="btn btn-dark btn-sm" onClick={() => window.print()}><Icon name="download" size={15} /> Карточка заявки</button>
        </div>
      </div>

      {error && <div className="banner banner-danger" style={{ marginBottom: 16 }}><Icon name="alert" size={16} />{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, alignItems: 'start' }}>
        <div className="col gap-16">
          <div className="card card-pad">
            <div className="card-head">
              <div>
                <div className="card-title">Профиль клиента</div>
                <div className="tiny muted mt-8">данные анкеты и обслуживания в банке</div>
              </div>
              {c.has_alfa_account && <span className="pill pill-green"><span className="dot" /> Клиент банка</span>}
            </div>
            <div className="grid grid-3" style={{ gap: '0 24px' }}>
              <div>
                <div className="kv"><span>ИНН</span><b>{c.inn}</b></div>
                <div className="kv"><span>ОГРН</span><b>{c.ogrn}</b></div>
                <div className="kv"><span>Форма</span><b>{c.legal_form}</b></div>
                <div className="kv"><span>Отрасль</span><b>{c.industry}</b></div>
              </div>
              <div>
                <div className="kv"><span>Регион</span><b>{c.region}</b></div>
                <div className="kv"><span>Сотрудники</span><b>{c.employees_count}</b></div>
                <div className="kv"><span>С даты регистрации</span><b>{dateShort(c.founded_date)}</b></div>
                <div className="kv"><span>ОКВЭД</span><b style={{ maxWidth: 170 }}>{client.okved_name}</b></div>
              </div>
              <div>
                <div className="kv"><span>Руководитель</span><b style={{ maxWidth: 160 }}>{client.director_name}</b></div>
                <div className="kv"><span>Клиент банка с</span><b>{client.alfa_client_since ? dateShort(client.alfa_client_since) : '—'}</b></div>
                <div className="kv"><span>Залог</span><b>{client.collateral_available ? client.collateral_desc : 'нет'}</b></div>
                <div className="kv"><span>Заявка</span><b>{app.purpose}</b></div>
              </div>
            </div>
            {app.purpose_details && (
              <div className="banner banner-info mt-12">
                <Icon name="info" size={16} /> Комментарий клиента: {app.purpose_details}
              </div>
            )}
          </div>

          <div className="grid grid-2">
            <div className="card card-pad">
              <div className="card-title" style={{ marginBottom: 10 }}>Финансовые показатели</div>
              <div className="kv"><span>Выручка (сред. в мес.)</span><b>{money(c.revenue_avg_monthly)}</b></div>
              <div className="kv"><span>Выручка за 12 мес.</span><b>{money(c.revenue_12m)}</b></div>
              <div className="kv"><span>Прибыль за 12 мес.</span><b>{money(c.net_profit_12m)}</b></div>
              <div className="kv"><span>Платежи по кредитам</span><b>{money(c.existing_monthly_payments)}</b></div>
              <div className="kv"><span>Обороты по счёту</span><b>{money(c.account_turnover_monthly)}</b></div>
              <div className="mt-16">
                <div className="tiny muted" style={{ marginBottom: 8 }}>Динамика выручки, 6 мес.</div>
                <MiniBars data={client.dynamics} />
              </div>
            </div>

            <div className="card card-pad">
              <div className="row-between">
                <div className="card-title">Бюро кредитных историй</div>
                <span className={`pill ${bki.bki_score >= 700 ? 'pill-green' : bki.bki_score >= 600 ? 'pill-amber' : 'pill-red'}`}>
                  {bki.bki_score}
                </span>
              </div>
              <div className="kv mt-8"><span>Действующие кредиты</span><b>{bki.active_loans}</b></div>
              <div className="kv"><span>Общий долг</span><b>{money(bki.total_debt)}</b></div>
              <div className="kv"><span>Платёж в месяц</span><b>{money(bki.monthly_payments)}</b></div>
              <div className="kv"><span>Макс. просрочка (12 мес.)</span><b className={bki.max_delay_days_12m > 30 ? 'text-red' : ''}>{bki.max_delay_days_12m} дн.</b></div>
              <div className="kv"><span>Просрочки (12 мес.)</span><b>{bki.delinquencies_12m}</b></div>
              <div className="kv"><span>Запросы (6 мес.)</span><b>{bki.inquiries_6m}</b></div>
              <p className="tiny muted mt-12" style={{ lineHeight: 1.5 }}>{bki.summary}</p>
            </div>
          </div>

          <div className="card card-pad">
            <div className="row-between">
              <div>
                <div className="card-title">Проверки ЕГРЮЛ и ФНС</div>
                <div className="tiny muted mt-8">{reg.source}</div>
              </div>
              <span className={`pill ${reg.status === 'Действующий' && !reg.tax_debt ? 'pill-green' : 'pill-red'}`}>
                {reg.status}
              </span>
            </div>
            <div className="grid grid-2 mt-12" style={{ gap: '0 24px' }}>
              <div>
                <Check ok={!reg.tax_debt} label="Задолженность по налогам" detail={reg.tax_debt ? 'Обнаружена' : 'Не обнаружена'} />
                <Check ok={!reg.mass_address} label="Адрес регистрации" detail={reg.mass_address ? 'Признак массового адреса' : 'Без признаков массовости'} />
              </div>
              <div>
                <Check ok={!reg.fns_violations} label="Нарушения ФНС" detail={reg.fns_violations ? 'Есть нарушения' : 'Не найдены'} />
                <Check ok={!reg.director_changed_recently} label="Смена руководителя" detail={reg.director_changed_recently ? 'Менее года назад' : 'Не менялся'} />
              </div>
            </div>
          </div>

          <div className="card card-pad">
            <div className="row-between">
              <div className="card-title">Документы клиента</div>
              <span className="tiny muted">{app.documents.length} файлов</span>
            </div>
            {app.documents.length === 0 ? (
              <div className="small muted mt-12">Клиент пока не загрузил документы. Можно запросить уточнения.</div>
            ) : (
              <div className="mt-12">
                {app.documents.map((d) => (
                  <div key={d.id} className="row-between" style={{ padding: '9px 0', borderBottom: '1px solid var(--line-2)' }}>
                    <div className="row gap-12">
                      <div className="event-icon"><Icon name="doc" size={15} /></div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{d.title}</div>
                        <div className="tiny muted">{d.filename} · {d.size_kb} КБ · {dateTime(d.created_at)}</div>
                      </div>
                    </div>
                    <span className={`pill ${d.status === 'verified' ? 'pill-green' : 'pill-gray'}`}>
                      {d.status === 'verified' ? 'Проверен' : 'Загружен'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card card-pad">
            <div className="card-title" style={{ marginBottom: 14 }}>История обработки</div>
            <div className="timeline">
              {[...app.events].reverse().map((e, idx) => (
                <div key={e.id} className={`tl-item ${idx === 0 ? 'current' : 'done'}`}>
                  <span className="tl-dot"><Icon name={e.actor_type === 'bank' ? 'shield' : e.actor_type === 'client' ? 'user' : 'settings'} size={9} style={{ color: idx === 0 ? '#fff' : 'var(--muted)' }} /></span>
                  <div className="tl-title">{e.title}</div>
                  {e.comment && <div className="tl-comment">{e.comment}</div>}
                  <div className="tl-meta">{e.actor_name} · {dateTime(e.created_at)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col gap-16">
          <div className="card card-pad">
            <div className="row-between">
              <div>
                <div className="card-title">Скоринговая оценка</div>
                <div className="tiny muted mt-8">балльная модель · {scoring?.score ?? '—'}/1000</div>
              </div>
              {scoring && <ScoreRing score={scoring.score} riskClass={scoring.risk_class} size={66} stroke={7} />}
            </div>
            {scoring && (
              <>
                <div className="row gap-8 wrap mt-12">
                  <span className={`pill ${riskTone[scoring.risk_class]}`}>{scoring.risk_class} · {riskClassLabel(scoring.risk_class)}</span>
                  <span className="pill pill-gray">PD ≈ {percent(scoring.pd_percent)}</span>
                  {scoring.debt_load_percent != null && <span className="pill pill-gray">Нагрузка {percent(scoring.debt_load_percent)}</span>}
                </div>
                {scoring.hard_stops?.length > 0 && (
                  <div className="banner banner-danger mt-12">
                    <Icon name="alert" size={16} />
                    <div>
                      <b>Стоп-факторы:</b>
                      <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                        {scoring.hard_stops.map((s) => <li key={s}>{s}</li>)}
                      </ul>
                    </div>
                  </div>
                )}
                <div className="mt-12">
                  {scoring.factors.map((f) => (
                    <div key={f.code} className="factor">
                      <div className="factor-head">
                        <span style={{ fontWeight: 600 }}>{f.title}</span>
                        <span className="mono muted">{Math.round(f.points)}/{f.max_points}</span>
                      </div>
                      <div className="tiny muted" style={{ marginTop: 2 }}>{f.value}</div>
                      <div className="factor-bar">
                        <div className={`factor-fill ${f.impact}`} style={{ width: `${Math.round((f.points / f.max_points) * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="divider" />
                <div className="kv" style={{ padding: '6px 0' }}><span>Рекомендованная сумма</span><b>{money(scoring.recommended_amount)}</b></div>
                <div className="kv" style={{ padding: '6px 0' }}><span>Рекомендованная ставка</span><b>{percent(scoring.recommended_rate)}</b></div>
                <div className="kv" style={{ padding: '6px 0' }}><span>Платёж при рекомендации</span><b>{money(scoring.monthly_payment)}</b></div>
              </>
            )}
          </div>

          <div className="card card-pad decision-panel">
            <div className="card-title">Кредитное решение</div>
            {!canDecide && (
              <div className="banner banner-info mt-12">
                <Icon name="info" size={16} />
                <span>
                  Заявка не требует решения: статус «{app.status_label}».
                  {offer ? ` Предложение: ${money(offer.amount)} под ${percent(offer.rate)} на ${offer.term_months} мес.` : ''}
                </span>
              </div>
            )}
            {canDecide && (
              <>
                <div className="tiny muted mt-8">Запрошено клиентом: {money(app.amount)} · {app.term_months} мес. · {app.purpose}</div>
                <div className="decision-tabs mt-12">
                  {ACTIONS.map((a) => (
                    <button key={a.key} className={`decision-tab ${action === a.key ? 'active' : ''}`} onClick={() => setAction(a.key)}>
                      {a.label}
                    </button>
                  ))}
                </div>

                {(action === 'approve' || action === 'counter_offer') && (
                  <div className="mt-16">
                    <div className="field">
                      <label>Сумма предложения, ₽</label>
                      <input className="input" type="number" value={amount} step="10000" onChange={(e) => setAmount(e.target.value)} />
                      <span className="hint">Лимиты продукта: {moneyShort(app.product.min_amount)} — {moneyShort(app.product.max_amount)}</span>
                    </div>
                    <div className="row gap-8 mt-12">
                      <div className="field grow">
                        <label>Ставка, %</label>
                        <input className="input" type="number" value={rate} step="0.1" onChange={(e) => setRate(e.target.value)} />
                      </div>
                      <div className="field grow">
                        <label>Срок, мес.</label>
                        <input className="input" type="number" value={term} step="1" onChange={(e) => setTerm(e.target.value)} />
                      </div>
                    </div>
                    {conditionsChanged && (
                      <div className="banner banner-warn mt-12">
                        <Icon name="info" size={16} />
                        Условия отличаются от запрошенных клиентом ({money(app.amount)} · {app.term_months} мес.).
                        Заявка уйдёт клиенту как контрпредложение.
                      </div>
                    )}
                    {action === 'approve' && !conditionsChanged && ['C', 'D'].includes(app.risk_class) && (
                      <div className="banner banner-warn mt-12">
                        <Icon name="alert" size={16} />
                        Для риск-класса {app.risk_class} политика рекомендует контрпредложение. Одобрение
                        на исходных условиях потребует обоснования в комментарии.
                      </div>
                    )}
                  </div>
                )}

                {action === 'request_info' && (
                  <div className="field mt-16">
                    <label>Что уточнить у клиента</label>
                    <textarea className="textarea" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Например: расшифровка прочих расходов за последние 3 месяца" />
                  </div>
                )}

                {action === 'decline' && (
                  <div className="mt-16">
                    <div className="tiny muted" style={{ marginBottom: 8 }}>Причины отказа (минимум одна)</div>
                    <div className="col gap-8">
                      {DECLINE_REASONS.map((r) => (
                        <label key={r} className="row gap-8" style={{ alignItems: 'flex-start', cursor: 'pointer' }}>
                          <input
                            type="checkbox" checked={reasons.includes(r)} style={{ marginTop: 3 }}
                            onChange={(e) => setReasons((prev) => (e.target.checked ? [...prev, r] : prev.filter((x) => x !== r)))}
                          />
                          <span className="small">{r}</span>
                        </label>
                      ))}
                    </div>
                    <div className="field mt-12">
                      <label>Комментарий клиенту</label>
                      <textarea className="textarea" value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Объясните решение понятным языком" />
                    </div>
                  </div>
                )}

                {action !== 'request_info' && action !== 'decline' && (
                  <div className="field mt-12">
                    <label>Комментарий к решению</label>
                    <textarea className="textarea" style={{ minHeight: 70 }} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Обоснование для истории заявки" />
                  </div>
                )}

                <div className="banner banner-info mt-12">
                  <Icon name="shield" size={16} />
                  Все действия андеррайтера фиксируются в журнале с указанием роли и времени.
                </div>

                <button className="btn btn-primary btn-block mt-16" disabled={disabled} onClick={submitDecision}>
                  {busy ? <span className="spinner" /> : <Icon name={ACTIONS.find((a) => a.key === action)?.icon || 'check'} size={16} />}
                  {action === 'approve' ? 'Одобрить и сформировать предложение'
                    : action === 'counter_offer' ? 'Отправить контрпредложение'
                      : action === 'request_info' ? 'Запросить уточнения'
                        : 'Зафиксировать отказ'}
                </button>
              </>
            )}

            {offer && !canDecide && (
              <div className="offer-box mt-12">
                <div className="tiny muted">Текущее предложение</div>
                <div className="offer-payment">{money(offer.monthly_payment)}</div>
                <div className="kv"><span>Сумма</span><b>{money(offer.amount)}</b></div>
                <div className="kv"><span>Ставка</span><b>{percent(offer.rate)}</b></div>
                <div className="kv"><span>Срок</span><b>{offer.term_months} мес.</b></div>
                {offer.comment && <p className="tiny muted mt-8" style={{ lineHeight: 1.5 }}>{offer.comment}</p>}
              </div>
            )}
          </div>

          <div className="card card-pad">
            <div className="row gap-8">
              <Icon name="shield" size={17} style={{ color: 'var(--muted)' }} />
              <div className="card-title">Маршрутизация</div>
            </div>
            <p className="small muted mt-8" style={{ lineHeight: 1.5 }}>
              Заявка попала к андеррайтеру, потому что риск-класс пограничный или сумма превышает порог
              автоматического одобрения. Автоматические решения по классам A и B формируются конвейером без участия человека.
            </p>
            <button className="btn btn-ghost btn-sm mt-12" onClick={() => navigate('/bank/analytics')}>
              Правила и метрики конвейера <Icon name="arrowRight" size={14} />
            </button>
          </div>

          <PaymentSchedule schedule={app.schedule} title="График платежей по текущим условиям" compact />
        </div>
      </div>
    </div>
  );
}
