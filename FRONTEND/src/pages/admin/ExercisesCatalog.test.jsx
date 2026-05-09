import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ExercisesCatalog from './ExercisesCatalog.jsx';

vi.mock('../../api/exercises/get_catalog.js', () => ({
  getExercisesCatalog: vi.fn(),
}));
vi.mock('../../api/user_exercises/get_list.js', () => ({
  getUserExercises: vi.fn(),
}));
vi.mock('../../api/user_exercises/post.js', () => ({
  addUserExercise: vi.fn(),
}));

import { getExercisesCatalog } from '../../api/exercises/get_catalog.js';
import { getUserExercises } from '../../api/user_exercises/get_list.js';
import { addUserExercise } from '../../api/user_exercises/post.js';

const fixture = [
  { name: 'bridges_level_1', title: 'Krátké mosty', family: 'Mosty', level: 1 },
  { name: 'pushups_level_1', title: 'Kliky o zeď', family: 'Kliky', level: 1 },
  { name: 'pushups_level_2', title: 'Kliky v předklonu', family: 'Kliky', level: 2 },
  { name: 'squats_level_1', title: 'Dřepy ve svíčce', family: 'Dřepy', level: 1 },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/admin/exercises']}>
      <ExercisesCatalog />
    </MemoryRouter>,
  );
}

describe('ExercisesCatalog page', () => {
  beforeEach(() => {
    getExercisesCatalog.mockReset();
    getExercisesCatalog.mockResolvedValue(fixture);
    getUserExercises.mockReset();
    getUserExercises.mockResolvedValue([]);
    addUserExercise.mockReset();
    addUserExercise.mockResolvedValue({
      exercise_name: 'pushups_level_1',
      user_level: 'beginner',
      target_reps: 10,
      target_sets: 1,
      rest_seconds: 90,
      created_at: '2026-05-08T12:00:00Z',
    });
  });

  it('renders one row per catalog entry', async () => {
    renderPage();

    await waitFor(() => expect(getExercisesCatalog).toHaveBeenCalledTimes(1));

    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Kliky v předklonu')).toBeInTheDocument();
    expect(screen.getByText('Krátké mosty')).toBeInTheDocument();
    expect(screen.getByText('Dřepy ve svíčce')).toBeInTheDocument();
  });

  it('renders the heading "Cviky (katalog)"', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Cviky (katalog)' })).toBeInTheDocument();
  });

  it('search filters rows by title', async () => {
    renderPage();
    await screen.findByText('Kliky o zeď');

    const search = screen.getByTestId('catalog-search').querySelector('input');
    fireEvent.change(search, { target: { value: 'klik' } });

    await waitFor(() => {
      expect(screen.queryByText('Krátké mosty')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Kliky v předklonu')).toBeInTheDocument();
  });

  it('search filters rows by family', async () => {
    renderPage();
    await screen.findByText('Kliky o zeď');

    const search = screen.getByTestId('catalog-search').querySelector('input');
    fireEvent.change(search, { target: { value: 'mosty' } });

    await waitFor(() => {
      expect(screen.queryByText('Kliky o zeď')).not.toBeInTheDocument();
    });
    expect(screen.getByText('Krátké mosty')).toBeInTheDocument();
  });

  it('shows empty state when no rows match the filter', async () => {
    renderPage();
    await screen.findByText('Kliky o zeď');

    const search = screen.getByTestId('catalog-search').querySelector('input');
    fireEvent.change(search, { target: { value: 'zzznomatch' } });

    expect(await screen.findByText(/Žádné cviky neodpovídají/)).toBeInTheDocument();
  });

  it('shows error alert when the catalog API call fails', async () => {
    getExercisesCatalog.mockRejectedValueOnce(new Error('boom'));
    renderPage();

    expect(await screen.findByText(/Nepodařilo se načíst katalog cviků/)).toBeInTheDocument();
  });

  it('renders an Add button for rows the user has not added', async () => {
    renderPage();
    expect(await screen.findByTestId('add-pushups_level_1')).toBeInTheDocument();
    expect(screen.getByTestId('add-bridges_level_1')).toBeInTheDocument();
  });

  it('marks rows as Přidáno when the user already has them', async () => {
    getUserExercises.mockResolvedValue([
      { exercise_name: 'pushups_level_1', user_level: 'beginner' },
    ]);
    renderPage();

    expect(await screen.findByTestId('added-pushups_level_1')).toBeInTheDocument();
    expect(screen.queryByTestId('add-pushups_level_1')).not.toBeInTheDocument();
    // The other rows still show an Add button.
    expect(screen.getByTestId('add-bridges_level_1')).toBeInTheDocument();
  });

  it('clicking Add posts to /user-exercises and replaces the button with Přidáno', async () => {
    renderPage();

    const addBtn = await screen.findByTestId('add-pushups_level_1');
    fireEvent.click(addBtn);

    await waitFor(() =>
      expect(addUserExercise).toHaveBeenCalledWith('pushups_level_1'),
    );
    expect(await screen.findByTestId('added-pushups_level_1')).toBeInTheDocument();
  });
});
