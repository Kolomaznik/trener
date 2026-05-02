import { useCallback, useId, useMemo, useState } from 'react';
import { Button, Card, Col, Row, Select, Slider, Space, Tag, Tooltip, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import frontSvgRaw from '../assets/muscle-map-front.svg?raw';
import backSvgRaw from '../assets/muscle-map-back.svg?raw';
import femaleFrontSvgRaw from '../assets/muscle-map-female-front.svg?raw';
import femaleBackSvgRaw from '../assets/muscle-map-female-back.svg?raw';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COLORS = [
  { value: '#e63946', label: 'Červená' },
  { value: '#f4a261', label: 'Oranžová' },
  { value: '#e9c46a', label: 'Žlutá' },
  { value: '#2a9d8f', label: 'Zelená' },
  { value: '#457b9d', label: 'Modrá' },
  { value: '#6a4c93', label: 'Fialová' },
];

const INTENSITY_MARKS = { 0: 'Žádná', 1: 'Lehká', 2: 'Střední', 3: 'Vysoká' };
const intensityToOpacity = (i) => [0, 0.3, 0.62, 0.9][i];

const randomColor = () => COLORS[Math.floor(Math.random() * COLORS.length)].value;
const randomIntensity = () => Math.ceil(Math.random() * 3); // 1–3

function parseBodySvg(svgRaw, fallbackViewBox) {
  if (typeof DOMParser === 'undefined') {
    return { viewBox: fallbackViewBox, pathsBySlug: {} };
  }

  const doc = new DOMParser().parseFromString(svgRaw, 'image/svg+xml');
  const svgEl = doc.querySelector('svg');
  if (!svgEl) {
    return { viewBox: fallbackViewBox, pathsBySlug: {} };
  }

  const pathsBySlug = {};
  doc.querySelectorAll('g[data-slug]').forEach((groupEl) => {
    const slug = groupEl.getAttribute('data-slug');
    if (!slug) return;
    pathsBySlug[slug] = Array.from(groupEl.querySelectorAll('path'))
      .map((pathEl) => pathEl.getAttribute('d'))
      .filter(Boolean);
  });

  return {
    viewBox: svgEl.getAttribute('viewBox') || fallbackViewBox,
    pathsBySlug,
  };
}

const FRONT_SVG = parseBodySvg(frontSvgRaw, '0 0 724 1448');
const BACK_SVG = parseBodySvg(backSvgRaw, '724 0 724 1448');
const FEMALE_FRONT_SVG = parseBodySvg(femaleFrontSvgRaw, '-50 -40 734 1538');
const FEMALE_BACK_SVG = parseBodySvg(femaleBackSvgRaw, '756 0 774 1448');

const MUSCLE_GROUPS = [
  { id: 'chest', label: 'Prsní svaly', slugs: { front: ['chest'] } },
  { id: 'deltoids', label: 'Ramena (deltoid)', slugs: { front: ['deltoids'], back: ['deltoids'] } },
  { id: 'biceps', label: 'Biceps', slugs: { front: ['biceps'] } },
  { id: 'triceps', label: 'Triceps', slugs: { front: ['triceps'], back: ['triceps'] } },
  { id: 'forearms', label: 'Předloktí', slugs: { front: ['forearm'], back: ['forearm'] } },
  { id: 'abs', label: 'Břišní svaly', slugs: { front: ['abs'] } },
  { id: 'obliques', label: 'Šikmé svaly', slugs: { front: ['obliques'] } },
  { id: 'trapezius', label: 'Trapézový sval', slugs: { front: ['trapezius'], back: ['trapezius'] } },
  { id: 'lats', label: 'Široký sval zádový', slugs: { back: ['upper-back'] } },
  { id: 'lower_back', label: 'Dolní záda', slugs: { back: ['lower-back'] } },
  { id: 'quadriceps', label: 'Stehenní svaly', slugs: { front: ['quadriceps'] } },
  { id: 'hamstrings', label: 'Zadní svaly stehna', slugs: { back: ['hamstring'] } },
  { id: 'glutes', label: 'Hýžďové svaly', slugs: { back: ['gluteal'] } },
  { id: 'calves', label: 'Lýtkové svaly', slugs: { front: ['calves'], back: ['calves'] } },
  { id: 'adductors', label: 'Adduktory', slugs: { front: ['adductors'], back: ['adductors'] } },
  { id: 'tibialis', label: 'Holenní sval', slugs: { front: ['tibialis'] } },
  { id: 'neck', label: 'Krk', slugs: { front: ['neck'], back: ['neck'] } },
  { id: 'knees', label: 'Kolena', slugs: { front: ['knees'] } },
  { id: 'hands', label: 'Ruce', slugs: { front: ['hands'], back: ['hands'] } },
  { id: 'ankles', label: 'Kotníky', slugs: { front: ['ankles'], back: ['ankles'] } },
  { id: 'feet', label: 'Chodidla', slugs: { front: ['feet'], back: ['feet'] } },
];

const initMuscleData = () =>
  Object.fromEntries(MUSCLE_GROUPS.map((g) => [g.id, { color: randomColor(), intensity: randomIntensity() }]));

const getGroupPaths = (group, view, pathsBySlug) => {
  const slugs = group.slugs[view] || [];
  return slugs.flatMap((slug) => pathsBySlug[slug] || []);
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function BodyHighlighter({ gender: controlledGender }) {
  const svgId = useId().replace(/:/g, '');
  const [internalGender, setInternalGender] = useState('male');
  const isControlled = controlledGender === 'male' || controlledGender === 'female';
  const gender = isControlled ? controlledGender : internalGender;
  const setGender = isControlled ? () => {} : setInternalGender;
  const [muscleData, setMuscleData] = useState(initMuscleData);
  const [selected, setSelected] = useState(MUSCLE_GROUPS[0].id);
  const [hoveredGroupId, setHoveredGroupId] = useState(null);

  const frontSvgData = gender === 'female' ? FEMALE_FRONT_SVG : FRONT_SVG;
  const backSvgData = gender === 'female' ? FEMALE_BACK_SVG : BACK_SVG;
  const frontPathsBySlug = frontSvgData.pathsBySlug;
  const backPathsBySlug = backSvgData.pathsBySlug;

  const handleRandomize = useCallback(() => setMuscleData(initMuscleData()), []);

  const updateSelected = (field, value) =>
    setMuscleData((prev) => ({ ...prev, [selected]: { ...prev[selected], [field]: value } }));

  const selectedData = muscleData[selected] || { color: COLORS[0].value, intensity: 1 };
  const selectedMeta = MUSCLE_GROUPS.find((g) => g.id === selected);
  const hoveredMeta = MUSCLE_GROUPS.find((g) => g.id === hoveredGroupId);

  const visibleGroups = useMemo(
    () =>
      MUSCLE_GROUPS.filter(
        (g) => getGroupPaths(g, 'front', frontPathsBySlug).length > 0 || getGroupPaths(g, 'back', backPathsBySlug).length > 0,
      ),
    [frontPathsBySlug, backPathsBySlug],
  );

  const renderBodyFigure = (side, svgData, pathsBySlug) => {
    const backgroundPaths = Object.values(pathsBySlug).flatMap((paths) => paths);
    const gradientId = `bodyGrad-${svgId}-${side}`;
    const shadowId = `bodyShadow-${svgId}-${side}`;

    return (
      <div style={{ width: '48%' }}>
        <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 6 }}>
          {side === 'front' ? 'Přední' : 'Zadní'} pohled
        </Text>
        <svg
          viewBox={svgData.viewBox}
          width="100%"
          style={{ userSelect: 'none' }}
          aria-label={`Lidská postava, ${side === 'front' ? 'přední' : 'zadní'} pohled`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f4f5f6" />
              <stop offset="100%" stopColor="#d8dadd" />
            </linearGradient>
            <filter id={shadowId} x="-12%" y="-12%" width="124%" height="124%">
              <feDropShadow dx="0" dy="1.5" stdDeviation="1.2" floodColor="#5b5e66" floodOpacity="0.25" />
            </filter>
          </defs>

          <g>
            {backgroundPaths.map((d, i) => (
              <path
                key={`bg-${side}-${i}`}
                d={d}
                fill={`url(#${gradientId})`}
                fillOpacity={0.52}
                stroke="#7f8791"
                strokeWidth={0.45}
                filter={`url(#${shadowId})`}
                style={{ pointerEvents: 'none' }}
              />
            ))}
          </g>

          {visibleGroups.map((group) => {
            const groupPaths = getGroupPaths(group, side, pathsBySlug);
            const data = muscleData[group.id];
            if (!data || data.intensity === 0 || groupPaths.length === 0) return null;
            const opacity = intensityToOpacity(data.intensity);
            const isSelected = group.id === selected;

            return (
              <g key={`${side}-${group.id}`}>
                {groupPaths.map((d, i) => (
                  <path
                    key={i}
                    d={d}
                    fill={data.color}
                    fillOpacity={opacity}
                    stroke={isSelected ? '#ffffff' : 'none'}
                    strokeWidth={isSelected ? 1.8 : 0}
                    style={{ cursor: 'pointer', transition: 'fill-opacity 0.25s' }}
                    onClick={() => setSelected(group.id)}
                    onMouseEnter={() => setHoveredGroupId(group.id)}
                    onMouseLeave={() => setHoveredGroupId(null)}
                  />
                ))}
                {isSelected &&
                  groupPaths.map((d, i) => (
                    <path
                      key={`ring-${i}`}
                      d={d}
                      fill="none"
                      stroke="#ffffff"
                      strokeWidth={1.7}
                      strokeDasharray="4 2"
                      style={{ pointerEvents: 'none' }}
                    />
                  ))}
              </g>
            );
          })}

          {visibleGroups.map((group) => {
            const groupPaths = getGroupPaths(group, side, pathsBySlug);
            if (groupPaths.length === 0) return null;
            return (
              <g key={`title-${side}-${group.id}`} style={{ pointerEvents: 'none' }}>
                {groupPaths.map((d, i) => (
                  <path key={i} d={d} fill="transparent" stroke="none">
                    <title>{group.label}</title>
                  </path>
                ))}
              </g>
            );
          })}
        </svg>
      </div>
    );
  };

  return (
    <Row gutter={[24, 24]} align="top">
      {/* ------------------------------------------------------------------ */}
      {/* SVG body panel                                                       */}
      {/* ------------------------------------------------------------------ */}
      <Col xs={24} sm={12} style={{ display: 'flex', justifyContent: 'center' }}>
        <Card
          size="small"
          style={{ width: '100%', maxWidth: 340 }}
          styles={{ body: { padding: 12, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 } }}
        >
          {!isControlled && (
            <Space>
              <Button type={gender === 'male' ? 'primary' : 'default'} size="small" onClick={() => setGender('male')}>
                Muž
              </Button>
              <Button type={gender === 'female' ? 'primary' : 'default'} size="small" onClick={() => setGender('female')}>
                Žena
              </Button>
            </Space>
          )}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', alignItems: 'flex-start', width: '100%' }}>
            {renderBodyFigure('front', frontSvgData, frontPathsBySlug)}
            {renderBodyFigure('back', backSvgData, backPathsBySlug)}
          </div>

          <Text type="secondary" style={{ textAlign: 'center' }}>
            {hoveredMeta ? `Nadjeto: ${hoveredMeta.label}` : 'Najeď nebo klikni na svalovou partii v mapě.'}
          </Text>
        </Card>
      </Col>

      {/* ------------------------------------------------------------------ */}
      {/* Controls panel                                                       */}
      {/* ------------------------------------------------------------------ */}
      <Col xs={24} sm={12}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Button icon={<ReloadOutlined />} onClick={handleRandomize} block>
            Náhodné barvy a intenzity
          </Button>

          <Card size="small" title="Vyberte svalovou partii">
            <Select
              value={selected}
              onChange={setSelected}
              style={{ width: '100%' }}
              options={MUSCLE_GROUPS.map((g) => ({ value: g.id, label: g.label }))}
            />
          </Card>

          {selectedMeta && (
            <Card
              size="small"
              title={
                <Space>
                  <span
                    style={{
                      display: 'inline-block',
                      width: 14,
                      height: 14,
                      borderRadius: 3,
                      backgroundColor: selectedData.color,
                      border: '1px solid #ccc',
                      flexShrink: 0,
                    }}
                  />
                  {selectedMeta.label}
                </Space>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                <Text type="secondary">Barva</Text>
                <Space wrap>
                  {COLORS.map((c) => (
                    <Tooltip key={c.value} title={c.label}>
                      <div
                        role="button"
                        aria-label={c.label}
                        tabIndex={0}
                        onClick={() => updateSelected('color', c.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') updateSelected('color', c.value);
                        }}
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 6,
                          backgroundColor: c.value,
                          cursor: 'pointer',
                          border: selectedData.color === c.value ? '3px solid #333' : '2px solid transparent',
                          outline: selectedData.color === c.value ? '2px solid #fff' : 'none',
                          outlineOffset: '-4px',
                          transition: 'border 0.15s',
                        }}
                      />
                    </Tooltip>
                  ))}
                </Space>

                <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
                  Intenzita
                </Text>
                <Slider
                  min={0}
                  max={3}
                  step={1}
                  value={selectedData.intensity}
                  marks={INTENSITY_MARKS}
                  onChange={(v) => updateSelected('intensity', v)}
                  style={{ marginBottom: 24 }}
                />
              </Space>
            </Card>
          )}

          <Card size="small" title="Legenda" styles={{ body: { padding: '8px 12px' } }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {visibleGroups.map((g) => {
                const d = muscleData[g.id];
                return (
                  <Tag
                    key={g.id}
                    color={d.intensity > 0 ? d.color : 'default'}
                    style={{ cursor: 'pointer', fontWeight: g.id === selected ? 700 : 400 }}
                    onClick={() => setSelected(g.id)}
                  >
                    {g.label}
                  </Tag>
                );
              })}
            </div>
          </Card>
        </Space>
      </Col>
    </Row>
  );
}
