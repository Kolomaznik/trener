import { useEffect, useMemo, useRef, useState } from 'react';
import { Alert, Divider, Flex, Grid, Spin, Typography } from 'antd';
import BodyHighlighter from '../components/BodyHighlighter.jsx';
import { getDashboard } from '../api/dashboard/get.js';
import { useUserSettings } from '../context/UserSettingsContext.jsx';

const { Title, Paragraph } = Typography;
const HEATMAP_COLORS = ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'];
const MONTH_LABELS = [
  'Led',
  'Úno',
  'Bře',
  'Dub',
  'Kvě',
  'Čvn',
  'Čvc',
  'Srp',
  'Zář',
  'Říj',
  'Lis',
  'Pro',
];
const DAY_LABELS = [null, 'Po', null, 'St', null, 'Pá', null];

function parseISODate(value) {
  const [y, m, d] = value.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function formatDateKey(dateValue) {
  return `${dateValue.getFullYear()}-${String(dateValue.getMonth() + 1).padStart(2, '0')}-${String(
    dateValue.getDate(),
  ).padStart(2, '0')}`;
}

function getLevel(value, maxValue) {
  if (value <= 0 || maxValue <= 0) return 0;
  return Math.min(4, Math.max(1, Math.ceil((value / maxValue) * 4)));
}

export default function Home() {
  const screens = Grid.useBreakpoint();
  const isMobile = !screens.md;
  const { userSettings } = useUserSettings();
  const CELL_SIZE = isMobile ? 10 : 12;
  const CELL_GAP = isMobile ? 2 : 3;
  const DAY_LABEL_COL = isMobile ? 22 : 26;

  const [overview, setOverview] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [overviewError, setOverviewError] = useState('');
  const [containerWidth, setContainerWidth] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return undefined;
    const observer = new ResizeObserver((entries) => {
      if (entries[0]) setContainerWidth(entries[0].contentRect.width);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [isLoading]);

  useEffect(() => {
    let cancelled = false;

    getDashboard()
      .then((data) => {
        if (cancelled) return;
        setOverview(data.year_summary);
      })
      .catch(() => {
        if (cancelled) return;
        setOverviewError('Nepodařilo se načíst roční přehled cvičení.');
      })
      .finally(() => {
        if (cancelled) return;
        setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const { weeks, monthLabels } = useMemo(() => {
    if (!overview?.start_date || !overview?.end_date) {
      return { weeks: [], monthLabels: [] };
    }

    const start = parseISODate(overview.start_date);
    const end = parseISODate(overview.end_date);
    const dayMap = new Map((overview.days ?? []).map((d) => [d.date, d.count]));
    const maxCount = (overview.days ?? []).reduce((m, d) => Math.max(m, d.count), 0);

    const builtWeeks = [];
    const cursor = new Date(start);
    while (cursor <= end) {
      const week = [];
      for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
        if (cursor > end) {
          week.push({ key: `pad-${cursor.getTime()}-${dayIndex}`, inRange: false });
        } else {
          const dateKey = formatDateKey(cursor);
          const count = dayMap.get(dateKey) ?? 0;
          week.push({
            key: dateKey,
            date: new Date(cursor),
            count,
            level: getLevel(count, maxCount),
            inRange: true,
          });
        }
        cursor.setDate(cursor.getDate() + 1);
      }
      builtWeeks.push(week);
    }

    const labels = [];
    let lastMonth = -1;
    builtWeeks.forEach((week, weekIndex) => {
      const firstInRange = week.find((c) => c.inRange);
      if (!firstInRange) return;
      const monthIndex = firstInRange.date.getMonth();
      if (monthIndex !== lastMonth && firstInRange.date.getDate() <= 7) {
        labels.push({ weekIndex, label: MONTH_LABELS[monthIndex] });
        lastMonth = monthIndex;
      }
    });

    return { weeks: builtWeeks, monthLabels: labels };
  }, [overview]);

  const { visibleWeeks, visibleMonthLabels } = useMemo(() => {
    if (containerWidth <= 0 || weeks.length === 0) {
      return { visibleWeeks: weeks, visibleMonthLabels: monthLabels };
    }
    const cellPlusGap = CELL_SIZE + CELL_GAP;
    const available = containerWidth - DAY_LABEL_COL - CELL_GAP;
    const maxVisible = Math.max(1, Math.floor(available / cellPlusGap));
    const count = Math.min(weeks.length, maxVisible);
    const offset = weeks.length - count;
    return {
      visibleWeeks: weeks.slice(offset),
      visibleMonthLabels: monthLabels
        .filter((m) => m.weekIndex >= offset)
        .map((m) => ({ ...m, weekIndex: m.weekIndex - offset })),
    };
  }, [weeks, monthLabels, containerWidth, CELL_SIZE, CELL_GAP, DAY_LABEL_COL]);

  return (
    <Typography>
      {overviewError && (
        <Alert type="error" showIcon message={overviewError} style={{ marginBottom: 12 }} />
      )}

      {isLoading ? (
        <Flex justify="center" style={{ padding: 24 }}>
          <Spin />
        </Flex>
      ) : (
        <div ref={containerRef} style={{ width: '100%' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateRows: `auto repeat(7, auto)`,
            gridTemplateColumns: `${DAY_LABEL_COL}px repeat(${visibleWeeks.length}, ${CELL_SIZE}px)`,
            gap: `${CELL_GAP}px`,
            width: 'max-content',
          }}
        >
          {visibleMonthLabels.map((m) => (
            <div
              key={`mlbl-${m.weekIndex}`}
              style={{
                gridRow: 1,
                gridColumn: m.weekIndex + 2,
                fontSize: 11,
                color: '#666',
                whiteSpace: 'nowrap',
                lineHeight: 1,
              }}
            >
              {m.label}
            </div>
          ))}

          {DAY_LABELS.map((label, i) =>
            label ? (
              <div
                key={`dlbl-${i}`}
                style={{
                  gridRow: i + 2,
                  gridColumn: 1,
                  fontSize: 11,
                  color: '#666',
                  display: 'flex',
                  alignItems: 'center',
                  lineHeight: 1,
                }}
              >
                {label}
              </div>
            ) : null,
          )}

          {visibleWeeks.map((week, weekIndex) =>
            week.map((cell, dayIndex) =>
              cell.inRange ? (
                <div
                  key={cell.key}
                  title={`${cell.date.toLocaleDateString('cs-CZ')}: ${cell.count} cvičení`}
                  style={{
                    gridRow: dayIndex + 2,
                    gridColumn: weekIndex + 2,
                    width: CELL_SIZE,
                    height: CELL_SIZE,
                    backgroundColor: HEATMAP_COLORS[cell.level],
                    borderRadius: 2,
                    border: '1px solid rgba(27,31,35,0.06)',
                  }}
                />
              ) : null,
            ),
          )}
        </div>
        </div>
      )}

      <Flex
        align="center"
        justify="flex-end"
        gap={4}
        style={{ marginTop: 4, fontSize: 11, color: '#666' }}
      >
        <span>Méně</span>
        {HEATMAP_COLORS.map((color, i) => (
          <div
            key={`legend-${i}`}
            style={{
              width: CELL_SIZE,
              height: CELL_SIZE,
              backgroundColor: color,
              borderRadius: 2,
              border: '1px solid rgba(27,31,35,0.06)',
            }}
          />
        ))}
        <span>Více</span>
      </Flex>
      <Divider />
    </Typography>
  );
}
