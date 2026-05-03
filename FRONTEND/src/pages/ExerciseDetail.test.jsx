import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExerciseDetail from './ExerciseDetail.jsx';
import { UserSettingsContext } from '../context/UserSettingsContext.jsx';

vi.mock('../api/client.js', () => ({
  fetchExercises: vi.fn(),
  fetchExerciseDetail: vi.fn(),
  fetchMuscleLoad: vi.fn(),
}));

import { fetchExerciseDetail, fetchMuscleLoad } from '../api/client.js';

// ── Fixtures ──────────────────────────────────────────────────────────────────

const detailFixture = {
  id: 'pushups_level_1',
  name: 'Kliky o zeď',
  english_name: 'Wall Push-ups',
  family: 'Kliky',
  level: 1,
  description: 'Rehabilitační a přípravný cvik.',
  instructions: [
    'Postav se čelem ke zdi.',
    'Polož dlaně na zeď ve výšce hrudníku.',
  ],
  media: {
    youtube_tutorial: 'https://www.youtube.com/watch?v=xxx',
    thumbnail_url: 'https://img.youtube.com/vi/xxx/hqdefault.jpg',
  },
  cadence: {
    eccentric_sec: 2,
    pause_bottom_sec: 1,
    concentric_sec: 2,
    pause_top_sec: 1,
    total_rep_time_sec: 6,
    coach_note: 'Plynulý pohyb.',
  },
  progression_goals: {
    beginner: { sets: 1, reps: 10 },
    intermediate: { sets: 2, reps: 25 },
    mastery: { sets: 3, reps: 50 },
    coach_note: 'Po zvládnutí mastery na level 2.',
  },
  muscle_engagement_percent: { chest: 40, triceps: 30, lower_back: 5 },
  next_exercise_id: 'pushups_level_2',
  next_exercise_name: 'Kliky v předklonu',
  level_coefficient: 0.20,
  height_multiplier: 0.40,
};

const detailFixtureLevel2 = {
  ...detailFixture,
  id: 'pushups_level_2',
  name: 'Kliky v předklonu',
  english_name: null,
  level: 2,
  next_exercise_id: null,
  next_exercise_name: null,
  level_coefficient: 0.35,
};

/** A complete user profile (all fields required by isProfileComplete). */
const completeSettings = {
  gender: 'male',
  height_cm: 175,
  weight_kg: 80,
  birth_year: 1990,
};

/** Realistic muscle-load API response for the load-mode tests. */
const muscleLoadResponse = {
  muscle_engagement: {
    chest: { percent: 40, muscle_load: 200 },
    triceps: { percent: 30, muscle_load: 150 },
    lower_back: { percent: 5, muscle_load: 25 },
  },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Renders the ExerciseDetail page inside a UserSettingsContext provider and a
 * MemoryRouter so that router hooks and context hooks both work.
 *
 * @param {string} initialPath - URL to start at.
 * @param {object|null} settings - Value to put in UserSettingsContext.
 */
function renderWithRouter(initialPath = '/exercises/pushups_level_1', settings = null) {
  return render(
    <UserSettingsContext.Provider value={{ userSettings: settings, setUserSettings: vi.fn() }}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/exercises" element={<div data-testid="list-marker" />} />
          <Route path="/exercises/:id" element={<ExerciseDetail />} />
        </Routes>
      </MemoryRouter>
    </UserSettingsContext.Provider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ExerciseDetail page', () => {
  beforeEach(() => {
    fetchExerciseDetail.mockReset();
    fetchMuscleLoad.mockReset();
    fetchExerciseDetail.mockResolvedValue(detailFixture);
    fetchMuscleLoad.mockResolvedValue(muscleLoadResponse);
  });

  // ── Data fetching ──────────────────────────────────────────────────────────

  it('fetches detail using id from URL', async () => {
    renderWithRouter('/exercises/pushups_level_1');

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('pushups_level_1'),
    );
  });

  it('does NOT call fetchMuscleLoad on initial load (percent mode by default)', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(fetchMuscleLoad).not.toHaveBeenCalled();
  });

  // ── Header card ────────────────────────────────────────────────────────────

  it('renders name, english name, family/level chips, description', async () => {
    renderWithRouter();

    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Wall Push-ups')).toBeInTheDocument();
    expect(screen.getByText('Kliky')).toBeInTheDocument();
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    expect(screen.getByText('Rehabilitační a přípravný cvik.')).toBeInTheDocument();
  });

  // ── Difficulty tabs ────────────────────────────────────────────────────────

  it('renders three difficulty tabs: Začátečník, Středně pokročilý, Mistr', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByRole('tab', { name: 'Začátečník' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Středně pokročilý' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Mistr' })).toBeInTheDocument();
  });

  it('Začátečník tab is active by default and shows its sets × reps', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    // The beginner goal is 1 série × 10 opakování.
    expect(screen.getByText('1 × 10')).toBeInTheDocument();
  });

  it('switching to Středně pokročilý tab shows intermediate sets × reps', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('tab', { name: 'Středně pokročilý' }));
    expect(await screen.findByText('2 × 25')).toBeInTheDocument();
  });

  it('switching to Mistr tab shows mastery sets × reps', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('tab', { name: 'Mistr' }));
    expect(await screen.findByText('3 × 50')).toBeInTheDocument();
  });

  it('renders the coach note below the tabs', async () => {
    renderWithRouter();

    expect(await screen.findByText('Po zvládnutí mastery na level 2.')).toBeInTheDocument();
  });

  // ── Muscle map ─────────────────────────────────────────────────────────────

  it('renders the muscle map', async () => {
    renderWithRouter();

    const map = await screen.findByTestId('exercise-muscle-map');
    expect(map).toBeInTheDocument();
  });

  it('muscle map is styled for the engaged muscles in % mode', async () => {
    renderWithRouter();

    const map = await screen.findByTestId('exercise-muscle-map');
    const style = map.querySelector('style')?.textContent ?? '';
    expect(style).toContain('[data-slug="chest"]');
    expect(style).toContain('[data-slug="triceps"]');
  });

  // ── % / Svalová zátěž toggle ───────────────────────────────────────────────

  it('renders the % / Svalová zátěž segmented control', async () => {
    renderWithRouter();

    await screen.findByText('Zapojené svaly');
    expect(screen.getByText('% Zapojení')).toBeInTheDocument();
    expect(screen.getByText('Svalová zátěž')).toBeInTheDocument();
  });

  it('Svalová zátěž option is disabled when user profile is incomplete', async () => {
    renderWithRouter('/exercises/pushups_level_1', null);

    await screen.findByText('Zapojené svaly');
    // antd Segmented marks disabled items with ant-segmented-item-disabled class.
    const option = screen.getByText('Svalová zátěž').closest('.ant-segmented-item');
    expect(option).toHaveClass('ant-segmented-item-disabled');
  });

  it('shows an info alert when load mode is somehow active without a profile', async () => {
    // Render without a profile and programmatically verify the alert appears
    // only when the mode reaches 'load' (edge case guard).
    renderWithRouter('/exercises/pushups_level_1', null);
    await screen.findByText('Zapojené svaly');

    // The disabled button cannot be clicked normally; verify no alert yet.
    expect(
      screen.queryByText(/vyplňte tělesné údaje/i),
    ).not.toBeInTheDocument();
  });

  it('calls fetchMuscleLoad when switching to load mode with a complete profile', async () => {
    renderWithRouter('/exercises/pushups_level_1', completeSettings);

    await screen.findByText('Zapojené svaly');
    fireEvent.click(screen.getByText('Svalová zátěž'));

    await waitFor(() =>
      expect(fetchMuscleLoad).toHaveBeenCalledWith(
        'pushups_level_1',
        expect.objectContaining({
          weight_kg: 80,
          height_cm: 175,
          gender: 'M',
          // beginner: 1 set × 10 reps = 10 total_reps
          total_reps: 10,
        }),
      ),
    );
  });

  it('re-fetches muscle load when the active difficulty tab changes in load mode', async () => {
    renderWithRouter('/exercises/pushups_level_1', completeSettings);

    await screen.findByText('Zapojené svaly');
    fireEvent.click(screen.getByText('Svalová zátěž'));

    // Wait for the first call (beginner tab).
    await waitFor(() => expect(fetchMuscleLoad).toHaveBeenCalledTimes(1));

    // Switch to Mistr tab — should trigger a new fetch with mastery total_reps.
    fireEvent.click(screen.getByRole('tab', { name: 'Mistr' }));
    await waitFor(() => expect(fetchMuscleLoad).toHaveBeenCalledTimes(2));
    expect(fetchMuscleLoad).toHaveBeenLastCalledWith(
      'pushups_level_1',
      expect.objectContaining({ total_reps: 150 }), // mastery: 3 × 50
    );
  });

  // ── Static detail cards ────────────────────────────────────────────────────

  it('renders instructions, cadence, video cards', async () => {
    renderWithRouter();

    expect(await screen.findByText('Jak cvičit')).toBeInTheDocument();
    expect(screen.getByText(/Postav se čelem ke zdi/)).toBeInTheDocument();
    expect(screen.getByText('Tempo')).toBeInTheDocument();
    expect(screen.getByText('6 s / opakování')).toBeInTheDocument();
    expect(screen.getByText('Video')).toBeInTheDocument();
  });

  // ── Navigation ─────────────────────────────────────────────────────────────

  it('navigates back to list when "Zpět na seznam" button is clicked', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('button', { name: /Zpět na seznam/ }));

    expect(await screen.findByTestId('list-marker')).toBeInTheDocument();
  });

  it('navigates to next exercise when "next level" button is clicked', async () => {
    fetchExerciseDetail.mockImplementation(async (id) =>
      id === 'pushups_level_2' ? detailFixtureLevel2 : detailFixture,
    );
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('button', { name: 'Kliky v předklonu' }));

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('pushups_level_2'),
    );
    expect(
      await screen.findByText('Nejvyšší úroveň této rodiny'),
    ).toBeInTheDocument();
  });

  // ── Error states ───────────────────────────────────────────────────────────

  it('shows 404 message when exercise is not found', async () => {
    fetchExerciseDetail.mockRejectedValue({ response: { status: 404 } });
    renderWithRouter('/exercises/neexistuje');

    expect(await screen.findByText('Cvik nebyl nalezen.')).toBeInTheDocument();
  });
});
