import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';

export default function AdminLogs({ token }) {
  const { t } = useTranslation();
  const [logs, setLogs] = useState([]);
  const [users, setUsers] = useState([]);
  const [filter, setFilter] = useState('');
  const [userFilter, setUserFilter] = useState('');
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [offset, setOffset] = useState(0);
  const [expandedId, setExpandedId] = useState(null);
  const limit = 50;

  const headers = { 'Authorization': `Bearer ${token}` };

  useEffect(() => {
    fetch('/api/admin/users', { headers }).then(r => r.json()).then(setUsers).catch(() => {});
  }, []);

  const loadLogs = () => {
    setLoading(true);
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (filter) params.set('status', filter);
    if (userFilter) params.set('user_id', userFilter);
    if (search) params.set('search', search);
    fetch(`/api/admin/logs?${params}`, { headers })
      .then(r => r.json())
      .then(data => { setLogs(data); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { setOffset(0); }, [filter, userFilter, search]);
  useEffect(() => { loadLogs(); }, [filter, userFilter, search, offset]);

  const doSearch = () => { setSearch(searchInput); };

  const statusBadge = (status) => {
    const cls = status === 'sent' ? 'badge-success'
      : status === 'failed' ? 'badge-error'
      : status === 'bounced' ? 'badge-error'
      : 'badge-warning';
    return <span className={`badge ${cls}`}>{t(`logs.status_${status}`)}</span>;
  };

  return (
    <div className="page-wide">
      <div className="page-header">
        <h1 className="page-title">{t('admin.logs')}</h1>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        {['', 'sent', 'failed', 'bounced'].map(f => (
          <button
            key={f}
            className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setFilter(f)}
          >
            {f === '' ? t('logs.filter_all') : t(`logs.filter_${f}`)}
          </button>
        ))}
        <select
          className="form-input"
          value={userFilter}
          onChange={e => setUserFilter(e.target.value)}
          style={{ width: 'auto', padding: '4px 8px', fontSize: 13 }}
        >
          <option value="">{t('admin.all_users')}</option>
          {users.map(u => (
            <option key={u.id} value={u.id}>{u.email}</option>
          ))}
        </select>
        <div style={{ display: 'flex', gap: 4 }}>
          <input
            className="form-input"
            placeholder={t('logs.search_placeholder')}
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            style={{ padding: '4px 8px', fontSize: 13, width: 200 }}
          />
          <button className="btn btn-sm btn-secondary" onClick={doSearch}>🔍</button>
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
        <>
          <div className="card" style={{ padding: 0, overflow: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>{t('logs.time')}</th>
                  <th>{t('admin.user')}</th>
                  <th>{t('logs.sender')}</th>
                  <th>{t('logs.recipient')}</th>
                  <th>{t('logs.subject')}</th>
                  <th>{t('logs.provider')}</th>
                  <th>{t('logs.status')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <>
                    <tr key={log.id}>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td style={{ fontSize: 12 }}>{log.user_email || '-'}</td>
                      <td style={{ fontSize: 12 }}>{log.sender}</td>
                      <td style={{ fontSize: 12 }}>{log.recipient}</td>
                      <td style={{ fontSize: 12, maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{log.subject || '-'}</td>
                      <td style={{ fontSize: 12 }}>{log.provider_name || '-'}</td>
                      <td>{statusBadge(log.status)}</td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '2px 8px', fontSize: 11 }}
                          onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                        >
                          {expandedId === log.id ? '▲' : '▼'}
                        </button>
                      </td>
                    </tr>
                    {expandedId === log.id && (
                      <tr key={`${log.id}-detail`}>
                        <td colSpan={8} style={{ background: 'var(--bg-secondary)', fontSize: 12, padding: 12 }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                            <div><strong>{t('logs.client_ip')}:</strong> {log.client_ip || '-'}</div>
                            <div><strong>{t('logs.proxy_ip')}:</strong> {log.proxy_ip || '-'}</div>
                            <div><strong>{t('logs.queue_id')}:</strong> {log.queue_id || '-'}</div>
                            <div><strong>{t('logs.provider')}:</strong> {log.provider_name || '-'}</div>
                          </div>
                          {log.error_message && (
                            <div style={{ marginTop: 8, padding: 8, background: 'var(--bg)', borderRadius: 4, color: 'var(--error)', fontFamily: 'monospace', wordBreak: 'break-all' }}>
                              {log.error_message}
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'center' }}>
            <button className="btn btn-sm btn-secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>
              ← {t('common.back')}
            </button>
            <span style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: '32px' }}>
              {offset + 1} - {offset + logs.length}
            </span>
            <button className="btn btn-sm btn-secondary" disabled={logs.length < limit} onClick={() => setOffset(offset + limit)}>
              {t('common.next')} →
            </button>
          </div>
        </>
      )}
    </div>
  );
}