/** Centralized API client for CarePulse */

const API_BASE = import.meta.env.VITE_API_URL || "";

let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
  if (token) localStorage.setItem("cp_access_token", token);
  else localStorage.removeItem("cp_access_token");
}

export function getAccessToken(): string | null {
  if (_accessToken) return _accessToken;
  return localStorage.getItem("cp_access_token");
}

interface ApiError {
  status: number;
  code: string;
  message: string;
}

function buildHeaders(extra?: Record<string, string>): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json", ...extra };
  const token = getAccessToken();
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let code = "API_ERROR";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body?.error?.code ?? code;
      message = body?.error?.message ?? message;
    } catch {}
    const err: ApiError = { status: res.status, code, message };
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, { headers: buildHeaders() });
    return handleResponse<T>(res);
  },
  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: buildHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },
  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PUT",
      headers: buildHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },
  async patch<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      method: "PATCH",
      headers: buildHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return handleResponse<T>(res);
  },
  async delete<T>(path: string): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, { method: "DELETE", headers: buildHeaders() });
    return handleResponse<T>(res);
  },
};
