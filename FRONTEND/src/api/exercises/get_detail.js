import { apiClient } from '../client.js';

export async function getExerciseDetail(exerciseName) {
  const response = await apiClient.get(`/exercises/${exerciseName}`);
  return response.data;
}
