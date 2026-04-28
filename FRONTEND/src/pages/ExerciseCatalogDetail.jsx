import { useEffect, useState } from 'react';
import { Alert, Card, Descriptions, Empty, Space, Spin, Tag, Typography } from 'antd';
import { Link, useParams } from 'react-router-dom';
import { fetchExerciseDetail } from '../api/client.js';

const { Title, Paragraph, Text } = Typography;

export default function ExerciseCatalogDetail() {
  const { slug } = useParams();
  const [status, setStatus] = useState('loading');
  const [exercise, setExercise] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadData() {
      setStatus('loading');
      setError('');
      try {
        const response = await fetchExerciseDetail(slug);
        if (!active) return;
        setExercise(response);
        setStatus('ready');
      } catch (loadError) {
        if (!active) return;
        if (loadError?.response?.status === 404) {
          setStatus('not-found');
          return;
        }
        setError('Nepodařilo se načíst detail cviku.');
        setStatus('error');
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, [slug]);

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <Typography>
        <Title level={2}>Exercise Detail</Title>
        <Paragraph>
          <Link to="/exercise-catalog">← Zpět na katalog</Link>
        </Paragraph>
      </Typography>

      {status === 'loading' && <Spin tip="Načítám detail..." />}
      {status === 'error' && <Alert type="error" showIcon message={error} />}
      {status === 'not-found' && <Empty description="Cvik nebyl nalezen." />}

      {status === 'ready' && exercise && (
        <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
          <Card title={exercise.name}>
            <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
              <Text>{exercise.description}</Text>

              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="Kategorie">{exercise.metadata?.category}</Descriptions.Item>
                <Descriptions.Item label="Úroveň">{exercise.metadata?.level}</Descriptions.Item>
                <Descriptions.Item label="Zdroj">{exercise.metadata?.source_book}</Descriptions.Item>
              </Descriptions>

              <div>
                <Title level={5}>Svalové partie</Title>
                <Space wrap>
                  {(exercise.muscle_load ?? []).map((muscle) => (
                    <Tag key={muscle.name}>{`${muscle.name} (${muscle.intensity}/5)`}</Tag>
                  ))}
                </Space>
              </div>

              <div>
                <Title level={5}>Časování</Title>
                <Text>{exercise.timing?.raw}</Text>
              </div>

              <div>
                <Title level={5}>Kroky</Title>
                <Space direction="vertical" size="small" style={{ display: 'flex' }}>
                  {(exercise.steps ?? []).map((step, index) => (
                    <Text key={`${exercise.slug}-${index + 1}`}>{`${index + 1}. ${step}`}</Text>
                  ))}
                </Space>
              </div>

              <div>
                <Title level={5}>Progrese</Title>
                <Space direction="vertical" size="small" style={{ display: 'flex' }}>
                  <Text>Předchozí: {exercise.progression?.previous_slug ?? '---'}</Text>
                  <Text>Další: {exercise.progression?.next_slug ?? '---'}</Text>
                  <Text>Podmínka: {exercise.progression?.unlock_condition ?? '---'}</Text>
                </Space>
              </div>

              <div>
                <Title level={5}>Média</Title>
                {exercise.media?.video_url ? (
                  <a href={exercise.media.video_url} target="_blank" rel="noreferrer">
                    Otevřít video ukázku
                  </a>
                ) : (
                  <Text>Video není dostupné.</Text>
                )}
              </div>
            </Space>
          </Card>
        </Space>
      )}
    </Space>
  );
}
