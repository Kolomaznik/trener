import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

export async function fetchExercises() {
  const response = await apiClient.get('/exercises');
  return response.data;
}

export async function fetchExerciseDetail(exerciseId, level) {
  const response = await apiClient.get(`/exercises/${exerciseId}`, {
    params: { level },
  });
  return response.data;
}
