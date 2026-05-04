import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Row,
  Segmented,
  Skeleton,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { ArrowLeftOutlined, PlayCircleOutlined } from '@ant-design/icons';
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';
import { fetchExerciseDetail } from '../api/client.js';

const { Title, Paragraph, Text } = Typography;

/** The three difficulty tiers every exercise has. */
const DIFFICULTIES = [
  { key: 'beginner', label: 'Začátečník' },
  { key: 'intermediate', label: 'Středně pokročilý' },
  { key: 'mastery', label: 'Mistr' },
];

export default function ExerciseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    fetchExerciseDetail(id)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((err) => {
        if (!active) return;
        if (err?.response?.status === 404) {
          setError('Cvik nebyl nalezen.');
        } else {
          console.error('Failed to load exercise detail:', err);
          setError('Nepodařilo se načíst detail cviku.');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/exercises')}
        style={{ padding: 0 }}
      >
        Zpět na seznam
      </Button>

      {error && <Alert type="error" message={error} showIcon />}

      {loading || !detail ? (
        <Card>
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      ) : (
        <ExerciseDetailBody detail={detail} navigate={navigate} id={id} />
      )}
    </Space>
  );
}

function ExerciseDetailBody({ detail, navigate, id }) {
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* ── Header card: name, tags, description ─────────────────────────── */}
      <Card>
        <Space direction="vertical" size={4}>
          <Title level={2} style={{ margin: 0 }}>
            {detail.name}
          </Title>
          {detail.english_name && (
            <Text type="secondary">{detail.english_name}</Text>
          )}
          <Space size={4} wrap>
            <Tag color="blue">{detail.family}</Tag>
            <Tag>Level {detail.level}</Tag>
          </Space>
        </Space>
        <Paragraph style={{ marginTop: 12, marginBottom: 12 }}>
          {detail.description}
        </Paragraph>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={() => navigate(`/exercises/${id}/workout`)}
          size="large"
        >
          Začít cvičit
        </Button>
      </Card>

      {/* ── Difficulty tabs (Začátečník/Středně pokročilý/Mistr) + muscle map */}
      {detail.progression_goals && (
        <ProgressionAndMuscleCard detail={detail} />
      )}

      {/* ── Static detail cards ──────────────────────────────────────────── */}
      <Row gutter={[16, 16]}>
        <Col xs={24} md={14}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            {detail.instructions?.length > 0 && (
              <Card size="small" title="Jak cvičit">
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {detail.instructions.map((step, idx) => (
                    <li key={idx} style={{ marginBottom: 4 }}>
                      {step}
                    </li>
                  ))}
                </ol>
              </Card>
            )}

            {detail.cadence && (
              <Card size="small" title="Tempo">
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="Spouštění">
                    {detail.cadence.eccentric_sec} s
                  </Descriptions.Item>
                  <Descriptions.Item label="Pauza dole">
                    {detail.cadence.pause_bottom_sec} s
                  </Descriptions.Item>
                  <Descriptions.Item label="Zvedání">
                    {detail.cadence.concentric_sec} s
                  </Descriptions.Item>
                  <Descriptions.Item label="Pauza nahoře">
                    {detail.cadence.pause_top_sec} s
                  </Descriptions.Item>
                  <Descriptions.Item label="Celkem">
                    {detail.cadence.total_rep_time_sec} s / opakování
                  </Descriptions.Item>
                </Descriptions>
                <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                  {detail.cadence.coach_note}
                </Paragraph>
              </Card>
            )}

            {detail.media?.youtube_tutorial && (
              <Card size="small" title="Video">
                <a
                  href={detail.media.youtube_tutorial}
                  target="_blank"
                  rel="noreferrer"
                >
                  {detail.media.thumbnail_url ? (
                    <img
                      src={detail.media.thumbnail_url}
                      alt={detail.name}
                      style={{ maxWidth: '100%', borderRadius: 8 }}
                    />
                  ) : (
                    <span>YouTube tutorial</span>
                  )}
                </a>
              </Card>
            )}
          </Space>
        </Col>
      </Row>

      {detail.next_exercise_id ? (
        <Alert
          type="info"
          showIcon
          message={
            <Space>
              <Text>Další úroveň:</Text>
              <Button
                type="link"
                onClick={() => navigate(`/exercises/${detail.next_exercise_id}`)}
                style={{ padding: 0 }}
              >
                {detail.next_exercise_name}
              </Button>
            </Space>
          }
        />
      ) : (
        <Alert type="success" showIcon message="Nejvyšší úroveň této rodiny" />
      )}
    </Space>
  );
}

/**
 * Card containing:
 *  1. Tabs: Začátečník | Středně pokročilý | Mistr
 *     Each tab shows sets × reps and, when available, the total "Přemístěná
 *     zátěž" in kg (= weight_kg × reps × level_coefficient).
 *  2. Coach note (shared below all tabs)
 *  3. Divider
 *  4. Muscle map with toggle: % Zapojení ↔ Přemístěná zátěž (kg)
 *
 * The muscle load data is pre-computed by the backend and embedded directly
 * in `detail.muscle_load_by_difficulty`.  No separate API call is made.
 * The toggle is disabled when the backend could not compute the load (user not
 * authenticated or has no weight_kg in their profile).
 */
function ProgressionAndMuscleCard({ detail }) {
  const [activeTab, setActiveTab] = useState('beginner');
  const [mapMode, setMapMode] = useState('percent'); // 'percent' | 'load'

  const loadByDifficulty = detail.muscle_load_by_difficulty; // null or { beginner, intermediate, mastery }
  const hasLoadData = loadByDifficulty != null;

  // Derive what to show on the muscle map.
  const displayEngagement = (() => {
    if (mapMode === 'load' && hasLoadData) {
      const tierData = loadByDifficulty[activeTab] ?? {};
      const entries = Object.entries(tierData);
      if (entries.length === 0) return detail.muscle_engagement_percent ?? {};
      // Normalise to 0–100 so ExerciseMuscleMap can colour muscles by relative
      // intensity without any internal changes.
      const maxLoad = Math.max(...entries.map(([, m]) => m.muscle_load), 1);
      return Object.fromEntries(
        entries.map(([muscle, { muscle_load }]) => [
          muscle,
          Math.round((muscle_load / maxLoad) * 100),
        ]),
      );
    }
    return detail.muscle_engagement_percent ?? {};
  })();

  // Min/max per-muscle load (kg) for the active tier — used by the legend.
  const activeLoadRange = useMemo(() => {
    if (!hasLoadData) return null;
    const tierData = loadByDifficulty[activeTab] ?? {};
    const loads = Object.values(tierData).map((m) => m.muscle_load);
    if (loads.length === 0) return null;
    return { min: Math.min(...loads), max: Math.max(...loads) };
  }, [hasLoadData, loadByDifficulty, activeTab]);

  const tabItems = DIFFICULTIES.map(({ key, label }) => {
    const goal = detail.progression_goals?.[key];

    return {
      key,
      label,
      children: goal ? (
        <div style={{ textAlign: 'center', padding: '16px 0 8px' }}>
          <Title level={2} style={{ margin: 0, lineHeight: 1 }}>
            {goal.sets} × {goal.reps}
          </Title>
        </div>
      ) : (
        <Text type="secondary">Žádné cíle pro tuto úroveň.</Text>
      ),
    };
  });

  return (
    <Card>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ marginTop: 4 }}
      />
      <Divider />

      {/* ── Muscle map section ──────────────────────────────────────────── */}
      {!hasLoadData && (
        <Alert
          type="info"
          showIcon
          message="Přihlaste se a vyplňte hmotnost v profilu pro výpočet přemístěné zátěže."
          style={{ marginBottom: 12 }}
        />
      )}

      <ExerciseMuscleMap engagement={displayEngagement} mode={mapMode} loadRange={activeLoadRange} />

      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
        <Segmented
          options={[
            { label: '% Zapojení', value: 'percent' },
            { label: 'Zátěž (kg)', value: 'load', disabled: !hasLoadData },
          ]}
          value={mapMode}
          onChange={setMapMode}
        />
      </div>
    </Card>
  );
}
