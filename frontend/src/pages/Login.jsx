import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { api } from '../lib/api.js';
import { useAuth } from '../context/AuthContext.jsx';
import Icon, { BrandMark } from '../components/Icons.jsx';

const FALLBACK = [
  { email: 'ivan@vesna.ru', role: 'client', who: 'Кофейня «Весна» — сильный профиль, автоматическое одобрение' },
  { email: 'petr@stroymaster.ru', role: 'client', who: 'ИП «СтройМастер» — заявка уходит андеррайтеру' },
  { email: 'anna@tehnopark.ru', role: 'client', who: 'ООО «ТехноПарк» — высокая нагрузка, ручное решение' },
  { email: 'underwriter@alfabank.ru', role: 'bank', who: 'Андеррайтер МСБ — очередь заявок и решения' },
];

const ICONS = { client: 'user', bank: 'shield' };

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('ivan@vesna.ru');
  const [password, setPassword] = useState('demo1234');
  const [accounts, setAccounts] = useState(FALLBACK);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api('/auth/demo-accounts', { auth: false })
      .then((data) => { if (data?.accounts?.length) setAccounts(data.accounts); })
      .catch(() => {});
  }, []);

  if (user) return <Navigate to={user.role === 'bank' ? '/bank' : '/app'} replace />;

  async function signIn(nextEmail = email, nextPassword = password) {
    setBusy(true);
    setError('');
    try {
      const account = await login(nextEmail, nextPassword);
      navigate(account.role === 'bank' ? '/bank' : '/app', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-side">
        <div className="row gap-12">
          <BrandMark size={42} />
          <div className="brand-text" style={{ color: '#fff' }}>
            <b style={{ fontSize: 16 }}>Альфа-Бизнес</b>
            <span style={{ color: 'rgba(255,255,255,0.55)' }}>Умный кредитный кабинет</span>
          </div>
        </div>

        <div>
          <span className="hero-eyebrow">Кредитный конвейер для МСП</span>
          <h1>Финансирование бизнеса — от потребности до денег на счёте</h1>
          <p>
            Один кабинет для предпринимателя и единый процесс для банка: подбор продукта,
            заявка, скоринг, ручное рассмотрение и подписание — с прозрачным статусом на каждом шаге.
          </p>
          <div className="auth-points">
            <div className="auth-point"><span className="num">1</span> Подбор продукта под задачу бизнеса и предварительный лимит</div>
            <div className="auth-point"><span className="num">2</span> Скоринг по данным БКИ, ЕГРЮЛ и ФНС — автоматическое решение</div>
            <div className="auth-point"><span className="num">3</span> Андеррайтер подключается только к пограничным заявкам</div>
            <div className="auth-point"><span className="num">4</span> Предложение, документы и выдача — внутри кабинета</div>
          </div>
        </div>

        <div className="tiny" style={{ color: 'rgba(255,255,255,0.42)', lineHeight: 1.6 }}>
          Демонстрационный прототип. Все компании, ИНН и финансовые показатели — синтетические.
          Интеграции с БКИ, ЕГРЮЛ и ФНС смоделированы локальными моками.
        </div>
      </div>

      <div className="auth-main">
        <div className="auth-box">
          <div className="row gap-8" style={{ marginBottom: 18 }}>
            <span className="pill pill-red"><Icon name="lock" size={13} /> Демо-доступ</span>
            <span className="tiny muted">пароль у всех: demo1234</span>
          </div>
          <h2>Вход в кредитный кабинет</h2>
          <p>Выберите тестовую роль или введите учётные данные вручную.</p>

          <form onSubmit={(e) => { e.preventDefault(); signIn(); }} className="col gap-16">
            <div className="field">
              <label>Email</label>
              <input
                className="input" type="email" value={email} autoComplete="username"
                onChange={(e) => setEmail(e.target.value)} placeholder="name@company.ru"
              />
            </div>
            <div className="field">
              <label>Пароль</label>
              <input
                className="input" type="password" value={password} autoComplete="current-password"
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••"
              />
            </div>
            {error && <div className="banner banner-danger"><Icon name="alert" size={16} />{error}</div>}
            <button className="btn btn-primary btn-block" disabled={busy} type="submit">
              {busy ? <span className="spinner" /> : <Icon name="arrowRight" size={17} />}
              Войти в кабинет
            </button>
          </form>

          <div className="divider" style={{ marginTop: 26 }} />
          <div className="tiny muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Быстрый вход в демо
          </div>
          <div className="demo-list">
            {accounts.map((a) => (
              <button key={a.email} className="demo-item" onClick={() => { setEmail(a.email); setPassword('demo1234'); signIn(a.email, 'demo1234'); }}>
                <span className={`avatar ${a.role === 'client' ? 'red' : ''}`}>
                  <Icon name={ICONS[a.role] || 'user'} size={16} />
                </span>
                <span className="grow">
                  <b>{a.email}</b>
                  <span>{a.who}</span>
                </span>
                <span className="pill pill-gray">{a.role === 'bank' ? 'Банк' : 'Клиент'}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
