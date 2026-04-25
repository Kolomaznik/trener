import { Button, Grid, Typography } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

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
    </Typography>
  );
}
