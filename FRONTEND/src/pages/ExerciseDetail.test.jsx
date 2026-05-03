import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExerciseDetail from './ExerciseDetail.jsx';

vi.mock('../api/client.js', () => ({
  fetchExercises: vi.fn(),
  fetchExerciseDetail: vi.fn(),
}));

import { fetchExerciseDetail } from '../api/client.js';

// ── Fixtures ──────────────────────────────────────────────────────────────────

/**
 * Muscle load for pushups_level_1 (level_coefficient = 0.20), user weight = 80 kg.
 * Formula: total_load = weight_kg × total_reps × level_coefficient
 *   beginner     (1×10  = 10  reps): 80 × 10  × 0.20 = 160 kg total
 *   intermediate (2×25  = 50  reps): 80 × 50  × 0.20 = 800 kg total
 *   mastery      (3×50  = 150 reps): 80 × 150 × 0.20 = 2400 kg total
 */
const muscleLoadByDifficulty = {
  beginner: {
    chest: { percent: 40, muscle_load: 64.0 },   // 160 × 0.40
    triceps: { percent: 30, muscle_load: 48.0 },  // 160 × 0.30
    lower_back: { percent: 5, muscle_load: 8.0 }, // 160 × 0.05
  },
  intermediate: {
    chest: { percent: 40, muscle_load: 320.0 },
    triceps: { percent: 30, muscle_load: 240.0 },
    lower_back: { percent: 5, muscle_load: 40.0 },
  },
  mastery: {
    chest: { percent: 40, muscle_load: 960.0 },
    triceps: { percent: 30, muscle_load: 720.0 },
    lower_back: { percent: 5, muscle_load: 120.0 },
  },
};

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
  muscle_load_by_difficulty: muscleLoadByDifficulty,
  next_exercise_id: 'pushups_level_2',
  next_exercise_name: 'Kliky v předklonu',
  level_coefficient: 0.20,
  height_multiplier: 0.40,
};

/** Fixture without load data — simulates an unauthenticated / no-profile response. */
const detailFixtureNoLoad = {
  ...detailFixture,
  muscle_load_by_difficulty: null,
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

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderWithRouter(initialPath = '/exercises/pushups_level_1') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/exercises" element={<div data-testid="list-marker" />} />
        <Route path="/exercises/:id" element={<ExerciseDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ExerciseDetail page', () => {
  beforeEach(() => {
    fetchExerciseDetail.mockReset();
    fetchExerciseDetail.mockResolvedValue(detailFixture);
  });

  // ── Data fetching ──────────────────────────────────────────────────────────

  it('fetches detail using id from URL', async () => {
    renderWithRouter('/exercises/pushups_level_1');

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('pushups_level_1'),
    );
  });

  it('makes exactly one API call on load (no separate muscle-load request)', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(fetchExerciseDetail).toHaveBeenCalledTimes(1);
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

  // ── % / Přemístěná zátěž toggle ───────────────────────────────────────────

  it('renders the toggle: % Zapojení and Přemístěná zátěž (kg)', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    expect(screen.getByText('% Zapojení')).toBeInTheDocument();
    expect(screen.getByText('Přemístěná zátěž (kg)')).toBeInTheDocument();
  });

  it('Přemístěná zátěž option is disabled when load data is absent', async () => {
    fetchExerciseDetail.mockResolvedValue(detailFixtureNoLoad);
    renderWithRouter();

    await screen.findByText('% Zapojení');
    const option = screen.getByText('Přemístěná zátěž (kg)').closest('.ant-segmented-item');
    expect(option).toHaveClass('ant-segmented-item-disabled');
  });

  it('shows an info alert when load data is absent', async () => {
    fetchExerciseDetail.mockResolvedValue(detailFixtureNoLoad);
    renderWithRouter();

    expect(await screen.findByText(/Přihlaste se a vyplňte hmotnost/i)).toBeInTheDocument();
  });

  it('does NOT show the info alert when load data is present', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.queryByText(/Přihlaste se a vyplňte hmotnost/i)).not.toBeInTheDocument();
  });

  it('switching to Přemístěná zátěž mode does not call fetchExerciseDetail again', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));

    // Still exactly 1 call — no extra API request
    expect(fetchExerciseDetail).toHaveBeenCalledTimes(1);
  });

  it('muscle map updates immediately when switching to load mode (no spinner needed)', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));

    // The map should still be present (no loading state)
    expect(screen.getByTestId('exercise-muscle-map')).toBeInTheDocument();
  });

  // ── Map legend switches between modes ──────────────────────────────────────

  it('shows "Zapojení" legend title in default % mode', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    expect(screen.getByTestId('muscle-map-scale')).toHaveTextContent('Zapojení');
  });

  it('switches legend title to "Přemístěná zátěž" when load mode is active', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));

    expect(screen.getByTestId('muscle-map-scale')).toHaveTextContent('Přemístěná zátěž');
  });

  it('shows qualitative load labels (not % labels) when load mode is active', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));

    const scale = screen.getByTestId('muscle-map-scale');
    // Should show actual tonne values, not % labels or the old qualitative words
    expect(scale.textContent).toMatch(/\d+\.\d+\s*t/);
    expect(scale).not.toHaveTextContent('50 %+');
    expect(scale).not.toHaveTextContent('Nejvíce');
  });

  it('shows 5 tonne stops in load mode matching fixture min/max (beginner tier)', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));

    // beginner: chest=64, triceps=48, lower_back=8 → max=64, min=8
    // 5 stops: 64, 50, 36, 22, 8 kg → 0.06, 0.05, 0.04, 0.02, 0.01 t (toFixed(2))
    const scale = screen.getByTestId('muscle-map-scale');
    const swatches = scale.querySelectorAll('span');
    expect(swatches).toHaveLength(5);
    // Top stop = max (0.06 t), bottom stop = min (0.01 t)
    expect(swatches[0].textContent).toBe('0.06\u202ft');
    expect(swatches[4].textContent).toBe('0.01\u202ft');
  });

  it('restores % labels when switching back to % mode', async () => {
    renderWithRouter();

    await screen.findByText('% Zapojení');
    fireEvent.click(screen.getByText('Přemístěná zátěž (kg)'));
    fireEvent.click(screen.getByText('% Zapojení'));

    const scale = screen.getByTestId('muscle-map-scale');
    expect(scale).toHaveTextContent('50 %+');
    expect(scale.textContent).not.toMatch(/\d+\.\d+\s*t/);
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
