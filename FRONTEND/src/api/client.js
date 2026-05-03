import axios from 'axios';

const AUTH_TOKEN_STORAGE_KEY = 'trainer_google_auth_token';

function readAccessToken() {
  try {
    const raw = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed === 'string') return parsed.length > 0 ? parsed : null;
    if (typeof parsed?.accessToken === 'string' && parsed.accessToken.length > 0) {
      if (typeof parsed.expiresAtMs === 'number' && parsed.expiresAtMs <= Date.now()) {
        return null;
      }
      return parsed.accessToken;
    }
    return null;
  } catch {
    return null;
  }
}

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = readAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchExercises() {
  const response = await apiClient.get('/exercises');
  return response.data;
}

export async function fetchExerciseDetail(exerciseId) {
  const response = await apiClient.get(`/exercises/${exerciseId}`);
  return response.data;
}
