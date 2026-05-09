import { apiClient } from '../client.js';

export async function addUserExercise(exerciseName) {
  const response = await apiClient.post('/user-exercises', {
    exercise_name: exerciseName,
  });
  return response.data;
}
