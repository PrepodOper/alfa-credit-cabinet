import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api.js';
import { dateShort, dateTime, money, percent, riskClassLabel, statusMeta, timeAgo } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import StatusPill from '../components/StatusPill.jsx';
import ScoreRing from '../components/ScoreRing.jsx';
import Modal from '../components/Modal.jsx';
import { useToast } from '../components/Toast.jsx';

const PROCESSING = new Set(['submitted', 'validation', 'scoring', 'manual_review', 'client_info_provided', 'offer_formed']);
const STEPS = ['Заявка', 'Проверка и скоринг', 'Решение банка', 'Документы', 'Выдача'];

function currentStep(status) {
  if (['draft'].includes(status)) return 0;
  if (['submitted', 'validation', 'scoring'].includes(status)) return 1;
  if (['manual_review', 'info_requested', 'client_info_provided', 'declined', 'expired'].includes(status)) return 2;
  if (['offer_issued', 'offer_accepted', 'signing'].includes(status)) return 3;
  return 4;
}

const DOC_TYPES = [
  { value: 'charter', label: 'Учредительные документы' },
  { value: 'financials', label: 'Финансовая отчётность' },
  { value: 'collateral', label: 'Документы по залогу' },
  { value: 'other', label: 'Другое' },
];

export default function ApplicationDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [app, setApp] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [infoText, setInfoText] = useState('');
  const [modal, setModal] = useState(null);
  const [docTitle, setDocTitle] = useState('');
  const [docType, setDocType] = useState('financials');
  const pollRef = useRef(null);

  const load = useCallback(async (silent = false) => {
    try {
      const data = await api(`/applications/${id}`);
      setApp(data);
      setError('');
    } catch (e) {
      if (!silent) setError(e.message);
    }
  }, [id]);

  useEffect(() => { setApp(null); load(); }, [load]);

  useEffect(() => {
    if (!app || !PROCESSING.has(app.status)) return undefined;
    pollRef.current = window.setInterval(() => load(true), 1800);
    return () => window.clearInterval(pollRef.current);
  }, [app?.status, load]);

  const step = useMemo(() => (app ? currentStep(app.status) : 0), [app]);

  if (!app) {
    return (
      <div className="page">
        {error ? <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div> : <div className="skeleton" style={{ height: 420 }} />}
      </div>
    );
  }

  const offer = app.offer;
  const scoring = app.scoring;
  const meta = statusMeta(app.status);

  async function act(name, fn, successMessage) {
    setBusy(name);
    setError('');
    try {
      await fn();
      if (successMessage) toast.push(successMessage);
      await load(true);
      setModal(null);
    } catch (e) {
      setError(e.message);
      toast.push(e.message, 'error');
    } finally {
      setBusy('');
    }
  }

  const acceptOffer = (accept) => act('offer', () => api(`/applications/${app.id}/offer/accept`, {
    method: 'POST', body: { accept, comment: accept ? '' : 'Клиент отклонил предложение' },
  }), accept ? 'Предложение принято' : 'Предложение отклонено');

  const signDocs = () => act('sign', () => api(`/applications/${app.id}/sign`, { method: 'POST' }), 'Документы подписаны');

  const sendInfo = () => act('info', () => api(`/applications/${app.id}/info`, {
    method: 'POST', body: { comment: infoText },
  }), 'Уточнения отправлены банку');

  const addDocument = () => act('doc', () => api(`/applications/${app.id}/documents`, {
    method: 'POST',
    body: { title: docTitle || 'Документ', doc_type: docType, filename: `${docType}_${app.number}.pdf`, size_kb: 240 },
  }), 'Документ загружен');

  const statusTone = {
    declined: { bg: 'var(--red-soft)', color: 'var(--red-600)', icon: 'x' },
    funded: { bg: 'var(--green-soft)', color: 'var(--green)', icon: 'checkCircle' },
    info_requested: { bg: 'var(--orange-soft)', color: 'var(--orange)', icon: 'alert' },
    signing: { bg: 'var(--purple-soft)', color: 'var(--purple)', icon: 'doc' },
    offer_issued: { bg: 'var(--purple-soft)', color: 'var(--purple)', icon: 'sparkles' },
    expired: { bg: '#f1f2f5', color: 'var(--muted)', icon: 'clock' },
  }[app.status] || { bg: 'var(--blue-soft)', color: 'var(--blue)', icon: 'clock' };

  return (
    <div className="page">
      <Link to="/app/applications" className="row gap-8 small muted" style={{ marginBottom: 16, fontWeight: 600 }}>
        <Icon name="arrowLeft" size={16} /> Все заявки
      </Link>

      <div className="row-between wrap" style={{ alignItems: 'flex-start', gap: 16, marginBottom: 18 }}>
        <div>
          <div className="row gap-12 wrap">
            <h1 style={{ fontSize: 25, letterSpacing: '-0.025em' }}>{app.product.name}</h1>
            <StatusPill status={app.status} live />
            {app.status === 'manual_review' && <span className="pill pill-amber"><Icon name="users" size={12} /> Андеррайтер</span>}
            {PROCESSING.has(app.status) && <span className="pill pill-blue"><span className="pulse-dot" /> автообновление</span>}
          </div>
          <p className="muted small mt-8">
            Заявка № {app.number} · создана {dateTime(app.created_at)} · {money(app.amount)} на {app.term_months} мес.
          </p>
        </div>
        <div className="row gap-8">
          <button className="btn btn-secondary btn-sm" onClick={() => load()}>
            <Icon name="refresh" size={15} /> Обновить
          </button>
        </div>
      </div>

      {error && <div className="banner banner-danger" style={{ marginBottom: 16 }}><Icon name="alert" size={16} />{error}</div>}

      <div className="card" style={{ padding: '20px 24px', marginBottom: 16 }}>
        <div className="steps">
          {STEPS.map((label, i) => {
            const done = app.status === 'funded' ? true : i < step;
            const current = i === step && app.status !== 'funded';
            const failed = current && app.status === 'declined';
            return (
              <div key={label} className={`step ${done ? 'done' : ''} ${current ? 'current' : ''}`}>
                {i < STEPS.length - 1 && <span className="step-line" style={failed ? { background: '#f3c2bc' } : undefined} />}
                <span className="step-dot" style={failed ? { background: 'var(--red-soft)', borderColor: 'var(--red)', color: 'var(--red-600)' } : undefined}>
                  {done ? <Icon name="check" size={13} /> : i + 1}
                </span>
                <span className="step-label">{label}</span>
              </div>
            );
          })}
        </div>
        <div className="progress-track mt-16">
          <div
            className={`progress-fill ${app.status === 'funded' ? 'green' : app.status === 'declined' ? 'red' : ''}`}
            style={{ width: `${Math.max(4, app.progress_percent)}%` }}
          />
        </div>
      </div>

      <div className="status-banner" style={{ borderColor: 'var(--line)', background: `linear-gradient(90deg, ${statusTone.bg}, #fff 70%)` }}>
        <div className="row gap-16" style={{ alignItems: 'flex-start' }}>
          <div className="status-icon" style={{ background: statusTone.bg, color: statusTone.color }}>
            <Icon name={statusTone.icon} size={22} />
          </div>
          <div>
            <h3>{meta.label}</h3>
            <p style={{ maxWidth: 640 }}>{app.next_action}</p>
            {app.status === 'manual_review' && app.score && (
              <p className="tiny muted" style={{ marginTop: 6 }}>
                Заявка проходит ручную проверку андеррайтером: {app.score}/1000, риск-класс {app.risk_class}.
              </p>
            )}
          </div>
        </div>
        {app.score && (
          <div className="col" style={{ alignItems: 'center', gap: 4 }}>
            <ScoreRing score={app.score} riskClass={app.risk_class || 'C'} size={62} stroke={6} />
            <span className="tiny muted">риск-класс {app.risk_class}</span>
          </div>
        )}
      </div>

      {app.status === 'declined' && (
        <div className="card card-pad mt-16" style={{ borderColor: '#f3c2bc' }}>
          <div className="row gap-12" style={{ alignItems: 'flex-start' }}>
            <div className="status-icon" style={{ background: 'var(--red-soft)', color: 'var(--red-600)' }}>
              <Icon name="alert" size={20} />
            </div>
            <div className="grow">
              <div className="card-title">Причины отказа</div>
              <ul className="small muted" style={{ margin: '10px 0 0', paddingLeft: 18, lineHeight: 1.7 }}>
                {app.decline_reasons.map((r) => <li key={r}>{r}</li>)}
              </ul>
              <div className="row gap-8 mt-16">
                <button className="btn btn-secondary btn-sm" onClick={() => navigate('/app/products')}>Подать новую заявку</button>
                <button className="btn btn-ghost btn-sm" onClick={() => navigate('/app/news')}>Что можно улучшить</button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-16" style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 16, alignItems: 'start' }}>
        <div className="col gap-16">
          {offer && ['offer_issued', 'offer_accepted', 'signing', 'funded'].includes(app.status) && (
            <div className="offer-box">
              <div className="row-between wrap">
                <div className="row gap-8">
                  <Icon name="sparkles" size={18} style={{ color: 'var(--purple)' }} />
                  <span className="card-title">{offer.is_counter_offer ? 'Контрпредложение банка' : 'Предложение банка'}</span>
                </div>
                <span className={`pill ${offer.is_counter_offer ? 'pill-amber' : 'pill-green'}`}>
                  {offer.is_counter_offer ? 'Условия скорректированы' : 'Одобрено'}
                </span>
              </div>

              {offer.is_counter_offer && (
                <div className="banner banner-warn mt-12">
                  <Icon name="info" size={16} />
                  <span>
                    Вы запрашивали {money(offer.requested_amount)} на {offer.requested_term_months} мес.
                    Банк готов предложить {money(offer.amount)} на {offer.term_months} мес. на условиях ниже.
                  </span>
                </div>
              )}

              <div className="mt-16">
                <div className="tiny muted">Платёж в месяц</div>
                <div className="offer-payment">{money(offer.monthly_payment)}</div>
              </div>
              <div className="offer-grid">
                <div className="offer-cell"><span>Сумма</span><b>{money(offer.amount)}</b></div>
                <div className="offer-cell"><span>Ставка</span><b>{percent(offer.rate)}</b></div>
                <div className="offer-cell"><span>Срок</span><b>{offer.term_months} мес.</b></div>
              </div>

              {offer.comment && <p className="small muted mt-12" style={{ lineHeight: 1.5 }}>{offer.comment}</p>}

              {app.status === 'offer_issued' && (
                <>
                  <div className="row gap-8 tiny muted mt-12">
                    <Icon name="clock" size={14} /> Предложение действует до {dateTime(offer.expires_at)}
                  </div>
                  <div className="row gap-8 mt-16 wrap">
                    <button className="btn btn-primary" disabled={busy === 'offer'} onClick={() => acceptOffer(true)}>
                      {busy === 'offer' ? <span className="spinner" /> : <Icon name="check" size={16} />} Принять предложение
                    </button>
                    <button className="btn btn-secondary" disabled={busy === 'offer'} onClick={() => setModal('decline')}>
                      Отказаться
                    </button>
                  </div>
                </>
              )}
              {app.status === 'funded' && (
                <div className="banner banner-success mt-16">
                  <Icon name="checkCircle" size={16} />
                  <span>Кредит выдан. Средства зачислены на счёт {app.credit_account}.</span>
                </div>
              )}
            </div>
          )}

          {app.status === 'signing' && (
            <div className="card card-pad">
              <div className="row-between">
                <div className="card-title">Документы к подписанию</div>
                <span className="pill pill-purple"><Icon name="lock" size={12} /> УКЭП</span>
              </div>
              <p className="small muted mt-8">Проверьте пакет документов. Подписание происходит в демо-режиме внутри кабинета.</p>
              <div className="mt-16">
                {app.signature_docs.map((d) => (
                  <div key={d.code} className="row-between" style={{ padding: '10px 0', borderBottom: '1px solid var(--line-2)' }}>
                    <div className="row gap-12">
                      <Icon name="doc" size={18} style={{ color: 'var(--muted)' }} />
                      <div>
                        <div style={{ fontSize: 13.5, fontWeight: 600 }}>{d.title}</div>
                        <div className="tiny muted">{d.pages} стр. · PDF</div>
                      </div>
                    </div>
                    <Icon name={d.signed ? 'checkCircle' : 'eye'} size={16} style={{ color: d.signed ? 'var(--green)' : 'var(--muted)' }} />
                  </div>
                ))}
              </div>
              <button className="btn btn-primary btn-block mt-16" disabled={busy === 'sign'} onClick={signDocs}>
                {busy === 'sign' ? <span className="spinner" /> : <Icon name="lock" size={16} />} Подписать документы
              </button>
            </div>
          )}

          {app.status === 'info_requested' && (
            <div className="card card-pad" style={{ borderColor: '#f7d1ae' }}>
              <div className="row gap-8">
                <Icon name="alert" size={18} style={{ color: 'var(--orange)' }} />
                <div className="card-title">Банк запросил уточнения</div>
              </div>
              {app.decision_comment && <p className="small mt-12" style={{ lineHeight: 1.55 }}>{app.decision_comment}</p>}
              <div className="field mt-16">
                <label>Ваш ответ для банка</label>
                <textarea
                  className="textarea" value={infoText} onChange={(e) => setInfoText(e.target.value)}
                  placeholder="Опишите запрошенные сведения. При необходимости приложите документ ниже."
                />
              </div>
              <div className="row gap-8 mt-12 wrap">
                <button className="btn btn-primary" disabled={busy === 'info' || !infoText.trim()} onClick={sendInfo}>
                  {busy === 'info' ? <span className="spinner" /> : <Icon name="arrowRight" size={16} />} Отправить уточнения
                </button>
                <button className="btn btn-secondary" onClick={() => { setDocTitle(''); setModal('doc'); }}>
                  <Icon name="upload" size={15} /> Приложить документ
                </button>
              </div>
            </div>
          )}

          {app.status === 'funded' && (
            <div className="card card-pad" style={{ background: 'linear-gradient(160deg,#f2fbf7,#fff)' }}>
              <div className="row gap-16" style={{ alignItems: 'flex-start' }}>
                <div className="status-icon" style={{ background: 'var(--green-soft)', color: 'var(--green)', width: 52, height: 52 }}>
                  <Icon name="checkCircle" size={26} />
                </div>
                <div className="grow">
                  <div className="card-title" style={{ fontSize: 18 }}>Финансирование предоставлено</div>
                  <p className="small muted mt-8">
                    {money(app.offer.amount)} зачислены на расчётный счёт {app.credit_account}. Первый платёж —
                    {' '}{dateShort(new Date(Date.now() + 30 * 86400000).toISOString())}, далее ежемесячно {money(app.offer.monthly_payment)}.
                  </p>
                  <div className="row gap-8 mt-16 wrap">
                    <button className="btn btn-secondary btn-sm" onClick={() => toast.push('График платежей — демо-файл')}>
                      <Icon name="download" size={15} /> График платежей
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => navigate('/app/news')}>
                      Полезные материалы для заёмщика
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="card card-pad">
            <div className="card-head">
              <div>
                <div className="card-title">Документы по заявке</div>
                <div className="tiny muted mt-8">Обязательный пакет: {app.required_docs.length || 0} документов</div>
              </div>
              {!['funded', 'declined', 'expired'].includes(app.status) && (
                <button className="btn btn-secondary btn-sm" onClick={() => { setDocTitle(''); setModal('doc'); }}>
                  <Icon name="upload" size={15} /> Загрузить
                </button>
              )}
            </div>
            {app.documents.length === 0 ? (
              <div className="small muted" style={{ padding: '8px 0' }}>
                Документы пока не загружены. Если банк запросит — прикрепите их здесь.
              </div>
            ) : (
              <div>
                {app.documents.map((d) => (
                  <div key={d.id} className="row-between" style={{ padding: '10px 0', borderBottom: '1px solid var(--line-2)' }}>
                    <div className="row gap-12">
                      <div className="event-icon"><Icon name="doc" size={15} /></div>
                      <div>
                        <div style={{ fontSize: 13.5, fontWeight: 600 }}>{d.title}</div>
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
            {app.required_docs.length > 0 && (
              <div className="mt-16">
                <div className="tiny muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                  Потребуется по продукту
                </div>
                <div className="row gap-8 wrap">
                  {app.required_docs.map((d) => <span key={d} className="tag"><Icon name="doc" size={12} /> {d}</span>)}
                </div>
              </div>
            )}
          </div>

          <div className="card card-pad">
            <div className="card-head">
              <div className="card-title">История заявки</div>
              <span className="tiny muted">все события процесса</span>
            </div>
            <div className="timeline">
              {[...app.events].reverse().map((e, idx) => (
                <div key={e.id} className={`tl-item ${idx === 0 ? 'current' : 'done'}`}>
                  <span className="tl-dot"><Icon name={e.actor_type === 'client' ? 'user' : e.actor_type === 'bank' ? 'shield' : 'settings'} size={9} style={{ color: idx === 0 ? '#fff' : 'var(--muted)' }} /></span>
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
            <div className="card-title" style={{ marginBottom: 14 }}>Параметры заявки</div>
            <div className="kv"><span>Продукт</span><b>{app.product.name}</b></div>
            <div className="kv"><span>Сумма</span><b>{money(app.amount)}</b></div>
            <div className="kv"><span>Срок</span><b>{app.term_months} мес.</b></div>
            <div className="kv"><span>Цель</span><b>{app.purpose}</b></div>
            <div className="kv">
              <span>{app.offer ? 'Ставка по предложению' : 'Ставка'}</span>
              <b>{app.offer ? percent(app.offer.rate) : `от ${percent(app.product.base_rate)}`}</b>
            </div>
            <div className="kv">
              <span>{app.offer ? 'Платёж по предложению' : 'Платёж'}</span>
              <b>{app.offer ? money(app.offer.monthly_payment) : '—'}</b>
            </div>
            <div className="kv"><span>Номер</span><b>{app.number}</b></div>
          </div>

          {scoring && (
            <div className="card card-pad">
              <div className="row-between">
                <div>
                  <div className="card-title">Оценка заявки</div>
                  <div className="tiny muted mt-8">балльная модель · прозрачные факторы</div>
                </div>
                <ScoreRing score={scoring.score} riskClass={scoring.risk_class} size={58} stroke={6} />
              </div>
              <div className="row gap-8 mt-12 wrap">
                <span className="pill pill-gray">{riskClassLabel(scoring.risk_class)}</span>
                <span className="pill pill-gray">PD ≈ {percent(scoring.pd_percent)}</span>
              </div>
              <div className="mt-12">
                {scoring.factors.map((f) => (
                  <div key={f.code} className="factor">
                    <div className="factor-head">
                      <span style={{ fontWeight: 600 }}>{f.title}</span>
                      <span className="mono muted">{Math.round(f.points)}/{f.max_points}</span>
                    </div>
                    <div className="tiny muted" style={{ marginTop: 3 }}>{f.value}</div>
                    <div className="factor-bar">
                      <div className={`factor-fill ${f.impact}`} style={{ width: `${Math.round((f.points / f.max_points) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="tiny muted mt-12" style={{ lineHeight: 1.5 }}>
                Скоринг показывает уровень риска. Итоговое решение учитывает также правила продукта,
                сумму и срок — поэтому одинаковый балл может давать разные условия.
              </div>
            </div>
          )}

          <div className="card card-pad">
            <div className="row gap-8">
              <Icon name="shield" size={17} style={{ color: 'var(--muted)' }} />
              <div className="card-title">Безопасность</div>
            </div>
            <p className="small muted mt-8" style={{ lineHeight: 1.5 }}>
              Все действия в заявке фиксируются в журнале. Запросы в БКИ и ЕГРЮЛ выполняются
              только с согласия клиента, указанного в заявке.
            </p>
          </div>
        </div>
      </div>

      {modal === 'decline' && (
        <Modal
          title="Отказаться от предложения?"
          subtitle="Заявка будет закрыта, при необходимости вы сможете подать новую"
          onClose={() => setModal(null)}
          footer={(
            <>
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Оставить</button>
              <button className="btn btn-danger" disabled={busy === 'offer'} onClick={() => acceptOffer(false)}>
                Отказаться
              </button>
            </>
          )}
        >
          <p className="small muted" style={{ lineHeight: 1.6 }}>
            Если условия не подходят, вы можете отказаться и подать заявку с другими параметрами.
            Отказ не влияет на кредитную историю.
          </p>
        </Modal>
      )}

      {modal === 'doc' && (
        <Modal
          title="Загрузить документ"
          subtitle="Демо-режим: файл не передаётся, но событие фиксируется в заявке"
          onClose={() => setModal(null)}
          footer={(
            <>
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Отмена</button>
              <button className="btn btn-primary" disabled={busy === 'doc' || !docTitle.trim()} onClick={addDocument}>
                {busy === 'doc' ? <span className="spinner" /> : <Icon name="upload" size={16} />} Загрузить
              </button>
            </>
          )}
        >
          <div className="field">
            <label>Тип документа</label>
            <select className="select" value={docType} onChange={(e) => setDocType(e.target.value)}>
              {DOC_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div className="field mt-16">
            <label>Название документа</label>
            <input className="input" value={docTitle} onChange={(e) => setDocTitle(e.target.value)} placeholder="Например: Оборотно-сальдовая ведомость за 9 месяцев" />
          </div>
        </Modal>
      )}
    </div>
  );
}
