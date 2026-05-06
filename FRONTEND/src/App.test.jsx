import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api/user/settings/get.js', () => ({
  getUserSettings: vi.fn(),
}));
vi.mock('./api/user/settings/patch.js', () => ({
  patchUserSettings: vi.fn(),
}));
vi.mock('./pages/Home.jsx', () => ({ default: () => <div>HOME PAGE</div> }));
vi.mock('./pages/Exercises.jsx', () => ({ default: () => <div>EXERCISES PAGE</div> }));

import App from './App.jsx';
import { getUserSettings } from './api/user/settings/get.js';

const STORAGE_KEY = 'trainer_google_auth_token';

function PathSpy() {
  const { pathname } = useLocation();
  return <div data-testid="pathname">{pathname}</div>;
}

function renderAppAt(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="*" element={
          <>
            <PathSpy />
            <App />
          </>
        } />
      </Routes>
    </MemoryRouter>,
  );
}

describe('App profile guard', () => {
  beforeEach(() => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ accessToken: 'tok-test', expiresAtMs: Date.now() + 60_000 }),
    );
    getUserSettings.mockReset();
  });

  afterEach(() => {
    window.localStorage.clear();
    vi.clearAllMocks();
  });

  it('redirects to /settings when required fields are missing', async () => {
    getUserSettings.mockResolvedValue({
      email: 'a@b.cz',
      name: 'A',
      picture: 'p',
      gender: null,
      height_cm: null,
      weight_kg: null,
      birth_year: null,
    });

    renderAppAt('/');

    await waitFor(() => {
      expect(screen.getByTestId('pathname').textContent).toBe('/settings');
    });
  });

  it('does not redirect when profile is complete', async () => {
    getUserSettings.mockResolvedValue({
      email: 'a@b.cz',
      name: 'A',
      picture: 'p',
      gender: 'male',
      height_cm: 180,
      weight_kg: 75,
      birth_year: 1990,
    });

    renderAppAt('/');

    await waitFor(() => {
      expect(getUserSettings).toHaveBeenCalled();
    });

    expect(screen.getByTestId('pathname').textContent).toBe('/');
  });

  it('redirects from /exercises to /settings when profile is incomplete', async () => {
    getUserSettings.mockResolvedValue({
      email: 'a@b.cz',
      name: 'A',
      picture: 'p',
      gender: 'male',
      height_cm: null,
      weight_kg: null,
      birth_year: null,
    });

    renderAppAt('/exercises');

    await waitFor(() => {
      expect(screen.getByTestId('pathname').textContent).toBe('/settings');
    });
  });

  it('keeps the user on /settings even if profile is incomplete (no infinite loop)', async () => {
    getUserSettings.mockResolvedValue({
      email: 'a@b.cz',
      name: 'A',
      picture: 'p',
      gender: null,
      height_cm: null,
      weight_kg: null,
      birth_year: null,
    });

    renderAppAt('/settings');

    await waitFor(() => {
      expect(getUserSettings).toHaveBeenCalled();
    });
    expect(screen.getByTestId('pathname').textContent).toBe('/settings');
  });
});
