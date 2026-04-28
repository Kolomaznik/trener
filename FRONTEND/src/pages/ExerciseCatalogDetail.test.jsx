import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import ExerciseCatalogDetail from './ExerciseCatalogDetail.jsx';

vi.mock('../api/client.js', () => ({
  fetchExerciseDetail: vi.fn(),
}));

import { fetchExerciseDetail } from '../api/client.js';

function renderPage(path = '/exercise-catalog/drepy-u1-drep-1') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/exercise-catalog/:slug" element={<ExerciseCatalogDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ExerciseCatalogDetail', () => {
  it('renders detail', async () => {
    fetchExerciseDetail.mockResolvedValue({
      slug: 'drepy-u1-drep-1',
      name: 'Dřep 1',
      description: 'Detailní popis',
      muscle_load: [{ name: 'Hýždě', intensity: 4 }],
      performance_criteria: { zacatecnik: '1x10' },
      timing: { raw: 'Tempo 2-1-2-1' },
      steps: ['Krok 1', 'Krok 2'],
      media: { video_url: 'https://example.com/video' },
      progression: { previous_slug: null, next_slug: 'drepy-u2-drep-2', unlock_condition: null },
      metadata: { category: 'drepy', level: 1, source_book: 'Test', order: 1, is_active: true },
    });

    renderPage();

    await waitFor(() => expect(screen.getByText('Dřep 1')).toBeInTheDocument());
    expect(screen.getByText(/Detailní popis/i)).toBeInTheDocument();
    expect(screen.getByText(/Tempo 2-1-2-1/i)).toBeInTheDocument();
  });

  it('renders not found state', async () => {
    fetchExerciseDetail.mockRejectedValue({ response: { status: 404 } });

    renderPage('/exercise-catalog/unknown');

    await waitFor(() => expect(screen.getByText(/Cvik nebyl nalezen/i)).toBeInTheDocument());
  });

  it('renders error state', async () => {
    fetchExerciseDetail.mockRejectedValue(new Error('boom'));

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Nepodařilo se načíst detail cviku/i)).toBeInTheDocument(),
    );
  });
});
