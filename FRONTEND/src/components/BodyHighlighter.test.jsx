import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import BodyHighlighter from './BodyHighlighter.jsx';

describe('BodyHighlighter — gender prop', () => {
  it('renders the male/female toggle when no gender prop is given (uncontrolled)', () => {
    render(<BodyHighlighter />);
    expect(screen.getByRole('button', { name: /muž/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /žena/i })).toBeInTheDocument();
  });

  it('hides the gender toggle when controlled with gender="male"', () => {
    render(<BodyHighlighter gender="male" />);
    expect(screen.queryByRole('button', { name: /muž/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /žena/i })).not.toBeInTheDocument();
  });

  it('hides the gender toggle when controlled with gender="female"', () => {
    render(<BodyHighlighter gender="female" />);
    expect(screen.queryByRole('button', { name: /muž/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /žena/i })).not.toBeInTheDocument();
  });

  it('falls back to uncontrolled when prop value is invalid', () => {
    render(<BodyHighlighter gender="invalid" />);
    expect(screen.getByRole('button', { name: /muž/i })).toBeInTheDocument();
  });

  it('renders a different SVG for male vs female', () => {
    const { container: maleContainer, unmount } = render(<BodyHighlighter gender="male" />);
    const maleSvg = maleContainer.querySelector('[data-testid="body-highlighter-svg"] svg');
    const maleViewBox = maleSvg?.getAttribute('viewBox');
    unmount();

    const { container: femaleContainer } = render(<BodyHighlighter gender="female" />);
    const femaleSvg = femaleContainer.querySelector('[data-testid="body-highlighter-svg"] svg');
    const femaleViewBox = femaleSvg?.getAttribute('viewBox');

    expect(maleViewBox).toBeTruthy();
    expect(femaleViewBox).toBeTruthy();
    expect(maleViewBox).not.toEqual(femaleViewBox);
  });
});
