import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TreningVezne from './TreningVezne.jsx';

vi.mock('../api/trening-vezne/get.js', () => ({
  getTreningVezne: vi.fn(),
}));

import { getTreningVezne } from '../api/trening-vezne/get.js';

const FAMILIES = [
  { key: 'pushups', title: 'Kliky' },
  { key: 'squats', title: 'Dřepy' },
  { key: 'pullups', title: 'Shyby' },
  { key: 'legraises', title: 'Zdvihy nohou' },
  { key: 'bridges', title: 'Mosty' },
  { key: 'hspu', title: 'Kliky ve stojce' },
];
const LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

function emptyMatrix() {
  const cells = {};
  for (const family of FAMILIES) {
    cells[family.key] = {};
    for (const level of LEVELS) {
      cells[family.key][String(level)] = { stars: 0, achieved_at: null };
    }
  }
  return { families: FAMILIES, levels: LEVELS, cells };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <TreningVezne />
    </MemoryRouter>,
  );
}

describe('TreningVezne page', () => {
  beforeEach(() => {
    getTreningVezne.mockReset();
    getTreningVezne.mockResolvedValue(emptyMatrix());
  });

  it('renders all six family columns in the header', async () => {
    renderPage();
    await waitFor(() => expect(getTreningVezne).toHaveBeenCalledTimes(1));
    for (const family of FAMILIES) {
      expect(await screen.findByRole('columnheader', { name: family.title })).toBeInTheDocument();
    }
    expect(screen.getByRole('columnheader', { name: 'Level' })).toBeInTheDocument();
  });

  it('renders ten level rows', async () => {
    renderPage();
    await screen.findByRole('columnheader', { name: 'Kliky' });
    const rows = screen.getAllByRole('row');
    // 1 header row + 10 data rows
    expect(rows).toHaveLength(11);
  });

  it('renders no dates when nothing is achieved', async () => {
    renderPage();
    await screen.findByRole('columnheader', { name: 'Kliky' });
    // cs-CZ short date format is "D. M. YY" (with spaces); assert no such pattern renders.
    expect(screen.queryByText(/\d+\.\s*\d+\.\s*\d+/)).not.toBeInTheDocument();
  });

  it('renders achieved date below stars when cell has achieved_at', async () => {
    const matrix = emptyMatrix();
    matrix.cells.pushups['1'] = { stars: 2, achieved_at: '2026-05-01T10:00:00Z' };
    getTreningVezne.mockResolvedValue(matrix);

    renderPage();
    await screen.findByRole('columnheader', { name: 'Kliky' });
    expect(screen.getByText(/1\.\s*5\.\s*26/)).toBeInTheDocument();
  });

  it('shows error alert when the fetch fails', async () => {
    getTreningVezne.mockRejectedValue(new Error('boom'));
    renderPage();
    expect(
      await screen.findByText('Nepodařilo se načíst přehled tréninku.'),
    ).toBeInTheDocument();
  });
});
