import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../lib/api.js';
import { money, moneyShort, percent } from '../lib/format.js';
import { annuity, clampAmount, termOptions, totalInterest } from '../lib/calc.js';
import Icon from '../components/Icons.jsx';
import ProductIcon from '../components/ProductIcon.jsx';
import Modal from '../components/Modal.jsx';
import { useToast } from '../components/Toast.jsx';

export default function ProductDetail() {
  const { code } = useParams();
  const navigate = useNavigate();
  const toast = useToast();

  const [product, setProduct] = useState(null);
  const [amount, setAmount] = useState(0);
  const [term, setTerm] = useState(0);
  const [purpose, setPurpose] = useState('');
  const [details, setDetails] = useState('');
  const [eligibility, setEligibility] = useState(null);
  const [error, setError] = useState('');
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api(`/products/${code}`).then((p) => {
      setProduct(p);
      const start = Math.round(Math.min(p.max_amount, Math.max(p.min_amount, p.max_amount * 0.4)) / 10_000) * 10_000;
      setAmount(clampAmount(p, start));
      setTerm(Math.min(p.max_term_months, Math.max(p.min_term_months, 12)));
      setPurpose(p.purposes[0] || '');
    }).catch((e) => setError(e.message));
  }, [code]);

  useEffect(() => {
    if (!product || !amount || !term) return;
    let alive = true;
    const timer = setTimeout(() => {
      api(`/products/${product.code}/eligibility?amount=${amount}&term_months=${term}`)
        .then((data) => alive && setEligibility(data))
        .catch(() => {});
    }, 300);
    return () => { alive = false; clearTimeout(timer); };
  }, [product, amount, term]);

  const rate = eligibility?.estimated_rate ?? product?.base_rate ?? 0;
  const payment = useMemo(() => (product ? annuity(amount, rate, term) : 0), [product, amount, rate, term]);
  const interest = useMemo(() => (product ? totalInterest(amount, rate, term) : 0), [product, amount, rate, term]);
  const terms = product ? termOptions(product) : [];

  if (!product) {
    return (
      <div className="page">
        {error ? <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div> : <div className="skeleton" style={{ height: 320 }} />}
      </div>
    );
  }

  const step = product.max_amount > 3_000_000 ? 100_000 : 10_000;
  const amountOutside = amount < product.min_amount || amount > product.max_amount;

  async function submit() {
    setSubmitting(true);
    setError('');
    try {
      const app = await api('/applications', {
        method: 'POST',
        body: {
          product_code: product.code,
          amount: Number(amount),
          term_months: Number(term),
          purpose,
          purpose_details: details,
          submit: true,
        },
      });
      toast.push('Заявка отправлена в банк');
      navigate(`/app/applications/${app.id}`);
    } catch (e) {
      setError(e.message);
      setConfirmOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <Link to="/app/products" className="row gap-8 small muted" style={{ marginBottom: 16, fontWeight: 600 }}>
        <Icon name="arrowLeft" size={16} /> Все продукты
      </Link>

      <div className="row-between" style={{ alignItems: 'flex-start', gap: 20, flexWrap: 'wrap' }}>
        <div className="row gap-16" style={{ alignItems: 'flex-start' }}>
          <ProductIcon icon={product.icon} size={54} />
          <div>
            <div className="row gap-8 wrap">
              <h1 style={{ fontSize: 26, letterSpacing: '-0.025em' }}>{product.name}</h1>
              {product.badge && <span className="pill pill-red">{product.badge}</span>}
            </div>
            <p className="muted small mt-8" style={{ maxWidth: 620, lineHeight: 1.5 }}>{product.tagline}</p>
          </div>
        </div>
        <div className="row gap-8">
          <span className="tag"><Icon name="wallet" size={13} /> до {moneyShort(product.max_amount)}</span>
          <span className="tag"><Icon name="calendar" size={13} /> до {product.max_term_months} мес.</span>
          <span className="tag"><Icon name="percent" size={13} /> от {percent(product.base_rate)}</span>
        </div>
      </div>

      {error && <div className="banner banner-danger mt-16"><Icon name="alert" size={16} />{error}</div>}

      <div className="calc-grid mt-24">
        <div className="col gap-16">
          <div className="card card-pad">
            <div className="card-head">
              <div>
                <div className="card-title">Параметры заявки</div>
                <div className="tiny muted mt-8">Предварительный расчёт без влияния на кредитную историю</div>
              </div>
              <span className="pill pill-teal"><span className="dot" /> Расчёт онлайн</span>
            </div>

            <div className="field">
              <div className="row-between">
                <label>Сумма кредита</label>
                <span className="tiny muted">{moneyShort(product.min_amount)} — {moneyShort(product.max_amount)}</span>
              </div>
              <div className="input-group">
                <input
                  className="input input-lg" type="number" value={amount}
                  min={product.min_amount} max={product.max_amount} step={step}
                  onChange={(e) => setAmount(Number(e.target.value))}
                  onBlur={() => setAmount(clampAmount(product, Number(amount) || product.min_amount))}
                />
                <span className="suffix">₽</span>
              </div>
              <input
                className="range mt-8" type="range"
                min={product.min_amount} max={product.max_amount} step={step}
                value={Math.min(Math.max(amount, product.min_amount), product.max_amount)}
                onChange={(e) => setAmount(Number(e.target.value))}
              />
              {amountOutside && <div className="banner banner-warn mt-8"><Icon name="alert" size={15} />Сумма вне лимитов продукта</div>}
            </div>

            <div className="field mt-24">
              <label>Срок</label>
              <div className="choice-row">
                {terms.map((t) => (
                  <button key={t} className={`choice ${term === t ? 'active' : ''}`} onClick={() => setTerm(t)}>
                    {t} мес.
                  </button>
                ))}
              </div>
            </div>

            <div className="field mt-24">
              <label>Цель финансирования</label>
              <select className="select" value={purpose} onChange={(e) => setPurpose(e.target.value)}>
                {product.purposes.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>

            <div className="field mt-16">
              <label>Комментарий для банка</label>
              <textarea
                className="textarea" placeholder="Например: закупка кофе и упаковки на ноябрь–декабрь, поставщик — ООО «Зерно»"
                value={details} onChange={(e) => setDetails(e.target.value)} maxLength={500}
              />
              <span className="hint">Необязательно, но помогает андеррайтеру при ручном рассмотрении</span>
            </div>
          </div>

          <div className="card card-pad">
            <div className="card-title">Условия и требования</div>
            <p className="small muted mt-8" style={{ lineHeight: 1.55 }}>{product.description}</p>
            <div className="grid grid-2 mt-16" style={{ gap: 20 }}>
              <div>
                <div className="tiny muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                  Преимущества
                </div>
                <div className="col gap-8">
                  {product.features.map((f) => (
                    <div key={f} className="row gap-8 small"><Icon name="check" size={15} style={{ color: 'var(--green)' }} />{f}</div>
                  ))}
                </div>
              </div>
              <div>
                <div className="tiny muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                  Документы
                </div>
                <div className="col gap-8">
                  {product.documents.map((d) => (
                    <div key={d} className="row gap-8 small"><Icon name="doc" size={15} style={{ color: 'var(--muted)' }} />{d}</div>
                  ))}
                </div>
              </div>
            </div>
            <div className="divider" />
            <div className="row gap-16 wrap small muted">
              <span className="row gap-8"><Icon name="clock" size={15} /> Минимальный срок бизнеса: {product.min_business_age_months} мес.</span>
              <span className="row gap-8"><Icon name="shield" size={15} /> {product.requires_collateral ? 'Требуется залог' : 'Без залога'}</span>
            </div>
          </div>
        </div>

        <div className="col gap-16">
          <div className="calc-result">
            <div className="tiny" style={{ color: 'rgba(255,255,255,0.55)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
              Ежемесячный платёж
            </div>
            <div className="calc-payment">{money(payment)}</div>
            <div className="tiny" style={{ color: 'rgba(255,255,255,0.5)', marginTop: 4 }}>
              предварительно · ставка {percent(rate)}
            </div>
            <div className="calc-lines">
              <div className="calc-line"><span>Сумма</span><b>{money(amount)}</b></div>
              <div className="calc-line"><span>Срок</span><b>{term} мес.</b></div>
              <div className="calc-line"><span>Ставка</span><b>{percent(rate)} годовых</b></div>
              <div className="calc-line"><span>Проценты за весь срок</span><b>{money(interest)}</b></div>
            </div>
            <button
              className="btn btn-primary btn-block mt-24"
              onClick={() => { setConsent(false); setConfirmOpen(true); }}
            >
              Подать заявку <Icon name="arrowRight" size={16} />
            </button>
            <div className="tiny mt-12" style={{ color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>
              Итоговые условия банк подтвердит после проверки данных. Подача заявки не влияет на кредитную историю
              до момента одобрения.
            </div>
          </div>

          <div className="card card-pad">
            <div className="card-title" style={{ marginBottom: 6 }}>Предварительная проверка</div>
            <div className="tiny muted" style={{ marginBottom: 12 }}>Проверяем соответствие требованиям продукта по данным компании</div>
            {!eligibility && <div className="skeleton" style={{ height: 90 }} />}
            {eligibility?.checks.map((c) => (
              <div key={c.name} className="row gap-12" style={{ padding: '9px 0', alignItems: 'flex-start' }}>
                <span style={{
                  width: 22, height: 22, borderRadius: 7, display: 'grid', placeItems: 'center', flex: '0 0 auto',
                  background: c.ok ? 'var(--green-soft)' : 'var(--amber-soft)',
                  color: c.ok ? 'var(--green)' : 'var(--amber)',
                }}>
                  <Icon name={c.ok ? 'check' : 'alert'} size={13} />
                </span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600 }}>{c.name}</div>
                  <div className="tiny muted" style={{ lineHeight: 1.4, marginTop: 2 }}>{c.detail}</div>
                </div>
              </div>
            ))}
            {eligibility && !eligibility.eligible && (
              <div className="banner banner-warn mt-12">
                <Icon name="info" size={16} />
                Часть требований не выполнена — заявку можно отправить, но банк может запросить уточнения.
              </div>
            )}
          </div>
        </div>
      </div>

      {confirmOpen && (
        <Modal
          title="Отправить заявку в банк?"
          subtitle="Проверьте параметры перед отправкой"
          onClose={() => setConfirmOpen(false)}
          footer={(
            <>
              <button className="btn btn-secondary" onClick={() => setConfirmOpen(false)}>Изменить</button>
              <button className="btn btn-primary" disabled={!consent || submitting} onClick={submit}>
                {submitting ? <span className="spinner" /> : <Icon name="arrowRight" size={16} />}
                Отправить заявку
              </button>
            </>
          )}
        >
          <div className="offer-box" style={{ background: '#fff' }}>
            <div className="row gap-12">
              <ProductIcon icon={product.icon} size={42} />
              <div>
                <div style={{ fontWeight: 650 }}>{product.name}</div>
                <div className="tiny muted">{money(amount)} · {term} мес. · {percent(rate)}</div>
              </div>
            </div>
            <div className="divider" />
            <div className="kv"><span>Платёж в месяц</span><b>{money(payment)}</b></div>
            <div className="kv"><span>Цель</span><b>{purpose}</b></div>
            {details && <div className="kv"><span>Комментарий</span><b style={{ maxWidth: 300 }}>{details}</b></div>}
          </div>
          <label className="row gap-8 mt-16" style={{ alignItems: 'flex-start', cursor: 'pointer' }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} style={{ marginTop: 3 }} />
            <span className="small muted" style={{ lineHeight: 1.5 }}>
              Согласен на обработку данных и запрос кредитной истории в БКИ. Понимаю, что итоговые условия
              определяются банком по результатам проверки.
            </span>
          </label>
        </Modal>
      )}
    </div>
  );
}
