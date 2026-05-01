import { useEffect, useState } from 'react';
import { Button, Drawer, Grid, Layout, Menu, Spin, Typography } from 'antd';
import { MenuOutlined } from '@ant-design/icons';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { apiClient } from './api/client.js';
import Home from './pages/Home.jsx';
import Exercises from './pages/Exercises.jsx';

const { Header, Content } = Layout;
const { useBreakpoint } = Grid;
const { Text } = Typography;
const GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const DEFAULT_GOOGLE_SCOPE = 'openid email profile';
const AUTH_TOKEN_STORAGE_KEY = 'trainer_google_auth_token';

const menuItems = [
  { key: '/', label: <Link to="/">Overview</Link> },
  { key: '/exercises', label: <Link to="/exercises">Exercises</Link> },
];

const drawerItems = [
  { key: '/', label: 'Overview' },
  { key: '/exercises', label: 'Exercises' },
];

function readTokenFromHash() {
  const hash = window.location.hash.replace(/^#/, '');
  const params = new URLSearchParams(hash);
  return params.get('access_token') ?? '';
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
    console.error('Failed to load user settings:', error);
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

  useEffect(() => {
    let cancelled = false;

    async function ensureAuthenticated() {
      const tokenFromHash = readTokenFromHash();
      if (tokenFromHash) {
        window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, tokenFromHash);
        window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`);
      }

      const savedToken = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;
      const redirectUri = import.meta.env.VITE_GOOGLE_REDIRECT_URI;

      if (savedToken || !clientId || !redirectUri) {
        if (!cancelled) setAuthReady(true);
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

  if (!authReady) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Content style={{ display: 'grid', placeItems: 'center', padding: 24, gap: 16 }}>
          <Spin size="large" />
          <Text>Redirecting to Google authentication…</Text>
        </Content>
      </Layout>
    );
  }

  return (
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
        {isMobile ? (
          <>
            <Button
              type="text"
              icon={<MenuOutlined style={{ color: '#fff', fontSize: 20 }} />}
              onClick={() => setDrawerOpen(true)}
              aria-label="Open menu"
              style={{ marginRight: 8 }}
            />
            <span style={{ color: '#fff', fontSize: 18, fontWeight: 500 }}>Trainer</span>
            <Drawer
              placement="left"
              open={drawerOpen}
              onClose={() => setDrawerOpen(false)}
              width={260}
              styles={{ body: { padding: 0 } }}
              title="Trainer"
            >
              <Menu
                mode="vertical"
                selectedKeys={[pathname]}
                items={drawerItems}
                onClick={({ key }) => {
                  navigate(key);
                  setDrawerOpen(false);
                }}
                style={{ borderInlineEnd: 0 }}
              />
            </Drawer>
          </>
        ) : (
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[pathname]}
            items={menuItems}
            style={{ flex: 1, minWidth: 0 }}
          />
        )}
      </Header>
      <Content
        className="safe-area-bottom"
        style={{ padding: isMobile ? 16 : 24, maxWidth: 1024, width: '100%', margin: '0 auto' }}
      >
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/exercises" element={<Exercises />} />
        </Routes>
      </Content>
    </Layout>
  );
}
