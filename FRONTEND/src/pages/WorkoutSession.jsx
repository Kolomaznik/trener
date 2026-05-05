import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Skeleton,
  Space,
  Statistic,
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
import {
  computeSessionStats,
  parseNumberFromTokens,
  shouldAcceptEvent,
  tokenizeTranscript,
} from '../features/voiceCounting.js';
import { getExerciseDetail } from '../api/exercises/get_detail.js';
import { postWorkoutSession } from '../api/workout-sessions/post.js';
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';

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

export default function WorkoutSession() {
  const { id: exerciseId } = useParams();
  const navigate = useNavigate();

  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(true);
  const [detailError, setDetailError] = useState(null);

  const [setNumber, setSetNumber] = useState(1);
  const [sessionState, setSessionState] = useState('idle');
  const [events, setEvents] = useState([]);
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [restActive, setRestActive] = useState(false);
  const [micError, setMicError] = useState('');

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

  const restSeconds = detail?.user_level?.rest_seconds ?? 60;
  const { elapsed, reset: resetElapsed } = useElapsedTimer(sessionState === 'listening');
  const { remaining: restRemaining, reset: resetRest } = useRestTimer(restSeconds, restActive);

  // Load exercise detail (includes user_level)
  useEffect(() => {
    if (!exerciseId) return undefined;
    let active = true;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDetailLoading(true);
    setDetailError(null);

    getExerciseDetail(exerciseId)
      .then((det) => {
        if (!active) return;
        setDetail(det);
      })
      .catch((err) => {
        if (!active) return;
        if (err?.response?.status === 404) {
          setDetailError('Cvik nebyl nalezen.');
        } else {
          setDetailError('Nepodařilo se načíst data cviku.');
        }
      })
      .finally(() => {
        if (active) setDetailLoading(false);
      });

    return () => {
      active = false;
    };
  }, [exerciseId]);

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
    const endedAt = new Date().toISOString();
    setSessionState('stopped');
    processedTokenCountRef.current = 0;
    resetTranscript();

    // Save session asynchronously
    setSaving(true);
    setSaveError(null);

    const currentEvents = events;
    const stats = computeSessionStats(currentEvents);
    const payload = {
      exercise_id: exerciseId,
      exercise_name: detail?.name ?? exerciseId,
      started_at: sessionStartedAt,
      ended_at: endedAt,
      total_duration_sec: elapsed,
      total_reps: stats.count,
      events: currentEvents.map(({ value, token, timestampMs, timestampIso }) => ({
        value,
        token,
        timestamp_ms: timestampMs,
        timestamp_iso: timestampIso,
      })),
      set_number: setNumber,
    };

    try {
      await postWorkoutSession(payload);
      // Re-fetch detail to get refreshed user_level
      const freshDetail = await getExerciseDetail(exerciseId);
      setDetail(freshDetail);
    } catch {
      setSaveError('Sérii se nepodařilo uložit. Data jsou zachována lokálně.');
    } finally {
      setSaving(false);
    }

    resetRest(restSeconds);
    setRestActive(true);
  };

  const startNextSet = () => {
    setSetNumber((prev) => prev + 1);
    setRestActive(false);
    setSessionState('idle');
  };

  const liveCount = events.length;
  const currentNumber = events.length > 0 ? events[events.length - 1].value : null;
  const summary = useMemo(() => computeSessionStats(events), [events]);

  const microphoneError =
    sessionState === 'listening' && isMicrophoneAvailable === false
      ? 'Mikrofon není dostupný. Povolte oprávnění mikrofonu v prohlížeči.'
      : '';
  const displayError = micError || microphoneError;

  if (detailLoading) {
    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </Space>
    );
  }

  if (detailError) {
    return (
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Button
          type="link"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate(`/exercises/${exerciseId}`)}
          style={{ padding: 0 }}
        >
          Zpět na cvik
        </Button>
        <Alert type="error" message={detailError} showIcon />
      </Space>
    );
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(`/exercises/${exerciseId}`)}
        style={{ padding: 0 }}
      >
        Zpět na cvik
      </Button>

      {/* Exercise info */}
      {detail && (
        <Card>
          <Space direction="vertical" size={4}>
            <Title level={3} style={{ margin: 0 }}>
              {detail.name}
            </Title>
            {detail.english_name && <Text type="secondary">{detail.english_name}</Text>}
            <Space size={4} wrap>
              <Tag color="blue">{detail.family}</Tag>
              <Tag>Level {detail.level}</Tag>
            </Space>
          </Space>
          <Paragraph style={{ marginTop: 8, marginBottom: 0 }}>{detail.description}</Paragraph>
        </Card>
      )}

      {/* User level and motivation */}
      {detail?.user_level && (
        <Card size="small" title="Tvoje úroveň">
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={LEVEL_COLORS[detail.user_level.level]}>
                {LEVEL_LABELS[detail.user_level.level] ?? detail.user_level.level}
              </Tag>
              {detail.user_level.target_reps != null && detail.user_level.target_sets != null && (
                <Text type="secondary">
                  Cíl: {detail.user_level.target_sets} × {detail.user_level.target_reps} opakování
                </Text>
              )}
            </Space>
            {detail.user_level.last_best_reps != null && (
              <Text>
                Naposledy nejlepší výkon: <Text strong>{detail.user_level.last_best_reps}</Text> opakování
              </Text>
            )}
            {detail.user_level.target_reps != null && (
              <Text type="secondary">
                🎯 Dnes překonej: <Text strong>{detail.user_level.target_reps}</Text> opakování
              </Text>
            )}
          </Space>
        </Card>
      )}

      {/* Set header */}
      <Card
        size="small"
        title={
          <Space>
            <Text strong>Série {setNumber}</Text>
            {sessionState === 'listening' && (
              <Tag color="green" data-testid="listening-badge">
                Naslouchám
              </Tag>
            )}
            {sessionState === 'stopped' && (
              <Tag color="blue" data-testid="done-badge">
                Hotovo
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

          {/* Live stats */}
          <Row gutter={16}>
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
                onClick={startNextSet}
                loading={saving}
                size="large"
              >
                Další série
              </Button>
            )}
          </Space>

          {/* Set result summary */}
          {sessionState === 'stopped' && (
            <Descriptions size="small" bordered column={1}>
              <Descriptions.Item label="Opakování">{summary.count}</Descriptions.Item>
              <Descriptions.Item label="Čas">
                {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, '0')}
              </Descriptions.Item>
              {summary.intervalsMs.length > 0 && (
                <Descriptions.Item label="Prům. interval">
                  {(
                    summary.intervalsMs.reduce((a, b) => a + b, 0) /
                    summary.intervalsMs.length /
                    1000
                  ).toFixed(1)}{' '}
                  s
                </Descriptions.Item>
              )}
            </Descriptions>
          )}

          {/* Rest timer */}
          {restActive && restRemaining > 0 && (
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
                <Button onClick={startNextSet}>Přeskočit odpočinek → Další série</Button>
              </Space>
            </Card>
          )}

          {restActive && restRemaining <= 0 && (
            <Alert
              type="success"
              showIcon
              message="Odpočinek skončil!"
              action={
                <Button size="small" type="primary" onClick={startNextSet}>
                  Další série
                </Button>
              }
            />
          )}
        </Space>
      </Card>

      {/* Muscle map + cadence info */}
      {detail && (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card size="small" title="Zapojené svaly">
              <ExerciseMuscleMap engagement={detail.muscle_engagement_percent ?? {}} />
            </Card>
          </Col>
          {detail.cadence && (
            <Col xs={24} md={12}>
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
            </Col>
          )}
        </Row>
      )}

      {/* End workout */}
      <Button
        type="default"
        onClick={() => navigate(`/exercises/${exerciseId}`)}
        style={{ width: '100%' }}
      >
        Ukončit trénink
      </Button>
    </Space>
  );
}
