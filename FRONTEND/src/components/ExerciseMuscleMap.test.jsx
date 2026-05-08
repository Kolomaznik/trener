import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import ExerciseMuscleMap from './ExerciseMuscleMap.jsx';

describe('ExerciseMuscleMap', () => {
  // ── Container + scale visibility ─────────────────────────────────────────────

  it('renders the SVG container and scale by default', () => {
    render(<ExerciseMuscleMap engagement={{ chest: 30 }} />);

    expect(screen.getByTestId('exercise-muscle-map')).toBeInTheDocument();
    expect(screen.getByTestId('muscle-map-scale')).toBeInTheDocument();
  });

  it('hides the scale when showScale={false}', () => {
    render(<ExerciseMuscleMap engagement={{ chest: 30 }} showScale={false} />);

    expect(screen.getByTestId('exercise-muscle-map')).toBeInTheDocument();
    expect(screen.queryByTestId('muscle-map-scale')).not.toBeInTheDocument();
  });

  // ── Scale: percent mode (default) ────────────────────────────────────────────

  it('shows percent-mode title and four stops by default', () => {
    render(<ExerciseMuscleMap engagement={{ chest: 30 }} />);

    const scale = screen.getByTestId('muscle-map-scale');
    expect(scale).toHaveTextContent('Zapojení');
    expect(scale).toHaveTextContent('50 %+');
    expect(scale).toHaveTextContent('25 %');
    expect(scale).toHaveTextContent('10 %');
    expect(scale).toHaveTextContent('< 10 %');
    expect(scale.querySelectorAll('span')).toHaveLength(4);
  });

  // ── Scale: load mode ─────────────────────────────────────────────────────────

  it('shows load-mode title and five tonne-formatted stops with a loadRange', () => {
    render(
      <ExerciseMuscleMap
        engagement={{ chest: 30 }}
        mode="load"
        loadRange={{ min: 100, max: 4000 }}
      />,
    );

    const scale = screen.getByTestId('muscle-map-scale');
    expect(scale).toHaveTextContent('Přemístěná zátěž');

    const swatches = scale.querySelectorAll('span');
    expect(swatches).toHaveLength(5);
    // Top stop = max (4 t), bottom stop = min (0.1 t).
    expect(swatches[0].textContent).toBe('4.00 t');
    expect(swatches[4].textContent).toBe('0.10 t');
  });

  it('renders no swatches in load mode when loadRange is missing', () => {
    render(<ExerciseMuscleMap engagement={{ chest: 30 }} mode="load" />);

    const scale = screen.getByTestId('muscle-map-scale');
    expect(scale).toHaveTextContent('Přemístěná zátěž');
    expect(scale.querySelectorAll('span')).toHaveLength(0);
  });

  it('renders no swatches in load mode when loadRange.max is zero', () => {
    render(
      <ExerciseMuscleMap
        engagement={{ chest: 30 }}
        mode="load"
        loadRange={{ min: 0, max: 0 }}
      />,
    );

    const scale = screen.getByTestId('muscle-map-scale');
    expect(scale.querySelectorAll('span')).toHaveLength(0);
  });

  // ── Per-muscle CSS rules ─────────────────────────────────────────────────────

  it('emits a CSS rule for each engaged muscle', () => {
    const { container } = render(
      <ExerciseMuscleMap engagement={{ chest: 30, biceps: 20 }} />,
    );

    const cssText = container.querySelector('style').textContent;
    expect(cssText).toMatch(/\[data-slug="chest"\]/);
    expect(cssText).toMatch(/\[data-slug="biceps"\]/);
  });

  it('skips muscles with engagement <= 0', () => {
    const { container } = render(
      <ExerciseMuscleMap engagement={{ chest: 0, biceps: -5, triceps: 10 }} />,
    );

    const cssText = container.querySelector('style').textContent;
    expect(cssText).not.toMatch(/\[data-slug="chest"\]/);
    expect(cssText).not.toMatch(/\[data-slug="biceps"\]/);
    expect(cssText).toMatch(/\[data-slug="triceps"\]/);
  });

  it('aliases compound engagement keys to canonical SVG slugs', () => {
    const { container } = render(
      <ExerciseMuscleMap
        engagement={{ lats: 30, glutes: 25, forearms: 10, hamstrings: 40 }}
      />,
    );

    const cssText = container.querySelector('style').textContent;
    expect(cssText).toMatch(/\[data-slug="upper-back"\]/); // lats
    expect(cssText).toMatch(/\[data-slug="gluteal"\]/); // glutes
    expect(cssText).toMatch(/\[data-slug="forearm"\]/); // forearms
    expect(cssText).toMatch(/\[data-slug="hamstring"\]/); // hamstrings
  });

  it('falls back to underscore-to-dash for unknown engagement keys', () => {
    const { container } = render(
      <ExerciseMuscleMap engagement={{ rotator_cuff: 30 }} />,
    );

    const cssText = container.querySelector('style').textContent;
    expect(cssText).toMatch(/\[data-slug="rotator-cuff"\]/);
  });

  // ── Mode-driven colour ───────────────────────────────────────────────────────

  it('uses the blue ramp in percent mode and the red ramp in load mode', () => {
    const { container, rerender } = render(
      <ExerciseMuscleMap engagement={{ chest: 30 }} />,
    );
    expect(container.querySelector('style').textContent).toMatch(/#1565c0/);

    rerender(
      <ExerciseMuscleMap
        engagement={{ chest: 30 }}
        mode="load"
        loadRange={{ min: 100, max: 4000 }}
      />,
    );
    expect(container.querySelector('style').textContent).toMatch(/#c62828/);
  });

  it('honours an explicit color prop, overriding the mode default', () => {
    const { container } = render(
      <ExerciseMuscleMap engagement={{ chest: 30 }} color="#abcdef" />,
    );

    const cssText = container.querySelector('style').textContent;
    expect(cssText).toMatch(/#abcdef/);
    expect(cssText).not.toMatch(/#1565c0/);
  });
});
