import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';

export default function AdminUsers({ token }) {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});

  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const load = () => {
    fetch('/api/admin/users', { headers }).then(r => r.json()).then(setUsers);
    fetch('/api/admin/stats', { headers }).then(r => r.json()).then(setStats);
  };

  useEffect(load, []);

  const updateUser = async (userId) => {
    await fetch(`/api/admin/users/${userId}`, {
      method: 'PATCH', headers, body: JSON.stringify(editForm),
    });
    setEditingId(null);
    load();
  };

  const deleteUser = async (userId, email) => {
    if (!confirm(`Delete user ${email}?`)) return;
    await fetch(`/api/admin/users/${userId}`, { method: 'DELETE', headers });
    load();
  };

  const toggleActive = async (user) => {
    await fetch(`/api/admin/users/${user.id}`, {
      method: 'PATCH', headers,
      body: JSON.stringify({ is_active: !user.is_active }),
    });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('admin.users')}</h1>
      </div>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.total_users}</div>
            <div className="stat-label">{t('admin.user_count', { count: stats.total_users })}</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.active_relays}<span style={{ fontSize: 16, color: 'var(--text-muted)' }}> / {stats.total_relays}</span></div>
            <div className="stat-label">{t('admin.active_relays')}</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.sent_today}</div>
            <div className="stat-label">{t('admin.total_sent')}</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: stats.errors_today > 0 ? 'var(--error)' : undefined }}>{stats.errors_today}</div>
            <div className="stat-label">{t('admin.total_errors')}</div>
          </div>
        </div>
      )}

      <div className="card" style={{ padding: 0, overflow: 'auto' }}>
        <table className="table">
          <thead>
            <tr>
              <th>{t('auth.email')}</th>
              <th>{t('auth.name')}</th>
              <th>{t('admin.role')}</th>
              <th>Relay</th>
              <th>{t('admin.max_relays')}</th>
              <th>{t('admin.expiry_days')}</th>
              <th>{t('clients.active')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td style={{ fontSize: 13 }}>{u.email}</td>
                <td style={{ fontSize: 13 }}>{u.name || '-'}</td>
                <td>
                  <span className={`badge ${u.role === 'admin' ? 'badge-warning' : 'badge-muted'}`}>
                    {t(`admin.role_${u.role}`)}
                  </span>
                </td>
                <td>{u.relay_count}</td>
                <td>
                  {editingId === u.id ? (
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      style={{ width: 70, padding: '4px 8px' }}
                      value={editForm.max_relays ?? u.max_relays}
                      onChange={e => setEditForm({ ...editForm, max_relays: parseInt(e.target.value) })}
                    />
                  ) : u.max_relays}
                </td>
                <td>
                  {editingId === u.id ? (
                    <input
                      className="form-input"
                      type="number"
                      min="0"
                      style={{ width: 70, padding: '4px 8px' }}
                      value={editForm.relay_expiry_days ?? (u.relay_expiry_days || 0)}
                      onChange={e => setEditForm({ ...editForm, relay_expiry_days: parseInt(e.target.value) })}
                      placeholder="0"
                    />
                  ) : (u.relay_expiry_days || t('admin.expiry_none'))}
                </td>
                <td>
                  <button
                    className={`badge ${u.is_active ? 'badge-success' : 'badge-error'}`}
                    style={{ cursor: 'pointer', border: 'none' }}
                    onClick={() => toggleActive(u)}
                  >
                    {u.is_active ? t('admin.activate') : t('admin.suspend')}
                  </button>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {editingId === u.id ? (
                      <>
                        <button className="btn btn-primary btn-sm" onClick={() => updateUser(u.id)}>{t('common.save')}</button>
                        <button className="btn btn-secondary btn-sm" onClick={() => setEditingId(null)}>{t('common.cancel')}</button>
                      </>
                    ) : (
                      <>
                        <button className="btn btn-secondary btn-sm" onClick={() => {
                          setEditingId(u.id);
                          setEditForm({ max_relays: u.max_relays, relay_expiry_days: u.relay_expiry_days || 0 });
                        }}>{t('common.edit')}</button>
                        {u.role !== 'admin' && (
                          <button className="btn btn-danger btn-sm" onClick={() => deleteUser(u.id, u.email)}>{t('common.delete')}</button>
                        )}
                      </>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
