import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { dateTime, money } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import StatusPill from '../components/StatusPill.jsx';

const FILTERS = [
  { key: 'all', label: 'Все' },
  { key: 'active', label: 'В работе' },
  { key: 'offer', label: 'Есть предложение' },
  { key: 'done', label: 'Выдано' },
  { key: 'declined', label: 'Отказы' },
];

const ACTIVE = ['submitted', 'validation', 'scoring', 'manual_review', 'info_requested', 'client_info_provided', 'signing'];
const OFFER = ['offer_issued', 'offer_accepted', 'signing'];

export default function Applications() {
  const [apps, setApps] = useState(null);
  const [filter, setFilter] = useState('all');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api('/applications').then(setApps).catch((e) => setError(e.message));
  }, []);

  const filtered = useMemo(() => {
    if (!apps) return [];
    if (filter === 'active') return apps.filter((a) => ACTIVE.includes(a.status));
    if (filter === 'offer') return apps.filter((a) => OFFER.includes(a.status));
    if (filter === 'done') return apps.filter((a) => a.status === 'funded');
    if (filter === 'declined') return apps.filter((a) => a.status === 'declined' || a.status === 'expired');
    return apps;
  }, [apps, filter]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Мои заявки</h1>
          <p>Все обращения в банк с прозрачным статусом: что проверяется сейчас и что требуется от вас.</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/app/products')}>
          <Icon name="plus" size={16} /> Новая заявка
        </button>
      </div>

      <div className="row gap-8 wrap" style={{ marginBottom: 16 }}>
        {FILTERS.map((f) => (
          <button key={f.key} className={`choice ${filter === f.key ? 'active' : ''}`} onClick={() => setFilter(f.key)}>
            {f.label}
          </button>
        ))}
      </div>

      {error && <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div>}

      <div className="card" style={{ overflow: 'hidden' }}>
        {apps === null ? (
          <div style={{ padding: 20 }}>
            {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 52, marginBottom: 10 }} />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            <div className="empty-icon"><Icon name="files" size={24} /></div>
            <h3>Заявок в этой категории нет</h3>
            <p>Выберите другой фильтр или создайте новую заявку — это займёт пару минут.</p>
            <button className="btn btn-primary btn-sm mt-16" onClick={() => navigate('/app/products')}>
              Перейти к продуктам
            </button>
          </div>
        ) : (
          <div className="scroll-x">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Заявка</th>
                  <th>Продукт</th>
                  <th>Сумма и срок</th>
                  <th>Статус</th>
                  <th>Создана</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id} className="clickable" onClick={() => navigate(`/app/applications/${a.id}`)}>
                    <td><b>{a.number}</b></td>
                    <td>{a.product.name}</td>
                    <td><b>{money(a.amount)}</b> <span className="tiny muted">/ {a.term_months} мес.</span></td>
                    <td><StatusPill status={a.status} live /></td>
                    <td className="muted">{dateTime(a.created_at)}</td>
                    <td style={{ textAlign: 'right' }}><Icon name="chevronRight" size={16} style={{ color: 'var(--muted-2)' }} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="row gap-16 mt-24 wrap">
        {['Автоматическое решение за минуты', 'Ручное рассмотрение — до 4 часов в рабочие дни', 'Документы и подписание — в кабинете'].map((t) => (
          <div key={t} className="row gap-8 small muted" style={{ padding: '8px 12px', background: '#fff', borderRadius: 10, border: '1px solid var(--line)' }}>
            <Icon name="checkCircle" size={15} style={{ color: 'var(--green)' }} /> {t}
          </div>
        ))}
      </div>
    </div>
  );
}
