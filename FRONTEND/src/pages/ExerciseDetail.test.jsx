import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExerciseDetail from './ExerciseDetail.jsx';

vi.mock('../api/client.js', () => ({
  fetchExercises: vi.fn(),
  fetchExerciseDetail: vi.fn(),
}));

import { fetchExerciseDetail } from '../api/client.js';

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
};

const detailFixtureLevel2 = {
  ...detailFixture,
  id: 'pushups_level_2',
  name: 'Kliky v předklonu',
  english_name: null,
  level: 2,
  next_exercise_id: null,
  next_exercise_name: null,
};

function renderWithRouter(initialPath = '/exercises/pushups_level_1') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/exercises" element={<div data-testid="list-marker" />} />
        <Route path="/exercises/:id" element={<ExerciseDetail />} />
        <Route path="/exercises/:id/workout" element={<div data-testid="workout-marker" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ExerciseDetail page', () => {
  beforeEach(() => {
    fetchExerciseDetail.mockReset();
    fetchExerciseDetail.mockResolvedValue(detailFixture);
  });

  it('fetches detail using id from URL', async () => {
    renderWithRouter('/exercises/pushups_level_1');

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('pushups_level_1'),
    );
  });

  it('renders name, english name, family/level chips, description', async () => {
    renderWithRouter();

    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Wall Push-ups')).toBeInTheDocument();
    expect(screen.getByText('Kliky')).toBeInTheDocument();
    expect(screen.getByText('Level 1')).toBeInTheDocument();
    expect(
      screen.getByText('Rehabilitační a přípravný cvik.'),
    ).toBeInTheDocument();
  });

  it('renders rich detail: instructions, cadence, progression, video', async () => {
    renderWithRouter();

    expect(await screen.findByText('Jak cvičit')).toBeInTheDocument();
    expect(screen.getByText(/Postav se čelem ke zdi/)).toBeInTheDocument();
    expect(screen.getByText('Tempo')).toBeInTheDocument();
    expect(screen.getByText('6 s / opakování')).toBeInTheDocument();
    expect(screen.getByText('Postup')).toBeInTheDocument();
    expect(screen.getByText('3 × 50')).toBeInTheDocument();
    expect(screen.getByText('Video')).toBeInTheDocument();
  });

  it('renders the muscle map with engaged-muscle styles', async () => {
    renderWithRouter();

    const map = await screen.findByTestId('exercise-muscle-map');
    expect(map).toBeInTheDocument();
    const style = map.querySelector('style')?.textContent ?? '';
    expect(style).toContain('[data-slug="chest"]');
    expect(style).toContain('[data-slug="triceps"]');
  });

  it('navigates back to list when "back" link is clicked', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('button', { name: /Zpět na seznam/ }));

    expect(await screen.findByTestId('list-marker')).toBeInTheDocument();
  });

  it('navigates to next exercise when "next level" link is clicked', async () => {
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

  it('shows 404 message when exercise not found', async () => {
    fetchExerciseDetail.mockRejectedValue({ response: { status: 404 } });
    renderWithRouter('/exercises/neexistuje');

    expect(await screen.findByText('Cvik nebyl nalezen.')).toBeInTheDocument();
  });

  it('renders "Začít cvičit" button that navigates to workout page', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    fireEvent.click(screen.getByRole('button', { name: /Začít cvičit/ }));

    expect(await screen.findByTestId('workout-marker')).toBeInTheDocument();
  });
});
