import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

export default function VerifyEmail() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading, success, error

  useEffect(() => {
    const token = searchParams.get('token');
    if (!token) {
      setStatus('error');
      return;
    }

    fetch(`/api/auth/verify?token=${token}`)
      .then(r => {
        if (r.ok) setStatus('success');
        else setStatus('error');
      })
      .catch(() => setStatus('error'));
  }, [searchParams]);

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="logo" style={{ justifyContent: 'center', marginBottom: 24 }}>
          <span className="logo-icon">⚡</span>
          <span className="logo-text" style={{ fontSize: 24 }}>{t('app.name')}</span>
        </div>

        {status === 'loading' && <p>{t('common.loading')}</p>}

        {status === 'success' && (
          <div>
            <div className="alert alert-success">{t('auth.verify_success')}</div>
            <Link to="/login" className="btn btn-primary" style={{ marginTop: 16 }}>
              {t('auth.login')}
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div>
            <div className="alert alert-error">{t('auth.verify_error')}</div>
            <Link to="/login" className="btn btn-secondary" style={{ marginTop: 16 }}>
              {t('auth.login')}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
