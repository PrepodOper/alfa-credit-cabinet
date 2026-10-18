import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../context/AuthContext.jsx';
import { money, moneyShort, percent, riskClassLabel, timeAgo } from '../lib/format.js';
import Icon from '../components/Icons.jsx';
import ProductIcon from '../components/ProductIcon.jsx';
import ScoreRing from '../components/ScoreRing.jsx';
import StatusPill from '../components/StatusPill.jsx';

function greeting() {
  const h = new Date().getHours();
  if (h < 5) return 'Доброй ночи';
  if (h < 12) return 'Доброе утро';
  if (h < 18) return 'Добрый день';
  return 'Добрый вечер';
}

export default function Dashboard() {
  const { user, company } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [news, setNews] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    Promise.all([api('/dashboard'), api('/news?limit=4')])
      .then(([dash, feed]) => {
        if (!alive) return;
        setData(dash);
        setNews(feed.items || []);
      })
      .catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, []);

  const firstName = (user?.full_name || '').split(' ')[1] || (user?.full_name || '').split(' ')[0] || 'Коллега';
  const meter = data?.credit_meter;
  const active = data?.active_application;

  return (
    <div className="page">
      <section className="hero">
        <div>
          <div className="hero-eyebrow">
            <Icon name="sparkles" size={14} /> Кредитный кабинет · {company?.legal_form} {company?.short_name || ''}
          </div>
          <h1>{greeting()}, {firstName}! Подберём финансирование под вашу задачу</h1>
          <p>
            Предварительный лимит рассчитан по данным о бизнесе, оборотам и кредитной истории.
            Подайте заявку — решение по типовым запросам занимает несколько минут.
          </p>
          <div className="hero-actions">
            <button className="btn btn-primary" onClick={() => navigate('/app/products')}>
              <Icon name="grid" size={17} /> Подобрать продукт
            </button>
            <button className="btn btn-secondary" onClick={() => navigate('/app/applications')}>
              Мои заявки <Icon name="arrowRight" size={16} />
            </button>
          </div>
        </div>

        <div className="gauge-card">
          <div className="row-between" style={{ alignItems: 'flex-start' }}>
            <div>
              <div className="gauge-label">{meter?.label || 'Предварительный лимит'}</div>
              <div className="gauge-value">{meter ? money(meter.amount) : '—'}</div>
            </div>
            {meter && <ScoreRing score={meter.score} riskClass={meter.risk_class} size={62} stroke={6} light />}
          </div>
          <div className="gauge-meta">
            <div><span>Ставка от</span><b>{meter ? percent(meter.rate) : '—'}</b></div>
            <div><span>Риск-класс</span><b>{meter?.risk_class} · {riskClassLabel(meter?.risk_class)}</b></div>
            <div><span>Долговая нагрузка</span><b>{meter ? percent(meter.debt_load_percent) : '—'}</b></div>
          </div>
        </div>
      </section>

      {error && <div className="banner banner-danger mt-16"><Icon name="alert" size={16} />{error}</div>}

      <div className="grid grid-4 mt-16">
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Всего заявок</div>
            <div className="stat-icon"><Icon name="files" size={17} /></div>
          </div>
          <div className="stat-value">{data?.stats.applications_total ?? '—'}</div>
          <div className="stat-hint">{data?.stats.active_count ? `${data.stats.active_count} в работе` : 'Нет активных заявок'}</div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Портфель</div>
            <div className="stat-icon"><Icon name="wallet" size={17} /></div>
          </div>
          <div className="stat-value">{data ? moneyShort(data.stats.portfolio) : '—'}</div>
          <div className="stat-hint green">{data?.stats.funded_count || 0} выданных кредита</div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Платёж по кредитам</div>
            <div className="stat-icon"><Icon name="calendar" size={17} /></div>
          </div>
          <div className="stat-value">{data ? money(data.stats.monthly_payment) : '—'}</div>
          <div className="stat-hint">в месяц по действующим договорам</div>
        </div>
        <div className="card stat">
          <div className="row-between">
            <div className="stat-label">Кредитный рейтинг</div>
            <div className="stat-icon"><Icon name="shield" size={17} /></div>
          </div>
          <div className="stat-value">{meter ? `${meter.score}/1000` : '—'}</div>
          <div className="stat-hint green">Класс {meter?.risk_class} — {riskClassLabel(meter?.risk_class)}</div>
        </div>
      </div>

      <div className="mt-24" style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, alignItems: 'start' }}>
        <div className="col gap-16">
          {active ? (
            <div className="card card-pad">
              <div className="row-between">
                <div className="row gap-12">
                  <ProductIcon icon={active.product.icon} size={42} />
                  <div>
                    <div className="row gap-8 wrap">
                      <span className="card-title">{active.product.name}</span>
                      <StatusPill status={active.status} live />
                    </div>
                    <div className="tiny muted mt-8">Заявка № {active.number} · {money(active.amount)} на {active.term_months} мес.</div>
                  </div>
                </div>
                <Link className="btn btn-secondary btn-sm" to={`/app/applications/${active.id}`}>
                  Открыть <Icon name="chevronRight" size={14} />
                </Link>
              </div>
              <div className="mt-16">
                <div className="row-between tiny muted" style={{ marginBottom: 8 }}>
                  <span>{active.status_label}</span>
                  <span>{active.progress_percent}%</span>
                </div>
                <div className="progress-track">
                  <div
                    className={`progress-fill ${active.status === 'declined' ? 'red' : active.status === 'funded' ? 'green' : ''}`}
                    style={{ width: `${active.progress_percent}%` }}
                  />
                </div>
                <div className="row gap-8 mt-12">
                  <Icon name="info" size={15} style={{ color: 'var(--muted)' }} />
                  <span className="small muted">{active.next_action}</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="card card-pad">
              <div className="row-between">
                <div>
                  <div className="card-title">Активных заявок нет</div>
                  <p className="small muted mt-8">
                    Выберите продукт — мы рассчитаем условия и покажем предварительное решение до отправки заявки.
                  </p>
                </div>
                <button className="btn btn-primary btn-sm" onClick={() => navigate('/app/products')}>
                  <Icon name="plus" size={15} /> Новая заявка
                </button>
              </div>
            </div>
          )}

          <div>
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div className="section-title">Рекомендуем вашему бизнесу</div>
              <Link to="/app/products" className="small text-red" style={{ fontWeight: 600 }}>Все продукты</Link>
            </div>
            <div className="grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0,1fr))' }}>
              {(data?.recommendations || []).slice(0, 2).map((p) => (
                <div key={p.code} className="card product-card">
                  <div className="row-between">
                    <ProductIcon icon={p.icon} />
                    <span className={`pill ${p.eligible ? 'pill-green' : 'pill-gray'}`}>
                      {p.eligible ? 'Доступно' : 'Недоступно'}
                    </span>
                  </div>
                  <div className="product-name mt-12">{p.name}</div>
                  <div className="product-tagline">{p.tagline}</div>
                  <div className="row-between" style={{ marginTop: 14 }}>
                    <div>
                      <div className="tiny muted">Ставка от</div>
                      <div className="product-rate">{percent(p.estimated_rate)}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div className="tiny muted">До</div>
                      <div style={{ fontWeight: 650 }}>{moneyShort(p.max_amount)}</div>
                    </div>
                  </div>
                  <button
                    className="btn btn-secondary btn-sm mt-16"
                    onClick={() => navigate(`/app/products/${p.code}`)}
                  >
                    {p.eligible ? 'Рассчитать и подать' : 'Посмотреть условия'}
                    <Icon name="arrowRight" size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="col gap-16">
          <div className="card card-pad">
            <div className="row-between" style={{ marginBottom: 14 }}>
              <div className="card-title">Лента для вашего бизнеса</div>
              <Link to="/app/news" className="tiny text-red" style={{ fontWeight: 600 }}>Все</Link>
            </div>
            <div className="col gap-16">
              {news.length === 0 && <div className="small muted">Загружаем новости…</div>}
              {news.slice(0, 3).map((n) => (
                <div key={n.id} style={{ cursor: 'pointer' }} onClick={() => navigate('/app/news', { state: { openId: n.id } })}>
                  <div className="tiny" style={{ color: 'var(--red-600)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {n.category_label}
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, lineHeight: 1.4, marginTop: 4 }}>{n.title}</div>
                  <div className="tiny muted mt-8">{timeAgo(n.published_at)} · {n.reading_time_min} мин</div>
                </div>
              ))}
            </div>
          </div>

          <div className="card card-pad" style={{ background: 'linear-gradient(160deg,#fff7f6,#fff)' }}>
            <div className="row gap-8">
              <Icon name="sparkles" size={18} style={{ color: 'var(--red)' }} />
              <div className="card-title">Умный помощник</div>
            </div>
            <p className="small muted mt-12" style={{ lineHeight: 1.55 }}>
              Не знаете, какой продукт подойдёт? Ответьте на 3 вопроса — подберём вариант и рассчитаем платёж.
            </p>
            <button className="btn btn-dark btn-sm mt-16" onClick={() => navigate('/app/products')}>
              Подобрать финансирование
            </button>
          </div>

          {company && (
            <div className="card card-pad">
              <div className="card-title" style={{ marginBottom: 12 }}>Профиль компании</div>
              <div className="kv"><span>Отрасль</span><b>{company.industry}</b></div>
              <div className="kv"><span>Регион</span><b>{company.region}</b></div>
              <div className="kv"><span>Сотрудники</span><b>{company.employees_count}</b></div>
              <div className="kv"><span>Клиент банка</span><b>{company.has_alfa_account ? 'Да' : 'Нет'}</b></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
