import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import { apiGet } from '../api';

export default function Dashboard() {
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);

  useEffect(() => { apiGet('/api/dashboard').then(setStats).catch(console.error); }, []);

  if (!stats) return <div className="loading">{t('common.loading')}</div>;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('dashboard.title')}</h1>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.sent_today}</div>
          <div className="stat-label">{t('dashboard.sent_today')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: stats.errors_today > 0 ? 'var(--error)' : undefined }}>
            {stats.errors_today}
          </div>
          <div className="stat-label">{t('dashboard.errors_today')}</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">
            {stats.providers_healthy}
            <span style={{ fontSize: 16, color: 'var(--text-muted)' }}>
              {' '}{t('dashboard.providers_total', { total: stats.providers_total })}
            </span>
          </div>
          <div className="stat-label">{t('dashboard.providers_healthy')}</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">{t('dashboard.provider_health')}</h2>
        </div>
        {stats.provider_health.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-text">{t('dashboard.setup_message')}</div>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>{t('providers.title')}</th>
                <th>Email</th>
                <th>{t('logs.status')}</th>
                <th>{t('dashboard.last_check_header')}</th>
              </tr>
            </thead>
            <tbody>
              {stats.provider_health.map(p => (
                <tr key={p.id}>
                  <td>
                    {p.name}
                    {p.is_default && <span className="badge badge-muted" style={{ marginLeft: 8 }}>default</span>}
                    {p.is_locked && <span className="badge badge-error" style={{ marginLeft: 8 }}>locked</span>}
                  </td>
                  <td>{p.email}</td>
                  <td>
                    <span className={`badge ${p.status === 'active' ? 'badge-success' : p.status === 'locked' ? 'badge-error' : 'badge-warning'}`}>
                      {t(`providers.status_${p.status}`, p.status)}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    {p.last_check ? new Date(p.last_check).toLocaleTimeString() : '-'}
                    {p.response_time_ms && ` (${p.response_time_ms}ms)`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">{t('dashboard.recent_activity')}</h2>
        </div>
        {stats.recent_logs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-text">{t('logs.no_logs')}</div>
          </div>
        ) : (
          <table className="table">
            <thead><tr><th>{t('logs.time')}</th><th>{t('logs.recipient')}</th><th>{t('logs.status')}</th></tr></thead>
            <tbody>
              {stats.recent_logs.map(log => (
                <tr key={log.id}>
                  <td style={{ fontSize: 13, color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString()}</td>
                  <td>{log.recipient}</td>
                  <td>
                    <span className={`badge ${log.status === 'sent' ? 'badge-success' : log.status === 'failed' ? 'badge-error' : 'badge-warning'}`}>
                      {t(`logs.status_${log.status}`)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
