import { useEffect, useState } from 'react';
import { Alert, Card, Empty, Space, Spin, Tag, Typography } from 'antd';
import { Link } from 'react-router-dom';
import { fetchExerciseCatalog } from '../api/client.js';

const { Title, Paragraph, Text } = Typography;

export default function ExerciseCatalogList() {
  const [status, setStatus] = useState('loading');
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function loadData() {
      setStatus('loading');
      setError('');
      try {
        const response = await fetchExerciseCatalog();
        if (!active) return;
        setItems(response.items ?? []);
        setStatus('ready');
      } catch {
        if (!active) return;
        setError('Nepodařilo se načíst katalog cviků.');
        setStatus('error');
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, []);

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <Typography>
        <Title level={2}>Exercise Catalog</Title>
        <Paragraph>Seznam cviků z backend API včetně návazností mezi úrovněmi.</Paragraph>
      </Typography>

      {status === 'loading' && <Spin tip="Načítám cviky..." />}
      {status === 'error' && <Alert type="error" showIcon message={error} />}
      {status === 'ready' && items.length === 0 && <Empty description="Katalog je zatím prázdný." />}

      {status === 'ready' && items.length > 0 && (
        <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
          {items.map((item) => (
            <Card key={item.slug} title={<Link to={`/exercise-catalog/${item.slug}`}>{item.name}</Link>}>
              <Space direction="vertical" size="small" style={{ display: 'flex' }}>
                <Space wrap>
                  <Tag color="blue">Kategorie: {item.category}</Tag>
                  <Tag color="purple">Úroveň: {item.level}</Tag>
                  {item.has_video && <Tag color="green">Video</Tag>}
                </Space>
                <Text>{item.short_description}</Text>
                <Space wrap>
                  {(item.muscle_load ?? []).map((muscle) => (
                    <Tag key={`${item.slug}-${muscle.name}`}>{`${muscle.name} (${muscle.intensity}/5)`}</Tag>
                  ))}
                </Space>
              </Space>
            </Card>
          ))}
        </Space>
      )}
    </Space>
  );
}
