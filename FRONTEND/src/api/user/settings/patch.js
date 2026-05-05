import { apiClient } from '../client.js';

export async function patchUserSettings(patch) {
  await apiClient.patch('/user/settings', patch);
}
