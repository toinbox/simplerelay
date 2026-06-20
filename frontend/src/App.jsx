import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useState, useEffect, useCallback } from 'react';
import Dashboard from './pages/Dashboard';
import Providers from './pages/Providers';
import Logs from './pages/Logs';
import Wizard from './pages/Wizard';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import VerifyEmail from './pages/VerifyEmail';
import AdminUsers from './pages/AdminUsers';
import AdminProxies from './pages/AdminProxies';
import AdminLimits from './pages/AdminLimits';
import AdminLogs from './pages/AdminLogs';
import LanguageSwitcher from './components/LanguageSwitcher';

export default function App() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [needsSetup, setNeedsSetup] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore session
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  // Check setup status when authenticated
  useEffect(() => {
    if (!token) return;
    fetch('/api/setup-status', {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(r => {
        if (r.status === 401) { handleLogout(); return null; }
        return r.json();
      })
      .then(data => { if (data) setNeedsSetup(data.needs_setup); })
      .catch(() => setNeedsSetup(false));
  }, [token]);

  const handleLogin = useCallback((userData, accessToken) => {
    setUser(userData);
    setToken(accessToken);
    navigate('/dashboard');
  }, [navigate]);

  const handleLogout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setToken(null);
    setNeedsSetup(null);
    fetch('/api/auth/logout', { method: 'POST' });
    navigate('/login');
  }, [navigate]);

  if (loading) {
    return <div className="loading">{t('common.loading')}</div>;
  }

  // Not authenticated — show auth pages
  if (!user) {
    return (
      <div className="app">
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/verify" element={<VerifyEmail />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </div>
    );
  }

  // Authenticated but needs first relay setup
  if (needsSetup) {
    return (
      <div className="app">
        <Wizard token={token} onComplete={() => setNeedsSetup(false)} />
      </div>
    );
  }

  const isAdmin = user.role === 'admin';

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-header">
          <div className="logo">
            <span className="logo-icon">⚡</span>
            <span className="logo-text">{t('app.name')}</span>
          </div>
        </div>

        <div className="nav-links">
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <span className="nav-icon">📊</span>
            {t('nav.dashboard')}
          </NavLink>
          <NavLink to="/providers" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <span className="nav-icon">📧</span>
            {t('nav.providers')}
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
            <span className="nav-icon">📋</span>
            {t('nav.logs')}
          </NavLink>

          {isAdmin && (
            <>
              <div style={{ borderTop: '1px solid var(--border)', margin: '8px 0' }} />
              <NavLink to="/admin/users" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <span className="nav-icon">👥</span>
                {t('admin.users')}
              </NavLink>
              <NavLink to="/admin/proxies" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <span className="nav-icon">🌐</span>
                {t('admin.proxies')}
              </NavLink>
              <NavLink to="/admin/limits" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <span className="nav-icon">📊</span>
                {t('admin.provider_limits')}
              </NavLink>
              <NavLink to="/admin/logs" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                <span className="nav-icon">📋</span>
                {t('admin.logs')}
              </NavLink>
            </>
          )}
        </div>

        <div className="sidebar-footer">
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {user.email}
            {isAdmin && <span className="badge badge-warning" style={{ marginLeft: 6 }}>admin</span>}
          </div>
          <button className="btn btn-secondary btn-sm" style={{ width: '100%', justifyContent: 'center' }} onClick={handleLogout}>
            {t('auth.logout')}
          </button>
          <div style={{ marginTop: 8 }}>
            <LanguageSwitcher />
          </div>
        </div>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/dashboard" element={<Dashboard token={token} />} />
          <Route path="/providers" element={<Providers token={token} />} />
          <Route path="/clients" element={<Navigate to="/providers" replace />} />
          <Route path="/logs" element={<Logs token={token} />} />
          <Route path="/wizard" element={<Wizard token={token} onComplete={() => {}} />} />
          {isAdmin && (
            <>
              <Route path="/admin/users" element={<AdminUsers token={token} />} />
              <Route path="/admin/proxies" element={<AdminProxies token={token} />} />
              <Route path="/admin/limits" element={<AdminLimits token={token} />} />
              <Route path="/admin/logs" element={<AdminLogs token={token} />} />
            </>
          )}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </main>
    </div>
  );
}
