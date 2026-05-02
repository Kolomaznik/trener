import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import enUS from 'antd/locale/en_US';
import 'regenerator-runtime/runtime';
import 'antd/dist/reset.css';
import App from './App.jsx';
import './index.css';

const theme = {
  token: {
    controlHeight: 40,
    fontSize: 16,
    borderRadius: 8,
  },
  components: {
    Button: { controlHeight: 44 },
    Input: { controlHeight: 44 },
    Select: { controlHeight: 44 },
  },
};

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ConfigProvider locale={enUS} theme={theme}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </StrictMode>,
);
