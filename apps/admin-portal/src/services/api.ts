import type {
  AuthorizationDecision,
  Capabilities,
  Role,
  SessionUser,
  UserAccess,
} from "../types";

let accessToken = sessionStorage.getItem("accessToken") ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(path, {
    ...options,
    headers,
    credentials: "include",
  });
  if (response.status === 401 && retry && path !== "/api/v1/auth/login") {
    const refreshed = await refresh();
    if (refreshed) return request<T>(path, options, false);
  }
  if (!response.ok) {
    const problem = await response.json().catch(() => null);
    throw new ApiError(problem?.detail ?? "API request failed", response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function refresh(): Promise<boolean> {
  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    clearToken();
    return false;
  }
  const body = (await response.json()) as { accessToken: string };
  setToken(body.accessToken);
  return true;
}

function setToken(token: string): void {
  accessToken = token;
  sessionStorage.setItem("accessToken", token);
}

function clearToken(): void {
  accessToken = "";
  sessionStorage.removeItem("accessToken");
}

export const api = {
  hasSession: () => Boolean(accessToken),
  async login(email: string, password: string): Promise<void> {
    const result = await request<{ accessToken: string }>(
      "/api/v1/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
    );
    setToken(result.accessToken);
  },
  async logout(): Promise<void> {
    try {
      await request<void>("/api/v1/auth/logout", { method: "POST" }, false);
    } finally {
      clearToken();
    }
  },
  me: () => request<SessionUser>("/api/v1/me"),
  capabilities: () => request<Capabilities>("/api/v1/me/capabilities"),
  roles: () => request<Role[]>("/api/v1/roles"),
  users: () => request<UserAccess[]>("/api/v1/users"),
  permissions: () => request<string[]>("/api/v1/permissions"),
  createRole: (name: string, permissions: string[]) =>
    request<Role>("/api/v1/roles", {
      method: "POST",
      body: JSON.stringify({ name, permissions }),
    }),
  evaluate: (
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ) =>
    request<AuthorizationDecision>("/api/v1/authorization/evaluate", {
      method: "POST",
      body: JSON.stringify({ userId, permission, resource }),
    }),
};
