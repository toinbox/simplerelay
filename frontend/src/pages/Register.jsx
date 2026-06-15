import { useTranslation } from 'react-i18next';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import LanguageSwitcher from '../components/LanguageSwitcher';

export default function Register() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError(t('auth.password_min'));
      return;
    }

    setLoading(true);

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name: name || null }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || t('auth.register_error'));
        setLoading(false);
        return;
      }

      setSuccess(true);
    } catch {
      setError(t('auth.register_error'));
    }
    setLoading(false);
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div style={{ marginBottom: 20 }}><LanguageSwitcher /></div>
        <div className="logo" style={{ justifyContent: 'center', marginBottom: 24 }}>
          <span className="logo-icon">⚡</span>
          <span className="logo-text" style={{ fontSize: 24 }}>{t('app.name')}</span>
        </div>

        {success ? (
          <div>
            <div className="alert alert-success">{t('auth.verify_sent', { email })}</div>
            <div className="auth-links">
              <Link to="/login">{t('auth.login')}</Link>
            </div>
          </div>
        ) : (
          <>
            <h1 className="auth-title">{t('auth.register')}</h1>

            {error && <div className="alert alert-error">{error}</div>}

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">{t('auth.name')}</label>
                <input className="form-input" type="text" value={name} onChange={e => setName(e.target.value)} autoFocus />
              </div>
              <div className="form-group">
                <label className="form-label">{t('auth.email')}</label>
                <input className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
              <div className="form-group">
                <label className="form-label">{t('auth.password')}</label>
                <input className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} />
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('auth.password_min')}</span>
              </div>

              <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                {loading ? t('common.loading') : t('auth.register')}
              </button>
            </form>

            <div className="auth-links">
              <span style={{ color: 'var(--text-muted)' }}>{t('auth.have_account')} </span>
              <Link to="/login">{t('auth.login')}</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
