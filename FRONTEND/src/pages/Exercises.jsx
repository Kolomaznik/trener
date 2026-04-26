import { useEffect, useState } from 'react';
import {
  Alert,
  Card,
  Col,
  List,
  Row,
  Segmented,
  Skeleton,
  Space,
  Tag,
  Typography,
} from 'antd';
import { fetchExerciseDetail, fetchExercises } from '../api/client.js';

const { Title, Paragraph, Text } = Typography;

function levelLabel(level) {
  if (level === 'beginner') return 'Začátečník';
  if (level === 'advanced') return 'Pokročilý';
  return 'Expert';
}

export default function Exercises() {
  const [exercises, setExercises] = useState([]);
  const [selectedExerciseId, setSelectedExerciseId] = useState(null);
  const [selectedLevel, setSelectedLevel] = useState('beginner');
  const [detail, setDetail] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;

    async function loadExercises() {
      setLoadingList(true);
      setError(null);
      try {
        const data = await fetchExercises();
        if (!active) return;
        setExercises(data);
        if (data.length > 0) {
          setSelectedExerciseId((previous) => previous ?? data[0].id);
        }
      } catch {
        if (!active) return;
        setError('Nepodařilo se načíst seznam cviků.');
      } finally {
        if (active) setLoadingList(false);
      }
    }

    loadExercises();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadDetail() {
      if (!selectedExerciseId) return;
      setLoadingDetail(true);
      setError(null);
      try {
        const data = await fetchExerciseDetail(selectedExerciseId, selectedLevel);
        if (!active) return;
        setDetail(data);
      } catch {
        if (!active) return;
        setError('Nepodařilo se načíst detail cviku.');
      } finally {
        if (active) setLoadingDetail(false);
      }
    }

    loadDetail();
    return () => {
      active = false;
    };
  }, [selectedExerciseId, selectedLevel]);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography>
        <Title level={2}>Cviky – Trénink vězně</Title>
        <Paragraph>
          MVP obsahuje jen základní cviky z knihy: kliky, dřepy, shyby, zvedání nohou, mosty a
          stojky.
        </Paragraph>
      </Typography>

      {error && <Alert type="error" message={error} showIcon />}

      <Row gutter={[16, 16]}>
        <Col xs={24} md={10}>
          <Card title="Seznam cviků">
            {loadingList ? (
              <Skeleton active paragraph={{ rows: 6 }} />
            ) : (
              <List
                dataSource={exercises}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      background: selectedExerciseId === item.id ? '#f5f5f5' : 'transparent',
                      borderRadius: 8,
                      paddingInline: 12,
                    }}
                    onClick={() => {
                      setSelectedExerciseId(item.id);
                      setSelectedLevel('beginner');
                    }}
                  >
                    <List.Item.Meta
                      title={`${item.order}. ${item.category}`}
                      description={
                        <Space direction="vertical" size={2}>
                          <Text>{item.description}</Text>
                          {item.next_exercise_id ? (
                            <Text type="secondary">Další v pořadí: {item.next_exercise_id}</Text>
                          ) : (
                            <Text type="secondary">Poslední cvik v pevné návaznosti</Text>
                          )}
                        </Space>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} md={14}>
          <Card title="Detail cviku">
            {loadingDetail || !detail ? (
              <Skeleton active paragraph={{ rows: 8 }} />
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Space direction="vertical" size={4}>
                  <Title level={3} style={{ margin: 0 }}>
                    {detail.name}
                  </Title>
                  <Text type="secondary">{detail.category}</Text>
                </Space>

                <Paragraph style={{ marginBottom: 0 }}>{detail.description}</Paragraph>
                <Text>
                  <strong>Frekvence:</strong> {detail.frequency}
                </Text>

                <div>
                  <Text strong>Zapojené svaly:</Text>
                  <div style={{ marginTop: 8 }}>
                    {detail.muscles.map((muscle) => (
                      <Tag key={muscle}>{muscle}</Tag>
                    ))}
                  </div>
                </div>

                <div>
                  <Text strong>Úroveň:</Text>
                  <div style={{ marginTop: 8 }}>
                    <Segmented
                      value={selectedLevel}
                      options={detail.level_order.map((level) => ({
                        value: level,
                        label: levelLabel(level),
                      }))}
                      onChange={(value) => setSelectedLevel(value)}
                    />
                  </div>
                </div>

                <Card size="small" title={detail.level_detail.title}>
                  <Paragraph style={{ marginBottom: 8 }}>
                    <strong>Dávkování:</strong> {detail.level_detail.reps}
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>{detail.level_detail.note}</Paragraph>
                </Card>

                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12}>
                    <Card size="small" title="Správně">
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {detail.correct.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </Card>
                  </Col>
                  <Col xs={24} sm={12}>
                    <Card size="small" title="Špatně">
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {detail.incorrect.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </Card>
                  </Col>
                </Row>
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  );
}
