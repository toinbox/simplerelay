import { apiGet, apiFetch } from '../api';
import { useTranslation } from 'react-i18next';
import { useState, useEffect, useRef, useCallback } from 'react';

const APP_PASSWORD_PROVIDERS = ['gmail', 'outlook', 'yahoo'];

export default function Providers() {
  const { t, i18n } = useTranslation();
  const [providers, setProviders] = useState([]);
  const [presets, setPresets] = useState({});
  const [relayInfo, setRelayInfo] = useState({ hostname: '', port: 2525 });
  const [showAdd, setShowAdd] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(null);
  const [detected, setDetected] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [form, setForm] = useState({ email: '', host: '', port: 587, user: '', password: '', tls: 'starttls' });
  const [testingId, setTestingId] = useState(null);
  const [testTo, setTestTo] = useState('');
  const [testStatus, setTestStatus] = useState({});
  const [dnsCheckId, setDnsCheckId] = useState(null);
  const [dnsResults, setDnsResults] = useState({});
  const [dnsLoading, setDnsLoading] = useState(null);
  const [showPassword, setShowPassword] = useState({});

  // Per-provider clients
  const [providerClients, setProviderClients] = useState({});
  const [addingClientFor, setAddingClientFor] = useState(null);
  const [clientForm, setClientForm] = useState({ client_type: 'ip', ip_cidr: '' });
  const [newCreds, setNewCreds] = useState(null);
  const [editingClient, setEditingClient] = useState(null);
  const [editForm, setEditForm] = useState({});
  const detectTimer = useRef(null);

  const loadProviders = () => {
    apiFetch('/api/providers/').then(r => r.json()).then(setProviders);
  };

  useEffect(() => {
    loadProviders();
    apiFetch('/api/providers/presets').then(r => r.json()).then(setPresets);
    apiFetch('/api/relay-info').then(r => r.json()).then(setRelayInfo).catch(() => {});
  }, []);

  // Load clients for all providers when providers change
  useEffect(() => {
    providers.forEach(p => loadClientsFor(p.id));
  }, [providers]);

  const loadClientsFor = (providerId) => {
    apiFetch(`/api/clients/?provider_id=${providerId}`).then(r => r.json()).then(clients => {
      setProviderClients(prev => ({ ...prev, [providerId]: clients }));
    });
  };

  // Auto-detect provider from email
  const detectProvider = async (email) => {
    if (!email || !email.includes('@')) return;
    setDetecting(true);
    try {
      const res = await apiFetch('/api/providers/detect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      setDetected(data);
      if (data.preset) {
        setSelectedPreset(data.provider_type);
        setForm(f => ({
          ...f,
          host: data.preset.smtp_host || f.host,
          port: data.preset.smtp_port || f.port,
          tls: data.preset.tls_mode || f.tls,
          user: email,
        }));
      }
    } catch (e) {
      console.error(e);
    }
    setDetecting(false);
  };

  const selectPreset = (key) => {
    const preset = presets[key];
    setSelectedPreset(key);
    setDetected({ provider_type: key, provider_name: preset.name, preset });
    setForm({ ...form, host: preset.smtp_host, port: preset.smtp_port, tls: preset.tls_mode });
  };

  const needsAppPassword = APP_PASSWORD_PROVIDERS.includes(selectedPreset);
  const appPasswordUrl = detected?.preset?.app_password_url
    || (selectedPreset && presets[selectedPreset]?.app_password_url);

  const getProviderNote = () => {
    if (!detected?.preset) return null;
    const lang = i18n.language?.substring(0, 2) || 'en';
    return detected.preset[`notes_${lang}`] || detected.preset.notes_en || null;
  };

  const addProvider = async () => {
    const authMethod = needsAppPassword ? 'app_password' : 'plain';
    await apiFetch('/api/providers/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_type: selectedPreset || 'custom',
        email: form.email,
        smtp_host: form.host,
        smtp_port: form.port,
        tls_mode: form.tls,
        auth_method: authMethod,
        username: form.user || form.email,
        password: form.password,
      }),
    });
    setShowAdd(false);
    setSelectedPreset(null);
    setDetected(null);
    setForm({ email: '', host: '', port: 587, user: '', password: '', tls: 'starttls' });
    loadProviders();
  };

  const deleteProvider = async (id, name) => {
    if (!confirm(t('providers.delete_confirm', { name }))) return;
    await apiFetch(`/api/providers/${id}`, { method: 'DELETE' });
    loadProviders();
  };

  const testProvider = async (id) => {
    const res = await apiFetch(`/api/providers/${id}/test`, { method: 'POST' });
    const data = await res.json();
    alert(data.healthy ? t('wizard.step2_test_ok') : t('wizard.step2_test_fail', { error: data.error }));
    loadProviders();
  };

  const sendTestEmail = async (providerEmail) => {
    if (!testTo) return;
    setTestStatus({ ...testStatus, [providerEmail]: 'sending' });
    try {
      const res = await apiFetch('/api/test-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from: providerEmail, to: testTo }),
      });
      const data = await res.json();
      setTestStatus({ ...testStatus, [providerEmail]: data.success ? 'ok' : (data.error || 'error') });
    } catch (e) {
      setTestStatus({ ...testStatus, [providerEmail]: String(e) });
    }
  };

  const checkDns = async (provider) => {
    if (dnsCheckId === provider.id) {
      setDnsCheckId(null);
      return;
    }
    setDnsCheckId(provider.id);
    setDnsLoading(provider.id);
    try {
      const domain = provider.email.split('@')[1];
      const res = await apiFetch('/api/providers/dns-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, provider_type: provider.provider_type }),
      });
      const data = await res.json();
      setDnsResults(prev => ({ ...prev, [provider.id]: data }));
    } catch (e) {
      setDnsResults(prev => ({ ...prev, [provider.id]: null }));
    }
    setDnsLoading(null);
  };

  const DOMAIN_ROUTING_TYPES = ['custom', 'amazon_ses', 'sendgrid', 'mailgun'];

  const toggleDomainRouting = async (provider) => {
    try {
      await apiFetch(`/api/providers/${provider.id}/domain-routing`, { method: 'PATCH' });
      loadProviders();
    } catch (e) {
      console.error(e);
    }
  };

  // --- Client (access control) management per provider ---
  const addClientFor = async (providerId) => {
    const providerEmail = providers.find(p => p.id === providerId)?.email || '';
    if (clientForm.client_type === 'ip') {
      const ips = clientForm.ip_cidr.split(/[,\n\s]+/).map(s => s.trim()).filter(Boolean);
      for (const ip of ips) {
        await apiFetch('/api/clients/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: ip, client_type: 'ip', provider_id: providerId, ip_cidr: ip }),
        });
      }
      setClientForm({ client_type: 'ip', ip_cidr: '' });
      setAddingClientFor(null);
    } else {
      const res = await apiFetch('/api/clients/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: providerEmail, client_type: 'smtp_auth', provider_id: providerId }),
      });
      const data = await res.json();
      if (data.smtp_password_plain) {
        setNewCreds(data);
      }
      setClientForm({ client_type: 'ip', ip_cidr: '' });
    }
    loadClientsFor(providerId);
  };

  const deleteClient = async (clientId, providerId) => {
    if (!confirm(t('clients.delete_confirm', { name: '' }))) return;
    await apiFetch(`/api/clients/${clientId}`, { method: 'DELETE' });
    loadClientsFor(providerId);
  };

  const toggleClient = async (clientId, providerId) => {
    await apiFetch(`/api/clients/${clientId}/toggle`, { method: 'PATCH' });
    loadClientsFor(providerId);
  };

  const startEdit = (client) => {
    setEditingClient(client.id);
    setEditForm({
      name: client.name,
      ip_cidr: client.ip_cidr || client.ip_address || '',
    });
  };

  const saveEdit = async (clientId, providerId) => {
    await apiFetch(`/api/clients/${clientId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: editForm.name,
        ip_cidr: editForm.ip_cidr || undefined,
        ip_address: editForm.ip_cidr || undefined,
      }),
    });
    setEditingClient(null);
    loadClientsFor(providerId);
  };

  const regeneratePassword = async (clientId, providerId) => {
    const res = await apiFetch(`/api/clients/${clientId}/regenerate`, { method: 'POST' });
    const data = await res.json();
    if (data.smtp_password_plain) {
      setNewCreds(data);
    }
    loadClientsFor(providerId);
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('providers.title')}</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
          + {t('providers.add')}
        </button>
      </div>

      {showAdd && (
        <div className="card">
          <div className="form-group">
            <label className="form-label">Email</label>
            <input
              className="form-input"
              type="email"
              value={form.email}
              placeholder={t('wizard.step1_placeholder')}
              onChange={e => {
                const email = e.target.value;
                setForm({ ...form, email, user: email });
                setDetected(null);
                setSelectedPreset(null);
                clearTimeout(detectTimer.current);
                if (email.includes('@') && email.split('@')[1]?.includes('.')) {
                  detectTimer.current = setTimeout(() => detectProvider(email), 400);
                }
              }}
            />
          </div>

          {detecting && <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 12 }}>{t('wizard.step1_detecting')}</p>}

          {detected && detected.provider_name && (
            <div className="alert alert-success" style={{ marginBottom: 12 }}>
              {t('wizard.step1_detected', { provider: detected.provider_name })}
            </div>
          )}

          {needsAppPassword && (
            <div className="alert alert-warning" style={{ marginBottom: 12 }}>
              <div style={{ marginBottom: appPasswordUrl ? 8 : 0 }}>
                {getProviderNote()}
              </div>
              {appPasswordUrl && (
                <a href={appPasswordUrl} target="_blank" rel="noopener noreferrer" style={{ fontWeight: 600, color: '#fbbf24' }}>
                  {t('wizard.step2_app_password_link')} →
                </a>
              )}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_host')}</label>
              <input className="form-input" value={form.host} onChange={e => setForm({ ...form, host: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_port')}</label>
              <input className="form-input" type="number" value={form.port} onChange={e => setForm({ ...form, port: parseInt(e.target.value) })} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_tls')}</label>
              <select className="form-input" value={form.tls} onChange={e => setForm({ ...form, tls: e.target.value })}>
                <option value="starttls">STARTTLS</option>
                <option value="ssl">SSL/TLS</option>
                <option value="none">None</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_user')}</label>
              <input className="form-input" value={form.user} onChange={e => setForm({ ...form, user: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">
                {needsAppPassword ? t('wizard.step2_app_password_label') : t('wizard.step2_manual_password')}
              </label>
              <input className="form-input" type="password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-primary" onClick={addProvider}>{t('common.save')}</button>
            <button className="btn btn-secondary" onClick={() => setShowAdd(false)}>{t('common.cancel')}</button>
          </div>
        </div>
      )}

      {providers.length === 0 && !showAdd ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📧</div>
            <div className="empty-state-text">{t('providers.no_providers')}</div>
          </div>
        </div>
      ) : (
        providers.map(p => {
          const clients = providerClients[p.id] || [];
          const hasAccess = clients.some(c => c.is_active);
          return (
            <div className="card" key={p.id} style={!hasAccess ? { borderLeft: '3px solid var(--color-error, #e53e3e)' } : {}}>
              {/* Provider header */}
              <div className="card-header">
                <div>
                  <span className="card-title">{p.name}</span>
                  {p.is_default && <span className="badge badge-muted" style={{ marginLeft: 8 }}>default</span>}
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  {!hasAccess && (
                    <span className="badge badge-warning">⚠ open relay</span>
                  )}
                  <span className={`badge ${p.status === 'active' && hasAccess ? 'badge-success' : 'badge-error'}`}>
                    {hasAccess ? t(`providers.status_${p.status}`) : t('common.disabled')}
                  </span>
                </div>
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 12 }}>
                {p.email} → {p.smtp_host}:{p.smtp_port}
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
                {p.daily_limit
                  ? t('providers.daily_usage', { sent: p.daily_sent, limit: p.daily_limit })
                  : t('providers.daily_unlimited', { sent: p.daily_sent })
                }
              </div>
              {p.expires_at && (
                <div style={{ fontSize: 13, color: new Date(p.expires_at) < new Date() ? 'var(--error)' : 'var(--text-muted)', marginBottom: 12 }}>
                  {t('providers.expires_at')}: {new Date(p.expires_at).toLocaleDateString()}
                </div>
              )}
              {p.is_locked && p.locked_reason && (
                <div className="alert alert-error" style={{ fontSize: 13, marginBottom: 12 }}>
                  🔒 {p.locked_reason}
                </div>
              )}

              {/* Domain routing toggle — only for supported provider types */}
              {DOMAIN_ROUTING_TYPES.includes(p.provider_type) && (
                <div style={{ fontSize: 13, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={p.domain_routing || false}
                      onChange={() => toggleDomainRouting(p)}
                    />
                    {t('providers.domain_routing')}
                  </label>
                  {p.domain_routing && (
                    <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                      *@{p.email.split('@')[1]}
                    </span>
                  )}
                </div>
              )}

              {/* Relay connection info */}
              <div className="info-box" style={{ marginBottom: 12 }}>
                <div><span className="label">{t('wizard.step5_host')}: </span><span className="value">{relayInfo.hostname}</span></div>
                <div><span className="label">{t('wizard.step5_port')}: </span><span className="value">{relayInfo.port}</span></div>
                <div><span className="label">{t('wizard.step5_from')}: </span><span className="value">{p.email}</span></div>
              </div>

              {/* Access control per provider */}
              <div style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <strong style={{ fontSize: 13 }}>🔒 {t('clients.title')}</strong>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setAddingClientFor(addingClientFor === p.id ? null : p.id);
                      setNewCreds(null);
                      setClientForm({ client_type: 'ip', ip_cidr: '' });
                    }}
                  >
                    + {t('clients.add')}
                  </button>
                </div>

                {/* Add client form */}
                {addingClientFor === p.id && (
                  <div style={{ background: 'var(--bg-secondary)', padding: 12, borderRadius: 8, marginBottom: 8 }}>
                    <div className="form-group" style={{ marginBottom: 8 }}>
                      <label className="form-label" style={{ fontSize: 12 }}>{t('clients.type')}</label>
                      <select className="form-input" value={clientForm.client_type} onChange={e => setClientForm({ ...clientForm, client_type: e.target.value })}>
                        <option value="ip">{t('clients.type_ip')}</option>
                        <option value="smtp_auth">{t('clients.type_auth')}</option>
                      </select>
                    </div>
                    {clientForm.client_type === 'ip' && (
                      <div className="form-group" style={{ marginBottom: 8 }}>
                        <label className="form-label" style={{ fontSize: 12 }}>{t('clients.ip_address')}</label>
                        <textarea
                          className="form-input"
                          value={clientForm.ip_cidr}
                          onChange={e => setClientForm({ ...clientForm, ip_cidr: e.target.value })}
                          placeholder={t('wizard.step4_ip_placeholder_multi')}
                          rows={2}
                          style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: 12 }}
                        />
                      </div>
                    )}
                    {newCreds && newCreds.provider_id === p.id && (
                      <div className="alert alert-success" style={{ marginBottom: 8 }}>
                        <div style={{ marginBottom: 4 }}><strong>{t('wizard.step4_auth_username')}:</strong> {newCreds.smtp_username}</div>
                        <div><strong>{t('wizard.step4_auth_password')}:</strong> <code>{newCreds.smtp_password_plain}</code></div>
                        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{t('clients.save_credentials')}</div>
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-primary btn-sm" onClick={() => addClientFor(p.id)}>{t('common.save')}</button>
                      <button className="btn btn-secondary btn-sm" onClick={() => { setAddingClientFor(null); setNewCreds(null); }}>{t('common.cancel')}</button>
                    </div>
                  </div>
                )}

                {/* Client list */}
                {clients.length > 0 ? (
                  <div style={{ fontSize: 13 }}>
                    {clients.map(c => (
                      <div key={c.id} style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '6px 8px', borderRadius: 6,
                        background: c.is_active ? 'var(--bg-secondary)' : 'transparent',
                        opacity: c.is_active ? 1 : 0.5,
                        marginBottom: 4,
                      }}>
                        {editingClient === c.id ? (
                          /* Edit mode */
                          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1 }}>
                            <input
                              className="form-input"
                              value={editForm.name}
                              onChange={e => setEditForm({ ...editForm, name: e.target.value })}
                              style={{ flex: 1, padding: '4px 8px', fontSize: 13 }}
                            />
                            {c.client_type === 'ip' && (
                              <input
                                className="form-input"
                                value={editForm.ip_cidr}
                                onChange={e => setEditForm({ ...editForm, ip_cidr: e.target.value })}
                                style={{ flex: 1, padding: '4px 8px', fontSize: 13, fontFamily: 'monospace' }}
                              />
                            )}
                            <button className="btn btn-primary btn-sm" onClick={() => saveEdit(c.id, p.id)} style={{ padding: '2px 10px' }}>{t('common.save')}</button>
                            <button className="btn btn-secondary btn-sm" onClick={() => setEditingClient(null)} style={{ padding: '2px 10px' }}>{t('common.cancel')}</button>
                          </div>
                        ) : (
                          /* View mode */
                          <>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span className="badge badge-muted" style={{ fontSize: 11 }}>
                                {c.client_type === 'ip' ? 'IP' : 'AUTH'}
                              </span>
                              <span style={{ fontWeight: 500, fontFamily: 'monospace' }}>
                                {c.client_type === 'ip' ? (c.ip_cidr || c.ip_address) : (
                                  c.smtp_password_plain ? (
                                    <>
                                      {showPassword[c.id] ? c.smtp_password_plain : '••••••••••••'}
                                      <button
                                        onClick={() => setShowPassword(prev => ({ ...prev, [c.id]: !prev[c.id] }))}
                                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0 4px', fontSize: 16, color: '#ffffff' }}
                                        title={showPassword[c.id] ? 'Hide' : 'Show'}
                                      >
                                        {showPassword[c.id] ? '🙈' : '👁'}
                                      </button>
                                    </>
                                  ) : '***'
                                )}
                              </span>
                            </div>
                            <div style={{ display: 'flex', gap: 4 }}>
                              <button
                                className={`badge ${c.is_active ? 'badge-success' : 'badge-error'}`}
                                style={{ cursor: 'pointer', border: 'none', fontSize: 11 }}
                                onClick={() => toggleClient(c.id, p.id)}
                                title={c.is_active ? t('common.enabled') : t('common.disabled')}
                              >
                                {c.is_active ? '✓' : '✗'}
                              </button>
                              <button className="btn btn-secondary btn-sm" onClick={() => startEdit(c)} style={{ padding: '2px 8px', fontSize: 11 }}>{t('common.edit')}</button>
                              {c.client_type === 'smtp_auth' && (
                                <button className="btn btn-secondary btn-sm" onClick={() => regeneratePassword(c.id, p.id)} style={{ padding: '2px 8px', fontSize: 11 }}>🔑</button>
                              )}
                              <button className="btn btn-danger btn-sm" onClick={() => deleteClient(c.id, p.id)} style={{ padding: '2px 8px', fontSize: 11 }}>✗</button>
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="alert alert-error" style={{ fontSize: 13 }}>
                    ⚠ {t('clients.no_clients_provider')}
                  </div>
                )}

                {/* Show regenerated creds */}
                {newCreds && newCreds.provider_id === p.id && addingClientFor !== p.id && (
                  <div className="alert alert-success" style={{ marginTop: 8 }}>
                    <div style={{ marginBottom: 4 }}><strong>{t('wizard.step4_auth_username')}:</strong> {newCreds.smtp_username}</div>
                    <div><strong>{t('wizard.step4_auth_password')}:</strong> <code>{newCreds.smtp_password_plain}</code></div>
                    <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{t('clients.save_credentials')}</div>
                  </div>
                )}
              </div>

              {/* Provider actions */}
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button className="btn btn-secondary btn-sm" onClick={() => checkDns(p)}>
                  {dnsLoading === p.id ? t('common.loading') : '🔍 DNS'}
                </button>
                <button className="btn btn-secondary btn-sm" onClick={() => testProvider(p.id)}>{t('providers.test')}</button>
                <button className="btn btn-secondary btn-sm" onClick={() => setTestingId(testingId === p.id ? null : p.id)}>{t('wizard.step5_test_send')}</button>
                <button className="btn btn-danger btn-sm" onClick={() => deleteProvider(p.id, p.name)}>{t('providers.delete')}</button>
              </div>

              {/* DNS check results */}
              {dnsCheckId === p.id && dnsResults[p.id] && (
                <div style={{ marginTop: 12 }}>
                  {dnsResults[p.id].map((r, i) => (
                    <div key={i} className="dns-result">
                      <span className={r.status === 'ok' ? 'dns-ok' : 'dns-missing'}>
                        {r.status === 'ok' ? '✓' : '✗'}
                      </span>
                      <div>
                        <strong>{t(`dns.${r.record_type}_record`)}</strong>
                        {' - '}
                        <span style={{ color: r.status === 'ok' ? 'var(--success, #38a169)' : 'var(--warning, #d69e2e)' }}>
                          {t(`dns.status_${r.status}`)}
                        </span>
                        {r.current_value && (
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 4, wordBreak: 'break-all' }}>
                            {r.current_value}
                          </div>
                        )}
                        {r.suggestion && <div className="dns-suggestion">{r.suggestion}</div>}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Test email */}
              {testingId === p.id && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      className="form-input"
                      type="email"
                      placeholder="test@example.com"
                      value={testTo}
                      onChange={e => setTestTo(e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => sendTestEmail(p.email)}
                      disabled={!testTo || testStatus[p.email] === 'sending'}
                    >
                      {testStatus[p.email] === 'sending' ? t('common.loading') : t('wizard.step5_test_send')}
                    </button>
                  </div>
                  {testStatus[p.email] === 'ok' && <div className="alert alert-success" style={{ marginTop: 8 }}>{t('wizard.step5_test_ok')}</div>}
                  {testStatus[p.email] && testStatus[p.email] !== 'ok' && testStatus[p.email] !== 'sending' && (
                    <div className="alert alert-error" style={{ marginTop: 8 }}>{t('wizard.step5_test_fail', { error: testStatus[p.email] })}</div>
                  )}
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
