import { useCallback, useId, useMemo, useState } from 'react';
import { Button, Card, Col, Row, Select, Slider, Space, Tag, Tooltip, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import maleSvgRaw from '../assets/muscle-map-male.svg?raw';
import femaleSvgRaw from '../assets/muscle-map-female.svg?raw';

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

const MUSCLE_GROUPS = [
  { id: 'chest', label: 'Prsní svaly', slugs: ['chest'] },
  { id: 'deltoids', label: 'Ramena (deltoid)', slugs: ['deltoids'] },
  { id: 'biceps', label: 'Biceps', slugs: ['biceps'] },
  { id: 'triceps', label: 'Triceps', slugs: ['triceps'] },
  { id: 'forearms', label: 'Předloktí', slugs: ['forearm'] },
  { id: 'abs', label: 'Břišní svaly', slugs: ['abs'] },
  { id: 'obliques', label: 'Šikmé svaly', slugs: ['obliques'] },
  { id: 'trapezius', label: 'Trapézový sval', slugs: ['trapezius'] },
  { id: 'lats', label: 'Široký sval zádový', slugs: ['upper-back'] },
  { id: 'lower_back', label: 'Dolní záda', slugs: ['lower-back'] },
  { id: 'quadriceps', label: 'Stehenní svaly', slugs: ['quadriceps'] },
  { id: 'hamstrings', label: 'Zadní svaly stehna', slugs: ['hamstring'] },
  { id: 'glutes', label: 'Hýžďové svaly', slugs: ['gluteal'] },
  { id: 'calves', label: 'Lýtkové svaly', slugs: ['calves'] },
  { id: 'adductors', label: 'Adduktory', slugs: ['adductors'] },
  { id: 'tibialis', label: 'Holenní sval', slugs: ['tibialis'] },
  { id: 'neck', label: 'Krk', slugs: ['neck'] },
  { id: 'knees', label: 'Kolena', slugs: ['knees'] },
  { id: 'hands', label: 'Ruce', slugs: ['hands'] },
  { id: 'ankles', label: 'Kotníky', slugs: ['ankles'] },
  { id: 'feet', label: 'Chodidla', slugs: ['feet'] },
];

const MUSCLE_BY_SLUG = (() => {
  const map = {};
  for (const group of MUSCLE_GROUPS) {
    for (const slug of group.slugs) {
      map[slug] = group.id;
    }
  }
  return map;
})();

const HIGHLIGHTABLE_SLUGS = Object.keys(MUSCLE_BY_SLUG);

const initMuscleData = () =>
  Object.fromEntries(
    MUSCLE_GROUPS.map((g) => [g.id, { color: randomColor(), intensity: randomIntensity() }]),
  );

function extractAvailableSlugs(svgRaw) {
  if (typeof DOMParser === 'undefined') return new Set();
  const doc = new DOMParser().parseFromString(svgRaw, 'image/svg+xml');
  const slugs = new Set();
  doc.querySelectorAll('g[data-slug]').forEach((el) => {
    const slug = el.getAttribute('data-slug');
    if (slug) slugs.add(slug);
  });
  return slugs;
}

const MALE_AVAILABLE = extractAvailableSlugs(maleSvgRaw);
const FEMALE_AVAILABLE = extractAvailableSlugs(femaleSvgRaw);

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function BodyHighlighter({ gender: controlledGender }) {
  const reactId = useId().replace(/:/g, '');
  const scopeId = `body-highlighter-${reactId}`;
  const [internalGender, setInternalGender] = useState('male');
  const isControlled = controlledGender === 'male' || controlledGender === 'female';
  const gender = isControlled ? controlledGender : internalGender;
  const setGender = isControlled ? () => {} : setInternalGender;
  const [muscleData, setMuscleData] = useState(initMuscleData);
  const [selected, setSelected] = useState(MUSCLE_GROUPS[0].id);
  const [hoveredGroupId, setHoveredGroupId] = useState(null);

  const svgRaw = gender === 'female' ? femaleSvgRaw : maleSvgRaw;
  const availableSlugs = gender === 'female' ? FEMALE_AVAILABLE : MALE_AVAILABLE;

  const visibleGroups = useMemo(
    () => MUSCLE_GROUPS.filter((g) => g.slugs.some((slug) => availableSlugs.has(slug))),
    [availableSlugs],
  );

  const handleRandomize = useCallback(() => setMuscleData(initMuscleData()), []);

  const updateSelected = (field, value) =>
    setMuscleData((prev) => ({ ...prev, [selected]: { ...prev[selected], [field]: value } }));

  const selectedData = muscleData[selected] || { color: COLORS[0].value, intensity: 1 };
  const selectedMeta = MUSCLE_GROUPS.find((g) => g.id === selected);
  const hoveredMeta = MUSCLE_GROUPS.find((g) => g.id === hoveredGroupId);

  const cssRules = useMemo(() => {
    const lines = [
      `#${scopeId} svg { width: 100%; height: auto; display: block; }`,
    ];
    // Make all highlightable muscles clickable.
    for (const slug of HIGHLIGHTABLE_SLUGS) {
      lines.push(
        `#${scopeId} [data-slug="${slug}"] { cursor: pointer; }`,
      );
    }
    // Apply color + intensity per group.
    for (const group of MUSCLE_GROUPS) {
      const data = muscleData[group.id];
      if (!data || data.intensity === 0) continue;
      const opacity = intensityToOpacity(data.intensity);
      for (const slug of group.slugs) {
        lines.push(
          `#${scopeId} [data-slug="${slug}"] path { ` +
            `fill: ${data.color} !important; ` +
            `fill-opacity: ${opacity} !important; ` +
            `transition: fill-opacity 0.25s; }`,
        );
      }
    }
    // Selection ring (dashed white outline).
    if (selectedMeta) {
      for (const slug of selectedMeta.slugs) {
        lines.push(
          `#${scopeId} [data-slug="${slug}"] path { ` +
            `stroke: #ffffff !important; stroke-width: 0.6 !important; ` +
            `stroke-dasharray: 1.4 0.7 !important; }`,
        );
      }
    }
    return lines.join('\n');
  }, [muscleData, scopeId, selectedMeta]);

  const findSlug = (target) => {
    if (!target?.closest) return null;
    const groupEl = target.closest('[data-slug]');
    if (!groupEl) return null;
    return groupEl.getAttribute('data-slug');
  };

  const handleClick = (event) => {
    const slug = findSlug(event.target);
    const muscleId = slug ? MUSCLE_BY_SLUG[slug] : null;
    if (muscleId) setSelected(muscleId);
  };

  const handleMouseOver = (event) => {
    const slug = findSlug(event.target);
    const muscleId = slug ? MUSCLE_BY_SLUG[slug] : null;
    setHoveredGroupId(muscleId ?? null);
  };

  const handleMouseOut = (event) => {
    // Only clear if mouse left the SVG entirely (relatedTarget is outside).
    const next = event.relatedTarget;
    if (next && next.closest && next.closest('[data-slug]')) return;
    setHoveredGroupId(null);
  };

  return (
    <Row gutter={[24, 24]} align="top">
      {/* ------------------------------------------------------------------ */}
      {/* SVG body panel                                                       */}
      {/* ------------------------------------------------------------------ */}
      <Col xs={24} sm={12} style={{ display: 'flex', justifyContent: 'center' }}>
        <Card
          size="small"
          style={{ width: '100%', maxWidth: 420 }}
          styles={{
            body: {
              padding: 12,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 12,
            },
          }}
        >
          {!isControlled && (
            <Space>
              <Button
                type={gender === 'male' ? 'primary' : 'default'}
                size="small"
                onClick={() => setGender('male')}
              >
                Muž
              </Button>
              <Button
                type={gender === 'female' ? 'primary' : 'default'}
                size="small"
                onClick={() => setGender('female')}
              >
                Žena
              </Button>
            </Space>
          )}

          <div
            id={scopeId}
            data-testid="body-highlighter-svg"
            style={{ width: '100%' }}
            onClick={handleClick}
            onMouseOver={handleMouseOver}
            onMouseOut={handleMouseOut}
          >
            <style>{cssRules}</style>
            <div dangerouslySetInnerHTML={{ __html: svgRaw }} />
          </div>

          <Text type="secondary" style={{ textAlign: 'center' }}>
            {hoveredMeta
              ? `Nadjeto: ${hoveredMeta.label}`
              : 'Najeď nebo klikni na svalovou partii v mapě.'}
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
              options={visibleGroups.map((g) => ({ value: g.id, label: g.label }))}
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
                          if (e.key === 'Enter' || e.key === ' ')
                            updateSelected('color', c.value);
                        }}
                        style={{
                          width: 28,
                          height: 28,
                          borderRadius: 6,
                          backgroundColor: c.value,
                          cursor: 'pointer',
                          border:
                            selectedData.color === c.value
                              ? '3px solid #333'
                              : '2px solid transparent',
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
