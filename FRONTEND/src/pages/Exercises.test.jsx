import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Exercises from './Exercises.jsx';

vi.mock('../api/client.js', () => ({
  fetchExercises: vi.fn(),
  fetchExerciseDetail: vi.fn(),
}));

import { fetchExerciseDetail, fetchExercises } from '../api/client.js';

const listFixture = [
  {
    id: 'pushups',
    order: 1,
    category: 'Kliky',
    name: 'Kliky',
    description: 'Tlakový cvik.',
    image: '/favicon.svg',
    available_levels: ['beginner', 'advanced', 'expert'],
    next_exercise_id: 'squats',
    next_exercise_name: 'Dřepy',
  },
  {
    id: 'squats',
    order: 2,
    category: 'Dřepy',
    name: 'Dřepy',
    description: 'Cvik na nohy.',
    image: '/favicon.svg',
    available_levels: ['beginner', 'advanced', 'expert'],
    next_exercise_id: null,
    next_exercise_name: null,
  },
];

function detailFixture({ id = 'pushups', level = 'beginner', title = 'Začátečník' } = {}) {
  return {
    id,
    order: 1,
    category: id === 'pushups' ? 'Kliky' : 'Dřepy',
    name: id === 'pushups' ? 'Kliky' : 'Dřepy',
    description: id === 'pushups' ? 'Tlakový cvik.' : 'Cvik na nohy.',
    image: '/favicon.svg',
    muscles: ['hrudník', 'triceps'],
    frequency: '2–4x týdně',
    correct: ['Rovná linie těla'],
    incorrect: ['Propadlá bedra'],
    level,
    level_detail: { title, reps: '3 série po 8–12', note: 'Drž techniku.' },
    level_order: ['beginner', 'advanced', 'expert'],
  };
}

describe('Exercises page', () => {
  beforeEach(() => {
    fetchExercises.mockReset();
    fetchExerciseDetail.mockReset();
    fetchExercises.mockResolvedValue(listFixture);
    fetchExerciseDetail.mockResolvedValue(detailFixture());
  });

  it('renders the list of exercises after loading', async () => {
    render(<Exercises />);

    await waitFor(() => expect(fetchExercises).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('1. Kliky')).toBeInTheDocument();
    expect(screen.getByText('2. Dřepy')).toBeInTheDocument();
    expect(screen.getByText(/Další v pořadí: Dřepy/)).toBeInTheDocument();
    expect(screen.getByText('Poslední cvik v pevné návaznosti')).toBeInTheDocument();
  });

  it('auto-loads detail of the first exercise', async () => {
    render(<Exercises />);

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('pushups', 'beginner'),
    );
    expect(
      await screen.findByText(/3 série po 8–12/, undefined, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it('loads detail when another exercise is clicked', async () => {
    fetchExerciseDetail.mockImplementation(async (id, level) =>
      detailFixture({ id, level, title: level === 'beginner' ? 'Začátečník' : 'Pokročilý' }),
    );
    render(<Exercises />);

    await screen.findByText('1. Kliky');
    fetchExerciseDetail.mockClear();
    fireEvent.click(screen.getByText('2. Dřepy'));

    await waitFor(() =>
      expect(fetchExerciseDetail).toHaveBeenCalledWith('squats', 'beginner'),
    );
  });

  it('shows an error alert when list fails to load', async () => {
    fetchExercises.mockRejectedValue(new Error('boom'));
    render(<Exercises />);

    expect(
      await screen.findByText('Nepodařilo se načíst seznam cviků.'),
    ).toBeInTheDocument();
  });
});
