import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  List,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';
import {
  computeSessionStats,
  parseNumberFromTokens,
  shouldAcceptEvent,
  tokenizeTranscript,
} from '../features/voiceCounting.js';

const { Title, Paragraph, Text } = Typography;

function createEvent({ value, token, timestampMs, fallbackId }) {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `${timestampMs}-${fallbackId}`,
    value,
    token,
    timestampMs,
    timestampIso: new Date(timestampMs).toISOString(),
    timeLabel: new Date(timestampMs).toLocaleTimeString('cs-CZ'),
  };
}

function isHttpsRequired() {
  const hostname = window.location.hostname;
  const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1';
  return !isLocalhost && window.location.protocol !== 'https:';
}

export default function VoiceCounting() {
  const [sessionState, setSessionState] = useState('idle');
  const [events, setEvents] = useState([]);
  const [sessionStartedAt, setSessionStartedAt] = useState(null);
  const [sessionEndedAt, setSessionEndedAt] = useState(null);
  const [sessionSummary, setSessionSummary] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const processedTokenCountRef = useRef(0);
  const previousEventRef = useRef(null);
  const wakeLockRef = useRef(null);
  const fallbackEventIdRef = useRef(0);

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition,
    isMicrophoneAvailable,
  } = useSpeechRecognition();

  const micStatus = listening ? 'aktivní' : 'neaktivní';
  const httpsWarningVisible = typeof window !== 'undefined' && isHttpsRequired();

  const releaseWakeLock = async () => {
    if (wakeLockRef.current) {
      await wakeLockRef.current.release();
      wakeLockRef.current = null;
    }
  };

  const requestWakeLock = async () => {
    try {
      if (!('wakeLock' in navigator)) return;
      wakeLockRef.current = await navigator.wakeLock.request('screen');
    } catch (error) {
      console.error('Wake lock request failed:', error);
      setErrorMessage('Nepodařilo se aktivovat wake lock. Naslouchání může být při uspání přerušeno.');
    }
  };

  const resetSession = async () => {
    await SpeechRecognition.stopListening();
    await releaseWakeLock();
    setSessionState('idle');
    setEvents([]);
    setSessionStartedAt(null);
    setSessionEndedAt(null);
    setSessionSummary(null);
    setErrorMessage('');
    processedTokenCountRef.current = 0;
    previousEventRef.current = null;
    resetTranscript();
  };

  const startSession = async () => {
    setErrorMessage('');
    const startedAt = new Date().toISOString();
    setSessionState('listening');
    setSessionStartedAt(startedAt);
    setSessionEndedAt(null);
    setSessionSummary(null);
    processedTokenCountRef.current = 0;
    previousEventRef.current = null;
    resetTranscript();

    try {
      await SpeechRecognition.startListening({ continuous: true, language: 'cs-CZ' });
      await requestWakeLock();
    } catch (error) {
      console.error('Start listening failed:', error);
      setSessionState('idle');
      setErrorMessage('Nepodařilo se spustit naslouchání. Zkontrolujte oprávnění mikrofonu.');
    }
  };

  const stopSession = async () => {
    await SpeechRecognition.stopListening();
    await releaseWakeLock();
    const endedAt = new Date().toISOString();
    setSessionState('stopped');
    setSessionEndedAt(endedAt);
    setSessionSummary(computeSessionStats(events));
    processedTokenCountRef.current = 0;
    resetTranscript();
  };

  useEffect(() => {
    if (sessionState !== 'listening') return;
    if (!transcript) return;

    const tokens = tokenizeTranscript(transcript);
    if (processedTokenCountRef.current > tokens.length) {
      processedTokenCountRef.current = 0;
    }

    const newTokens = tokens.slice(processedTokenCountRef.current);
    let index = 0;
    const acceptedEvents = [];

    while (index < newTokens.length) {
      const parsed = parseNumberFromTokens(newTokens, index);
      if (!parsed) {
        index += 1;
        continue;
      }

      const timestampMs = Date.now();
      fallbackEventIdRef.current += 1;
      const event = createEvent({
        value: parsed.value,
        token: parsed.token,
        timestampMs,
        fallbackId: fallbackEventIdRef.current,
      });

      if (shouldAcceptEvent(event, previousEventRef.current)) {
        acceptedEvents.push(event);
        previousEventRef.current = event;
      }

      index += parsed.consumed;
    }

    if (acceptedEvents.length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setEvents((prev) => [...prev, ...acceptedEvents]);
    }

    processedTokenCountRef.current = tokens.length;
    if (tokens.length > 50) {
      resetTranscript();
      processedTokenCountRef.current = 0;
    }
  }, [transcript, resetTranscript, sessionState]);

  useEffect(() => {
    return () => {
      releaseWakeLock();
    };
  }, []);

  const liveCount = events.length;
  const currentNumber = events.length > 0 ? events[events.length - 1].value : null;
  const summary = useMemo(() => sessionSummary ?? computeSessionStats(events), [events, sessionSummary]);
  const microphoneError =
    sessionState === 'listening' && isMicrophoneAvailable === false
      ? 'Mikrofon není dostupný. Povolte oprávnění mikrofonu v prohlížeči.'
      : '';
  const displayError = errorMessage || microphoneError;

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <Typography>
        <Title>Voice counting</Title>
        <Paragraph>Hlasové počítání opakování s rozpoznáváním čísel a statistikou.</Paragraph>
      </Typography>

      {!browserSupportsSpeechRecognition && (
        <Alert
          type="error"
          showIcon
          message="Tento prohlížeč nepodporuje rozpoznávání řeči (Web Speech API)."
        />
      )}

      {httpsWarningVisible && (
        <Alert
          type="warning"
          showIcon
          message="Na mobilu používejte HTTPS, jinak mikrofon nemusí fungovat."
        />
      )}

      {displayError && <Alert type="error" showIcon message={displayError} />}

      <Card title="Voice counting session">
        <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
          <Space wrap>
            <Tag color={sessionState === 'listening' ? 'green' : 'default'}>
              Stav relace: {sessionState}
            </Tag>
            <Tag color={listening ? 'green' : 'default'}>Stav mikrofonu: {micStatus}</Tag>
          </Space>

          <Space size="large" wrap>
            <Statistic title="Aktuální číslo" value={currentNumber ?? '---'} />
            <Statistic title="Rozpoznáno čísel" value={liveCount} />
          </Space>

          <Space wrap>
            <Button
              type="primary"
              onClick={startSession}
              disabled={!browserSupportsSpeechRecognition || sessionState === 'listening'}
            >
              Začít poslouchat
            </Button>
            <Button onClick={stopSession} disabled={sessionState !== 'listening'}>
              Zastavit počítání
            </Button>
            <Button onClick={resetSession}>Nová relace</Button>
          </Space>

          <Descriptions size="small" bordered column={1}>
            <Descriptions.Item label="Začátek relace">
              {sessionStartedAt ? new Date(sessionStartedAt).toLocaleString('cs-CZ') : '---'}
            </Descriptions.Item>
            <Descriptions.Item label="Konec relace">
              {sessionEndedAt ? new Date(sessionEndedAt).toLocaleString('cs-CZ') : '---'}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>

      <Card title="Statistiky">
        <Space direction="vertical" size="small" style={{ display: 'flex' }}>
          <Text>Počet: {summary.count}</Text>
          <Text>Min: {summary.min ?? '---'}</Text>
          <Text>Max: {summary.max ?? '---'}</Text>
          <Text>Průměr: {summary.average ?? '---'}</Text>
          <Text>Frekvence: {Object.entries(summary.frequency).map(([k, v]) => `${k}: ${v}`).join(', ') || '---'}</Text>
          <Text>
            Intervaly (ms): {summary.intervalsMs.length > 0 ? summary.intervalsMs.join(', ') : '---'}
          </Text>
        </Space>
      </Card>

      <Card title={`Události (${events.length})`}>
        <List
          locale={{ emptyText: 'Zatím žádná rozpoznaná čísla.' }}
          dataSource={events}
          renderItem={(event) => (
            <List.Item>
              <Text>
                {event.value} ({event.token}) – {event.timeLabel}
              </Text>
            </List.Item>
          )}
        />
      </Card>
    </Space>
  );
}
