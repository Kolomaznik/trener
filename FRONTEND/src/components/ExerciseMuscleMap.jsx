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

const SCALE_STOPS = [
  { label: '50 %+', pct: 50 },
  { label: '25 %', pct: 25 },
  { label: '10 %', pct: 10 },
  { label: '< 10 %', pct: 1 },
];

function MuscleMapScale({ color }) {
  return (
    <div
      data-testid="muscle-map-scale"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        fontSize: 12,
        flexShrink: 0,
        lineHeight: 1.2,
      }}
    >
      <div style={{ fontWeight: 500, marginBottom: 2 }}>Zapojení</div>
      {SCALE_STOPS.map((stop) => (
        <div
          key={stop.label}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              background: color,
              opacity: intensityOpacity(stop.pct),
              borderRadius: 3,
            }}
          />
          <span style={{ color: 'rgba(0, 0, 0, 0.65)' }}>{stop.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function ExerciseMuscleMap({
  engagement = {},
  color = '#e63946',
  maxWidth = 420,
  showScale = true,
}) {
  const reactId = useId().replace(/:/g, '');
  const scopeId = `muscle-map-${reactId}`;

  const cssRules = useMemo(() => {
    const lines = [
      `#${scopeId} svg { width: 100%; height: auto; display: block; }`,
    ];
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

  const figure = (
    <div
      id={scopeId}
      data-testid="exercise-muscle-map"
      style={{
        flex: '1 1 auto',
        minWidth: 0,
        maxWidth: `min(100%, max(240px, min(${maxWidth}px, 60vh)))`,
      }}
    >
      <style>{cssRules}</style>
      <div dangerouslySetInnerHTML={{ __html: maleSvgRaw }} />
    </div>
  );

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
      }}
    >
      {figure}
      {showScale && <MuscleMapScale color={color} />}
    </div>
  );
}
