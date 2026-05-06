import { useEffect, useState } from 'react';
import { Alert, Card, Skeleton, Space, Table, Typography } from 'antd';
import { StarFilled, StarOutlined } from '@ant-design/icons';
import { getTreningVezne } from '../api/trening-vezne/get.js';

const { Title, Paragraph, Text } = Typography;

function formatAchievedAt(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleDateString('cs-CZ', { day: 'numeric', month: 'numeric', year: '2-digit' });
}

function StarsCell({ cell }) {
  const stars = cell?.stars ?? 0;
  const achievedAt = formatAchievedAt(cell?.achieved_at);
  return (
    <Space direction="vertical" size={2} style={{ alignItems: 'center', width: '100%' }}>
      <Space size={2}>
        {[0, 1, 2].map((i) =>
          i < stars ? (
            <StarFilled key={i} style={{ color: '#faad14', fontSize: 16 }} />
          ) : (
            <StarOutlined key={i} style={{ color: '#d9d9d9', fontSize: 16 }} />
          ),
        )}
      </Space>
      {achievedAt && (
        <Text type="secondary" style={{ fontSize: 11 }}>
          {achievedAt}
        </Text>
      )}
    </Space>
  );
}

export default function TreningVezne() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    getTreningVezne()
      .then((d) => {
        if (active) setData(d);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load trénink vězně overview:', err);
        setError('Nepodařilo se načíst přehled tréninku.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading || !data) {
    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Title level={2}>Trénink vězně</Title>
        {error ? (
          <Alert type="error" message={error} showIcon />
        ) : (
          <Card>
            <Skeleton active paragraph={{ rows: 10 }} />
          </Card>
        )}
      </Space>
    );
  }

  const columns = [
    {
      title: 'Level',
      dataIndex: 'level',
      key: 'level',
      width: 64,
      align: 'center',
      render: (level) => <Text strong>{level}</Text>,
    },
    ...data.families.map((family) => ({
      title: family.title,
      dataIndex: family.key,
      key: family.key,
      align: 'center',
      render: (cell) => <StarsCell cell={cell} />,
    })),
  ];

  const rows = data.levels.map((level) => {
    const row = { key: level, level };
    for (const family of data.families) {
      row[family.key] = data.cells?.[family.key]?.[String(level)] ?? null;
    }
    return row;
  });

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography>
        <Title level={2}>Trénink vězně</Title>
        <Paragraph>
          Přehled tvého postupu napříč Big Six. Hvězdičky odpovídají úrovním
          Začátečník / Pokročilý / Expert; pod nimi datum dosažení.
        </Paragraph>
      </Typography>

      {error && <Alert type="error" message={error} showIcon />}

      <Table
        columns={columns}
        dataSource={rows}
        pagination={false}
        size="small"
        bordered
        scroll={{ x: 'max-content' }}
      />
    </Space>
  );
}
