import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Skeleton,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';
import { fetchExerciseDetail, fetchExercisesByFamily } from '../api/client.js';

const { Title, Paragraph, Text } = Typography;

const PROGRESSION_LABELS = [
  { key: 'beginner', label: 'Začátečník' },
  { key: 'intermediate', label: 'Středně pokročilý' },
  { key: 'mastery', label: 'Mistr' },
];

export default function ExerciseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [familyExercises, setFamilyExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    fetchExerciseDetail(id)
      .then((data) => {
        if (!active) return;
        setDetail(data);
        return fetchExercisesByFamily(data.family).then((siblings) => {
          if (active) setFamilyExercises(siblings);
        });
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
        <ExerciseDetailBody
          detail={detail}
          familyExercises={familyExercises}
          navigate={navigate}
        />
      )}
    </Space>
  );
}

function ExerciseDetailBody({ detail, familyExercises, navigate }) {
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

      {/* ── Level tabs: progression goals + muscle map per level ─────────── */}
      {familyExercises.length > 0 && (
        <LevelTabs
          familyExercises={familyExercises}
          currentLevel={detail.level}
          navigate={navigate}
        />
      )}

      {/* ── Static detail cards for the currently viewed exercise ────────── */}
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

function LevelTabs({ familyExercises, currentLevel, navigate }) {
  const [activeKey, setActiveKey] = useState(String(currentLevel));

  function handleTabChange(key) {
    const target = familyExercises.find((ex) => String(ex.level) === key);
    if (target && target.level !== currentLevel) {
      setActiveKey(key);
      navigate(`/exercises/${target.id}`);
    }
  }

  const items = familyExercises.map((ex) => ({
    key: String(ex.level),
    label: `Level ${ex.level}`,
    children: <LevelTabContent exercise={ex} />,
  }));

  return (
    <Card size="small">
      <Tabs
        activeKey={activeKey}
        onChange={handleTabChange}
        items={items}
        data-testid="level-tabs"
      />
    </Card>
  );
}

function LevelTabContent({ exercise }) {
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} md={14}>
        {exercise.progression_goals ? (
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Text strong>Postup</Text>
            <Table
              size="small"
              bordered
              pagination={false}
              columns={PROGRESSION_LABELS.map(({ key, label }) => ({
                title: label,
                dataIndex: key,
                key,
                align: 'center',
              }))}
              dataSource={[
                {
                  key: 'goals',
                  ...Object.fromEntries(
                    PROGRESSION_LABELS.map(({ key }) => {
                      const goal = exercise.progression_goals[key];
                      return [key, goal ? `${goal.sets} × ${goal.reps}` : '—'];
                    }),
                  ),
                },
              ]}
            />
            {exercise.progression_goals.coach_note && (
              <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                {exercise.progression_goals.coach_note}
              </Paragraph>
            )}
          </Space>
        ) : (
          <Text type="secondary">Žádné cíle pro tuto úroveň.</Text>
        )}
      </Col>
      <Col xs={24} md={10}>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          Zapojené svaly
        </Text>
        <ExerciseMuscleMap engagement={exercise.muscle_engagement_percent ?? {}} />
      </Col>
    </Row>
  );
}
