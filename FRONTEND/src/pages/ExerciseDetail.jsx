import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
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
import ExerciseMuscleMap from '../components/ExerciseMuscleMap.jsx';
import { fetchExerciseDetail, postWorkoutSession } from '../api/client.js';
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
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    setLoading(true);
    setError(null);
    fetchExerciseDetail(id)
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
  }, [id]);

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Button
        type="link"
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/exercises')}
        style={{ padding: 0 }}
      >
        Zpět na seznam
      </Button>

      {error && <Alert type="error" message={error} showIcon />}

      {loading || !detail ? (
        <Card>
          <Skeleton active paragraph={{ rows: 10 }} />
        </Card>
      ) : (
        <ExerciseDetailBody
          detail={detail}
          setDetail={setDetail}
          navigate={navigate}
          id={id}
        />
      )}
    </Space>
  );
}

function ExerciseDetailBody({ detail, setDetail, navigate, id }) {
  // ── Workout session state ─────────────────────────────────────────────────
  const levelInfo = detail.user_level ?? null;
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

    setSaving(true);
    setSaveError(null);

    const currentEvents = events;
    const stats = computeSessionStats(currentEvents);
    const payload = {
      exercise_id: id,
      exercise_name: detail?.name ?? id,
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
      const freshDetail = await fetchExerciseDetail(id);
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

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {/* ── Compact header: name, tags ───────────────────────────────────── */}
      <Card>
        <Space direction="vertical" size={4}>
          <Title level={2} style={{ margin: 0 }}>
            {detail.name}
          </Title>
          {detail.english_name && (
            <Text type="secondary">{detail.english_name}</Text>
          )}
          <Space size={4} wrap>
            <Tag color="blue">{detail.family}</Tag>
            <Tag>Level {detail.level}</Tag>
          </Space>
        </Space>
      </Card>

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
          </Space>
        </Card>
      )}

      {/* ── Exercise counter: série tracker ──────────────────────────────── */}
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

      {/* ── Description ──────────────────────────────────────────────────── */}
      {detail.description && (
        <Card size="small">
          <Paragraph style={{ margin: 0 }}>{detail.description}</Paragraph>
        </Card>
      )}

      {/* ── Static detail cards ──────────────────────────────────────────── */}
      {detail.instructions?.length > 0 && (
        <Card size="small" title="Jak cvičit">
          <ol style={{ margin: 0, paddingLeft: 20 }}>
            {detail.instructions.map((step, idx) => (
              <li key={idx} style={{ marginBottom: 4 }}>
                {step}
              </li>
            ))}
          </ol>
        </Card>
      )}

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

      <MediaSection media={detail.media} exerciseName={detail.name} />

      {/* ── Difficulty tabs + muscle map ─────────────────────────────────── */}
      {detail.progression_goals && (
        <ProgressionAndMuscleCard detail={detail} />
      )}

      {detail.next_exercise_id ? (
        <Alert
          type="info"
          showIcon
          message={
            <Space>
              <Text>Další úroveň:</Text>
              <Button
                type="link"
                onClick={() => navigate(`/exercises/${detail.next_exercise_id}`)}
                style={{ padding: 0 }}
              >
                {detail.next_exercise_name}
              </Button>
            </Space>
          }
        />
      ) : (
        <Alert type="success" showIcon message="Nejvyšší úroveň této rodiny" />
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
