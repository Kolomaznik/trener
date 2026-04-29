import { useCallback, useState } from 'react';
import { Button, Card, Col, Row, Select, Slider, Space, Tag, Tooltip, Typography } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';

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

// ---------------------------------------------------------------------------
// Muscle group meta-data
// ---------------------------------------------------------------------------

const MUSCLE_GROUPS = [
  { id: 'chest', label: 'Prsní svaly', view: 'front' },
  { id: 'deltoids', label: 'Ramena (deltoid)', view: 'both' },
  { id: 'biceps', label: 'Biceps', view: 'front' },
  { id: 'triceps', label: 'Triceps', view: 'back' },
  { id: 'forearms', label: 'Předloktí', view: 'both' },
  { id: 'abs', label: 'Břišní svaly', view: 'front' },
  { id: 'obliques', label: 'Šikmé svaly', view: 'front' },
  { id: 'trapezius', label: 'Trapézový sval', view: 'back' },
  { id: 'lats', label: 'Záda (latissimus)', view: 'back' },
  { id: 'lower_back', label: 'Dolní záda', view: 'back' },
  { id: 'quadriceps', label: 'Stehenní svaly', view: 'front' },
  { id: 'hamstrings', label: 'Zadní svaly stehna', view: 'back' },
  { id: 'glutes', label: 'Hýžďové svaly', view: 'back' },
  { id: 'calves', label: 'Lýtkové svaly', view: 'both' },
];

const initMuscleData = () =>
  Object.fromEntries(MUSCLE_GROUPS.map((g) => [g.id, { color: randomColor(), intensity: randomIntensity() }]));

// ---------------------------------------------------------------------------
// SVG shape data  (viewBox "0 0 120 303")
// ---------------------------------------------------------------------------

const FRONT_MUSCLES = {
  chest: [
    { type: 'ellipse', cx: 43, cy: 70, rx: 17, ry: 14 },
    { type: 'ellipse', cx: 77, cy: 70, rx: 17, ry: 14 },
  ],
  deltoids: [
    { type: 'ellipse', cx: 21, cy: 52, rx: 10, ry: 9 },
    { type: 'ellipse', cx: 99, cy: 52, rx: 10, ry: 9 },
  ],
  biceps: [
    { type: 'rect', x: 16, y: 68, width: 14, height: 46, rx: 6 },
    { type: 'rect', x: 90, y: 68, width: 14, height: 46, rx: 6 },
  ],
  forearms: [
    { type: 'rect', x: 14, y: 116, width: 12, height: 54, rx: 5 },
    { type: 'rect', x: 94, y: 116, width: 12, height: 54, rx: 5 },
  ],
  abs: [
    { type: 'ellipse', cx: 50, cy: 89, rx: 9, ry: 8 },
    { type: 'ellipse', cx: 70, cy: 89, rx: 9, ry: 8 },
    { type: 'ellipse', cx: 50, cy: 107, rx: 9, ry: 8 },
    { type: 'ellipse', cx: 70, cy: 107, rx: 9, ry: 8 },
    { type: 'ellipse', cx: 50, cy: 125, rx: 9, ry: 8 },
    { type: 'ellipse', cx: 70, cy: 125, rx: 9, ry: 8 },
  ],
  obliques: [
    { type: 'ellipse', cx: 36, cy: 108, rx: 9, ry: 25 },
    { type: 'ellipse', cx: 84, cy: 108, rx: 9, ry: 25 },
  ],
  quadriceps: [
    { type: 'rect', x: 32, y: 155, width: 25, height: 62, rx: 9 },
    { type: 'rect', x: 63, y: 155, width: 25, height: 62, rx: 9 },
  ],
  calves: [
    { type: 'ellipse', cx: 44, cy: 250, rx: 12, ry: 24 },
    { type: 'ellipse', cx: 76, cy: 250, rx: 12, ry: 24 },
  ],
};

const BACK_MUSCLES = {
  deltoids: [
    { type: 'ellipse', cx: 21, cy: 52, rx: 10, ry: 9 },
    { type: 'ellipse', cx: 99, cy: 52, rx: 10, ry: 9 },
  ],
  triceps: [
    { type: 'rect', x: 16, y: 68, width: 14, height: 46, rx: 6 },
    { type: 'rect', x: 90, y: 68, width: 14, height: 46, rx: 6 },
  ],
  forearms: [
    { type: 'rect', x: 14, y: 116, width: 12, height: 54, rx: 5 },
    { type: 'rect', x: 94, y: 116, width: 12, height: 54, rx: 5 },
  ],
  trapezius: [{ type: 'ellipse', cx: 60, cy: 60, rx: 30, ry: 18 }],
  lats: [
    { type: 'ellipse', cx: 35, cy: 98, rx: 14, ry: 36 },
    { type: 'ellipse', cx: 85, cy: 98, rx: 14, ry: 36 },
  ],
  lower_back: [{ type: 'rect', x: 40, y: 120, width: 40, height: 28, rx: 7 }],
  glutes: [
    { type: 'ellipse', cx: 43, cy: 162, rx: 20, ry: 20 },
    { type: 'ellipse', cx: 77, cy: 162, rx: 20, ry: 20 },
  ],
  hamstrings: [
    { type: 'rect', x: 32, y: 182, width: 25, height: 55, rx: 9 },
    { type: 'rect', x: 63, y: 182, width: 25, height: 55, rx: 9 },
  ],
  calves: [
    { type: 'ellipse', cx: 44, cy: 258, rx: 12, ry: 24 },
    { type: 'ellipse', cx: 76, cy: 258, rx: 12, ry: 24 },
  ],
};

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Shape({ shape, fill, opacity, onClick }) {
  const { type: Tag, ...props } = shape;
  return (
    <Tag
      {...props}
      style={{ fill, fillOpacity: opacity, cursor: 'pointer', transition: 'fill-opacity 0.25s' }}
      onClick={onClick}
    />
  );
}

function SelectionRing({ shape }) {
  const { type: Tag, ...props } = shape;
  return (
    <Tag
      {...props}
      style={{ fill: 'none', stroke: '#fff', strokeWidth: 2, strokeDasharray: '3 2', pointerEvents: 'none' }}
    />
  );
}

function BodySilhouette() {
  return (
    <g fill="#f5e6d3" stroke="#c8a882" strokeWidth="1">
      {/* Head */}
      <circle cx="60" cy="21" r="16" />
      {/* Neck */}
      <rect x="53" y="36" width="14" height="13" rx="4" />
      {/* Shoulder bar */}
      <rect x="21" y="46" width="78" height="14" rx="7" />
      {/* Torso */}
      <polygon points="30,58 90,58 88,110 86,130 90,150 30,150 34,130 32,110" />
      {/* Left upper arm */}
      <rect x="15" y="48" width="17" height="72" rx="7" />
      {/* Right upper arm */}
      <rect x="88" y="48" width="17" height="72" rx="7" />
      {/* Left forearm */}
      <rect x="13" y="122" width="15" height="58" rx="6" />
      {/* Right forearm */}
      <rect x="92" y="122" width="15" height="58" rx="6" />
      {/* Left hand */}
      <ellipse cx="20" cy="188" rx="8" ry="10" />
      {/* Right hand */}
      <ellipse cx="100" cy="188" rx="8" ry="10" />
      {/* Left thigh */}
      <rect x="30" y="150" width="28" height="72" rx="10" />
      {/* Right thigh */}
      <rect x="62" y="150" width="28" height="72" rx="10" />
      {/* Left lower leg */}
      <rect x="32" y="222" width="24" height="70" rx="9" />
      {/* Right lower leg */}
      <rect x="64" y="222" width="24" height="70" rx="9" />
      {/* Left foot */}
      <ellipse cx="44" cy="296" rx="15" ry="7" />
      {/* Right foot */}
      <ellipse cx="76" cy="296" rx="15" ry="7" />
    </g>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function BodyHighlighter() {
  const [view, setView] = useState('front');
  const [muscleData, setMuscleData] = useState(initMuscleData);
  const [selected, setSelected] = useState(MUSCLE_GROUPS[0].id);

  const muscles = view === 'front' ? FRONT_MUSCLES : BACK_MUSCLES;

  const handleRandomize = useCallback(() => setMuscleData(initMuscleData()), []);

  const updateSelected = (field, value) =>
    setMuscleData((prev) => ({ ...prev, [selected]: { ...prev[selected], [field]: value } }));

  const selectedData = muscleData[selected];
  const selectedMeta = MUSCLE_GROUPS.find((g) => g.id === selected);

  const visibleGroups = MUSCLE_GROUPS.filter((g) => g.view === view || g.view === 'both');

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
          <Space>
            <Button type={view === 'front' ? 'primary' : 'default'} size="small" onClick={() => setView('front')}>
              Přední pohled
            </Button>
            <Button type={view === 'back' ? 'primary' : 'default'} size="small" onClick={() => setView('back')}>
              Zadní pohled
            </Button>
          </Space>

          <svg
            viewBox="0 0 120 303"
            width="100%"
            style={{ maxWidth: 260, userSelect: 'none' }}
            aria-label="Lidská postava se zvýrazněnými svalovými skupinami"
          >
            <BodySilhouette />

            {Object.entries(muscles).map(([groupId, shapes]) => {
              const data = muscleData[groupId];
              if (!data || data.intensity === 0) return null;
              const opacity = intensityToOpacity(data.intensity);
              const isSelected = groupId === selected;

              return (
                <g key={groupId}>
                  {shapes.map((shape, i) => (
                    <Shape
                      key={i}
                      shape={shape}
                      fill={data.color}
                      opacity={opacity}
                      onClick={() => setSelected(groupId)}
                    />
                  ))}
                  {isSelected && shapes.map((shape, i) => <SelectionRing key={`ring-${i}`} shape={shape} />)}
                </g>
              );
            })}
          </svg>
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
                        onClick={() => updateSelected('color', c.value)}
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
