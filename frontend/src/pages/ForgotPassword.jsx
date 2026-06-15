import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Link } from 'react-router-dom';

export default function ForgotPassword() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      setSent(true);
    } catch {}
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="logo" style={{ justifyContent: 'center', marginBottom: 24 }}>
          <span className="logo-icon">⚡</span>
          <span className="logo-text" style={{ fontSize: 24 }}>{t('app.name')}</span>
        </div>

        <h1 className="auth-title">{t('auth.forgot_password')}</h1>

        {sent ? (
          <div>
            <div className="alert alert-success">{t('auth.reset_sent')}</div>
            <Link to="/login" className="btn btn-secondary" style={{ width: '100%', justifyContent: 'center' }}>
              {t('auth.login')}
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 16 }}>{t('auth.forgot_desc')}</p>
            <div className="form-group">
              <label className="form-label">{t('auth.email')}</label>
              <input
                className="form-input"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
              {loading ? t('common.loading') : t('auth.send_reset')}
            </button>
          </form>
        )}

        <div className="auth-links">
          <Link to="/login">{t('common.back')}</Link>
        </div>
      </div>
    </div>
  );
}
