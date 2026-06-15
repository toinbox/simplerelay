import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import LanguageSwitcher from '../components/LanguageSwitcher';

export default function Login({ onLogin }) {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notVerified, setNotVerified] = useState(false);
  const [resendSent, setResendSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setNotVerified(false);
    setLoading(true);

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (res.status === 403) {
        const data = await res.json();
        if (data.detail && data.detail.includes('not verified')) {
          setNotVerified(true);
        } else {
          setError(data.detail || t('auth.login_error'));
        }
        setLoading(false);
        return;
      }

      if (!res.ok) {
        setError(t('auth.login_error'));
        setLoading(false);
        return;
      }

      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      onLogin(data.user, data.access_token);
    } catch {
      setError(t('auth.login_error'));
    }
    setLoading(false);
  };

  const resendVerification = async () => {
    await fetch('/api/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    setResendSent(true);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div style={{ marginBottom: 20 }}><LanguageSwitcher /></div>
        <div className="logo" style={{ justifyContent: 'center', marginBottom: 24 }}>
          <span className="logo-icon">⚡</span>
          <span className="logo-text" style={{ fontSize: 24 }}>{t('app.name')}</span>
        </div>

        <h1 className="auth-title">{t('auth.login')}</h1>

        {error && <div className="alert alert-error">{error}</div>}

        {notVerified && (
          <div className="alert alert-warning">
            {t('auth.not_verified')}
            {resendSent ? (
              <div style={{ marginTop: 8 }}>{t('auth.verify_resent')}</div>
            ) : (
              <button className="btn btn-sm btn-secondary" style={{ marginTop: 8 }} onClick={resendVerification}>
                {t('auth.resend_verification')}
              </button>
            )}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">{t('auth.email')}</label>
            <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">{t('auth.password')}</label>
            <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>

          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
            {loading ? t('common.loading') : t('auth.login')}
          </button>
        </form>

        <div className="auth-links">
          <Link to="/forgot-password">{t('auth.forgot_password')}</Link>
          <br />
          <span style={{ color: 'var(--text-muted)' }}>{t('auth.no_account')} </span>
          <Link to="/register">{t('auth.register')}</Link>
        </div>
      </div>
    </div>
  );
}
