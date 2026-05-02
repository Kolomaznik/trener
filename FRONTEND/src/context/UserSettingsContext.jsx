import { createContext, useContext } from 'react';

export const UserSettingsContext = createContext({
  userSettings: null,
  setUserSettings: () => {},
});

export function useUserSettings() {
  return useContext(UserSettingsContext);
}

export function isProfileComplete(settings) {
  if (!settings) return false;
  return (
    settings.gender != null &&
    settings.height_cm != null &&
    settings.weight_kg != null &&
    settings.birth_year != null
  );
}
