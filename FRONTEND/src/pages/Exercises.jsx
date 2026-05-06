import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Card,
  Col,
  Empty,
  Row,
  Skeleton,
  Space,
  Tag,
  Typography,
} from 'antd';
import { getExercises } from '../api/exercises/get_list.js';

const { Title, Paragraph, Text } = Typography;

const LEVEL_LABELS = {
  beginner: 'Začátečník',
  intermediate: 'Středně pokročilý',
  mastery: 'Mistr',
};

const LEVEL_COLORS = {
  beginner: 'default',
  intermediate: 'blue',
  mastery: 'gold',
};

export default function Exercises() {
  const navigate = useNavigate();
  const [exercises, setExercises] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getExercises()
      .then((data) => {
        if (active) setExercises(data);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load exercises:', err);
        setError('Nepodařilo se načíst seznam cviků.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography>
        <Title level={2}>Cviky</Title>
        <Paragraph>
          Vyberte cvik z dlaždic níže. Detail s instrukcemi, tempem a svalovou mapou se otevře
          po kliknutí.
        </Paragraph>
      </Typography>

      {error && <Alert type="error" message={error} showIcon />}

      {loading ? (
        <Row gutter={[16, 16]}>
          {[0, 1, 2].map((i) => (
            <Col key={i} xs={24} sm={12} lg={8}>
              <Card>
                <Skeleton active paragraph={{ rows: 3 }} />
              </Card>
            </Col>
          ))}
        </Row>
      ) : exercises.length === 0 ? (
        <Empty description="Žádné cviky v databázi." />
      ) : (
        <Row gutter={[16, 16]}>
          {exercises.map((item) => (
            <Col key={item.name} xs={24} sm={12} lg={8}>
              <ExerciseTile
                item={item}
                onClick={() => navigate(`/exercises/${item.name}`)}
              />
            </Col>
          ))}
        </Row>
      )}
    </Space>
  );
}

function ExerciseTile({ item, onClick }) {
  return (
    <Card
      hoverable
      onClick={onClick}
      role="button"
      aria-label={`Otevřít cvik ${item.title}`}
      styles={{ body: { padding: 16 } }}
      style={{ height: '100%' }}
    >
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Space size={4} wrap>
          <Tag color="blue">{item.family}</Tag>
          <Tag>Level {item.level}</Tag>
          {item.user_level && (
            <Tag color={LEVEL_COLORS[item.user_level] ?? 'default'}>
              {LEVEL_LABELS[item.user_level] ?? 'Neznámá úroveň'}
            </Tag>
          )}
        </Space>
        <Title level={4} style={{ margin: 0 }}>
          {item.title}
        </Title>
        {item.next_exercise_name ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            Další úroveň: {item.next_exercise_title}
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            Nejvyšší úroveň této rodiny
          </Text>
        )}
      </Space>
    </Card>
  );
}
