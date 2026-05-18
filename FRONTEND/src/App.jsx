import { useEffect, useMemo, useState } from 'react';
import { Avatar, Button, Drawer, Grid, Layout, Menu, Spin, Typography } from 'antd';
import { DatabaseOutlined, MenuOutlined, UserOutlined, HomeOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from './api/client.js';
import { getUserSettings } from './api/user/settings/get.js';
import {
  UserSettingsContext,
  isProfileComplete,
} from './context/UserSettingsContext.jsx';
import Home from './pages/Home.jsx';
import Exercises from './pages/Exercises.jsx';
import ExerciseDetail from './pages/ExerciseDetail.jsx';
import VoiceCounting from './pages/VoiceCounting.jsx';
import Settings from './pages/Settings.jsx';
import TreningVezne from './pages/TreningVezne.jsx';
import ExercisesCatalog from './pages/admin/ExercisesCatalog.jsx';

const { Header, Content } = Layout;
const { useBreakpoint } = Grid;
const { Text } = Typography;
const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const DEFAULT_GOOGLE_SCOPE = 'openid email profile';
const AUTH_TOKEN_STORAGE_KEY = 'trainer_google_auth_token';

function readTokenFromHash() {
  const hash = window.location.hash.replace(/^#/, '');
  const params = new URLSearchParams(hash);
  const accessToken = params.get('access_token');
  const expiresInRaw = Number(params.get('expires_in') ?? 0);
  const expiresAtMs =
    Number.isFinite(expiresInRaw) && expiresInRaw > 0 ? Date.now() + expiresInRaw * 1000 : null;
  if (!accessToken) return null;
  return { accessToken, expiresAtMs };
}

function readValidStoredToken() {
  const rawValue = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!rawValue) return null;

  try {
    const parsed = JSON.parse(rawValue);
    if (typeof parsed === 'string') {
      return parsed.length > 0 ? parsed : null;
    }

    if (typeof parsed?.accessToken !== 'string' || parsed.accessToken.length === 0) {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      return null;
    }

    if (typeof parsed.expiresAtMs === 'number' && parsed.expiresAtMs <= Date.now()) {
      window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
      return null;
    }

    return parsed.accessToken;
  } catch {
    if (rawValue.length > 0) {
      return rawValue;
    }
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    return null;
  }
}

function buildGoogleOauthUrl({ clientId, redirectUri, email }) {
  const baseUrl = import.meta.env.VITE_GOOGLE_AUTH_URL || GOOGLE_AUTH_URL;
  const scope = import.meta.env.VITE_GOOGLE_OAUTH_SCOPE || DEFAULT_GOOGLE_SCOPE;
  const url = new URL(baseUrl);
  url.searchParams.set('client_id', clientId);
  url.searchParams.set('redirect_uri', redirectUri);
  url.searchParams.set('response_type', 'token');
  url.searchParams.set('scope', scope);
  if (email) {
    url.searchParams.set('login_hint', email);
  }
  return url.toString();
}

async function fetchUserEmail() {
  try {
    const response = await apiClient.get('/user/settings');
    return response.data?.email ?? '';
  } catch (error) {
    console.warn('Unable to load user settings for login_hint, continuing without it.', error);
    return '';
  }
}

export default function App() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [authError, setAuthError] = useState('');
  const [userSettings, setUserSettings] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function ensureAuthenticated() {
      const tokenFromHash = readTokenFromHash();
      if (tokenFromHash) {
        window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, JSON.stringify(tokenFromHash));
        window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      }

      const savedToken = readValidStoredToken();
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      const redirectUri = import.meta.env.VITE_GOOGLE_REDIRECT_URI;

      if (savedToken) {
        if (!cancelled) setAuthReady(true);
        return;
      }

      if (!clientId || !redirectUri) {
        if (!cancelled) {
          setAuthError('Authentication is currently unavailable. Please contact support.');
          setAuthReady(true);
        }
        return;
      }

      const email = await fetchUserEmail();
      const authUrl = buildGoogleOauthUrl({ clientId, redirectUri, email });
      window.location.assign(authUrl);
    }

    ensureAuthenticated();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!authReady || authError) return undefined;
    let cancelled = false;
    getUserSettings()
      .then((data) => {
        if (!cancelled) setUserSettings(data);
      })
      .catch((error) => {
        console.error('Failed to load user settings', error);
      });
    return () => {
      cancelled = true;
    };
  }, [authReady, authError]);

  useEffect(() => {
    if (!userSettings) return;
    if (!isProfileComplete(userSettings) && pathname !== '/settings') {
      navigate('/settings', { replace: true });
    }
  }, [userSettings, pathname, navigate]);

  const contextValue = useMemo(
    () => ({ userSettings, setUserSettings }),
    [userSettings],
  );

  const avatarNode = (
    <Avatar
      size="small"
      src={userSettings?.picture}
      icon={!userSettings?.picture ? <UserOutlined /> : undefined}
      alt={userSettings?.name ?? 'Settings'}
    />
  );

  const drawerTopItems = [
    { key: '/',
      icon: <HomeOutlined/>,
      label: 'Přehled'
    },
    { key: '/exercises',
      icon: <ThunderboltOutlined />,
      label: 'Cvičení' },
  ];

  const drawerBottomItems = [
    {
      type: 'group',
      label: 'Konfigurace',
      children: [
        {
          key: '/admin/exercises',
          icon: <DatabaseOutlined />,
          label: 'Katalog',
        },
        {
          key: '/settings',
          label: (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              {avatarNode}
              <span>{userSettings?.name ?? 'Nastavení'}</span>
            </span>
          ),
        },
      ],
    },
  ];

  if (!authReady) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ display: 'grid', placeItems: 'center', padding: 24, gap: 16 }}>
          <Spin size="large" />
          <Text>Redirecting to Google authentication...</Text>
        </Content>
      </Layout>
    );
  }

  if (authError) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ display: 'grid', placeItems: 'center', padding: 24 }}>
          <Text type="danger">{authError}</Text>
        </Content>
      </Layout>
    );
  }

  return (
    <UserSettingsContext.Provider value={contextValue}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header
          className="safe-area-top"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 10,
            display: 'flex',
            alignItems: 'center',
            padding: isMobile ? '0 12px' : '0 24px',
          }}
        >
          <Button
            type="text"
            icon={<MenuOutlined style={{ color: '#fff', fontSize: 20 }} />}
            onClick={() => setDrawerOpen(true)}
            aria-label="Open menu"
            style={{ marginRight: 8 }}
          />
          <span style={{ color: '#fff', fontSize: 18, fontWeight: 500 }}>Trainer</span>
          <div style={{ flex: 1 }} />
          <Drawer
            placement="left"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            width={isMobile ? 260 : 300}
            styles={{ body: { padding: 0, display: 'flex', flexDirection: 'column' } }}
            title="Trainer"
          >
            <Menu
              mode="vertical"
              selectedKeys={[pathname]}
              items={drawerTopItems}
              onClick={({ key }) => {
                navigate(key);
                setDrawerOpen(false);
              }}
              style={{ borderInlineEnd: 0 }}
            />
            <Menu
              mode="vertical"
              selectedKeys={[pathname]}
              items={drawerBottomItems}
              onClick={({ key }) => {
                navigate(key);
                setDrawerOpen(false);
              }}
              style={{ borderInlineEnd: 0, marginTop: 'auto', borderTop: '1px solid #f0f0f0' }}
            />
          </Drawer>
        </Header>
        <Content
          className="safe-area-bottom"
          style={{ padding: isMobile ? 16 : 24, maxWidth: 1024, width: '100%', margin: '0 auto' }}
        >
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/exercises" element={<Exercises />} />
            <Route path="/exercises/:name" element={<ExerciseDetail />} />
            <Route path="/trening-vezne" element={<TreningVezne />} />
            <Route path="/voice-counting" element={<VoiceCounting />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/admin/exercises" element={<ExercisesCatalog />} />
          </Routes>
        </Content>
      </Layout>
    </UserSettingsContext.Provider>
  );
}
