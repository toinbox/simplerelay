import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';

const FALLBACK_DOMAINS = [
  { key: 'gmail', label: 'Gmail' },
  { key: 'outlook', label: 'Outlook' },
  { key: 'seznam', label: 'Seznam' },
  { key: 'yahoo', label: 'Yahoo' },
  { key: 'custom', label: 'Custom' },
];

function parseProxyUrl(url) {
  try {
    const m = url.trim().match(
      /^socks5:\/\/(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$/i
    );
    if (m) return { host: m[3], port: parseInt(m[4]), username: m[1] || '', password: m[2] || '' };
  } catch {}
  return null;
}

function maskUrl(host, port, username) {
  const auth = username ? `${username}:***@` : '';
  return `socks5://${auth}${host}:${port || 1080}`;
}

export default function AdminProxies({ token }) {
  const { t } = useTranslation();
  const [proxies, setProxies] = useState([]);
  const [domains, setDomains] = useState(FALLBACK_DOMAINS);
  const [showAdd, setShowAdd] = useState(false);
  const [url, setUrl] = useState('');
  const [name, setName] = useState('');
  const [selectedDomains, setSelectedDomains] = useState([]);
  const [urlError, setUrlError] = useState('');
  const [testResults, setTestResults] = useState({});

  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const load = () => {
    fetch('/api/admin/proxies', { headers }).then(r => r.json()).then(setProxies);
  };

  const loadDomains = () => {
    fetch('/api/admin/proxy-domains', { headers })
      .then(r => r.json())
      .then(types => {
        // Merge API domains with fallback, keep unique
        const merged = new Map();
        FALLBACK_DOMAINS.forEach(d => merged.set(d.key, d.label));
        types.forEach(t => {
          if (!merged.has(t)) merged.set(t, t.charAt(0).toUpperCase() + t.slice(1));
        });
        setDomains(Array.from(merged, ([key, label]) => ({ key, label })));
      })
      .catch(() => setDomains(FALLBACK_DOMAINS));
  };

  useEffect(() => { load(); loadDomains(); }, []);

  const addProxy = async () => {
    const parsed = parseProxyUrl(url);
    if (!parsed) {
      setUrlError(t('admin.proxy_url_error'));
      return;
    }
    setUrlError('');
    await fetch('/api/admin/proxies', {
      method: 'POST', headers,
      body: JSON.stringify({
        name: name || `Proxy ${parsed.host}`,
        protocol: 'socks5',
        host: parsed.host,
        port: parsed.port,
        username: parsed.username || null,
        password: parsed.password || null,
        provider_types: selectedDomains.length > 0 ? selectedDomains : null,
      }),
    });
    setShowAdd(false);
    setUrl('');
    setName('');
    setSelectedDomains([]);
    load();
  };

  const toggleProxy = async (id) => {
    const proxy = proxies.find(p => p.id === id);
    await fetch(`/api/admin/proxies/${id}`, {
      method: 'PATCH', headers,
      body: JSON.stringify({ is_active: !proxy.is_active }),
    });
    load();
  };

  const deleteProxy = async (id, pname) => {
    if (!confirm(t('admin.proxy_confirm_delete', { name: pname }))) return;
    await fetch(`/api/admin/proxies/${id}`, { method: 'DELETE', headers });
    load();
  };

  const testProxy = async (id) => {
    setTestResults(r => ({ ...r, [id]: { loading: true } }));
    try {
      const res = await fetch(`/api/admin/proxies/${id}/test`, { method: 'POST', headers });
      const data = await res.json();
      setTestResults(r => ({ ...r, [id]: data }));
    } catch (e) {
      setTestResults(r => ({ ...r, [id]: { success: false, error: String(e) } }));
    }
  };

  const toggleDomain = (key) => {
    setSelectedDomains(d => d.includes(key) ? d.filter(k => k !== key) : [...d, key]);
  };

  // Toggle domain on existing proxy (PATCH)
  const toggleProxyDomain = async (proxyId, domainKey) => {
    const proxy = proxies.find(p => p.id === proxyId);
    if (!proxy) return;
    const current = proxy.provider_types || [];
    const updated = current.includes(domainKey)
      ? current.filter(k => k !== domainKey)
      : [...current, domainKey];
    await fetch(`/api/admin/proxies/${proxyId}`, {
      method: 'PATCH', headers,
      body: JSON.stringify({ provider_types: updated.length > 0 ? updated : null }),
    });
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{t('admin.proxies')}</h1>
        <button className="btn btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? `✕ ${t('common.cancel')}` : `+ ${t('admin.proxy_add')}`}
        </button>
      </div>

      {showAdd && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <div className="form-group" style={{ flex: '0 0 200px' }}>
              <label className="form-label">{t('admin.proxy_name')}</label>
              <input
                className="form-input"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Proxy EU 1"
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label className="form-label">{t('admin.proxy_url')}</label>
              <input
                className="form-input"
                value={url}
                onChange={e => { setUrl(e.target.value); setUrlError(''); }}
                placeholder="socks5://user:pass@1.2.3.4:1080"
                style={{ fontFamily: 'monospace', fontSize: 13 }}
              />
              {urlError && <span style={{ color: 'var(--error)', fontSize: 12 }}>{urlError}</span>}
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 12 }}>
            <label className="form-label">{t('admin.proxy_apply_to')}</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {domains.map(d => (
                <button
                  key={d.key}
                  onClick={() => toggleDomain(d.key)}
                  className={`badge ${selectedDomains.includes(d.key) ? 'badge-success' : 'badge-muted'}`}
                  style={{ cursor: 'pointer', border: 'none', padding: '4px 10px', fontSize: 13 }}
                >
                  {d.label}
                </button>
              ))}
            </div>
            <span style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, display: 'block' }}>
              {t('admin.proxy_apply_hint')}
            </span>
          </div>

          <button className="btn btn-primary" onClick={addProxy} disabled={!url.trim()}>
            {t('admin.proxy_save')}
          </button>
        </div>
      )}

      {proxies.length === 0 && !showAdd ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🌐</div>
            <div className="empty-state-text">{t('admin.proxy_empty')}</div>
          </div>
        </div>
      ) : proxies.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {proxies.map(p => {
            const tr = testResults[p.id];
            return (
              <div className="card" key={p.id} style={{ padding: 16 }}>
                {/* Row 1: Name, URL, status, actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                  <span style={{ fontWeight: 600, fontSize: 15, minWidth: 120 }}>{p.name}</span>
                  <code style={{ fontSize: 13, color: 'var(--text-muted)', flex: 1 }}>
                    {maskUrl(p.host, p.port, p.username)}
                  </code>
                  <button
                    className={`badge ${p.is_active ? 'badge-success' : 'badge-error'}`}
                    style={{ cursor: 'pointer', border: 'none' }}
                    onClick={() => toggleProxy(p.id)}
                  >
                    {p.is_active ? t('admin.proxy_active') : t('admin.proxy_disabled')}
                  </button>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => testProxy(p.id)}
                    disabled={tr?.loading}
                  >
                    {tr?.loading ? '...' : t('admin.proxy_test')}
                  </button>
                  <button className="btn btn-danger btn-sm" onClick={() => deleteProxy(p.id, p.name)}>
                    ✕
                  </button>
                </div>

                {/* Test result */}
                {tr && !tr.loading && (
                  <div style={{
                    fontSize: 13, fontFamily: 'monospace', marginBottom: 10, padding: '6px 10px',
                    borderRadius: 6, background: tr.success ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    color: tr.success ? 'var(--success)' : 'var(--error)',
                  }}>
                    {tr.success
                      ? `✓ IP: ${tr.ip}  •  ${tr.latency_ms}ms${tr.smtp_ok ? '  •  SMTP OK' : ''}`
                      : `✕ ${tr.error || 'Connection failed'}`
                    }
                  </div>
                )}

                {/* Row 2: Domain badges — clickable to add/remove */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', marginRight: 4 }}>
                    {t('admin.proxy_providers')}:
                  </span>
                  {domains.map(d => {
                    const isAssigned = p.provider_types ? p.provider_types.includes(d.key) : false;
                    const isCatchAll = !p.provider_types;
                    return (
                      <button
                        key={d.key}
                        onClick={() => toggleProxyDomain(p.id, d.key)}
                        className={`badge ${isAssigned ? 'badge-success' : 'badge-muted'}`}
                        style={{ cursor: 'pointer', border: 'none', padding: '2px 8px', fontSize: 11 }}
                      >
                        {d.label}
                      </button>
                    );
                  })}
                  {!p.provider_types && (
                    <span style={{ fontSize: 11, color: 'var(--warning)', fontStyle: 'italic', marginLeft: 4 }}>
                      ⚡ {t('admin.proxy_fallback_hint')}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
