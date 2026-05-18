import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  message,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import { CheckCircleTwoTone, PlusOutlined } from '@ant-design/icons';
import { getExerciseList } from '../../api/catalog/get_exercise_list.js';
import { addUserExercise } from '../../api/user_exercises/post.js';

const { Title } = Typography;

export default function ExercisesCatalog() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [pendingName, setPendingName] = useState(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);

    getExerciseList()
      .then((catalog) => {
        if (!active) return;
        setRows(catalog);
      })
      .catch((err) => {
        if (!active) return;
        console.error('Failed to load exercises catalog:', err);
        setError('Nepodařilo se načíst katalog cviků.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return rows;
    return rows.filter((row) =>
      [row.title, row.name]
        .some((field) => field?.toLowerCase().includes(needle)),
    );
  }, [rows, search]);

  const handleAdd = async (record) => {
    setPendingName(record.name);
    try {
      await addUserExercise(record.name);
      setRows((prev) =>
        prev.map((row) =>
          row.name === record.name ? { ...row, status: 'in_progress' } : row,
        ),
      );
      message.success(`Cvik „${record.title}" přidán do tvého seznamu.`);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      console.error('Failed to add exercise:', err);
      message.error(detail || 'Cvik se nepodařilo přidat.');
    } finally {
      setPendingName(null);
    }
  };

  const columns = useMemo(
    () => [
      {
        title: 'Název',
        dataIndex: 'title',
        key: 'title',
        sorter: (a, b) => a.title.localeCompare(b.title, 'cs'),
        defaultSortOrder: 'ascend',
      },
      {
        title: 'Akce',
        key: 'action',
        width: 160,
        render: (_value, record) => {
          if (record.status === 'completed') {
            return (
              <Tag
                color="success"
                icon={<CheckCircleTwoTone twoToneColor="#52c41a" />}
                data-testid={`completed-${record.name}`}
              >
                Splněno
              </Tag>
            );
          }
          if (record.status === 'in_progress') {
            return (
              <Tag color="warning" data-testid={`in-progress-${record.name}`}>
                In progress
              </Tag>
            );
          }
          return (
            <Button
              type="primary"
              size="small"
              icon={<PlusOutlined />}
              loading={pendingName === record.name}
              onClick={() => handleAdd(record)}
              data-testid={`add-${record.name}`}
            >
              Přidat
            </Button>
          );
        },
      },
    ],
    // handleAdd is recreated each render but only needs pendingName for
    // memoization correctness; ESLint's exhaustive-deps would force the
    // function in here, which would defeat the memo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pendingName],
  );

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Typography>
        <Title level={2} style={{ marginBottom: 0 }}>Katalog</Title>
      </Typography>

      {error && <Alert type="error" showIcon message={error} />}

      <Card>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <Input.Search
            placeholder="Hledat podle názvu"
            allowClear
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            data-testid="catalog-search"
          />

          {loading ? (
            <div style={{ display: 'grid', placeItems: 'center', padding: 24 }}>
              <Spin />
            </div>
          ) : filtered.length === 0 ? (
            <Empty description="Žádné cviky neodpovídají filtru." />
          ) : (
            <Table
              rowKey="name"
              dataSource={filtered}
              columns={columns}
              size="middle"
              pagination={{ pageSize: 25, hideOnSinglePage: true }}
              data-testid="catalog-table"
            />
          )}
        </Space>
      </Card>
    </Space>
  );
}
