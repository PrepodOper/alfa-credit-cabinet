import { useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '../lib/api.js';
import { dateShort, timeAgo } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import Modal from '../components/Modal.jsx';

const CATEGORIES = [
  { key: 'all', label: 'Все' },
  { key: 'bank', label: 'Альфа-Банк' },
  { key: 'market', label: 'Рынок' },
  { key: 'support', label: 'Поддержка' },
  { key: 'product', label: 'Продукты' },
  { key: 'education', label: 'База знаний' },
];

const CATEGORY_ICON = { bank: 'bank', market: 'chart', support: 'shield', product: 'sparkles', education: 'doc' };

export default function News() {
  const location = useLocation();
  const [category, setCategory] = useState('all');
  const [data, setData] = useState(null);
  const [active, setActive] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    api(`/news?category=${category}&limit=30`)
      .then((d) => {
        if (!alive) return;
        setData(d);
        if (location.state?.openId) {
          const found = d.items.find((i) => i.id === location.state.openId);
          if (found) setActive(found);
          window.history.replaceState({}, '');
        }
      })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [category]);

  const items = data?.items || [];
  const feature = useMemo(() => items[0], [items]);
  const rest = useMemo(() => items.slice(1), [items]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Новости для вашего бизнеса</h1>
          <p>
            Лента настроена под профиль компании и стадию кредитного пути: важные изменения условий,
            объяснения по заявке и рекомендации следующих шагов.
          </p>
        </div>
        {data?.context && (
          <div className="card card-pad-sm" style={{ minWidth: 240 }}>
            <div className="tiny muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              Персонализация
            </div>
            <div className="row gap-8 wrap mt-8">
              <span className="tag tag-red"><Icon name="building" size={12} /> {data.context.industry || 'Отрасль'}</span>
              <span className="tag"><Icon name="files" size={12} /> {data.context.stage_label}</span>
              {data.context.has_alfa_account && <span className="tag"><Icon name="wallet" size={12} /> Клиент банка</span>}
            </div>
          </div>
        )}
      </div>

      <div className="row gap-8 wrap" style={{ marginBottom: 18 }}>
        {CATEGORIES.map((c) => (
          <button key={c.key} className={`choice ${category === c.key ? 'active' : ''}`} onClick={() => setCategory(c.key)}>
            {c.label}
          </button>
        ))}
      </div>

      {error && <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div>}

      {feature && (
        <div className="news-hero" style={{ marginBottom: 16 }}>
          <div className="news-feature" style={{ cursor: 'pointer' }} onClick={() => setActive(feature)}>
            <div className="row gap-8">
              <span className="pill pill-red"><Icon name={CATEGORY_ICON[feature.category] || 'news'} size={12} /> {feature.category_label}</span>
              {feature.is_personal && <span className="pill pill-green"><span className="dot" /> Для вас</span>}
            </div>
            <h2>{feature.title}</h2>
            <p>{feature.summary}</p>
            <div className="row gap-12 tiny" style={{ color: 'rgba(255,255,255,0.5)', marginTop: 18, position: 'relative', zIndex: 1 }}>
              <span>{feature.source}</span><span>·</span><span>{timeAgo(feature.published_at)}</span><span>·</span>
              <span>{feature.reading_time_min} мин</span>
            </div>
          </div>

          <div className="card card-pad">
            <div className="row gap-8">
              <Icon name="sparkles" size={17} style={{ color: 'var(--red)' }} />
              <div className="card-title">Почему это в вашей ленте</div>
            </div>
            <p className="small muted mt-12" style={{ lineHeight: 1.55 }}>
              Лента собирается из общего потока по трём сигналам: отрасль компании,
              текущая стадия работы с банком и профиль обслуживания.
            </p>
            <div className="col gap-8 mt-16">
              {[
                ['Отрасль', data?.context?.industry || '—'],
                ['Стадия', data?.context?.stage_label || '—'],
                ['Клиент Альфа-Банка', data?.context?.has_alfa_account ? 'да' : 'нет'],
              ].map(([k, v]) => (
                <div key={k} className="kv" style={{ padding: '7px 0' }}><span>{k}</span><b>{v}</b></div>
              ))}
            </div>
            <div className="banner banner-info mt-12">
              <Icon name="info" size={16} />
              Персональные новости отмечены бейджем «Для вас».
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-auto">
        {rest.map((n) => (
          <div key={n.id} className="card news-card" onClick={() => setActive(n)}>
            <div className="row-between">
              <span className="news-cat">{n.category_label}</span>
              {n.is_personal && <span className="pill pill-green" style={{ height: 22 }}><span className="dot" /> Для вас</span>}
            </div>
            <div className="news-title">{n.title}</div>
            <div className="news-summary">{n.summary}</div>
            {n.relevance?.length > 0 && (
              <div className="row gap-4 wrap">
                {n.relevance.slice(0, 2).map((r) => <span key={r} className="tag" style={{ fontSize: 11 }}>{r}</span>)}
              </div>
            )}
            <div className="news-meta">
              <span>{n.source}</span><span>·</span><span>{dateShort(n.published_at)}</span><span>·</span>
              <span>{n.reading_time_min} мин</span>
            </div>
          </div>
        ))}
      </div>

      {items.length === 0 && !error && (
        <div className="card empty">
          <div className="empty-icon"><Icon name="news" size={24} /></div>
          <h3>В этой категории пока нет материалов</h3>
          <p>Выберите другой раздел ленты.</p>
        </div>
      )}

      {active && (
        <Modal
          wide
          title={active.title}
          subtitle={`${active.category_label} · ${active.source} · ${dateShort(active.published_at)}`}
          onClose={() => setActive(null)}
          footer={<button className="btn btn-secondary" onClick={() => setActive(null)}>Закрыть</button>}
        >
          <p className="small" style={{ lineHeight: 1.7, color: 'var(--ink-2)' }}>{active.summary}</p>
          <p className="small muted mt-16" style={{ lineHeight: 1.75 }}>{active.body}</p>
          {active.relevance?.length > 0 && (
            <div className="banner banner-info mt-16">
              <Icon name="sparkles" size={16} />
              <span>Материал подобран для вас: {active.relevance.join(' · ')}</span>
            </div>
          )}
          <div className="tiny muted mt-16">{active.reading_time_min} мин чтения · демонстрационная публикация</div>
        </Modal>
      )}
    </div>
  );
}
