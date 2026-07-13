export const TOKEN_KEY = "ds_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

export function isAuthed(): boolean {
  return !!getToken();
}

/** Apply the stored bearer token to the window so it survives a hard reload. */
export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  return token ? { ...(extra || {}), Authorization: `Bearer ${token}` } : extra || {};
}
