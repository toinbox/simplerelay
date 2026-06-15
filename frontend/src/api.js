/**
 * Make authenticated API calls. Reads token from localStorage.
 */
export async function apiFetch(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  return res;
}

export async function apiGet(url) {
  const res = await apiFetch(url);
  return res.json();
}

export async function apiPost(url, body) {
  const res = await apiFetch(url, { method: 'POST', body });
  return res;
}

export async function apiPatch(url, body) {
  const res = await apiFetch(url, { method: 'PATCH', body });
  return res;
}

export async function apiDelete(url) {
  const res = await apiFetch(url, { method: 'DELETE' });
  return res;
}
