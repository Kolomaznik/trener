import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ExercisesCatalog from './ExercisesCatalog.jsx';

vi.mock('../../api/catalog/get_exercise_list.js', () => ({
  getExerciseList: vi.fn(),
}));
vi.mock('../../api/user_exercises/post.js', () => ({
  addUserExercise: vi.fn(),
}));

import { getExerciseList } from '../../api/catalog/get_exercise_list.js';
import { addUserExercise } from '../../api/user_exercises/post.js';

const fixture = [
  { name: 'bridges_level_1', title: 'Krátké mosty', status: 'not_added' },
  { name: 'pushups_level_1', title: 'Kliky o zeď', status: 'not_added' },
  { name: 'pushups_level_2', title: 'Kliky v předklonu', status: 'in_progress' },
  { name: 'squats_level_1', title: 'Dřepy ve svíčce', status: 'completed' },
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
    getExerciseList.mockReset();
    getExerciseList.mockResolvedValue(fixture);
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

    await waitFor(() => expect(getExerciseList).toHaveBeenCalledTimes(1));

    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Kliky v předklonu')).toBeInTheDocument();
    expect(screen.getByText('Krátké mosty')).toBeInTheDocument();
    expect(screen.getByText('Dřepy ve svíčce')).toBeInTheDocument();
  });

  it('renders the heading "Katalog"', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Katalog' })).toBeInTheDocument();
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

  it('shows empty state when no rows match the filter', async () => {
    renderPage();
    await screen.findByText('Kliky o zeď');

    const search = screen.getByTestId('catalog-search').querySelector('input');
    fireEvent.change(search, { target: { value: 'zzznomatch' } });

    expect(await screen.findByText(/Žádné cviky neodpovídají/)).toBeInTheDocument();
  });

  it('shows error alert when the catalog API call fails', async () => {
    getExerciseList.mockRejectedValueOnce(new Error('boom'));
    renderPage();

    expect(await screen.findByText(/Nepodařilo se načíst katalog cviků/)).toBeInTheDocument();
  });

  it('renders an Add button for rows the user has not added', async () => {
    renderPage();
    expect(await screen.findByTestId('add-pushups_level_1')).toBeInTheDocument();
    expect(screen.getByTestId('add-bridges_level_1')).toBeInTheDocument();
  });

  it('renders an In progress label for rows the user has added but not completed', async () => {
    renderPage();
    expect(await screen.findByTestId('in-progress-pushups_level_2')).toBeInTheDocument();
    expect(screen.queryByTestId('add-pushups_level_2')).not.toBeInTheDocument();
  });

  it('renders a Splněno label for rows the user has completed', async () => {
    renderPage();
    expect(await screen.findByTestId('completed-squats_level_1')).toBeInTheDocument();
    expect(screen.queryByTestId('add-squats_level_1')).not.toBeInTheDocument();
  });

  it('clicking Add posts to /user-exercises and flips the row to In progress', async () => {
    renderPage();

    const addBtn = await screen.findByTestId('add-pushups_level_1');
    fireEvent.click(addBtn);

    await waitFor(() =>
      expect(addUserExercise).toHaveBeenCalledWith('pushups_level_1'),
    );
    expect(await screen.findByTestId('in-progress-pushups_level_1')).toBeInTheDocument();
  });
});
