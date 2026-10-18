import { useEffect, useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import Icon, { BrandMark } from './Icons.jsx';
import Modal from './Modal.jsx';
import { api } from '../lib/api.js';

const CLIENT_NAV = [
  { to: '/app', label: 'Обзор', icon: 'home', end: true },
  { to: '/app/products', label: 'Кредитные продукты', icon: 'grid' },
  { to: '/app/applications', label: 'Мои заявки', icon: 'files' },
  { to: '/app/news', label: 'Новости', icon: 'news' },
  { to: '/app/company', label: 'Моя компания', icon: 'building' },
];

const BANK_NAV = [
  { to: '/bank', label: 'Очередь заявок', icon: 'files', end: true },
  { to: '/bank/analytics', label: 'Аналитика конвейера', icon: 'chart' },
];

const TITLES = [
  [/^\/app$/, 'Обзор'],
  [/^\/app\/products\/[^/]+$/, 'Кредитный продукт'],
  [/^\/app\/products$/, 'Кредитные продукты'],
  [/^\/app\/applications\/[^/]+$/, 'Заявка'],
  [/^\/app\/applications$/, 'Мои заявки'],
  [/^\/app\/news$/, 'Новости для вашего бизнеса'],
  [/^\/app\/company$/, 'Моя компания'],
  [/^\/bank\/applications\/[^/]+$/, 'Заявка · бэк-офис'],
  [/^\/bank\/analytics$/, 'Аналитика конвейера'],
  [/^\/bank$/, 'Очередь заявок'],
];

function initials(name = '') {
  return name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
}

export default function Layout({ role }) {
  const { user, company, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [switchOpen, setSwitchOpen] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [switching, setSwitching] = useState(false);

  useEffect(() => {
    if (!switchOpen || accounts.length) return;
    api('/auth/demo-accounts', { auth: false }).then((d) => setAccounts(d.accounts || [])).catch(() => {});
  }, [switchOpen, accounts.length]);

  async function switchAccount(email) {
    setSwitching(true);
    try {
      // переключение демо-роли: выходим и входим под другой учётной записью
      logout();
      const data = await api('/auth/login', { method: 'POST', body: { email, password: 'demo1234' }, auth: false });
      window.localStorage.setItem('alfacredit.token', data.token);
      window.localStorage.setItem('alfacredit.user', JSON.stringify(data.user));
      if (data.company) window.localStorage.setItem('alfacredit.company', JSON.stringify(data.company));
      window.location.href = data.user.role === 'bank' ? '/bank' : '/app';
    } catch (e) {
      setSwitching(false);
    }
  }

  useEffect(() => { setMenuOpen(false); }, [location.pathname]);

  const nav = role === 'bank' ? BANK_NAV : CLIENT_NAV;
  const title = TITLES.find(([re]) => re.test(location.pathname))?.[1] || 'Кабинет';
  const home = role === 'bank' ? '/bank' : '/app';

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <BrandMark size={40} />
          <div className="brand-text">
            <b>Альфа-Бизнес</b>
            <span>{role === 'bank' ? 'Рабочее место андеррайтера' : 'Кредитный кабинет'}</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">{role === 'bank' ? 'Бэк-офис' : 'Кабинет'}</div>
          {nav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Icon name={item.icon} size={19} />
              {item.label}
            </NavLink>
          ))}
          <div className="nav-section">Демо</div>
          <button className="nav-link" onClick={() => setSwitchOpen(true)} style={{ border: 'none', background: 'transparent', width: '100%', textAlign: 'left' }}>
            <Icon name="switch" size={19} />
            Сменить роль
          </button>
        </nav>

        <div className="sidebar-footer">
          {role === 'client' && company ? (
            <div className="row gap-8" style={{ marginBottom: 12 }}>
              <div className="avatar red" style={{ width: 30, height: 30, borderRadius: 8, fontSize: 11 }}>
                {company.legal_form === 'ИП' ? 'ИП' : 'ООО'}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {company.short_name}
                </div>
                <div className="tiny muted">ИНН {company.inn}</div>
              </div>
            </div>
          ) : null}
          <div className="row gap-8">
            <div className="avatar">{initials(user?.full_name)}</div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: 12.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.full_name}
              </div>
              <div className="tiny muted" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user?.position || (role === 'bank' ? 'Сотрудник банка' : 'Предприниматель')}
              </div>
            </div>
            <button
              className="icon-btn"
              title="Выйти"
              onClick={() => { logout(); navigate('/login'); }}
              style={{ width: 32, height: 32 }}
            >
              <Icon name="logout" size={16} />
            </button>
          </div>
        </div>
      </aside>

      {menuOpen && <div className="sidebar-scrim" onClick={() => setMenuOpen(false)} />}

      <div className="main">
        <header className="topbar">
          <div className="row gap-12">
            <button className="icon-btn" onClick={() => setMenuOpen(true)} style={{ display: 'none' }} id="mobile-menu-btn">
              <Icon name="menu" size={18} />
            </button>
            <div className="topbar-title">
              <span>{title}</span>
            </div>
          </div>
          <div className="topbar-actions">
            {role === 'bank' && <span className="pill pill-dark"><Icon name="shield" size={13} /> Бэк-офис</span>}
            {role === 'client' && <span className="pill pill-teal"><span className="dot" /> Демо-данные</span>}
            <button className="icon-btn" title="Уведомления">
              <Icon name="bell" size={18} />
            </button>
            <button className="user-chip" onClick={() => navigate(home)}>
              <div className={`avatar ${role === 'client' ? 'red' : ''}`}>{initials(user?.full_name)}</div>
              <div className="user-meta">
                <b>{user?.full_name}</b>
                <span>{role === 'bank' ? user?.position || 'Банк' : company?.short_name || 'Бизнес'}</span>
              </div>
            </button>
          </div>
        </header>
        <Outlet />
      </div>
      {switchOpen && (
        <Modal
          title="Демонстрационные роли"
          subtitle="Пароль для всех учётных записей: demo1234"
          onClose={() => setSwitchOpen(false)}
        >
          <div className="demo-list">
            {accounts.map((a) => (
              <button key={a.email} className="demo-item" disabled={switching} onClick={() => switchAccount(a.email)}>
                <span className={`avatar ${a.role === 'client' ? 'red' : ''}`}>
                  <Icon name={a.role === 'bank' ? 'shield' : 'user'} size={16} />
                </span>
                <span className="grow">
                  <b>{a.email}</b>
                  <span>{a.who}</span>
                </span>
                <span className="pill pill-gray">{a.role === 'bank' ? 'Банк' : 'Клиент'}</span>
              </button>
            ))}
            {accounts.length === 0 && <div className="small muted">Загружаем список…</div>}
          </div>
          <div className="banner banner-info mt-16">
            <Icon name="info" size={16} />
            Переключение ролей — только для демонстрации: в проде доступы разделены и выдаются по принципу
            минимальных привилегий.
          </div>
        </Modal>
      )}
      <style>{`@media (max-width: 860px){ #mobile-menu-btn{display:grid !important} }`}</style>
    </div>
  );
}
