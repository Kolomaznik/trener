import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Empty,
  Skeleton,
  Space,
  Typography,
} from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';
import { getUserExercises } from '../api/user_exercises/get_list.js';

const { Title, Paragraph } = Typography;

export default function Exercises() {
  const navigate = useNavigate();
  const [firstName, setFirstName] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getUserExercises()
      .then((data) => {
        if (!active) return;
        const list = Array.isArray(data) ? data : [];
        setFirstName(list.length > 0 ? list[0].exercise_name : null);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load user exercises:', err);
        setError('Nepodařilo se načíst tvůj seznam cviků.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 3 }} />
      </Card>
    );
  }

  if (error) {
    return <Alert type="error" message={error} showIcon />;
  }

  if (firstName) {
    return <Navigate to={`/exercises/${firstName}`} replace />;
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography>
        <Title level={2}>Moje cviky</Title>
        <Paragraph>
          Tvůj osobní seznam. Cviky přidáváš v katalogu — viz tlačítko níže.
        </Paragraph>
      </Typography>
      <Empty
        description="Zatím nemáš žádné cviky. Přidej si je z katalogu."
        data-testid="empty-state"
      >
        <Button
          type="primary"
          icon={<DatabaseOutlined />}
          onClick={() => navigate('/admin/exercises')}
        >
          Otevřít katalog cviků
        </Button>
      </Empty>
    </Space>
  );
}
