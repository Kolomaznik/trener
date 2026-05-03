import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Exercises from './Exercises.jsx';

vi.mock('../api/client.js', () => ({
  fetchExercises: vi.fn(),
  fetchExerciseDetail: vi.fn(),
}));

import { fetchExercises } from '../api/client.js';

const listFixture = [
  {
    id: 'pushups_level_1',
    name: 'Kliky o zeď',
    family: 'Kliky',
    level: 1,
    description: 'Rehabilitační a přípravný cvik.',
    next_exercise_id: 'pushups_level_2',
    next_exercise_name: 'Kliky v předklonu',
  },
  {
    id: 'pushups_level_2',
    name: 'Kliky v předklonu',
    family: 'Kliky',
    level: 2,
    description: 'Náročnější varianta.',
    next_exercise_id: null,
    next_exercise_name: null,
  },
];

function renderWithRouter(initialPath = '/exercises') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/exercises" element={<Exercises />} />
        <Route path="/exercises/:id" element={<div data-testid="detail-marker" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Exercises page (tile grid)', () => {
  beforeEach(() => {
    fetchExercises.mockReset();
    fetchExercises.mockResolvedValue(listFixture);
  });

  it('renders tiles for each exercise', async () => {
    renderWithRouter();

    await waitFor(() => expect(fetchExercises).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Kliky v předklonu')).toBeInTheDocument();
    expect(screen.getAllByText('Kliky').length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText(/Level \d/).length).toBeGreaterThanOrEqual(2);
  });

  it('shows "next level" hint on tiles that have one, "highest" otherwise', async () => {
    renderWithRouter();

    expect(
      await screen.findByText(/Další úroveň: Kliky v předklonu/),
    ).toBeInTheDocument();
    expect(screen.getByText('Nejvyšší úroveň této rodiny')).toBeInTheDocument();
  });

  it('navigates to detail when a tile is clicked', async () => {
    renderWithRouter();

    const tile = await screen.findByRole('button', {
      name: 'Otevřít cvik Kliky o zeď',
    });
    fireEvent.click(tile);

    expect(await screen.findByTestId('detail-marker')).toBeInTheDocument();
  });

  it('shows error alert when list fails to load', async () => {
    fetchExercises.mockRejectedValue(new Error('boom'));
    renderWithRouter();

    expect(
      await screen.findByText('Nepodařilo se načíst seznam cviků.'),
    ).toBeInTheDocument();
  });

  it('shows empty state when no exercises in DB', async () => {
    fetchExercises.mockResolvedValue([]);
    renderWithRouter();

    expect(
      await screen.findByText('Žádné cviky v databázi.'),
    ).toBeInTheDocument();
  });
});
