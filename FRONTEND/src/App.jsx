import { useState } from 'react';
import { Button, Drawer, Grid, Layout, Menu } from 'antd';
import { MenuOutlined } from '@ant-design/icons';
import { Link, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import Home from './pages/Home.jsx';
import Exercises from './pages/Exercises.jsx';
import ExerciseCatalogList from './pages/ExerciseCatalogList.jsx';
import ExerciseCatalogDetail from './pages/ExerciseCatalogDetail.jsx';

const { Header, Content } = Layout;
const { useBreakpoint } = Grid;

const menuItems = [
  { key: '/', label: <Link to="/">Overview</Link> },
  { key: '/exercises', label: <Link to="/exercises">Exercises</Link> },
  { key: '/exercise-catalog', label: <Link to="/exercise-catalog">Exercise Catalog</Link> },
];

const drawerItems = [
  { key: '/', label: 'Overview' },
  { key: '/exercises', label: 'Exercises' },
  { key: '/exercise-catalog', label: 'Exercise Catalog' },
];

export default function App() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [drawerOpen, setDrawerOpen] = useState(false);
  const selectedKey = pathname.startsWith('/exercise-catalog') ? '/exercise-catalog' : pathname;

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
                selectedKeys={[selectedKey]}
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
            selectedKeys={[selectedKey]}
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
          <Route path="/exercise-catalog" element={<ExerciseCatalogList />} />
          <Route path="/exercise-catalog/:slug" element={<ExerciseCatalogDetail />} />
        </Routes>
      </Content>
    </Layout>
  );
}
