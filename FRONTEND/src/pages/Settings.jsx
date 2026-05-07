import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Avatar,
  Card,
  Col,
  Form,
  InputNumber,
  Radio,
  Row,
  Space,
  Spin,
  Typography,
} from 'antd';
import {
  CheckCircleTwoTone,
  CloseCircleTwoTone,
  LoadingOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { isProfileComplete, useUserSettings } from '../context/UserSettingsContext.jsx';
import { patchUserSettings } from '../api/user/settings/patch.js';

const { Title, Text } = Typography;
const DEBOUNCE_MS = 500;

const unitLabelStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '0 11px',
  background: 'rgba(0,0,0,0.02)',
  border: '1px solid #d9d9d9',
  borderLeft: 0,
  borderRadius: '0 6px 6px 0',
  color: 'rgba(0,0,0,0.45)',
  whiteSpace: 'nowrap',
};

function SaveStatus({ status }) {
  if (status === 'saving') {
    return (
      <Text type="secondary">
        <LoadingOutlined /> Ukládám…
      </Text>
    );
  }
  if (status === 'saved') {
    return (
      <Text type="secondary">
        <CheckCircleTwoTone twoToneColor="#52c41a" /> Uloženo
      </Text>
    );
  }
  if (status === 'error') {
    return (
      <Text type="danger">
        <CloseCircleTwoTone twoToneColor="#ff4d4f" /> Chyba ukládání
      </Text>
    );
  }
  return null;
}

export default function Settings() {
  const { userSettings, setUserSettings } = useUserSettings();
  const [statuses, setStatuses] = useState({});
  const timersRef = useRef({});

  useEffect(
    () => () => {
      Object.values(timersRef.current).forEach((id) => clearTimeout(id));
    },
    [],
  );

  if (!userSettings) {
    return (
      <Space style={{ width: '100%', justifyContent: 'center', padding: 24 }}>
        <Spin />
      </Space>
    );
  }

  const setFieldStatus = (field, value) =>
    setStatuses((prev) => ({ ...prev, [field]: value }));

  const sendPatch = async (field, value) => {
    setFieldStatus(field, 'saving');
    try {
      await patchUserSettings({ [field]: value });
      setUserSettings((prev) => ({ ...prev, [field]: value }));
      setFieldStatus(field, 'saved');
    } catch {
      setFieldStatus(field, 'error');
    }
  };

  const patchImmediate = (field, value) => {
    if (timersRef.current[field]) {
      clearTimeout(timersRef.current[field]);
      delete timersRef.current[field];
    }
    sendPatch(field, value);
  };

  const patchDebounced = (field, value) => {
    if (timersRef.current[field]) clearTimeout(timersRef.current[field]);
    setFieldStatus(field, 'saving');
    timersRef.current[field] = setTimeout(() => {
      delete timersRef.current[field];
      sendPatch(field, value);
    }, DEBOUNCE_MS);
  };

  const incomplete = !isProfileComplete(userSettings);
  const currentYear = new Date().getFullYear();
  const computedAge =
    userSettings.birth_year != null ? currentYear - userSettings.birth_year : null;

  return (
    <Typography style={{ maxWidth: 680 }}>
      <Title level={2}>Nastavení profilu</Title>

      {incomplete && (
        <Alert
          type="info"
          showIcon
          message="Pro pokračování vyplňte všechna pole níže."
          style={{ marginBottom: 16 }}
        />
      )}

      <Card
        title={
          <Space>
            <LockOutlined />
            <span>Účet Google</span>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        <Space align="center" style={{ marginBottom: 12 }}>
          <Avatar
            size={64}
            src={userSettings.picture}
            alt={userSettings.name ?? userSettings.email}
          />
          <div>
            <div style={{ fontWeight: 500 }}>{userSettings.name ?? '—'}</div>
            <div style={{ color: 'rgba(0,0,0,0.45)' }}>{userSettings.email}</div>
          </div>
        </Space>
        <div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            Tyto údaje jsou spravovány přes váš Google účet a nelze je zde změnit.
          </Text>
        </div>
      </Card>

      <Card title="Fyzické údaje">
        <Form layout="vertical">
          <p style={{ marginTop: 0, color: 'rgba(0,0,0,0.45)', fontSize: 13 }}>
            Využíváme pro výpočet svalové zátěže při cvičení.
          </p>

          <Row gutter={24}>
            <Col xs={24} sm={12}>
              <Form.Item
                label={
                  <Space>
                    <span>Pohlaví</span>
                    <SaveStatus status={statuses.gender} />
                  </Space>
                }
                required
              >
                <Radio.Group
                  value={userSettings.gender ?? undefined}
                  onChange={(event) => patchImmediate('gender', event.target.value)}
                  buttonStyle="solid"
                  size="large"
                >
                  <Radio.Button value="male">Muž</Radio.Button>
                  <Radio.Button value="female">Žena</Radio.Button>
                </Radio.Group>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item
                label={
                  <Space>
                    <span>Rok narození</span>
                    <SaveStatus status={statuses.birth_year} />
                  </Space>
                }
                required
                extra={computedAge != null ? `Aktuální věk: ${computedAge} let` : null}
              >
                <InputNumber
                  value={userSettings.birth_year ?? null}
                  min={1900}
                  max={currentYear}
                  onChange={(value) => patchDebounced('birth_year', value)}
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={24}>
            <Col xs={24} sm={12}>
              <Form.Item
                label={
                  <Space>
                    <span>Výška</span>
                    <SaveStatus status={statuses.height_cm} />
                  </Space>
                }
                required
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber
                    aria-label="Výška"
                    value={userSettings.height_cm ?? null}
                    min={50}
                    max={250}
                    style={{ width: '100%' }}
                    onChange={(value) => patchDebounced('height_cm', value)}
                  />
                  <span style={unitLabelStyle}>
                    cm
                  </span>
                </Space.Compact>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12}>
              <Form.Item
                label={
                  <Space>
                    <span>Hmotnost</span>
                    <SaveStatus status={statuses.weight_kg} />
                  </Space>
                }
                required
              >
                <Space.Compact style={{ width: '100%' }}>
                  <InputNumber
                    value={userSettings.weight_kg ?? null}
                    min={20}
                    max={300}
                    step={0.1}
                    style={{ width: '100%' }}
                    onChange={(value) => patchDebounced('weight_kg', value)}
                  />
                  <span style={unitLabelStyle}>
                    kg
                  </span>
                </Space.Compact>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>
    </Typography>
  );
}
