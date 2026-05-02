import { useId, useMemo } from 'react';
import maleSvgRaw from '../assets/muscle-map-male.svg?raw';

const ENGAGEMENT_TO_SLUGS = {
  chest: ['chest'],
  triceps: ['triceps'],
  biceps: ['biceps'],
  deltoids: ['deltoids'],
  trapezius: ['trapezius'],
  forearms: ['forearm'],
  forearm: ['forearm'],
  abs: ['abs'],
  obliques: ['obliques'],
  lower_back: ['lower-back'],
  upper_back: ['upper-back'],
  lats: ['upper-back'],
  glutes: ['gluteal'],
  gluteal: ['gluteal'],
  quadriceps: ['quadriceps'],
  hamstrings: ['hamstring'],
  hamstring: ['hamstring'],
  calves: ['calves'],
  adductors: ['adductors'],
  hands: ['hands'],
  neck: ['neck'],
  knees: ['knees'],
  ankles: ['ankles'],
  feet: ['feet'],
};

function slugsFor(key) {
  return ENGAGEMENT_TO_SLUGS[key] ?? [key.replace(/_/g, '-')];
}

function intensityOpacity(pct) {
  if (pct <= 0) return 0;
  return Math.min(1, 0.35 + (pct / 50) * 0.65);
}

export default function ExerciseMuscleMap({
  engagement = {},
  color = '#e63946',
  maxWidth = 360,
}) {
  const reactId = useId().replace(/:/g, '');
  const scopeId = `muscle-map-${reactId}`;

  const cssRules = useMemo(() => {
    const lines = [];
    for (const [key, pct] of Object.entries(engagement)) {
      if (!pct || pct <= 0) continue;
      const opacity = intensityOpacity(pct);
      for (const slug of slugsFor(key)) {
        lines.push(
          `#${scopeId} [data-slug="${slug}"] path { fill: ${color} !important; ` +
            `fill-opacity: ${opacity.toFixed(3)} !important; }`,
        );
      }
    }
    return lines.join('\n');
  }, [engagement, color, scopeId]);

  return (
    <div
      id={scopeId}
      data-testid="exercise-muscle-map"
      style={{ width: '100%', maxWidth, margin: '0 auto' }}
    >
      {cssRules && <style>{cssRules}</style>}
      <div dangerouslySetInnerHTML={{ __html: maleSvgRaw }} />
    </div>
  );
}
