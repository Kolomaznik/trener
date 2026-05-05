import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import WorkoutSession from './WorkoutSession.jsx';

vi.mock('../api/exercises/get_detail.js', () => ({
  getExerciseDetail: vi.fn(),
}));
vi.mock('../api/workout-sessions/post.js', () => ({
  postWorkoutSession: vi.fn(),
}));

vi.mock('react-speech-recognition', () => {
  const initialState = {
    transcript: '',
    listening: false,
    browserSupportsSpeechRecognition: true,
    isMicrophoneAvailable: true,
  };

  let state = { ...initialState };

  const startListening = vi.fn(async () => {
    state = { ...state, listening: true };
  });
  const stopListening = vi.fn(async () => {
    state = { ...state, listening: false };
  });
  const resetTranscript = vi.fn(() => {
    state = { ...state, transcript: '' };
  });
  const setMockState = (patch) => {
    state = { ...state, ...patch };
  };
  const resetMock = () => {
    state = { ...initialState };
    startListening.mockClear();
    stopListening.mockClear();
    resetTranscript.mockClear();
  };

  return {
    default: { startListening, stopListening },
    useSpeechRecognition: () => ({ ...state, resetTranscript }),
    __setMockState: setMockState,
    __resetMockState: resetMock,
    __mocks: { startListening, stopListening },
  };
});

import * as speechModule from 'react-speech-recognition';
import { getExerciseDetail } from '../api/exercises/get_detail.js';
import { postWorkoutSession } from '../api/workout-sessions/post.js';

const levelFixtureBeginner = {
  level: 'beginner',
  recent_sets: [],
  target_reps: 10,
  target_sets: 1,
  last_best_reps: null,
  rest_seconds: 90,
};

const levelFixtureIntermediate = {
  level: 'intermediate',
  recent_sets: [{ total_reps: 20, started_at: '2026-05-03T10:00:00Z', set_number: 1 }],
  target_reps: 25,
  target_sets: 2,
  last_best_reps: 20,
  rest_seconds: 60,
};

const detailFixture = {
  id: 'pushups_level_1',
  name: 'Kliky o zeď',
  english_name: 'Wall Push-ups',
  family: 'Kliky',
  level: 1,
  description: 'Rehabilitační cvik.',
  instructions: ['Postav se ke zdi.'],
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
    coach_note: 'Pokračuj na level 2.',
  },
  muscle_engagement_percent: { chest: 40, triceps: 30 },
  next_exercise_id: null,
  next_exercise_name: null,
  user_level: levelFixtureBeginner,
};

function renderWithRouter(path = '/exercises/pushups_level_1/workout') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/exercises/:id" element={<div data-testid="detail-marker" />} />
        <Route path="/exercises/:id/workout" element={<WorkoutSession />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('WorkoutSession page', () => {
  beforeEach(() => {
    speechModule.__resetMockState();
    getExerciseDetail.mockReset();
    postWorkoutSession.mockReset();

    getExerciseDetail.mockResolvedValue(detailFixture);
    postWorkoutSession.mockResolvedValue({ id: 'session-1', total_reps: 5 });
  });

  it('shows skeleton while loading', () => {
    getExerciseDetail.mockReturnValue(new Promise(() => {}));
    renderWithRouter();

    expect(document.querySelector('.ant-skeleton')).toBeInTheDocument();
  });

  it('renders exercise name and level badge after load', async () => {
    renderWithRouter();

    expect(await screen.findByText('Kliky o zeď')).toBeInTheDocument();
    expect(screen.getByText('Level 1')).toBeInTheDocument();
  });

  it('shows beginner level tag', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByText('Začátečník')).toBeInTheDocument();
  });

  it('shows intermediate level tag with last best reps', async () => {
    getExerciseDetail.mockResolvedValue({ ...detailFixture, user_level: levelFixtureIntermediate });
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByText('Středně pokročilý')).toBeInTheDocument();
    expect(screen.getByText(/Naposledy nejlepší výkon/)).toBeInTheDocument();
    expect(screen.getByText(/20/)).toBeInTheDocument();
  });

  it('shows target reps motivation message', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByText(/Dnes překonej/)).toBeInTheDocument();
    // target_reps = 10 is shown inside the motivation text
    const motivationEl = screen.getByText(/Dnes překonej/);
    expect(motivationEl.textContent).toMatch(/10/);
  });

  it('shows "Série 1" heading initially', async () => {
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByText('Série 1')).toBeInTheDocument();
  });

  it('shows Start button and activates listening on click', async () => {
    const { rerender } = renderWithRouter();

    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    rerender(
      <MemoryRouter initialEntries={['/exercises/pushups_level_1/workout']}>
        <Routes>
          <Route path="/exercises/:id" element={<div data-testid="detail-marker" />} />
          <Route path="/exercises/:id/workout" element={<WorkoutSession />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(speechModule.__mocks.startListening).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId('listening-badge')).toBeInTheDocument();
  });

  it('shows "Konec série" button while listening', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));

    await waitFor(() => expect(screen.getByRole('button', { name: /Konec série/ })).toBeInTheDocument());
  });

  it('stops listening and saves session when "Konec série" is clicked', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    await waitFor(() => screen.getByRole('button', { name: /Konec série/ }));

    fireEvent.click(screen.getByRole('button', { name: /Konec série/ }));

    await waitFor(() => expect(speechModule.__mocks.stopListening).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(postWorkoutSession).toHaveBeenCalledTimes(1));

    const call = postWorkoutSession.mock.calls[0][0];
    expect(call.exercise_id).toBe('pushups_level_1');
    expect(call.set_number).toBe(1);
  });

  it('shows rest timer after set completes', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    await waitFor(() => screen.getByRole('button', { name: /Konec série/ }));
    fireEvent.click(screen.getByRole('button', { name: /Konec série/ }));

    await waitFor(() => expect(screen.getByTestId('rest-timer')).toBeInTheDocument());
  });

  it('increments set number after skipping rest', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    await waitFor(() => screen.getByRole('button', { name: /Konec série/ }));
    fireEvent.click(screen.getByRole('button', { name: /Konec série/ }));

    await waitFor(() => screen.getByTestId('rest-timer'));
    fireEvent.click(screen.getByRole('button', { name: /Přeskočit odpočinek/ }));

    await waitFor(() => expect(screen.getByText('Série 2')).toBeInTheDocument());
  });

  it('registers counted reps from transcript', async () => {
    const { rerender } = renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    speechModule.__setMockState({ transcript: 'jedna dva tři' });

    rerender(
      <MemoryRouter initialEntries={['/exercises/pushups_level_1/workout']}>
        <Routes>
          <Route path="/exercises/:id" element={<div data-testid="detail-marker" />} />
          <Route path="/exercises/:id/workout" element={<WorkoutSession />} />
        </Routes>
      </MemoryRouter>,
    );

    // 3 distinct numbers → count should be 3
    await waitFor(() => {
      const opStats = screen.getAllByText(/^3$/);
      expect(opStats.length).toBeGreaterThan(0);
    });
  });

  it('shows unsupported browser alert', async () => {
    speechModule.__setMockState({ browserSupportsSpeechRecognition: false });
    renderWithRouter();

    await screen.findByText('Kliky o zeď');
    expect(screen.getByText(/nepodporuje rozpoznávání řeči/i)).toBeInTheDocument();
  });

  it('shows error message when detail fails to load', async () => {
    getExerciseDetail.mockRejectedValue({ response: { status: 404 } });
    renderWithRouter();

    expect(await screen.findByText('Cvik nebyl nalezen.')).toBeInTheDocument();
  });

  it('shows muscle map card', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    expect(screen.getByTestId('exercise-muscle-map')).toBeInTheDocument();
  });

  it('shows cadence info card', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    expect(screen.getByText('Tempo')).toBeInTheDocument();
    expect(screen.getByText('6 s / opakování')).toBeInTheDocument();
  });

  it('navigates back to exercise detail on back button', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Zpět na cvik/ }));

    expect(await screen.findByTestId('detail-marker')).toBeInTheDocument();
  });

  it('navigates back to exercise detail on "Ukončit trénink"', async () => {
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Ukončit trénink/ }));

    expect(await screen.findByTestId('detail-marker')).toBeInTheDocument();
  });

  it('shows save error when postWorkoutSession fails', async () => {
    postWorkoutSession.mockRejectedValue(new Error('Network error'));
    renderWithRouter();
    await screen.findByText('Kliky o zeď');

    fireEvent.click(screen.getByRole('button', { name: /Start série/ }));
    await waitFor(() => screen.getByRole('button', { name: /Konec série/ }));
    fireEvent.click(screen.getByRole('button', { name: /Konec série/ }));

    await waitFor(() =>
      expect(screen.getByText(/Sérii se nepodařilo uložit/i)).toBeInTheDocument(),
    );
  });
});
