import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Exercises from './Exercises.jsx';

vi.mock('../api/user_exercises/get_list.js', () => ({
  getUserExercises: vi.fn(),
}));

import { getUserExercises } from '../api/user_exercises/get_list.js';

const fixture = [
  {
    exercise_name: 'pushups_level_1',
    title: 'Kliky o zeď',
    family: 'Kliky',
    level: 1,
    user_level: 'intermediate',
    target_reps: 25,
    target_sets: 2,
  },
  {
    exercise_name: 'squats_level_1',
    title: 'Dřepy ve svíčce',
    family: 'Dřepy',
    level: 1,
    user_level: 'beginner',
    target_reps: 10,
    target_sets: 1,
  },
];

function renderWithRouter(initialPath = '/exercises') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/exercises" element={<Exercises />} />
        <Route path="/exercises/:name" element={<div data-testid="detail-marker" />} />
        <Route path="/admin/exercises" element={<div data-testid="catalog-marker" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Exercises page (user list)', () => {
  beforeEach(() => {
    getUserExercises.mockReset();
    getUserExercises.mockResolvedValue(fixture);
  });

  it('renders one tile per added exercise', async () => {
    renderWithRouter();

    await waitFor(() => expect(getUserExercises).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Dřepy ve svíčce')).toBeInTheDocument();
  });

  it('shows the user level tag when present', async () => {
    renderWithRouter();
    expect(await screen.findByText('Středně pokročilý')).toBeInTheDocument();
    expect(screen.getByText('Začátečník')).toBeInTheDocument();
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
    getUserExercises.mockRejectedValue(new Error('boom'));
    renderWithRouter();

    expect(
      await screen.findByText('Nepodařilo se načíst tvůj seznam cviků.'),
    ).toBeInTheDocument();
  });

  it('shows empty state with link to catalog when user has no added exercises', async () => {
    getUserExercises.mockResolvedValue([]);
    renderWithRouter();

    expect(await screen.findByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText(/přidej si je z katalogu/i)).toBeInTheDocument();

    const button = screen.getByRole('button', { name: /Otevřít katalog cviků/i });
    fireEvent.click(button);
    expect(await screen.findByTestId('catalog-marker')).toBeInTheDocument();
  });
});
