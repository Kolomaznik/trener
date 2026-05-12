import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Image,
  Row,
  Segmented,
  Skeleton,
  Space,
  Statistic,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  PlayCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import { Line } from '@ant-design/plots';
import ReactMarkdown from 'react-markdown';
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';
import { getExerciseDetail } from '../api/exercises/get_detail.js';
import { addUserExercise } from '../api/user_exercises/post.js';
import { putExerciseSeries } from '../api/exercises/series.js';
import { getUserExercises } from '../api/user_exercises/get_list.js';
import {
  computeSessionStats,
  parseNumberFromTokens,
  shouldAcceptEvent,
  tokenizeTranscript,
} from '../features/voiceCounting.js';

const { Title, Paragraph, Text } = Typography;

/** The three difficulty tiers every exercise has. */
const DIFFICULTIES = [
  { key: 'beginner', label: 'Začátečník' },
  { key: 'intermediate', label: 'Středně pokročilý' },
  { key: 'mastery', label: 'Mistr' },
];

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

const PACE_LABELS = {
  too_fast: { text: 'Příliš rychle', color: 'orange' },
  on_track: { text: 'V tempu', color: 'green' },
  too_slow: { text: 'Příliš pomalu', color: 'blue' },
};

const TREND_LABELS = {
  speeding_up: { text: 'Zrychlující', color: 'green' },
  steady: { text: 'Stabilní', color: 'default' },
  slowing_down: { text: 'Zpomalující', color: 'orange' },
};

function IntervalSparkline({ intervalsMs, cadenceMs }) {
  if (!intervalsMs || intervalsMs.length < 1) return null;

  // Rep 1 has no preceding interval. Prepend the median so the first rep
  // shows on the X axis instead of being missing from the chart.
  const sortedIntervals = [...intervalsMs].sort((a, b) => a - b);
  const medianMs = sortedIntervals[Math.floor(sortedIntervals.length / 2)];
  const displayValues = [medianMs, ...intervalsMs];

  const data = displayValues.map((v, i) => ({
    rep: i + 1,
    interval: v / 1000,
  }));

  const cadenceSec = cadenceMs != null ? cadenceMs / 1000 : 0;
  const dataMax = data.reduce((m, d) => Math.max(m, d.interval), 0);
  const yMax = Math.max(cadenceSec, dataMax) + 1;

  const annotations =
    cadenceMs != null
      ? [
          {
            type: 'lineY',
            data: [cadenceMs / 1000],
            style: { stroke: '#f5222d', lineDash: [4, 3], lineWidth: 1.5 },
            labelFormatter: () => `${(cadenceMs / 1000).toFixed(0)}s`,
          },
        ]
      : undefined;

  return (
    <div
      aria-label="Průběh tempa"
      style={{ width: '100%', marginTop: 8, pointerEvents: 'none' }}
    >
      <Line
        data={data}
        xField="rep"
        yField="interval"
        height={110}
        point={{ shapeField: 'circle', sizeField: 3 }}
        axis={{ x: { title: false }, y: { title: 'reps' } }}
        scale={{ y: { domain: [0, yMax] } }}
        annotations={annotations}
        tooltip={false}
      />
    </div>
  );
}

function LevelProgressPlot({ levelSets, targetReps }) {
  if (!levelSets || levelSets.length === 0) return null;

  const data = levelSets.map((s, i) => ({
    session: i + 1,
    reps: s.total_reps,
    completed: s.is_completed === true,
  }));

  const dataMax = data.reduce((m, d) => Math.max(m, d.reps), 0);
  const yMax = Math.max(targetReps ?? 0, dataMax) + 1;

  const annotations =
    targetReps != null
      ? [
          {
            type: 'lineY',
            data: [targetReps],
            style: { stroke: '#f5222d', lineDash: [4, 3], lineWidth: 1.5 },
            labelFormatter: () => `cíl ${targetReps}`,
          },
        ]
      : undefined;

  return (
    <div
      aria-label="Průběh úrovně"
      style={{ width: '100%', marginTop: 8, pointerEvents: 'none' }}
    >
      <Line
        data={data}
        xField="session"
        yField="reps"
        height={160}
        point={{
          shapeField: 'circle',
          sizeField: 4,
          style: {
            fill: (d) => (d.completed ? '#52c41a' : '#1677ff'),
            stroke: (d) => (d.completed ? '#52c41a' : '#1677ff'),
          },
        }}
        axis={{ x: { title: false }, y: { title: 'reps' } }}
        scale={{ y: { domain: [0, yMax] } }}
        annotations={annotations}
        tooltip={false}
      />
    </div>
  );
}

function CompletedSetCard({ set, levelInfo, cadenceMs }) {
  const { setNumber, rawEventCount, correctedTotalReps, durationSec, intervalsMs, evaluation } = set;
  const totalReps = correctedTotalReps ?? rawEventCount;
  const targetReps = levelInfo?.target_reps ?? null;
  const isCompleted = evaluation?.is_completed === true;
  const notEnough = !isCompleted && targetReps != null && totalReps < targetReps;
  const avgIntervalSec = evaluation?.avg_interval_sec != null
    ? evaluation.avg_interval_sec
    : intervalsMs.length > 0
      ? intervalsMs.reduce((a, b) => a + b, 0) / intervalsMs.length / 1000
      : null;

  return (
    <Card
      size="small"
      data-testid="evaluation-card"
      title={
        <Space wrap>
          <Text strong>Série {setNumber}:</Text>
          {isCompleted ? (
            <Tag color="green" data-testid="done-badge">Hotovo</Tag>
          ) : (
            <>
              {notEnough && (
                <Tag color="orange" data-testid="not-enough-badge">
                  Málo opakování
                </Tag>
              )}
              {evaluation?.pace_label && evaluation.pace_label !== 'on_track' && (
                <Tag color={PACE_LABELS[evaluation.pace_label]?.color}>
                  {PACE_LABELS[evaluation.pace_label]?.text ?? evaluation.pace_label}
                </Tag>
              )}
              {evaluation?.trend_label && evaluation.trend_label !== 'steady' && (
                <Tag color={TREND_LABELS[evaluation.trend_label]?.color}>
                  {TREND_LABELS[evaluation.trend_label]?.text ?? evaluation.trend_label}
                </Tag>
              )}
            </>
          )}
        </Space>
      }
    >
      <Space direction="vertical" size={12} style={{ width: '100%' }}>
        <Row gutter={16} justify="space-between" style={{ width: '100%' }}>
          <Col>
            <Statistic
              title="Čas"
              value={`${Math.floor(durationSec / 60)}:${String(durationSec % 60).padStart(2, '0')}`}
            />
          </Col>
          <Col>
            <Statistic title="Opakování" value={totalReps} />
          </Col>
          {avgIntervalSec != null && (
            <Col>
              <Statistic
                title="Prům. interval"
                value={`${avgIntervalSec.toFixed(1)} s`}
              />
            </Col>
          )}
        </Row>

        {correctedTotalReps != null && correctedTotalReps !== rawEventCount && (
          <Text data-testid="rep-correction-notice">
            Rozpoznáno {rawEventCount} čísel, odhadnutý počet:{' '}
            <Text strong>{correctedTotalReps}</Text>
          </Text>
        )}

        {evaluation?.recommendation && <Text>{evaluation.recommendation}</Text>}

        {evaluation && (
          <IntervalSparkline intervalsMs={intervalsMs} cadenceMs={cadenceMs} />
        )}
      </Space>
    </Card>
  );
}

function createEvent({ value, token, timestampMs, fallbackId }) {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `${timestampMs}-${fallbackId}`,
    value,
    token,
    timestampMs,
    timestampIso: new Date(timestampMs).toISOString(),
  };
}

function useElapsedTimer(active) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (active) {
      // Read elapsed once to resume from the current position when restarting.
      // It is intentionally omitted from deps to avoid restarting the RAF loop
      // on every tick. eslint-disable-next-line react-hooks/exhaustive-deps
      startRef.current = Date.now() - elapsed * 1000;
      const tick = () => {
        setElapsed(Math.floor((Date.now() - startRef.current) / 1000));
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);
    } else {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    }
    return () => {
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [active]); // eslint-disable-line react-hooks/exhaustive-deps

  const reset = () => {
    setElapsed(0);
    startRef.current = null;
  };

  return { elapsed, reset };
}

function useRestTimer(initialSeconds, active) {
  const [remaining, setRemaining] = useState(initialSeconds);

  useEffect(() => {
    if (!active || remaining <= 0) return undefined;
    const id = setTimeout(() => setRemaining((prev) => prev - 1), 1000);
    return () => clearTimeout(id);
  }, [active, remaining]);

  const reset = (seconds) => setRemaining(seconds);

  return { remaining, reset };
}

export default function ExerciseDetail() {
  const { name: exerciseName } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [userList, setUserList] = useState([]);

  useEffect(() => {
    if (!exerciseName) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    getExerciseDetail(exerciseName)
      .then((data) => {
        if (active) setDetail(data);
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
  }, [exerciseName]);

  useEffect(() => {
    let active = true;
    getUserExercises()
      .then((list) => {
        if (active) setUserList(Array.isArray(list) ? list : []);
      })
      .catch(() => {
        // Not critical — carousel siblings just won't render.
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {error && <Alert type="error" message={error} showIcon />}

      {loading || !detail ? (
        <Card>
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      ) : (
        <ExerciseDetailBody
          detail={detail}
          setDetail={setDetail}
          exerciseName={exerciseName}
          userList={userList}
        />
      )}
    </Space>
  );
}

const CAROUSEL_SLIDE_MS = 260;

const CAROUSEL_CSS = `
@keyframes hc-in-right { from { transform: translateX(60%) scale(0.92); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }
@keyframes hc-in-left  { from { transform: translateX(-60%) scale(0.92); opacity: 0; } to { transform: translateX(0) scale(1); opacity: 1; } }
@keyframes hc-out-left { from { transform: translateX(0) scale(1); opacity: 1; } to { transform: translateX(-60%) scale(0.92); opacity: 0; } }
@keyframes hc-out-right{ from { transform: translateX(0) scale(1); opacity: 1; } to { transform: translateX(60%) scale(0.92); opacity: 0; } }

.hc-side-preview-slot {
  flex: 0 0 5%;
  display: flex;
  align-items: center;
  padding: 0;
}
.hc-side-preview {
  width: 100%;
  height: 80%;
  background: #ffffff;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  opacity: 0.75;
  transition: opacity 200ms ease, transform 200ms ease;
}
.hc-side-preview-left {
  border-radius: 0 10px 10px 0;
  border-left: none;
}
.hc-side-preview-right {
  border-radius: 10px 0 0 10px;
  border-right: none;
}
.hc-side-preview:hover { opacity: 1; }
.hc-side-preview:focus-visible {
  outline: 2px solid #1677ff;
  outline-offset: 2px;
}
`;

function CarouselHeader({ detail, prev, next }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [slideFromInitial] = useState(() => location.state?.slideFrom ?? null);
  const [outgoing, setOutgoing] = useState(null); // 'next' | 'prev' | null
  const touchStartXRef = useRef(null);

  useEffect(() => {
    if (!outgoing) return undefined;
    const target = outgoing === 'next' ? next : prev;
    if (!target) {
      setOutgoing(null);
      return undefined;
    }
    const slideFrom = outgoing === 'next' ? 'right' : 'left';
    const id = setTimeout(() => {
      navigate(`/exercises/${target.exercise_name}`, { state: { slideFrom } });
    }, CAROUSEL_SLIDE_MS);
    return () => clearTimeout(id);
  }, [outgoing, next, prev, navigate]);

  const goTo = (dir) => {
    if (outgoing) return;
    const target = dir === 'next' ? next : prev;
    if (!target) return;
    setOutgoing(dir);
  };

  const handleTouchStart = (e) => {
    touchStartXRef.current = e.touches[0]?.clientX ?? null;
  };
  const handleTouchEnd = (e) => {
    const startX = touchStartXRef.current;
    touchStartXRef.current = null;
    if (startX == null) return;
    const dx = (e.changedTouches[0]?.clientX ?? startX) - startX;
    if (dx > 50) goTo('prev');
    else if (dx < -50) goTo('next');
  };

  let animation;
  if (outgoing === 'next') animation = `hc-out-left ${CAROUSEL_SLIDE_MS}ms ease forwards`;
  else if (outgoing === 'prev') animation = `hc-out-right ${CAROUSEL_SLIDE_MS}ms ease forwards`;
  else if (slideFromInitial === 'right') animation = `hc-in-right ${CAROUSEL_SLIDE_MS}ms ease`;
  else if (slideFromInitial === 'left') animation = `hc-in-left ${CAROUSEL_SLIDE_MS}ms ease`;

  return (
    <div style={{ overflow: 'hidden', marginLeft: -32, marginRight: -32 }}>
      <div
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        style={{
          display: 'flex',
          alignItems: 'stretch',
          gap: 12,
          touchAction: 'pan-y',
          paddingLeft: 16,
          paddingRight: 16,
        }}
      >
        <style>{CAROUSEL_CSS}</style>
        <CarouselSidePreview item={prev} side="left" onClick={() => goTo('prev')} />
        <div
          style={{
            flex: '1 1 auto',
            minWidth: 0,
            animation,
            willChange: animation ? 'transform, opacity' : undefined,
          }}
        >
          <Card>
            <div style={{ textAlign: 'center' }}>
              <Title level={2} style={{ margin: 0 }}>
                {detail.title}
              </Title>
              {detail.english_name && (
                <Text type="secondary">{detail.english_name}</Text>
              )}
              <div style={{ marginTop: 8 }}>
                <Space size={4} wrap style={{ justifyContent: 'center' }}>
                  <Tag color="blue">{detail.family}</Tag>
                  <Tag>Level {detail.level}</Tag>
                </Space>
              </div>
            </div>
          </Card>
        </div>
        <CarouselSidePreview item={next} side="right" onClick={() => goTo('next')} />
      </div>
    </div>
  );
}

function CarouselSidePreview({ item, side, onClick }) {
  const sideClass = side === 'left' ? 'hc-side-preview-left' : 'hc-side-preview-right';
  const inner = item ? (
    <button
      type="button"
      onClick={onClick}
      aria-label={`${side === 'left' ? 'Předchozí' : 'Další'} cvik: ${item.title ?? item.exercise_name}`}
      data-testid={`carousel-${side === 'left' ? 'prev' : 'next'}`}
      className={`hc-side-preview ${sideClass}`}
    />
  ) : (
    <div
      className={`hc-side-preview ${sideClass}`}
      aria-hidden
      style={{ visibility: 'hidden' }}
    />
  );
  return <div className="hc-side-preview-slot">{inner}</div>;
}

function ExerciseDetailBody({ detail, setDetail, exerciseName, userList }) {
  // ── Workout session state ─────────────────────────────────────────────────
  const levelInfo = detail.user_level ?? null;

  const { prevExercise, nextExercise } = useMemo(() => {
    const idx = userList.findIndex((e) => e.exercise_name === exerciseName);
    const len = userList.length;
    if (idx < 0 || len < 2) return { prevExercise: null, nextExercise: null };
    return {
      prevExercise: userList[(idx - 1 + len) % len],
      nextExercise: userList[(idx + 1) % len],
    };
  }, [userList, exerciseName]);
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState(null);
  const [setNumber, setSetNumber] = useState(1);
  const [sessionState, setSessionState] = useState('idle');
  const [events, setEvents] = useState([]);
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [restActive, setRestActive] = useState(false);
  const [micError, setMicError] = useState('');
  // Each entry: { setNumber, rawEventCount, correctedTotalReps, durationSec,
  // intervalsMs, evaluation }. Appended in stopSet, never cleared during the
  // session so the user can scroll back through every series they finished.
  const [completedSets, setCompletedSets] = useState([]);
  const [hydrated, setHydrated] = useState(false);

  // First-paint rehydration: when the user returns to the page mid-day,
  // populate completedSets from the server's today_sets so they can keep
  // adding series. Bounded to once because stopSet refetches detail.
  useEffect(() => {
    if (hydrated) return;
    if (!detail.user_level) return;
    const today = detail.user_level.today_sets ?? [];
    if (today.length > 0) {
      setCompletedSets(
        today.map((t) => ({
          setNumber: t.set_number,
          rawEventCount: t.total_reps,
          correctedTotalReps: t.total_reps,
          durationSec: t.total_duration_sec,
          intervalsMs: t.intervals_ms ?? [],
          evaluation: t.evaluation ?? null,
        })),
      );
      setSetNumber(today.length + 1);
    }
    setHydrated(true);
  }, [detail.user_level, hydrated]);

  const processedTokenCountRef = useRef(0);
  const previousEventRef = useRef(null);
  const wakeLockRef = useRef(null);
  const fallbackIdRef = useRef(0);

  const {
    transcript,
    resetTranscript,
    browserSupportsSpeechRecognition,
    isMicrophoneAvailable,
  } = useSpeechRecognition();

  const restSeconds = levelInfo?.rest_seconds ?? 60;
  const { elapsed, reset: resetElapsed } = useElapsedTimer(sessionState === 'listening');
  const { remaining: restRemaining, reset: resetRest } = useRestTimer(restSeconds, restActive);

  // Voice transcript processing
  useEffect(() => {
    if (sessionState !== 'listening') return;
    if (!transcript) return;

    const tokens = tokenizeTranscript(transcript);
    if (processedTokenCountRef.current > tokens.length) {
      processedTokenCountRef.current = 0;
    }

    const newTokens = tokens.slice(processedTokenCountRef.current);
    let idx = 0;
    const accepted = [];

    while (idx < newTokens.length) {
      const parsed = parseNumberFromTokens(newTokens, idx);
      if (!parsed) {
        idx += 1;
        continue;
      }
      const timestampMs = Date.now();
      fallbackIdRef.current += 1;
      const event = createEvent({
        value: parsed.value,
        token: parsed.token,
        timestampMs,
        fallbackId: fallbackIdRef.current,
      });
      if (shouldAcceptEvent(event, previousEventRef.current)) {
        accepted.push(event);
        previousEventRef.current = event;
      }
      idx += parsed.consumed;
    }

    if (accepted.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEvents((prev) => [...prev, ...accepted]);
    }

    processedTokenCountRef.current = tokens.length;
    if (tokens.length > 50) {
      resetTranscript();
      processedTokenCountRef.current = 0;
    }
  }, [transcript, resetTranscript, sessionState]);

  // Cleanup wake lock on unmount
  useEffect(
    () => () => {
      if (wakeLockRef.current) {
        wakeLockRef.current.release().catch(() => {});
        wakeLockRef.current = null;
      }
    },
    [],
  );

  const requestWakeLock = async () => {
    try {
      if ('wakeLock' in navigator) {
        wakeLockRef.current = await navigator.wakeLock.request('screen');
      }
    } catch {
      // wake lock optional, not critical
    }
  };

  const releaseWakeLock = async () => {
    if (wakeLockRef.current) {
      await wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
    }
  };

  const handleAddExercise = async () => {
    setAddError(null);
    setAdding(true);
    try {
      await addUserExercise(exerciseName);
      const fresh = await getExerciseDetail(exerciseName);
      setDetail(fresh);
    } catch (err) {
      console.error('Failed to add exercise:', err);
      const detail = err?.response?.data?.detail;
      setAddError(detail || 'Cvik se nepodařilo přidat.');
    } finally {
      setAdding(false);
    }
  };

  const startSet = async () => {
    setMicError('');
    setSaveError(null);
    setEvents([]);
    processedTokenCountRef.current = 0;
    previousEventRef.current = null;
    resetElapsed();
    resetTranscript();
    const startedAt = new Date().toISOString();
    setSessionStartedAt(startedAt);
    setSessionState('listening');
    setRestActive(false);

    try {
      await SpeechRecognition.startListening({ continuous: true, language: 'cs-CZ' });
      await requestWakeLock();
    } catch {
      setSessionState('idle');
      setMicError('Nepodařilo se spustit naslouchání. Zkontrolujte oprávnění mikrofonu.');
    }
  };

  const stopSet = async () => {
    await SpeechRecognition.stopListening();
    await releaseWakeLock();
    setSessionState('stopped');
    processedTokenCountRef.current = 0;
    resetTranscript();

    setSaving(true);
    setSaveError(null);

    const currentEvents = events;
    const stats = computeSessionStats(currentEvents);
    const payload = {
      exercise_id: exerciseName,
      started_at: sessionStartedAt,
      total_duration_sec: elapsed,
      total_reps: stats.count,
      counting: currentEvents.map(({ value, token, timestampMs, timestampIso }) => ({
        value,
        token,
        timestamp_ms: timestampMs,
        timestamp_iso: timestampIso,
      })),
      set_number: setNumber,
    };

    let evaluation = null;
    let correctedTotalReps = null;
    try {
      const result = await putExerciseSeries(payload);
      if (result?.evaluation != null) evaluation = result.evaluation;
      if (result?.total_reps != null) correctedTotalReps = result.total_reps;
      const freshDetail = await getExerciseDetail(exerciseName);
      setDetail(freshDetail);
    } catch {
      setSaveError('Sérii se nepodařilo uložit. Data jsou zachována lokálně.');
    } finally {
      setSaving(false);
    }

    setCompletedSets((prev) => [
      ...prev,
      {
        setNumber,
        rawEventCount: currentEvents.length,
        correctedTotalReps,
        durationSec: elapsed,
        intervalsMs: stats.intervalsMs,
        evaluation,
      },
    ]);

    resetRest(restSeconds);
    if ((levelInfo?.target_sets ?? 1) > 1) {
      setRestActive(true);
    }
  };

  const startNextSet = () => {
    setSetNumber((prev) => prev + 1);
    setRestActive(false);
    setSessionState('idle');
  };

  const startNextSerieNow = async () => {
    setSetNumber((prev) => prev + 1);
    setRestActive(false);
    await startSet();
  };

  const liveCount = events.length;
  const currentNumber = events.length > 0 ? events[events.length - 1].value : null;

  const microphoneError =
    sessionState === 'listening' && isMicrophoneAvailable === false
      ? 'Mikrofon není dostupný. Povolte oprávnění mikrofonu v prohlížeči.'
      : '';
  const displayError = micError || microphoneError;

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* ── Compact header: carousel with prev/next exercise previews ──── */}
      <CarouselHeader detail={detail} prev={prevExercise} next={nextExercise} />

      {/* ── Personal goal: Tvoje úroveň ──────────────────────────────────── */}
      {levelInfo && (
        <Card size="small" title="Tvoje úroveň">
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={LEVEL_COLORS[levelInfo.level]}>
                {LEVEL_LABELS[levelInfo.level] ?? levelInfo.level}
              </Tag>
              {levelInfo.target_reps !== null && levelInfo.target_sets !== null && (
                <Text type="secondary">
                  Cíl: {levelInfo.target_sets} × {levelInfo.target_reps} opakování
                </Text>
              )}
            </Space>
            {levelInfo.last_best_reps !== null && (
              <Text>
                Naposledy nejlepší výkon: <Text strong>{levelInfo.last_best_reps}</Text> opakování
              </Text>
            )}
            {levelInfo.target_reps !== null && (
              <Text type="secondary">
                🎯 Dnes překonej: <Text strong>{levelInfo.target_reps}</Text> opakování
              </Text>
            )}
            <LevelProgressPlot
              levelSets={levelInfo.level_sets}
              targetReps={levelInfo.target_reps}
            />
          </Space>
        </Card>
      )}

      {/* ── Add-to-list CTA when the user hasn't added the exercise ─────── */}
      {!levelInfo && (
        <Card
          size="small"
          data-testid="add-cta"
          style={{ borderColor: '#91caff', background: '#e6f4ff' }}
        >
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Text>
              Tento cvik zatím nemáš v seznamu. Přidej ho a začni s ním
              trénovat.
            </Text>
            {addError && <Alert type="error" showIcon message={addError} />}
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              loading={adding}
              onClick={handleAddExercise}
            >
              Přidat do mých cviků
            </Button>
          </Space>
        </Card>
      )}

      {/* ── Exercise counter: série tracker (added users only) ──────────── */}
      {levelInfo && (
      <Card
        size="small"
        title={
          <Space>
            <Text strong>Voice counting</Text>
            {sessionState === 'listening' && (
              <Tag color="green" data-testid="listening-badge">
                Naslouchám
              </Tag>
            )}
          </Space>
        }
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          {!browserSupportsSpeechRecognition && (
            <Alert
              type="error"
              showIcon
              message="Tento prohlížeč nepodporuje rozpoznávání řeči."
            />
          )}

          {displayError && <Alert type="error" showIcon message={displayError} />}
          {saveError && <Alert type="warning" showIcon message={saveError} />}

          {/* Live stats – only shown while the set is running */}
          {sessionState === 'listening' && (
            <Row gutter={16} data-testid="live-stats">
              <Col>
                <Statistic title="Opakování" value={liveCount} />
              </Col>
              <Col>
                <Statistic title="Aktuální číslo" value={currentNumber ?? '---'} />
              </Col>
              <Col>
                <Statistic
                  title="Čas"
                  value={`${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`}
                />
              </Col>
            </Row>
          )}

          {/* Controls */}
          <Space wrap>
            {sessionState === 'idle' && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={startSet}
                disabled={!browserSupportsSpeechRecognition}
                size="large"
              >
                Start série
              </Button>
            )}

            {sessionState === 'listening' && (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={stopSet}
                size="large"
              >
                Konec série
              </Button>
            )}

            {sessionState === 'stopped' && !restActive && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={startNextSerieNow}
                loading={saving}
                disabled={!browserSupportsSpeechRecognition}
                size="large"
              >
                Start série
              </Button>
            )}
          </Space>

          {/* All completed sets, newest first (e.g. 3, 2, 1) */}
          {completedSets
            .slice()
            .reverse()
            .map((set) => (
              <CompletedSetCard
                key={set.setNumber}
                set={set}
                levelInfo={levelInfo}
                cadenceMs={detail?.cadence?.total_rep_time_sec != null
                  ? detail.cadence.total_rep_time_sec * 1000
                  : null}
              />
            ))}

          {/* Rest timer – only when target_sets > 1 */}
          {levelInfo?.target_sets > 1 && restActive && restRemaining > 0 && (
            <Card
              size="small"
              style={{ background: '#f6ffed', borderColor: '#b7eb8f' }}
              data-testid="rest-timer"
            >
              <Space direction="vertical" size={8} style={{ width: '100%' }}>
                <Space>
                  <CheckCircleOutlined style={{ color: '#52c41a' }} />
                  <Text strong style={{ color: '#389e0d' }}>
                    Výborně! Odpočinek před další sérií
                  </Text>
                </Space>
                <Statistic
                  title="Zbývá odpočinku"
                  value={`${Math.floor(restRemaining / 60)}:${String(restRemaining % 60).padStart(2, '0')}`}
                />
                <Button onClick={startNextSerieNow}>Přeskočit odpočinek → Start série</Button>
              </Space>
            </Card>
          )}

          {levelInfo?.target_sets > 1 && restActive && restRemaining <= 0 && (
            <Alert
              type="success"
              showIcon
              message="Odpočinek skončil!"
              action={
                <Button size="small" type="primary" onClick={startNextSerieNow}>
                  Start série
                </Button>
              }
            />
          )}
        </Space>
      </Card>
      )}

      {/* ── Description ──────────────────────────────────────────────────── */}
      {detail.description && (
        <Card size="small">
          <ReactMarkdown>{detail.description}</ReactMarkdown>
        </Card>
      )}

      {/* ── Static detail cards ──────────────────────────────────────────── */}
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

      <MediaSection media={detail.media} exerciseName={detail.title} />

      {/* ── Difficulty tabs + muscle map ─────────────────────────────────── */}
      {detail.progression_goals && (
        <ProgressionAndMuscleCard detail={detail} />
      )}

    </Space>
  );
}

/**
 * Renders the `media` dict (free-form key → URL / data URL).
 *
 *  - **v1 backward compat**: if `media` has `youtube_tutorial` (and optionally
 *    `thumbnail_url`), renders a single linked thumbnail card.
 *  - **v2 (or any other shape)**: renders every entry as an image in an
 *    `Image.PreviewGroup` (click to zoom).  Caption uses the dict key.
 *
 * `data:` URIs and HTTP image URLs are both treated as renderable images.
 * Unrecognised string values are skipped.
 */
function MediaSection({ media, exerciseName }) {
  if (!media || typeof media !== 'object' || Object.keys(media).length === 0) {
    return null;
  }

  if (media.youtube_tutorial) {
    return (
      <Card size="small" title="Video">
        <a href={media.youtube_tutorial} target="_blank" rel="noreferrer">
          {media.thumbnail_url ? (
            <img
              src={media.thumbnail_url}
              alt={exerciseName}
              style={{ display: 'block', width: '100%', height: 'auto', borderRadius: 8 }}
            />
          ) : (
            <span>YouTube tutorial</span>
          )}
        </a>
      </Card>
    );
  }

  const items = Object.entries(media).filter(
    ([, value]) =>
      typeof value === 'string' &&
      (value.startsWith('data:image/') ||
        /^https?:\/\/.+\.(jpe?g|png|webp|gif|svg)(\?|$)/i.test(value)),
  );
  if (items.length === 0) return null;

  return (
    <Card size="small" title="Obrázky">
      <Image.PreviewGroup>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {items.map(([key, url]) => (
            <div key={key} style={{ textAlign: 'center', width: '100%' }}>
              <Image
                src={url}
                alt={key}
                styles={{ root: { width: '100%' } }}
                style={{ borderRadius: 8 }}
              />
              <Text
                type="secondary"
                style={{ fontSize: 12, display: 'block', marginTop: 4 }}
              >
                {key}
              </Text>
            </div>
          ))}
        </Space>
      </Image.PreviewGroup>
    </Card>
  );
}

/**
 * Card containing:
 *  1. Tabs: Začátečník | Středně pokročilý | Mistr
 *     Each tab shows sets × reps and, when available, the total "Přemístěná
 *     zátěž" in kg (= weight_kg × reps × level_coefficient).
 *  2. Coach note (shared below all tabs)
 *  3. Divider
 *  4. Muscle map with toggle: % Zapojení ↔ Přemístěná zátěž (kg)
 *
 * The muscle load data is pre-computed by the backend and embedded directly
 * in `detail.muscle_load_by_difficulty`.  No separate API call is made.
 * The toggle is disabled when the backend could not compute the load (user not
 * authenticated or has no weight_kg in their profile).
 */
function ProgressionAndMuscleCard({ detail }) {
  const [activeTab, setActiveTab] = useState('beginner');
  const [mapMode, setMapMode] = useState('percent'); // 'percent' | 'load'

  const loadByDifficulty = detail.muscle_load_by_difficulty; // null or { beginner, intermediate, mastery }
  const hasLoadData = loadByDifficulty != null;

  // Derive what to show on the muscle map.
  const displayEngagement = (() => {
    if (mapMode === 'load' && hasLoadData) {
      const tierData = loadByDifficulty[activeTab] ?? {};
      const entries = Object.entries(tierData);
      if (entries.length === 0) return detail.muscle_engagement_percent ?? {};
      // Normalise to 0–100 so ExerciseMuscleMap can colour muscles by relative
      // intensity without any internal changes.
      const maxLoad = Math.max(...entries.map(([, m]) => m.muscle_load), 1);
      return Object.fromEntries(
        entries.map(([muscle, { muscle_load }]) => [
          muscle,
          Math.round((muscle_load / maxLoad) * 100),
        ]),
      );
    }
    return detail.muscle_engagement_percent ?? {};
  })();

  // Min/max per-muscle load (kg) for the active tier — used by the legend.
  const activeLoadRange = useMemo(() => {
    if (!hasLoadData) return null;
    const tierData = loadByDifficulty[activeTab] ?? {};
    const loads = Object.values(tierData).map((m) => m.muscle_load);
    if (loads.length === 0) return null;
    return { min: Math.min(...loads), max: Math.max(...loads) };
  }, [hasLoadData, loadByDifficulty, activeTab]);

  const tabItems = DIFFICULTIES.map(({ key, label }) => {
    const goal = detail.progression_goals?.[key];

    return {
      key,
      label,
      children: goal ? (
        <div style={{ textAlign: 'center', padding: '16px 0 8px' }}>
          <Title level={2} style={{ margin: 0, lineHeight: 1 }}>
            {goal.sets} × {goal.reps}
          </Title>
        </div>
      ) : (
        <Text type="secondary">Žádné cíle pro tuto úroveň.</Text>
      ),
    };
  });

  return (
    <Card>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        style={{ marginTop: 4 }}
      />

      {detail.progression_goals?.coach_note && (
        <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
          {detail.progression_goals.coach_note}
        </Paragraph>
      )}

      <Divider />

      {/* ── Muscle map section ──────────────────────────────────────────── */}
      {!hasLoadData && (
        <Alert
          type="info"
          showIcon
          message="Přihlaste se a vyplňte hmotnost v profilu pro výpočet přemístěné zátěže."
          style={{ marginBottom: 12 }}
        />
      )}

      <ExerciseMuscleMap engagement={displayEngagement} mode={mapMode} loadRange={activeLoadRange} />

      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 12 }}>
        <Segmented
          options={[
            { label: '% Zapojení', value: 'percent' },
            { label: 'Přemístěná zátěž (kg)', value: 'load', disabled: !hasLoadData },
          ]}
          value={mapMode}
          onChange={setMapMode}
        />
      </div>
    </Card>
  );
}
