import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './context/AuthContext.jsx';
import Layout from './components/Layout.jsx';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Products from './pages/Products.jsx';
import ProductDetail from './pages/ProductDetail.jsx';
import Applications from './pages/Applications.jsx';
import ApplicationDetail from './pages/ApplicationDetail.jsx';
import News from './pages/News.jsx';
import Company from './pages/Company.jsx';
import BankQueue from './pages/BankQueue.jsx';
import BankApplication from './pages/BankApplication.jsx';
import BankAnalytics from './pages/BankAnalytics.jsx';

function FullLoader() {
  return (
    <div className="auth-main" style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
      <div className="col gap-12" style={{ alignItems: 'center' }}>
        <div className="spinner dark" style={{ width: 26, height: 26 }} />
        <span className="small muted">Загружаем кабинет…</span>
      </div>
    </div>
  );
}

function Protected({ role, children }) {
  const { user, loading } = useAuth();
  if (loading) return <FullLoader />;
  if (!user) return <Navigate to="/login" replace />;
  if (role && user.role !== role) return <Navigate to={user.role === 'bank' ? '/bank' : '/app'} replace />;
  return children;
}

function RootRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <FullLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === 'bank' ? '/bank' : '/app'} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RootRedirect />} />

      <Route
        path="/app"
        element={<Protected role="client"><Layout role="client" /></Protected>}
      >
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="products/:code" element={<ProductDetail />} />
        <Route path="applications" element={<Applications />} />
        <Route path="applications/:id" element={<ApplicationDetail />} />
        <Route path="news" element={<News />} />
        <Route path="company" element={<Company />} />
      </Route>

      <Route
        path="/bank"
        element={<Protected role="bank"><Layout role="bank" /></Protected>}
      >
        <Route index element={<BankQueue />} />
        <Route path="applications/:id" element={<BankApplication />} />
        <Route path="analytics" element={<BankAnalytics />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
