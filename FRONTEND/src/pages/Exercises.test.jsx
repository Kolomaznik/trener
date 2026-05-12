import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Exercises from './Exercises.jsx';

vi.mock('../api/user_exercises/get_list.js', () => ({
  getUserExercises: vi.fn(),
}));

import { getUserExercises } from '../api/user_exercises/get_list.js';

const fixture = [
  { exercise_name: 'pushups_level_1', title: 'Kliky o zeď' },
  { exercise_name: 'squats_level_1', title: 'Dřepy ve svíčce' },
];

function DetailMarker() {
  const { name } = useParams();
  return <div data-testid="detail-marker">{name}</div>;
}

function renderWithRouter(initialPath = '/exercises') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/exercises" element={<Exercises />} />
        <Route path="/exercises/:name" element={<DetailMarker />} />
        <Route path="/admin/exercises" element={<div data-testid="catalog-marker" />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Exercises entry redirector', () => {
  beforeEach(() => {
    getUserExercises.mockReset();
  });

  it('redirects to the first exercise from the user list', async () => {
    getUserExercises.mockResolvedValue(fixture);
    renderWithRouter();

    const marker = await screen.findByTestId('detail-marker');
    expect(marker.textContent).toBe('pushups_level_1');
  });

  it('shows empty state with link to catalog when user has no exercises', async () => {
    getUserExercises.mockResolvedValue([]);
    renderWithRouter();

    expect(await screen.findByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText(/přidej si je z katalogu/i)).toBeInTheDocument();

    const button = screen.getByRole('button', { name: /Otevřít katalog cviků/i });
    fireEvent.click(button);
    expect(await screen.findByTestId('catalog-marker')).toBeInTheDocument();
  });

  it('shows error alert when list fails to load', async () => {
    getUserExercises.mockRejectedValue(new Error('boom'));
    renderWithRouter();

    expect(
      await screen.findByText('Nepodařilo se načíst tvůj seznam cviků.'),
    ).toBeInTheDocument();
  });
});
