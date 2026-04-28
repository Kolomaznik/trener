import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import ExerciseCatalogList from './ExerciseCatalogList.jsx';

vi.mock('../api/client.js', () => ({
  fetchExerciseCatalog: vi.fn(),
}));

import { fetchExerciseCatalog } from '../api/client.js';

function renderPage() {
  return render(
    <MemoryRouter>
      <ExerciseCatalogList />
    </MemoryRouter>,
  );
}

describe('ExerciseCatalogList', () => {
  it('renders loading and list items', async () => {
    fetchExerciseCatalog.mockResolvedValue({
      items: [
        {
          slug: 'drepy-u1-drep-1',
          name: 'Dřep 1',
          category: 'drepy',
          level: 1,
          short_description: 'Popis cviku',
          has_video: true,
          muscle_load: [{ name: 'Hýždě', intensity: 4 }],
        },
      ],
    });

    renderPage();

    expect(screen.getByText(/Načítám cviky/i)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Dřep 1')).toBeInTheDocument());
    expect(screen.getByText(/Kategorie: drepy/i)).toBeInTheDocument();
    expect(screen.getByText(/Úroveň: 1/i)).toBeInTheDocument();
  });

  it('renders empty state', async () => {
    fetchExerciseCatalog.mockResolvedValue({ items: [] });

    renderPage();

    await waitFor(() => expect(screen.getByText(/Katalog je zatím prázdný/i)).toBeInTheDocument());
  });

  it('renders error state', async () => {
    fetchExerciseCatalog.mockRejectedValue(new Error('boom'));

    renderPage();

    await waitFor(() =>
      expect(screen.getByText(/Nepodařilo se načíst katalog cviků/i)).toBeInTheDocument(),
    );
  });
});
