import { useEffect, useState } from 'react';
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
  Spin,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';
import { fetchExerciseDetail, fetchMuscleLoad } from '../api/client.js';
import { isProfileComplete, useUserSettings } from '../context/UserSettingsContext.jsx';

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
        <ExerciseDetailBody detail={detail} navigate={navigate} />
      )}
    </Space>
  );
}

function ExerciseDetailBody({ detail, navigate }) {
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
        <Paragraph style={{ marginTop: 12, marginBottom: 0 }}>
          {detail.description}
        </Paragraph>
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
 *  1. Tabs: Začátečník | Středně pokročilý | Mistr — each shows sets × reps
 *  2. Coach note (below tabs, shared)
 *  3. Divider
 *  4. Muscle map with % / Svalová zátěž toggle
 *
 * When "Svalová zátěž" is selected and the user profile is complete, the
 * muscle-load API is called and the map is coloured by relative load instead
 * of raw engagement percentage.
 */
function ProgressionAndMuscleCard({ detail }) {
  const { userSettings } = useUserSettings();
  const [activeTab, setActiveTab] = useState('beginner');
  const [mapMode, setMapMode] = useState('percent'); // 'percent' | 'load'
  const [loadEngagement, setLoadEngagement] = useState(null);
  const [loadFetching, setLoadFetching] = useState(false);

  const profileComplete = isProfileComplete(userSettings);

  // Fetch muscle load whenever the mode, active tab, or exercise changes.
  useEffect(() => {
    if (mapMode !== 'load' || !profileComplete) return undefined;

    const goal = detail.progression_goals?.[activeTab];
    const total_reps = goal ? goal.sets * goal.reps : 10;
    const age = new Date().getFullYear() - userSettings.birth_year;
    // Age is approximated as (current_year − birth_year); it may be off by 1
    // for users who haven't yet had their birthday this year.  The impact on
    // the physiological coefficient is negligible (≤ 0.05).
    const gender = userSettings.gender === 'male' ? 'M' : 'F';

    let active = true;
    setLoadFetching(true);

    fetchMuscleLoad(detail.id, {
      weight_kg: userSettings.weight_kg,
      height_cm: userSettings.height_cm,
      age,
      gender,
      total_reps,
    })
      .then((data) => {
        if (!active) return;
        // Normalise absolute loads to 0–100 scale so ExerciseMuscleMap can
        // colour muscles by relative intensity without any internal changes.
        const entries = Object.entries(data.muscle_engagement);
        const maxLoad = Math.max(...entries.map(([, m]) => m.muscle_load), 1);
        const normalized = Object.fromEntries(
          entries.map(([muscle, { muscle_load }]) => [
            muscle,
            Math.round((muscle_load / maxLoad) * 100),
          ]),
        );
        setLoadEngagement(normalized);
      })
      .catch(() => {
        if (active) setLoadEngagement(null);
      })
      .finally(() => {
        if (active) setLoadFetching(false);
      });

    return () => {
      active = false;
    };
  }, [mapMode, activeTab, detail, profileComplete, userSettings]);

  // What to render on the muscle map.
  const displayEngagement =
    mapMode === 'load' && loadEngagement
      ? loadEngagement
      : (detail.muscle_engagement_percent ?? {});

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
          <Text type="secondary" style={{ fontSize: 13 }}>
            série × opakování
          </Text>
        </div>
      ) : (
        <Text type="secondary">Žádné cíle pro tuto úroveň.</Text>
      ),
    };
  });

  return (
    <Card>
      <Text strong style={{ fontSize: 15 }}>
        Postup
      </Text>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ marginTop: 4 }}
      />

      {detail.progression_goals?.coach_note && (
        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          {detail.progression_goals.coach_note}
        </Paragraph>
      )}

      <Divider />

      {/* ── Muscle map section ──────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12,
        }}
      >
        <Text strong style={{ fontSize: 15 }}>
          Zapojené svaly
        </Text>
        <Segmented
          options={[
            { label: '% Zapojení', value: 'percent' },
            { label: 'Svalová zátěž', value: 'load', disabled: !profileComplete },
          ]}
          value={mapMode}
          onChange={setMapMode}
        />
      </div>

      {mapMode === 'load' && !profileComplete && (
        <Alert
          type="info"
          showIcon
          message="Pro výpočet svalové zátěže vyplňte tělesné údaje v nastavení profilu."
          style={{ marginBottom: 12 }}
        />
      )}

      <Spin spinning={loadFetching}>
        <ExerciseMuscleMap engagement={displayEngagement} />
      </Spin>
    </Card>
  );
}
