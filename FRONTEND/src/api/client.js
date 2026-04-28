import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export async function fetchExerciseCatalog() {
  const { data } = await apiClient.get('/exercises');
  return data;
}

export async function fetchExerciseDetail(slug) {
  const { data } = await apiClient.get(`/exercises/${slug}`);
  return data;
}
