import { apiClient } from './client.js';

export async function updateUserSettings(patch) {
  const response = await apiClient.patch('/user/settings', patch);
  return response.data;
}
