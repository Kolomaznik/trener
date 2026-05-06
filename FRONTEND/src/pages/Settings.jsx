import { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Avatar,
  Descriptions,
  Form,
  InputNumber,
  Radio,
  Space,
  Spin,
  Typography,
} from 'antd';
import { CheckCircleTwoTone, CloseCircleTwoTone, LoadingOutlined } from '@ant-design/icons';
import { isProfileComplete, useUserSettings } from '../context/UserSettingsContext.jsx';
import { patchUserSettings } from '../api/user/settings/patch.js';

const { Title, Text } = Typography;
const DEBOUNCE_MS = 500;

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
    <Typography>
      <Title level={2}>Nastavení profilu</Title>

      {incomplete && (
        <Alert
          type="info"
          showIcon
          message="Pro pokračování vyplňte všechna pole níže."
          style={{ marginBottom: 16 }}
        />
      )}

      <Descriptions
        bordered
        column={1}
        size="small"
        style={{ marginBottom: 24 }}
        items={[
          {
            key: 'avatar',
            label: 'Avatar',
            children: (
              <Avatar
                size={64}
                src={userSettings.picture}
                alt={userSettings.name ?? userSettings.email}
              />
            ),
          },
          { key: 'name', label: 'Jméno', children: userSettings.name ?? '—' },
          { key: 'email', label: 'E-mail', children: userSettings.email },
        ]}
      />

      <Form layout="vertical">
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
          >
            <Radio.Button value="male">Muž</Radio.Button>
            <Radio.Button value="female">Žena</Radio.Button>
          </Radio.Group>
        </Form.Item>

        <Form.Item
          label={
            <Space>
              <span>Výška</span>
              <SaveStatus status={statuses.height_cm} />
            </Space>
          }
          required
        >
          <InputNumber
            value={userSettings.height_cm ?? null}
            min={50}
            max={250}
            addonAfter="cm"
            onChange={(value) => patchDebounced('height_cm', value)}
          />
        </Form.Item>

        <Form.Item
          label={
            <Space>
              <span>Hmotnost</span>
              <SaveStatus status={statuses.weight_kg} />
            </Space>
          }
          required
        >
          <InputNumber
            value={userSettings.weight_kg ?? null}
            min={20}
            max={300}
            step={0.1}
            addonAfter="kg"
            onChange={(value) => patchDebounced('weight_kg', value)}
          />
        </Form.Item>

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
      </Form>
    </Typography>
  );
}
