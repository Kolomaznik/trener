import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { UserSettingsContext } from '../context/UserSettingsContext.jsx';
import Settings from './Settings.jsx';

vi.mock('../api/updateUserSettings.js', () => ({
  updateUserSettings: vi.fn(),
}));

import { updateUserSettings } from '../api/updateUserSettings.js';

const baseSettings = {
  email: 'alice@example.com',
  name: 'Alice Example',
  picture: 'https://x/avatar.jpg',
  gender: null,
  height_cm: null,
  weight_kg: null,
  birth_year: null,
  created_at: '2026-05-01T12:00:00Z',
};

function renderWith(settings, setUserSettings = vi.fn()) {
  return render(
    <UserSettingsContext.Provider value={{ userSettings: settings, setUserSettings }}>
      <Settings />
    </UserSettingsContext.Provider>,
  );
}

describe('Settings page', () => {
  beforeEach(() => {
    updateUserSettings.mockReset();
    updateUserSettings.mockResolvedValue({ ...baseSettings, gender: 'male' });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows a spinner when settings are not yet loaded', () => {
    renderWith(null);
    const spinner = document.querySelector('.ant-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders read-only avatar, name, email from Google profile', () => {
    renderWith(baseSettings);
    expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    expect(screen.getByText('Alice Example')).toBeInTheDocument();
    const avatarImg = document.querySelector('img[src="https://x/avatar.jpg"]');
    expect(avatarImg).toBeTruthy();
  });

  it('shows the incomplete-profile alert when required fields are missing', () => {
    renderWith(baseSettings);
    expect(screen.getByText(/vyplňte všechna pole/i)).toBeInTheDocument();
  });

  it('hides the incomplete-profile alert when profile is complete', () => {
    renderWith({
      ...baseSettings,
      gender: 'male',
      height_cm: 180,
      weight_kg: 75,
      birth_year: 1990,
    });
    expect(screen.queryByText(/vyplňte všechna pole/i)).not.toBeInTheDocument();
  });

  it('PATCHes immediately when gender radio is clicked', async () => {
    renderWith(baseSettings);
    const muz = screen.getByText('Muž');
    fireEvent.click(muz);

    await waitFor(() => {
      expect(updateUserSettings).toHaveBeenCalledWith({ gender: 'male' });
    });
  });

  it('updates context with the response from PATCH', async () => {
    const setUserSettings = vi.fn();
    updateUserSettings.mockResolvedValue({ ...baseSettings, gender: 'female' });
    renderWith(baseSettings, setUserSettings);

    fireEvent.click(screen.getByText('Žena'));

    await waitFor(() => {
      expect(setUserSettings).toHaveBeenCalledWith(
        expect.objectContaining({ gender: 'female' }),
      );
    });
  });

  it('debounces PATCH for height_cm — does not fire immediately', async () => {
    vi.useFakeTimers();
    renderWith(baseSettings);
    const heightInput = document.querySelector('input[role="spinbutton"]');
    expect(heightInput).toBeTruthy();
    fireEvent.change(heightInput, { target: { value: '180' } });

    vi.advanceTimersByTime(100);
    expect(updateUserSettings).not.toHaveBeenCalled();

    vi.advanceTimersByTime(500);
    expect(updateUserSettings).toHaveBeenCalledWith({ height_cm: 180 });
  });

  it('shows "Uloženo" status after successful PATCH', async () => {
    renderWith(baseSettings);
    fireEvent.click(screen.getByText('Muž'));

    await waitFor(() => {
      expect(screen.getByText(/uloženo/i)).toBeInTheDocument();
    });
  });

  it('shows error status when PATCH fails', async () => {
    updateUserSettings.mockRejectedValue(new Error('500'));
    renderWith(baseSettings);
    fireEvent.click(screen.getByText('Muž'));

    await waitFor(() => {
      expect(screen.getByText(/chyba ukládání/i)).toBeInTheDocument();
    });
  });

  it('shows computed age next to the birth year field', () => {
    const currentYear = new Date().getFullYear();
    renderWith({
      ...baseSettings,
      gender: 'male',
      height_cm: 180,
      weight_kg: 80,
      birth_year: 1990,
    });
    expect(
      screen.getByText(new RegExp(`aktuální věk:\\s*${currentYear - 1990}\\s*let`, 'i')),
    ).toBeInTheDocument();
  });
});
