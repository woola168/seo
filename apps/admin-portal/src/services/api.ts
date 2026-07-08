import type {
  AuthorizationDecision,
  Capabilities,
  CollectionResponse,
  CreateInvitationInput,
  CustomerSummary,
  GeoAnalysisQueryRequest,
  GeoAnalysisRunResult,
  GeoAcceptQueryDraftRequest,
  Department,
  GeoDashboardReport,
  GeoDashboardReportQuery,
  GeoDummyProject,
  GeoEntityAliasRequest,
  GeoEntityAliasResource,
  GeoEntityRequest,
  GeoEntityResource,
  GeoGeneratedQuery,
  GeoJobRequest,
  GeoJobResource,
  GeoKMindHubWorkspaceMapping,
  GeoQueryDraftResource,
  GeoQueryDraftSelectionRequest,
  GeoQueryGenerationRunRequest,
  GeoQueryGenerationRunResource,
  GeoQueryGenerationResult,
  GeoMarketType,
  GeoProvider,
  GeoProjectRequest,
  GeoProjectResource,
  GeoQueryPlatformRequest,
  GeoQueryPlatformResource,
  GeoQueryResource,
  GeoQueryProvider,
  GeoQueryResearchRunRequest,
  GeoQueryResearchRunResource,
  GeoQueryResearchResult,
  GeoRegion,
  GeoRunRequestResult,
  GeoScheduleRequest,
  GeoScheduleResource,
  GeoTopicRequest,
  GeoTopicResource,
  GeoTopicInput,
  PageResponse,
  Role,
  SessionUser,
  TaskSummary,
  UserAccess,
  UserInvitation,
} from "../types";
import { problemMessage } from "./problem-details";

let accessToken = sessionStorage.getItem("accessToken") ?? "";
let refreshPromise: Promise<boolean> | null = null;
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, "") ?? "";

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
  const response = await fetch(apiUrl(path), {
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
  if (refreshPromise) return refreshPromise;
  refreshPromise = refreshAccessToken().finally(() => {
    refreshPromise = null;
  });
  return refreshPromise;
}

async function refreshAccessToken(): Promise<boolean> {
  const response = await fetch(apiUrl("/api/auth/refresh"), {
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

function apiUrl(path: string): string {
  if (!apiBaseUrl) return path;
  return `${apiBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
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
  geoAnalysis: {
    projects: (customerId = "") =>
      request<CollectionResponse<GeoProjectResource>>(
        `/api/geo/projects${customerId ? `?customerId=${customerId}` : ""}`,
      ),
    createProject: (input: GeoProjectRequest) =>
      request<GeoProjectResource>("/api/geo/projects", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    updateProject: (projectId: string, input: GeoProjectRequest) =>
      request<GeoProjectResource>(`/api/geo/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    deleteProject: (projectId: string) =>
      request<void>(`/api/geo/projects/${projectId}`, { method: "DELETE" }),
    markets: (projectId: string) =>
      request<CollectionResponse<unknown>>(
        `/api/geo/projects/${projectId}/markets`,
      ),
    kmindhubWorkspace: () =>
      request<GeoKMindHubWorkspaceMapping>(
        "/api/geo/integrations/kmindhub/workspace",
      ),
    entities: (projectId: string) =>
      request<CollectionResponse<GeoEntityResource>>(
        `/api/geo/projects/${projectId}/entities`,
      ),
    createEntity: (projectId: string, input: GeoEntityRequest) =>
      request<GeoEntityResource>(`/api/geo/projects/${projectId}/entities`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    updateEntity: (entityId: string, input: GeoEntityRequest) =>
      request<GeoEntityResource>(`/api/geo/entities/${entityId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    deleteEntity: (entityId: string) =>
      request<void>(`/api/geo/entities/${entityId}`, { method: "DELETE" }),
    aliases: (entityId: string) =>
      request<CollectionResponse<GeoEntityAliasResource>>(
        `/api/geo/entities/${entityId}/aliases`,
      ),
    createAlias: (entityId: string, input: GeoEntityAliasRequest) =>
      request<GeoEntityAliasResource>(`/api/geo/entities/${entityId}/aliases`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    deleteAlias: (aliasId: string) =>
      request<void>(`/api/geo/entity-aliases/${aliasId}`, { method: "DELETE" }),
    topics: (projectId: string) =>
      request<CollectionResponse<GeoTopicResource>>(
        `/api/geo/projects/${projectId}/topics`,
      ),
    createTopic: (projectId: string, input: GeoTopicRequest) =>
      request<GeoTopicResource>(`/api/geo/projects/${projectId}/topics`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    deleteTopic: (topicId: string) =>
      request<void>(`/api/geo/topics/${topicId}`, { method: "DELETE" }),
    queries: (projectId: string) =>
      request<CollectionResponse<GeoQueryResource>>(
        `/api/geo/projects/${projectId}/queries`,
      ),
    createQuery: (projectId: string, input: GeoAnalysisQueryRequest) =>
      request<GeoQueryResource>(`/api/geo/projects/${projectId}/queries`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    deleteQuery: (queryId: string) =>
      request<void>(`/api/geo/queries/${queryId}`, { method: "DELETE" }),
    runQueryResearch: (projectId: string, input: GeoQueryResearchRunRequest) =>
      request<GeoQueryResearchRunResource>(
        `/api/geo/projects/${projectId}/query-research-runs`,
        {
          method: "POST",
          body: JSON.stringify(input),
        },
      ),
    runQueryGeneration: (
      projectId: string,
      input: GeoQueryGenerationRunRequest,
    ) =>
      request<GeoQueryGenerationRunResource>(
        `/api/geo/projects/${projectId}/query-generation-runs`,
        {
          method: "POST",
          body: JSON.stringify(input),
        },
      ),
    updateQueryDraftSelection: (
      draftId: string,
      input: GeoQueryDraftSelectionRequest,
    ) =>
      request<GeoQueryDraftResource>(`/api/geo/query-drafts/${draftId}/selection`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    acceptQueryDraft: (draftId: string, input: GeoAcceptQueryDraftRequest) =>
      request<GeoQueryResource>(`/api/geo/query-drafts/${draftId}/accept`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    queryPlatforms: (queryId: string) =>
      request<CollectionResponse<GeoQueryPlatformResource>>(
        `/api/geo/queries/${queryId}/platforms`,
      ),
    replaceQueryPlatforms: (
      queryId: string,
      input: GeoQueryPlatformRequest[],
    ) =>
      request<CollectionResponse<GeoQueryPlatformResource>>(
        `/api/geo/queries/${queryId}/platforms`,
        {
          method: "PUT",
          body: JSON.stringify(input),
        },
      ),
    schedules: (queryId: string) =>
      request<CollectionResponse<GeoScheduleResource>>(
        `/api/geo/queries/${queryId}/schedules`,
      ),
    createSchedule: (queryId: string, input: GeoScheduleRequest) =>
      request<GeoScheduleResource>(`/api/geo/queries/${queryId}/schedules`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    updateSchedule: (scheduleId: string, input: GeoScheduleRequest) =>
      request<GeoScheduleResource>(`/api/geo/schedules/${scheduleId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    deleteSchedule: (scheduleId: string) =>
      request<void>(`/api/geo/schedules/${scheduleId}`, { method: "DELETE" }),
    createJob: (queryId: string, input: GeoJobRequest) =>
      request<GeoJobResource>(`/api/geo/queries/${queryId}/jobs`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    jobs: (projectId: string) =>
      request<CollectionResponse<GeoJobResource>>(
        `/api/geo/projects/${projectId}/jobs`,
      ),
    job: (jobId: string) => request<GeoJobResource>(`/api/geo/jobs/${jobId}`),
    runResults: (projectId: string) =>
      request<CollectionResponse<GeoAnalysisRunResult>>(
        `/api/geo/projects/${projectId}/run-results`,
      ),
    jobRunResults: (jobId: string) =>
      request<CollectionResponse<GeoAnalysisRunResult>>(
        `/api/geo/jobs/${jobId}/run-results`,
      ),
    runResult: (resultId: string) =>
      request<GeoAnalysisRunResult>(`/api/geo/run-results/${resultId}`),
    dashboardReport: (projectId: string, input: GeoDashboardReportQuery) => {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(input)) {
        if (value) params.set(key, value);
      }
      return request<GeoDashboardReport>(
        `/api/geo/projects/${projectId}/reports/dashboard?${params.toString()}`,
      );
    },
    dispatchJob: (jobId: string) =>
      request<GeoJobResource>(`/api/geo/jobs/${jobId}/dispatch`, {
        method: "POST",
      }),
    cancelJob: (jobId: string) =>
      request<GeoJobResource>(`/api/geo/jobs/${jobId}/cancel`, {
        method: "POST",
      }),
  },
  geoDummyProject: () =>
    request<GeoDummyProject>("/api/v1/geo-tracking/dummy-project"),
  researchGeoQueries: (input: {
    provider: GeoQueryProvider;
    brandName: string;
    competitorBrands: string[];
    keywords: string[];
    region: GeoRegion;
    language: string | null;
    marketType: GeoMarketType;
    audience: { name: string; description: string } | null;
  }) =>
    request<GeoQueryResearchResult>("/api/v1/geo-tracking/query-research", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  generateGeoQueries: (input: {
    seoTaskId?: string | null;
    provider: GeoQueryProvider;
    brandName: string;
    competitorBrands: string[];
    keywords: string[];
    region: GeoRegion;
    language: string | null;
    marketType: GeoMarketType;
    topics: GeoTopicInput[];
    topicNames: string[];
    intents: Array<{ category: string; description: string }>;
    audience: { name: string; description: string };
    brandMentionRules: {
      shouldMentionOwnBrand: boolean;
      shouldMentionCompetitor: boolean;
    };
    researchContext: string | null;
    maxQueries: number;
  }) =>
    request<GeoQueryGenerationResult>("/api/v1/geo-tracking/query-generation", {
      method: "POST",
      body: JSON.stringify(input),
    }),
  runGeoQueries: (
    seoTaskId: string | null,
    provider: GeoProvider,
    queries: GeoGeneratedQuery[],
  ) =>
    request<GeoRunRequestResult>("/api/v1/geo-tracking/run-requests", {
      method: "POST",
      body: JSON.stringify({
        ...(seoTaskId ? { seoTaskId } : {}),
        provider,
        timing: "run_now",
        queries: queries.map((query) => ({
          id: query.id,
          text: query.text,
          topicName: query.topicName,
          region: query.region,
          language: query.language,
          marketType: query.marketType,
          isBranded: query.isBranded,
          attributes: query.attributes,
          metadata: query.metadata,
        })),
    }),
  }),
};
