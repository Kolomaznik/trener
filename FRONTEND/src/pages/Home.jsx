import { useEffect, useMemo, useState } from 'react';
import { Alert, Divider, Flex, Grid, Spin, Tooltip, Typography } from 'antd';
import BodyHighlighter from '../components/BodyHighlighter.jsx';
import { getMonthlyOverview } from '../api/getMonthlyOverview.js';

const { Title, Paragraph } = Typography;
const { useBreakpoint } = Grid;
const HEATMAP_COLORS = ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'];

function formatMonthValue(dateValue) {
  return `${dateValue.getFullYear()}-${String(dateValue.getMonth() + 1).padStart(2, '0')}`;
}

function getLevel(value, maxValue) {
  if (value <= 0 || maxValue <= 0) return 0;
  return Math.min(4, Math.max(1, Math.ceil((value / maxValue) * 4)));
}

export default function Home() {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [overview, setOverview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [overviewError, setOverviewError] = useState('');
  const month = useMemo(() => formatMonthValue(new Date()), []);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setOverviewError('');

    getMonthlyOverview(month)
      .then((data) => {
        if (!active) return;
        setOverview(data);
      })
      .catch(() => {
        if (!active) return;
        setOverviewError('Nepodařilo se načíst měsíční přehled cvičení.');
      })
      .finally(() => {
        if (!active) return;
        setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [month]);

  const heatmapColumns = useMemo(() => {
    if (!overview?.days?.length) return [];
    const monthDate = new Date(`${overview.month}-01T00:00:00`);
    if (Number.isNaN(monthDate.getTime())) return [];

    const dayMap = new Map(overview.days.map((day) => [day.date, day.count]));
    const maxCount = overview.days.reduce((max, day) => Math.max(max, day.count), 0);
    const firstDay = new Date(monthDate);
    const lastDay = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
    const firstWeekDay = (firstDay.getDay() + 6) % 7;
    const totalCells = Math.ceil((firstWeekDay + lastDay.getDate()) / 7) * 7;

    const cells = Array.from({ length: totalCells }, (_, index) => {
      const dayInMonth = index - firstWeekDay + 1;
      const inMonth = dayInMonth >= 1 && dayInMonth <= lastDay.getDate();
      if (!inMonth) return { key: `empty-${index}`, date: null, count: 0, level: 0, inMonth: false };

      const dateValue = new Date(monthDate.getFullYear(), monthDate.getMonth(), dayInMonth);
      const dateKey = dateValue.toISOString().slice(0, 10);
      const count = dayMap.get(dateKey) ?? 0;
      return {
        key: dateKey,
        date: dateValue,
        count,
        level: getLevel(count, maxCount),
        inMonth: true,
      };
    });

    return Array.from({ length: cells.length / 7 }, (_, weekIndex) =>
      cells.slice(weekIndex * 7, weekIndex * 7 + 7),
    );
  }, [overview]);

  const monthLabel = useMemo(() => {
    if (!overview?.month) return '';
    const dateValue = new Date(`${overview.month}-01T00:00:00`);
    if (Number.isNaN(dateValue.getTime())) return overview.month;
    return new Intl.DateTimeFormat('cs-CZ', { month: 'long', year: 'numeric' }).format(dateValue);
  }, [overview]);

  return (
    <Typography>
      <Title>Overview</Title>
      <Paragraph>Welcome to Trainer. Pick up where you left off or start a new session.</Paragraph>

      <Title level={3}>Měsíční přehled cvičení</Title>
      <Paragraph style={{ marginBottom: 8 }}>{monthLabel}</Paragraph>

      {overviewError && <Alert type="error" showIcon message={overviewError} style={{ marginBottom: 12 }} />}

      {isLoading ? (
        <Spin />
      ) : (
        <Flex gap={4} style={{ overflowX: 'auto', paddingBottom: 8, marginBottom: 8 }}>
          {heatmapColumns.map((week, weekIndex) => (
            <Flex key={`week-${weekIndex}`} vertical gap={4}>
              {week.map((cell) =>
                cell.inMonth && cell.date ? (
                  <Tooltip
                    key={cell.key}
                    title={`${cell.date.toLocaleDateString('cs-CZ')}: ${cell.count} cvičení`}
                    mouseEnterDelay={0.1}
                  >
                    <div
                      style={{
                        width: isMobile ? 12 : 14,
                        height: isMobile ? 12 : 14,
                        borderRadius: 3,
                        backgroundColor: HEATMAP_COLORS[cell.level],
                        border: '1px solid rgba(27,31,35,0.06)',
                      }}
                    />
                  </Tooltip>
                ) : (
                  <div
                    key={cell.key}
                    style={{
                      width: isMobile ? 12 : 14,
                      height: isMobile ? 12 : 14,
                    }}
                  />
                ),
              )}
            </Flex>
          ))}
        </Flex>
      )}

      <Divider />

      <Title level={3}>Svalová mapa</Title>
      <Paragraph>
        Interaktivní přehled svalových partií. Klikněte na sval nebo vyberte partii ze seznamu a upravte barvu a
        intenzitu zvýraznění.
      </Paragraph>
      <BodyHighlighter />
    </Typography>
  );
}
