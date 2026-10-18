import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { moneyShort, percent } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import ProductIcon from '../components/ProductIcon.jsx';

const TASKS = [
  { label: 'Пополнить оборот', match: ['Оборотные средства', 'Закупка товара'] },
  { label: 'Купить оборудование', match: ['Оборудование', 'Расширение производства'] },
  { label: 'Закрыть кассовый разрыв', match: ['Кассовый разрыв', 'Платежи поставщикам'] },
  { label: 'Запустить новый проект', match: ['Недвижимость', 'Маркетинг и продвижение', 'Транспорт'] },
];

export default function Products() {
  const [products, setProducts] = useState([]);
  const [task, setTask] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api('/products').then(setProducts).catch((e) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!task) return products;
    const wanted = TASKS.find((t) => t.label === task)?.match || [];
    return products.filter((p) => p.purposes.some((x) => wanted.includes(x)));
  }, [products, task]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Кредитные продукты</h1>
          <p>
            Выберите задачу — покажем подходящие продукты, ставку и платёж. Предварительную проверку
            можно пройти до подачи заявки.
          </p>
        </div>
        <span className="pill pill-teal"><span className="dot" /> Синтетические данные</span>
      </div>

      <div className="card card-pad-sm" style={{ marginBottom: 18 }}>
        <div className="row wrap gap-8">
          <span className="small muted" style={{ fontWeight: 600, marginRight: 4 }}>Для какой задачи нужно финансирование?</span>
          <button className={`choice ${task === '' ? 'active' : ''}`} onClick={() => setTask('')}>Любая</button>
          {TASKS.map((t) => (
            <button key={t.label} className={`choice ${task === t.label ? 'active' : ''}`} onClick={() => setTask(t.label)}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div>}

      <div className="grid grid-auto">
        {filtered.map((p) => (
          <div key={p.code} className="card product-card">
            <div className="row-between">
              <ProductIcon icon={p.icon} />
              {p.badge && <span className="pill pill-red badge-corner">{p.badge}</span>}
            </div>
            <div className="row gap-8 mt-12" style={{ alignItems: 'baseline' }}>
              <span className="product-name">{p.name}</span>
            </div>
            <div className="product-tagline">{p.tagline}</div>
            <div style={{ marginTop: 14 }}>
              <div className="tiny muted">Ставка от</div>
              <div className="row gap-8" style={{ alignItems: 'baseline' }}>
                <span className="product-rate">{percent(p.base_rate)}</span>
                <span className="tiny muted">годовых</span>
              </div>
            </div>
            <div className="product-meta">
              <div><span>Сумма</span><b>{moneyShort(p.min_amount)} – {moneyShort(p.max_amount)}</b></div>
              <div><span>Срок</span><b>{p.min_term_months}–{p.max_term_months} мес.</b></div>
            </div>
            <div className="col gap-4 mt-12">
              {p.features.slice(0, 2).map((f) => (
                <div key={f} className="row gap-8 tiny muted">
                  <Icon name="check" size={13} style={{ color: 'var(--green)' }} /> {f}
                </div>
              ))}
            </div>
            <button className="btn btn-primary btn-sm mt-16" onClick={() => navigate(`/app/products/${p.code}`)}>
              Рассчитать условия <Icon name="arrowRight" size={15} />
            </button>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="card empty">
          <div className="empty-icon"><Icon name="search" size={24} /></div>
          <h3>Под выбранную задачу продуктов не нашлось</h3>
          <p>Сбросьте фильтр или посмотрите все продукты — банк подберёт вариант на рассмотрении.</p>
        </div>
      )}

      <div className="card card-pad mt-24" style={{ background: 'linear-gradient(140deg,#fff7f6,#fff)' }}>
        <div className="row gap-16 wrap">
          <div className="product-icon" style={{ background: '#fff', border: '1px solid var(--line)' }}>
            <Icon name="shield" size={22} />
          </div>
          <div className="grow" style={{ minWidth: 240 }}>
            <div className="card-title">Что проверит банк перед решением</div>
            <p className="small muted mt-8" style={{ lineHeight: 1.5 }}>
              Данные анкеты, кредитную историю (БКИ), статус в ЕГРЮЛ, задолженность по налогам и финансовые показатели.
              Часть проверок проходит автоматически — результат появится в заявке.
            </p>
          </div>
          <div className="row gap-24 wrap">
            {['БКИ', 'ЕГРЮЛ', 'ФНС', 'Скоринг'].map((x) => (
              <div key={x} className="col" style={{ alignItems: 'center', gap: 6 }}>
                <span className="pill pill-gray">{x}</span>
                <span className="tiny muted">мок-интеграция</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
