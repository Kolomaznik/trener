import { Button, Divider, Grid, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import BodyHighlighter from '../components/BodyHighlighter.jsx';

const { Title, Paragraph } = Typography;
const { useBreakpoint } = Grid;

export default function Home() {
  const navigate = useNavigate();
  const screens = useBreakpoint();
  const isMobile = !screens.md;

  return (
    <Typography>
      <Title>Overview</Title>
      <Paragraph>Welcome to Trainer. Pick up where you left off or start a new session.</Paragraph>
      <Button
        type="primary"
        size="large"
        icon={<PlayCircleOutlined />}
        block={isMobile}
        onClick={() => navigate('/exercises')}
      >
        Start Training
      </Button>

      <Divider />

      <Title level={3}>Svalová mapa</Title>
      <Paragraph>
        Interaktivní přehled svalových partií. Klikněte na sval nebo vyberte partii ze seznamu a upravte barvu a
        intenzitu zvýraznění.
      </Paragraph>
      <BodyHighlighter />
    </Typography>
  );
}
