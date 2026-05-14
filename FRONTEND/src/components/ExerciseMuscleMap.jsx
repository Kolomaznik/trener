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

/** Colours for each mode — load: red, percent: blue, series_count: green. */
const MODE_COLOR = {
  load: '#c62828',
  percent: '#1565c0',
  series_count: '#2e7d32',
};

function intensityOpacity(pct) {
  if (pct <= 0) return 0;
  return Math.min(1, 0.35 + (pct / 50) * 0.65);
}

/** Blend hexColor with white at given alpha (0–1) to produce a solid RGB string. */
function blendWithWhite(hexColor, alpha) {
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  return (
    `rgb(${Math.round(r * alpha + 255 * (1 - alpha))},` +
    `${Math.round(g * alpha + 255 * (1 - alpha))},` +
    `${Math.round(b * alpha + 255 * (1 - alpha))})`
  );
}

const PERCENT_SCALE_STOPS = [
  { label: '50 %+', pct: 50 },
  { label: '25 %', pct: 25 },
  { label: '10 %', pct: 10 },
  { label: '< 10 %', pct: 1 },
];

function buildLoadStops(loadRange) {
  if (!loadRange || loadRange.max <= 0) return [];
  const { min, max } = loadRange;
  return Array.from({ length: 5 }, (_, i) => {
    const value = max - (i * (max - min)) / 4;
    return {
      pct: (value / max) * 100,
      label: (value / 1000).toFixed(2) + '\u202ft',
    };
  });
}

function buildSeriesCountStops(loadRange) {
  if (!loadRange || loadRange.max <= 0) return [];
  const { min, max } = loadRange;
  return Array.from({ length: 5 }, (_, i) => {
    const value = max - (i * (max - min)) / 4;
    return {
      pct: (value / max) * 100,
      label: `${Math.round(value)}×`,
    };
  });
}

const SCALE_TITLES = {
  load: 'Přemístěná zátěž',
  series_count: 'Počet sérií',
  percent: 'Zapojení',
};

function MuscleMapScale({ color, mode = 'percent', loadRange = null }) {
  let stops;
  if (mode === 'load') stops = buildLoadStops(loadRange);
  else if (mode === 'series_count') stops = buildSeriesCountStops(loadRange);
  else stops = PERCENT_SCALE_STOPS;
  const title = SCALE_TITLES[mode] ?? SCALE_TITLES.percent;
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
      <div style={{ fontWeight: 500, marginBottom: 2 }}>{title}</div>
      {stops.map((stop, i) => {
        // Spread alpha evenly from 1.0 (top/max) down to 0.18 (bottom/min)
        // so every swatch is visually distinct regardless of the pct values.
        const alpha = 1.0 - (i / Math.max(stops.length - 1, 1)) * 0.82;
        return (
        <div
          key={stop.label}
          style={{ display: 'flex', alignItems: 'center', gap: 6 }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              background: blendWithWhite(color, alpha),
              borderRadius: 3,
            }}
          />
          <span style={{ color: 'rgba(0, 0, 0, 0.65)' }}>{stop.label}</span>
        </div>
        );
      })}
    </div>
  );
}

export default function ExerciseMuscleMap({
  engagement = {},
  color = null,
  maxWidth = 420,
  showScale = true,
  mode = 'percent',
  loadRange = null,
}) {
  const effectiveColor = color ?? MODE_COLOR[mode] ?? '#c62828';
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
          `#${scopeId} [data-slug="${slug}"] path { fill: ${effectiveColor} !important; ` +
            `fill-opacity: ${opacity.toFixed(3)} !important; }`,
        );
      }
    }
    return lines.join('\n');
  }, [engagement, effectiveColor, scopeId]);

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
      {showScale && <MuscleMapScale color={effectiveColor} mode={mode} loadRange={loadRange} />}
    </div>
  );
}
