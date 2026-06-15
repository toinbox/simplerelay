import { useTranslation } from 'react-i18next';
import { useState, useEffect } from 'react';
import { apiFetch } from '../api';
import LanguageSwitcher from '../components/LanguageSwitcher';

const STEPS = 5;

// Providers that require app passwords
const APP_PASSWORD_PROVIDERS = ['gmail', 'outlook', 'yahoo'];

export default function Wizard({ onComplete }) {
  const { t, i18n } = useTranslation();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState('');
  const [detected, setDetected] = useState(null);
  const [detecting, setDetecting] = useState(false);
  const [providerType, setProviderType] = useState(null);
  const [credentials, setCredentials] = useState({ host: '', port: 587, user: '', password: '', tls: 'starttls' });
  const [dnsResults, setDnsResults] = useState(null);
  const [dnsLoading, setDnsLoading] = useState(false);
  const [accessMethod, setAccessMethod] = useState('ip');
  const [clientIp, setClientIp] = useState('');
  const [smtpCreds, setSmtpCreds] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);
  const [providerId, setProviderId] = useState(null);
  const [relayInfo, setRelayInfo] = useState({ hostname: '', port: 2525 });

  // Load relay connection info
  useEffect(() => {
    apiFetch('/api/relay-info').then(r => r.json()).then(setRelayInfo).catch(() => {});
  }, []);

  // Run DNS check when entering step 3
  useEffect(() => {
    if (step === 3 && !dnsResults && !dnsLoading) {
      checkDns();
    }
  }, [step]);

  // Step 1: Detect provider from email
  const detectProvider = async () => {
    if (!email.includes('@')) return;
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
        setProviderType(data.provider_type);
        setCredentials({
          host: data.preset.smtp_host || '',
          port: data.preset.smtp_port || 587,
          user: email,
          password: '',
          tls: data.preset.tls_mode || 'starttls',
        });
      }
    } catch (e) {
      console.error(e);
    }
    setDetecting(false);
  };

  // Step 2: Save provider
  const saveProvider = async () => {
    const authMethod = APP_PASSWORD_PROVIDERS.includes(providerType) ? 'app_password' : 'plain';
    const res = await apiFetch('/api/providers/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_type: providerType || 'custom',
        email,
        smtp_host: credentials.host,
        smtp_port: credentials.port,
        tls_mode: credentials.tls,
        auth_method: authMethod,
        username: credentials.user,
        password: credentials.password,
        is_default: true,
      }),
    });
    if (res.ok) {
      const provider = await res.json();
      setProviderId(provider.id);
      return provider.id;
    }
    const err = await res.json().catch(() => null);
    const msg = err?.detail || `Error ${res.status}`;
    setTestResult({ healthy: false, error: msg });
    return null;
  };

  // Step 2: Test connection (real SMTP AUTH)
  const testConnection = async () => {
    let id = providerId;
    if (!id) {
      id = await saveProvider();
      if (!id) return;
    } else {
      // Provider already saved — update credentials before testing
      await apiFetch(`/api/providers/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          smtp_host: credentials.host,
          smtp_port: credentials.port,
          tls_mode: credentials.tls,
          username: credentials.user,
          password: credentials.password,
        }),
      });
    }
    setTestLoading(true);
    setTestResult(null);
    try {
      const res = await apiFetch(`/api/providers/${id}/test`, { method: 'POST' });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ healthy: false, error: String(e) });
    }
    setTestLoading(false);
  };

  // Step 3: Check DNS
  const checkDns = async () => {
    const domain = email.split('@')[1];
    if (!domain) return;
    setDnsLoading(true);
    try {
      const res = await apiFetch('/api/providers/dns-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, provider_type: providerType || 'custom' }),
      });
      setDnsResults(await res.json());
    } catch (e) {
      console.error(e);
    }
    setDnsLoading(false);
  };

  // Step 4: Save access control
  const saveClient = async () => {
    if (accessMethod === 'ip' && clientIp.trim()) {
      // Split on commas, newlines, spaces — create one client per IP
      const ips = clientIp.split(/[,\n\s]+/).map(s => s.trim()).filter(Boolean);
      for (const ip of ips) {
        await apiFetch('/api/clients/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: ip, client_type: 'ip', ip_cidr: ip, provider_id: providerId }),
        });
      }
    } else if (accessMethod === 'smtp_auth') {
      const res = await apiFetch('/api/clients/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'App', client_type: 'smtp_auth', provider_id: providerId }),
      });
      const data = await res.json();
      setSmtpCreds(data);
    }
  };

  // Step 5: Send test email
  const [testTo, setTestTo] = useState('');
  const [testStatus, setTestStatus] = useState(null);
  const [testSending, setTestSending] = useState(false);

  const sendTestEmail = async () => {
    if (!testTo) return;
    setTestSending(true);
    setTestStatus(null);
    try {
      const res = await apiFetch('/api/test-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from: email, to: testTo }),
      });
      const data = await res.json();
      setTestStatus(data.success ? 'ok' : data.error || 'error');
    } catch (e) {
      setTestStatus(String(e));
    }
    setTestSending(false);
  };

  // Helper: get provider note in current language
  const getProviderNote = () => {
    if (!detected?.preset) return null;
    const lang = i18n.language?.substring(0, 2) || 'en';
    return detected.preset[`notes_${lang}`] || detected.preset.notes_en || null;
  };

  // Helper: check if current provider needs app password
  const needsAppPassword = APP_PASSWORD_PROVIDERS.includes(providerType);
  const appPasswordUrl = detected?.preset?.app_password_url || null;

  const nextStep = async () => {
    if (step === 2 && !providerId) {
      const id = await saveProvider();
      if (!id) return;
    }
    if (step === 4) {
      await saveClient();
    }
    setStep(s => Math.min(s + 1, STEPS));
  };

  return (
    <div className="wizard">
      <div className="wizard-header">
        <div style={{ marginBottom: 20 }}><LanguageSwitcher /></div>
        <div className="logo" style={{ justifyContent: 'center', marginBottom: 16 }}>
          <span className="logo-icon">⚡</span>
          <span className="logo-text" style={{ fontSize: 28 }}>{t('app.name')}</span>
        </div>
        <h1 className="wizard-title">{t('wizard.title')}</h1>
        <p className="wizard-subtitle">{t('app.tagline')}</p>
      </div>

      {/* Progress */}
      <div className="wizard-steps">
        {Array.from({ length: STEPS }, (_, i) => (
          <div key={i} className={`wizard-step ${i + 1 === step ? 'active' : i + 1 < step ? 'done' : ''}`} />
        ))}
      </div>

      {/* Step 1: Email */}
      {step === 1 && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 8 }}>{t('wizard.step1_title')}</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 14 }}>{t('wizard.step1_desc')}</p>
          <div className="form-group">
            <input
              className="form-input"
              type="email"
              placeholder={t('wizard.step1_placeholder')}
              value={email}
              onChange={e => { setEmail(e.target.value); setDetected(null); }}
              onBlur={detectProvider}
            />
          </div>
          {detecting && <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('wizard.step1_detecting')}</p>}
          {detected && detected.provider_name && (
            <div className="alert alert-success">
              {t('wizard.step1_detected', { provider: detected.provider_name })}
            </div>
          )}
          {detected && !detected.provider_name && detected.preset && (
            <div className="alert alert-warning">
              {t('wizard.step1_guessed', { host: detected.preset.smtp_host })}
            </div>
          )}
          {detected && !detected.provider_name && !detected.preset && (
            <div className="alert alert-warning">{t('wizard.step1_not_detected')}</div>
          )}
        </div>
      )}

      {/* Step 2: Connect account */}
      {step === 2 && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 8 }}>{t('wizard.step2_title')}</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 14 }}>{t('wizard.step2_desc')}</p>

          {/* App password info box */}
          {needsAppPassword && (
            <div className="alert alert-warning" style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8 }}>{getProviderNote()}</div>
              {appPasswordUrl && (
                <a
                  href={appPasswordUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontWeight: 600 }}
                >
                  {t('wizard.step2_app_password_link')} →
                </a>
              )}
            </div>
          )}

          <div className="form-group">
            <label className="form-label">{t('wizard.step2_manual_host')}</label>
            <input className="form-input" value={credentials.host} onChange={e => setCredentials({ ...credentials, host: e.target.value })} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_port')}</label>
              <input className="form-input" type="number" value={credentials.port} onChange={e => setCredentials({ ...credentials, port: parseInt(e.target.value) })} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('wizard.step2_manual_tls')}</label>
              <select className="form-input" value={credentials.tls} onChange={e => {
                const tls = e.target.value;
                const portMap = { starttls: 587, ssl: 465, none: 25 };
                setCredentials({ ...credentials, tls, port: portMap[tls] || credentials.port });
              }}>
                <option value="starttls">{t('wizard.step2_tls_starttls')}</option>
                <option value="ssl">{t('wizard.step2_tls_ssl')}</option>
                <option value="none">{t('wizard.step2_tls_none')}</option>
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">{t('wizard.step2_manual_user')}</label>
            <input className="form-input" value={credentials.user} onChange={e => setCredentials({ ...credentials, user: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">
              {needsAppPassword ? t('wizard.step2_app_password_label') : t('wizard.step2_manual_password')}
            </label>
            <input className="form-input" type="password" value={credentials.password} onChange={e => setCredentials({ ...credentials, password: e.target.value })} />
          </div>

          {testResult && (
            <div className={`alert ${testResult.healthy ? 'alert-success' : 'alert-error'}`}>
              {testResult.healthy ? t('wizard.step2_test_ok') : t('wizard.step2_test_fail', { error: testResult.error })}
            </div>
          )}
          <button className="btn btn-secondary" onClick={testConnection} disabled={testLoading}>
            {testLoading ? t('common.loading') : t('wizard.step2_test')}
          </button>
        </div>
      )}

      {/* Step 3: DNS check */}
      {step === 3 && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 8 }}>{t('wizard.step3_title')}</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 14 }}>{t('wizard.step3_desc')}</p>

          {dnsLoading && <p style={{ color: 'var(--text-muted)' }}>{t('wizard.step3_checking')}</p>}
          {dnsResults && dnsResults.map((r, i) => (
            <div key={i} className="dns-result">
              <span className={r.status === 'ok' ? 'dns-ok' : 'dns-missing'}>
                {r.status === 'ok' ? '✓' : '⚠'}
              </span>
              <div>
                <strong>{t(`dns.${r.record_type}_record`)}</strong>
                <span style={{ marginLeft: 8 }} className={`badge ${r.status === 'ok' ? 'badge-success' : 'badge-warning'}`}>
                  {t(`dns.status_${r.status}`)}
                </span>
                {r.suggestion && <div className="dns-suggestion">{r.suggestion}</div>}
              </div>
            </div>
          ))}

          {!dnsLoading && dnsResults && (
            <button className="btn btn-secondary" onClick={checkDns} style={{ marginTop: 12 }}>
              {t('wizard.step3_recheck')}
            </button>
          )}
        </div>
      )}

      {/* Step 4: Security */}
      {step === 4 && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 8 }}>{t('wizard.step4_title')}</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 14 }}>{t('wizard.step4_desc')}</p>

          <div className="alert alert-error" style={{ marginBottom: 16 }}>
            ⚠ {t('clients.access_required')}
          </div>

          <div className="form-group">
            <label className="form-label">{t('wizard.step4_method')}</label>
            <select className="form-input" value={accessMethod} onChange={e => setAccessMethod(e.target.value)}>
              <option value="ip">{t('wizard.step4_ip')}</option>
              <option value="smtp_auth">{t('wizard.step4_auth')}</option>
            </select>
          </div>

          {accessMethod === 'ip' && (
            <div className="form-group">
              <label className="form-label">{t('wizard.step4_ip_add')}</label>
              <textarea
                className="form-input"
                placeholder={t('wizard.step4_ip_placeholder_multi')}
                value={clientIp}
                onChange={e => setClientIp(e.target.value)}
                rows={3}
                style={{ resize: 'vertical', fontFamily: 'monospace', fontSize: 13 }}
              />
            </div>
          )}

          {accessMethod === 'smtp_auth' && smtpCreds && (
            <div className="info-box">
              <div><span className="label">{t('wizard.step4_auth_username')}: </span><span className="value">{smtpCreds.smtp_username}</span></div>
              <div><span className="label">{t('wizard.step4_auth_password')}: </span><span className="value">{smtpCreds.smtp_password_plain}</span></div>
              <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>{t('clients.save_credentials')}</div>
            </div>
          )}
        </div>
      )}

      {/* Step 5: Done */}
      {step === 5 && (
        <div className="card">
          <h2 className="card-title" style={{ marginBottom: 8 }}>{t('wizard.step5_title')}</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 16, fontSize: 14 }}>{t('wizard.step5_desc')}</p>

          <div className="info-box" style={{ marginBottom: 20 }}>
            <div><span className="label">{t('wizard.step5_host')}: </span><span className="value">{relayInfo.hostname}</span></div>
            <div><span className="label">{t('wizard.step5_port')}: </span><span className="value">{relayInfo.port}</span></div>
            <div><span className="label">{t('wizard.step5_from')}: </span><span className="value">{email}</span></div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label className="form-label">{t('wizard.step5_test_to')}</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="form-input"
                type="email"
                placeholder="test@example.com"
                value={testTo}
                onChange={e => setTestTo(e.target.value)}
              />
              <button className="btn btn-primary" onClick={sendTestEmail} disabled={testSending || !testTo}>
                {testSending ? t('common.loading') : t('wizard.step5_test_send')}
              </button>
            </div>
            {testStatus === 'ok' && <div className="alert alert-success" style={{ marginTop: 8 }}>{t('wizard.step5_test_ok')}</div>}
            {testStatus && testStatus !== 'ok' && <div className="alert alert-error" style={{ marginTop: 8 }}>{t('wizard.step5_test_fail', { error: testStatus })}</div>}
          </div>

          <button className="btn btn-primary" onClick={onComplete}>{t('nav.dashboard')}</button>
        </div>
      )}

      {/* Navigation */}
      <div className="wizard-footer">
        {step > 1 ? (
          <button className="btn btn-secondary" onClick={() => setStep(s => s - 1)}>{t('common.back')}</button>
        ) : <div />}
        {step < STEPS ? (
          <button
            className="btn btn-primary"
            onClick={nextStep}
            disabled={
              (step === 1 && !email) ||
              (step === 4 && accessMethod === 'ip' && !clientIp.trim())
            }
          >
            {t('common.next')}
          </button>
        ) : null}
      </div>
    </div>
  );
}
