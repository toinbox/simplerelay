import { apiFetch } from '../api';
import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';

export default function Clients() {
  const { t } = useTranslation();
  const [providers, setProviders] = useState([]);
  const [clients, setClients] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [addEmail, setAddEmail] = useState('');
  const [clientType, setClientType] = useState('ip');
  const [ip, setIp] = useState('');
  const [newCreds, setNewCreds] = useState(null);
  const [editingClient, setEditingClient] = useState(null);
  const [editForm, setEditForm] = useState({});

  useEffect(() => {
    apiFetch('/api/providers/').then(r => r.json()).then(setProviders);
    loadClients();
  }, []);

  const loadClients = () => {
    apiFetch('/api/clients/').then(r => r.json()).then(setClients);
  };

  const getProviderByEmail = (email) => providers.find(p => p.email === email);
  const getProviderById = (id) => providers.find(p => p.id === id);

  const addClient = async () => {
    const provider = getProviderByEmail(addEmail);
    if (!provider) return;
    if (clientType === 'ip') {
      const ips = ip.split(/[,\n\s]+/).map(s => s.trim()).filter(Boolean);
      for (const oneIp of ips) {
        await apiFetch('/api/clients/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: oneIp, client_type: 'ip', provider_id: provider.id, ip_cidr: oneIp }),
        });
      }
      setShowAdd(false); setIp(''); setAddEmail('');
    } else {
      const res = await apiFetch('/api/clients/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: addEmail, client_type: 'smtp_auth', provider_id: provider.id }),
      });
      const data = await res.json();
      if (data.smtp_password_plain) setNewCreds(data);
      else { setShowAdd(false); setAddEmail(''); }
    }
    loadClients();
  };

  const deleteClient = async (id, n) => {
    if (!confirm(t('clients.delete_confirm', { name: n }))) return;
    await apiFetch(`/api/clients/${id}`, { method: 'DELETE' });
    loadClients();
  };

  const toggleClient = async (id) => {
    await apiFetch(`/api/clients/${id}/toggle`, { method: 'PATCH' });
    loadClients();
  };

  const startEdit = (c) => {
    setEditingClient(c.id);
    setEditForm({ name: c.name, ip_cidr: c.ip_cidr || c.ip_address || '' });
  };

  const saveEdit = async (id) => {
    await apiFetch(`/api/clients/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: editForm.name, ip_cidr: editForm.ip_cidr || undefined, ip_address: editForm.ip_cidr || undefined }),
    });
    setEditingClient(null);
    loadClients();
  };

  const regeneratePassword = async (id) => {
    const res = await apiFetch(`/api/clients/${id}/regenerate`, { method: 'POST' });
    const data = await res.json();
    if (data.smtp_password_plain) setNewCreds(data);
    loadClients();
  };

  // Group clients by provider email
  const grouped = {};
  clients.forEach(c => {
    const p = getProviderById(c.provider_id);
    const email = p ? p.email : '—';
    if (!grouped[email]) grouped[email] = [];
    grouped[email].push(c);
  });

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('clients.title')}</h1>
        <button className="btn btn-primary" onClick={() => { setShowAdd(!showAdd); setNewCreds(null); }}>
          + {t('clients.add')}
        </button>
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 20 }}>{t('clients.desc')}</p>

      {/* Add form — email selector inside */}
      {showAdd && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="form-group">
            <label className="form-label">{t('clients.select_email')}</label>
            <select className="form-input" value={addEmail} onChange={e => setAddEmail(e.target.value)}>
              <option value="">{t('clients.select_email_placeholder')}</option>
              {providers.map(p => (
                <option key={p.id} value={p.email}>{p.email}</option>
              ))}
            </select>
          </div>

          {addEmail && (
            <>
              <div className="form-group" style={{ marginBottom: 12 }}>
                <label className="form-label">{t('clients.type')}</label>
                <select className="form-input" value={clientType} onChange={e => setClientType(e.target.value)}>
                  <option value="ip">{t('clients.type_ip')}</option>
                  <option value="smtp_auth">{t('clients.type_auth')}</option>
                </select>
              </div>
              {clientType === 'ip' && (
                <div className="form-group">
                  <label className="form-label">{t('clients.ip_address')}</label>
                  <textarea className="form-input" value={ip} onChange={e => setIp(e.target.value)} placeholder={t('wizard.step4_ip_placeholder_multi')} rows={3} style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: 13 }} />
                </div>
              )}
              {newCreds && (
                <div className="alert alert-success" style={{ marginBottom: 16 }}>
                  <div style={{ marginBottom: 4 }}><strong>{t('wizard.step4_auth_username')}:</strong> {newCreds.smtp_username}</div>
                  <div><strong>{t('wizard.step4_auth_password')}:</strong> <code>{newCreds.smtp_password_plain}</code></div>
                  <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{t('clients.save_credentials')}</div>
                </div>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" onClick={addClient}>{t('common.save')}</button>
                <button className="btn btn-secondary" onClick={() => { setShowAdd(false); setNewCreds(null); setAddEmail(''); }}>{t('common.cancel')}</button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Existing rules grouped by email */}
      {Object.keys(grouped).length > 0 ? (
        Object.entries(grouped).map(([email, rules]) => (
          <div className="card" key={email} style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>📧 {email}</div>
            {rules.map(c => (
              <div key={c.id} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '8px 10px', borderRadius: 6,
                background: c.is_active ? 'var(--bg-secondary)' : 'transparent',
                opacity: c.is_active ? 1 : 0.5, marginBottom: 4,
              }}>
                {editingClient === c.id ? (
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1 }}>
                    <input className="form-input" value={editForm.name} onChange={e => setEditForm({ ...editForm, name: e.target.value })} style={{ flex: 1, padding: '4px 8px', fontSize: 13 }} />
                    {c.client_type === 'ip' && <input className="form-input" value={editForm.ip_cidr} onChange={e => setEditForm({ ...editForm, ip_cidr: e.target.value })} style={{ flex: 1, padding: '4px 8px', fontSize: 13, fontFamily: 'monospace' }} />}
                    <button className="btn btn-primary btn-sm" onClick={() => saveEdit(c.id)}>{t('common.save')}</button>
                    <button className="btn btn-secondary btn-sm" onClick={() => setEditingClient(null)}>{t('common.cancel')}</button>
                  </div>
                ) : (
                  <>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="badge badge-muted" style={{ fontSize: 11 }}>{c.client_type === 'ip' ? 'IP' : 'AUTH'}</span>
                      <span style={{ fontWeight: 500, fontFamily: 'monospace', fontSize: 13 }}>{c.client_type === 'ip' ? (c.ip_cidr || c.ip_address) : (c.smtp_password_plain || '***')}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className={`badge ${c.is_active ? 'badge-success' : 'badge-error'}`} style={{ cursor: 'pointer', border: 'none', fontSize: 11 }} onClick={() => toggleClient(c.id)}>{c.is_active ? t('common.enabled') : t('common.disabled')}</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => startEdit(c)} style={{ padding: '2px 8px', fontSize: 11 }}>{t('common.edit')}</button>
                      {c.client_type === 'smtp_auth' && <button className="btn btn-secondary btn-sm" onClick={() => regeneratePassword(c.id)} style={{ padding: '2px 8px', fontSize: 11 }}>🔑</button>}
                      <button className="btn btn-danger btn-sm" onClick={() => deleteClient(c.id, c.name)} style={{ padding: '2px 8px', fontSize: 11 }}>✗</button>
                    </div>
                  </>
                )}
              </div>
            ))}
            {newCreds && !showAdd && getProviderById(newCreds.provider_id)?.email === email && (
              <div className="alert alert-success" style={{ marginTop: 8 }}>
                <div style={{ marginBottom: 4 }}><strong>{t('wizard.step4_auth_username')}:</strong> {newCreds.smtp_username}</div>
                <div><strong>{t('wizard.step4_auth_password')}:</strong> <code>{newCreds.smtp_password_plain}</code></div>
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{t('clients.save_credentials')}</div>
              </div>
            )}
          </div>
        ))
      ) : !showAdd && (
        <div className="card">
          <div className="alert alert-warning">{t('clients.warning_open')}</div>
          <div className="empty-state">
            <div className="empty-state-icon">🔒</div>
            <div className="empty-state-text">{t('clients.no_clients')}</div>
          </div>
        </div>
      )}

      {/* Show emails without any rules */}
      {providers.filter(p => !grouped[p.email]).map(p => (
        <div className="card" key={p.id} style={{ marginBottom: 12, borderLeft: '3px solid var(--color-error, #e53e3e)' }}>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>📧 {p.email}</div>
          <div className="alert alert-error" style={{ margin: 0 }}>⚠ {t('clients.no_clients_provider')}</div>
        </div>
      ))}
    </div>
  );
}
