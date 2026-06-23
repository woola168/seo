import type {
  AuthorizationDecision,
  Capabilities,
  CreateInvitationInput,
  CustomerSummary,
  Department,
  PageResponse,
  Role,
  SessionUser,
  TaskSummary,
  UserAccess,
  UserInvitation,
} from "../types";
import { problemMessage } from "./problem-details";

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
  if (response.status === 401 && retry && path !== "/api/auth/login") {
    const refreshed = await refresh();
    if (refreshed) return request<T>(path, options, false);
  }
  if (!response.ok) {
    const problem: unknown = await response.json().catch(() => null);
    throw new ApiError(problemMessage(problem), response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function refresh(): Promise<boolean> {
  const response = await fetch("/api/auth/refresh", {
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
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
    );
    setToken(result.accessToken);
  },
  async logout(): Promise<void> {
    try {
      await request<void>("/api/auth/logout", { method: "POST" }, false);
    } finally {
      clearToken();
    }
  },
  me: () => request<SessionUser>("/api/me"),
  capabilities: () => request<Capabilities>("/api/me/capabilities"),
  roles: () => request<Role[]>("/api/roles"),
  users: () => request<UserAccess[]>("/api/users"),
  permissions: () => request<string[]>("/api/permissions"),
  departments: () => request<Department[]>("/api/departments"),
  createDepartment: (name: string, description: string) =>
    request<Department>("/api/departments", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  updateDepartment: (departmentId: string, name: string, description: string) =>
    request<Department>(`/api/departments/${departmentId}`, {
      method: "PATCH",
      body: JSON.stringify({ name, description }),
    }),
  deleteDepartment: (departmentId: string) =>
    request<void>(`/api/departments/${departmentId}`, {
      method: "DELETE",
    }),
  inviteUser: (input: CreateInvitationInput) =>
    request<UserInvitation>("/api/user-invitations", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  customers: () =>
    request<PageResponse<CustomerSummary>>(
      "/api/customers?page=1&pageSize=100",
    ),
  tasks: (customerId = "") =>
    request<PageResponse<TaskSummary>>(
      `/api/tasks?page=1&pageSize=100${customerId ? `&customerId=${customerId}` : ""}`,
    ),
  createCustomer: (name: string) =>
    request<CustomerSummary>("/api/customers", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  createTask: (customerId: string, name: string) =>
    request<TaskSummary>("/api/tasks", {
      method: "POST",
      body: JSON.stringify({ customerId, name }),
    }),
  requestPasswordReset: (email: string) =>
    request<void>("/api/auth/password-reset-requests", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (token: string, newPassword: string) =>
    request<void>("/api/auth/password-resets", {
      method: "POST",
      body: JSON.stringify({ token, newPassword }),
    }),
  acceptInvitation: (token: string, newPassword: string) =>
    request<void>("/api/auth/user-invitations/accept", {
      method: "POST",
      body: JSON.stringify({ token, newPassword }),
    }),
  createRole: (name: string, permissions: string[]) =>
    request<Role>("/api/roles", {
      method: "POST",
      body: JSON.stringify({ name, permissions }),
    }),
  updateRolePermissions: (roleId: string, permissions: string[]) =>
    request<Role>(`/api/roles/${roleId}/permissions`, {
      method: "PUT",
      body: JSON.stringify({ permissions }),
    }),
  deleteRole: (roleId: string) =>
    request<void>(`/api/roles/${roleId}`, {
      method: "DELETE",
    }),
  updateUserRoles: (userId: string, roleIds: string[]) =>
    request<UserAccess>(`/api/users/${userId}/roles`, {
      method: "PUT",
      body: JSON.stringify({ roleIds }),
    }),
  updateCustomerGrants: (userId: string, customerIds: string[]) =>
    request<UserAccess>(
      `/api/users/${userId}/customer-access-grants`,
      {
        method: "PUT",
        body: JSON.stringify({ customerIds }),
      },
    ),
  updateTaskGrants: (userId: string, taskIds: string[]) =>
    request<UserAccess>(`/api/users/${userId}/task-access-grants`, {
      method: "PUT",
      body: JSON.stringify({ taskIds }),
    }),
  evaluate: (
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ) =>
    request<AuthorizationDecision>("/api/authorization/evaluate", {
      method: "POST",
      body: JSON.stringify({ userId, permission, resource }),
    }),
};

