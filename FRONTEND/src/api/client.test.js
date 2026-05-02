import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { apiClient } from './client.js';

const STORAGE_KEY = 'trainer_google_auth_token';

async function runRequestInterceptors(initial) {
  const handlers = apiClient.interceptors.request.handlers.filter((h) => h && h.fulfilled);
  let config = initial;
  for (const h of handlers) {
    config = await h.fulfilled(config);
  }
  return config;
}

describe('apiClient request interceptor', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });
  afterEach(() => {
    window.localStorage.clear();
  });

  it('does NOT attach Authorization header when no token is in localStorage', async () => {
    const config = await runRequestInterceptors({ url: '/x', headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });

  it('attaches Bearer header when localStorage has accessToken object', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'tok-abc', expiresAtMs: Date.now() + 60_000 }),
    );
    const config = await runRequestInterceptors({ url: '/x', headers: {} });
    expect(config.headers.Authorization).toBe('Bearer tok-abc');
  });

  it('attaches Bearer header when localStorage has plain string token', async () => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify('plain-token'));
    const config = await runRequestInterceptors({ url: '/x', headers: {} });
    expect(config.headers.Authorization).toBe('Bearer plain-token');
  });

  it('skips Authorization when stored token has expired', async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'tok-old', expiresAtMs: Date.now() - 1 }),
    );
    const config = await runRequestInterceptors({ url: '/x', headers: {} });
    expect(config.headers.Authorization).toBeUndefined();
  });
});
