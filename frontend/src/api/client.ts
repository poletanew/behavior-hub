const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/v1";

let accessToken: string | null = localStorage.getItem("bh_access_token");
let refreshToken: string | null = localStorage.getItem("bh_refresh_token");

export function setTokens(access: string, refresh: string) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem("bh_access_token", access);
  localStorage.setItem("bh_refresh_token", refresh);
}

export function clearTokens() {
  accessToken = null;
  refreshToken = null;
  localStorage.removeItem("bh_access_token");
  localStorage.removeItem("bh_refresh_token");
}

export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshToken) return false;
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return false;
  const data = await response.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

async function withAuthRetry(doFetch: () => Promise<Response>, auth: boolean): Promise<Response> {
  let response = await doFetch();
  if (response.status === 401 && auth) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      response = await doFetch();
    }
  }
  return response;
}

async function throwIfError(response: Response): Promise<void> {
  if (response.ok) return;
  let detail: unknown = response.statusText;
  try {
    const errorBody = await response.json();
    detail = errorBody.detail ?? detail;
  } catch {
    // ignore parse errors
  }
  const message = typeof detail === "string" ? detail : JSON.stringify(detail);
  throw new ApiError(response.status, message, detail);
}

export async function apiRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {}
): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const doFetch = () => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (auth && accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
    return fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };

  const response = await withAuthRetry(doFetch, auth);
  await throwIfError(response);

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
    return fetch(`${API_BASE_URL}${path}`, { method: "POST", headers, body: formData });
  };

  const response = await withAuthRetry(doFetch, true);
  await throwIfError(response);
  return response.json() as Promise<T>;
}

export async function apiDownload(path: string): Promise<Blob> {
  const doFetch = () => {
    const headers: Record<string, string> = {};
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
    return fetch(`${API_BASE_URL}${path}`, { headers });
  };

  const response = await withAuthRetry(doFetch, true);
  await throwIfError(response);
  return response.blob();
}
