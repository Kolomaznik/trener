import { useState } from 'react';
import { Button, Drawer, Grid, Layout, Menu } from 'antd';
import { MenuOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import Home from './pages/Home.jsx';
import Exercises from './pages/Exercises.jsx';

const { Header, Content } = Layout;
const { useBreakpoint } = Grid;

const menuItems = [
  { key: '/', label: <Link to="/">Overview</Link> },
  { key: '/exercises', label: <Link to="/exercises">Exercises</Link> },
];

const drawerItems = [
  { key: '/', label: 'Overview' },
  { key: '/exercises', label: 'Exercises' },
];

export default function App() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [drawerOpen, setDrawerOpen] = useState(false);
  const startButtonLabel = isMobile ? 'Začít' : 'Začít cvičit';

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
            <div style={{ flex: 1 }} />
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => navigate('/exercises')}
              size="middle"
            >
              {startButtonLabel}
            </Button>
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
          <>
            <Menu
              theme="dark"
              mode="horizontal"
              selectedKeys={[pathname]}
              items={menuItems}
              style={{ flex: 1, minWidth: 0 }}
            />
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => navigate('/exercises')}>
              {startButtonLabel}
            </Button>
          </>
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
