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

  it('renders different SVG viewBox for male vs female', () => {
    const { container: maleContainer, unmount } = render(<BodyHighlighter gender="male" />);
    const maleSvgs = Array.from(maleContainer.querySelectorAll('svg[viewBox]'))
      .map((el) => el.getAttribute('viewBox'))
      .filter((v) => v && !v.startsWith('64'));
    unmount();

    const { container: femaleContainer } = render(<BodyHighlighter gender="female" />);
    const femaleSvgs = Array.from(femaleContainer.querySelectorAll('svg[viewBox]'))
      .map((el) => el.getAttribute('viewBox'))
      .filter((v) => v && !v.startsWith('64'));

    expect(maleSvgs).not.toEqual(femaleSvgs);
    expect(maleSvgs.some((v) => v === '0 0 724 1448')).toBe(true);
    expect(femaleSvgs.some((v) => v === '-50 -40 734 1538')).toBe(true);
  });
});
