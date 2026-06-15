import { apiGet, apiFetch } from '../api';
import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';

export default function Logs() {
  const { t } = useTranslation();
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const loadLogs = (status = '') => {
    setLoading(true);
    const params = new URLSearchParams({ limit: '100' });
    if (status) params.set('status', status);
    apiFetch(`/api/logs?${params}`)
      .then(r => r.json())
      .then(data => { setLogs(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadLogs(filter); }, [filter]);

  const statusBadge = (status) => {
    const cls = status === 'sent' ? 'badge-success'
      : status === 'failed' ? 'badge-error'
      : status === 'bounced' ? 'badge-error'
      : 'badge-warning';
    return <span className={`badge ${cls}`}>{t(`logs.status_${status}`)}</span>;
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('logs.title')}</h1>
        <div style={{ display: 'flex', gap: 4 }}>
          {['', 'sent', 'failed'].map(f => (
            <button
              key={f}
              className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(f)}
            >
              {f === '' ? t('logs.filter_all') : t(`logs.filter_${f}`)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="loading">{t('common.loading')}</div>
      ) : logs.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <div className="empty-state-text">{t('logs.no_logs')}</div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: 'auto' }}>
          <table className="table">
            <thead>
              <tr>
                <th>{t('logs.time')}</th>
                <th>{t('logs.sender')}</th>
                <th>{t('logs.recipient')}</th>
                <th>{t('logs.provider')}</th>
                <th>{t('logs.status')}</th>
                <th>{t('logs.error')}</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td style={{ fontSize: 13, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td style={{ fontSize: 13 }}>{log.sender}</td>
                  <td style={{ fontSize: 13 }}>{log.recipient}</td>
                  <td style={{ fontSize: 13 }}>{log.provider_name || '-'}</td>
                  <td>{statusBadge(log.status)}</td>
                  <td style={{ fontSize: 12, color: 'var(--error)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {log.error_message || ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
