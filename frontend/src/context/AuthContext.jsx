import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getToken, setToken } from '../lib/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(getToken());
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('alfacredit.user') || 'null');
    } catch {
      return null;
    }
  });
  const [company, setCompany] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('alfacredit.company') || 'null');
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(Boolean(getToken()));

  const persist = useCallback((nextToken, nextUser, nextCompany) => {
    setToken(nextToken);
    setTokenState(nextToken);
    setUser(nextUser);
    setCompany(nextCompany);
    if (nextUser) localStorage.setItem('alfacredit.user', JSON.stringify(nextUser));
    else localStorage.removeItem('alfacredit.user');
    if (nextCompany) localStorage.setItem('alfacredit.company', JSON.stringify(nextCompany));
    else localStorage.removeItem('alfacredit.company');
  }, []);

  const logout = useCallback(() => {
    persist('', null, null);
  }, [persist]);

  const login = useCallback(async (email, password) => {
    const data = await api('/auth/login', { method: 'POST', body: { email, password }, auth: false });
    persist(data.token, data.user, data.company);
    return data.user;
  }, [persist]);

  useEffect(() => {
    let cancelled = false;
    async function restore() {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const data = await api('/auth/me');
        if (!cancelled) {
          setUser(data.user);
          setCompany(data.company);
          localStorage.setItem('alfacredit.user', JSON.stringify(data.user));
          if (data.company) localStorage.setItem('alfacredit.company', JSON.stringify(data.company));
        }
      } catch {
        if (!cancelled) persist('', null, null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    restore();
    return () => { cancelled = true; };
  }, [persist]);

  useEffect(() => {
    const handler = () => persist('', null, null);
    window.addEventListener('alfacredit:unauthorized', handler);
    return () => window.removeEventListener('alfacredit:unauthorized', handler);
  }, [persist]);

  const value = useMemo(() => ({ token, user, company, loading, login, logout }), [token, user, company, loading, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
