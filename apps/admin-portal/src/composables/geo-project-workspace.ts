import { computed, ref, watch } from "vue";
import {
  createGeoMockState,
  geoPlatformCatalog as mockGeoPlatformCatalog,
} from "../mocks/geo-analysis";
import { api } from "../services/api";
import type {
  CollectionResponse,
  CustomerSummary,
  GeoEntityAliasResource,
  GeoEntityResource,
  GeoJobResource,
  GeoPlatform,
  GeoPlatformResource,
  GeoProject,
  GeoProjectRequest,
  GeoProjectResource,
  GeoProjectSummaryResource,
  GeoQueryPlatformResource,
  GeoQueryResource,
  GeoTopicResource,
  TaskSummary,
} from "../types";
import {
  getStoredGeoProjectId,
  resolveStoredGeoProjectId,
  setStoredGeoProjectId,
} from "../utils/geo-project-selection-storage";

const fallback = createGeoMockState();

export type GeoWorkspaceProfile =
  | "projects"
  | "entities"
  | "topics-queries"
  | "platforms-schedules"
  | "run-jobs";

function customerName(customers: CustomerSummary[], customerId: string | null): string {
  if (!customerId) return "未綁定 Customer";
  return customers.find((customer) => customer.id === customerId)?.name ?? `Customer ${shortId(customerId)}`;
}

function enrichProject(
  project: GeoProjectResource | GeoProjectSummaryResource,
  customers: CustomerSummary[],
): GeoProject {
  const summary = "ownBrand" in project ? project : null;
  return {
    ...project,
    customerName: summary?.customerName?.trim() || customerName(customers, project.customerId),
    ownBrand: summary?.ownBrand ?? null,
  };
}

export function shortId(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

export function formatGeoDate(value: string | null): string {
  if (!value) return "未排程";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function formatDateInput(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

export function useGeoProjectWorkspace(profile: GeoWorkspaceProfile) {
  const loading = ref(false);
  const actionLoading = ref(false);
  const usingMockData = ref(false);
  const errorMessage = ref("");
  const localMessage = ref("已連接 GEO Analysis API。");
  const selectedProjectId = ref("");
  const customers = ref<CustomerSummary[]>([]);
  const tasks = ref<TaskSummary[]>([]);
  const projects = ref<GeoProject[]>([]);
  const entities = ref<GeoEntityResource[]>([]);
  const aliases = ref<GeoEntityAliasResource[]>([]);
  const topics = ref<GeoTopicResource[]>([]);
  const queries = ref<GeoQueryResource[]>([]);
  const platforms = ref<GeoPlatform[]>([]);
  const queryPlatforms = ref<GeoQueryPlatformResource[]>([]);
  const jobs = ref<GeoJobResource[]>([]);
  let projectDetailsRequestId = 0;

  const selectedProject = computed(() =>
    projects.value.find((project) => project.id === selectedProjectId.value),
  );
  const selectedProjectQueries = computed(() =>
    queries.value.filter((query) => query.projectId === selectedProjectId.value),
  );
  const selectedProjectJobs = computed(() =>
    jobs.value
      .filter((job) => job.projectId === selectedProjectId.value)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
  );

  watch(selectedProjectId, (projectId) => {
    if (!usingMockData.value) setStoredGeoProjectId(projectId);
    if (projectId) void loadProjectDetails(projectId);
  });

  function setMessage(message: string): void {
    localMessage.value = message;
  }

  function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "API 操作失敗";
  }

  async function loadLookups(): Promise<void> {
    const [customerResult, taskResult] = await Promise.allSettled([
      api.customers(),
      api.tasks(),
    ]);
    if (customerResult.status === "fulfilled") {
      customers.value = customerResult.value.items;
    }
    if (taskResult.status === "fulfilled") {
      tasks.value = taskResult.value.items;
    }
  }

  async function loadProjects(): Promise<void> {
    loading.value = true;
    errorMessage.value = "";
    try {
      if (profile === "projects") await loadLookups();
      const response = await api.geoAnalysis.projects();
      usingMockData.value = false;
      projects.value = response.items.map((project) =>
        enrichProject(project, customers.value),
      );
      const nextProjectId = resolveStoredGeoProjectId(projects.value);
      if (!projects.value.length) {
        selectedProjectId.value = "";
        clearProjectDetails();
        setMessage("目前 API 尚無 GEO project。");
      } else if (selectedProjectId.value === nextProjectId) {
        await loadProjectDetails(nextProjectId);
      } else {
        selectedProjectId.value = nextProjectId;
      }
    } catch (error) {
      usingMockData.value = true;
      errorMessage.value = getErrorMessage(error);
      projects.value = fallback.projects.map((project) => ({ ...project }));
      const storedProjectId = getStoredGeoProjectId();
      const nextProjectId = projects.value.some((project) => project.id === storedProjectId)
        ? storedProjectId
        : projects.value[0]?.id ?? "";
      selectedProjectId.value = nextProjectId;
      loadMockProjectDetails(nextProjectId);
      setMessage("無法連線 GEO Analysis API，目前顯示示意資料。");
    } finally {
      loading.value = false;
    }
  }

  async function loadProjectDetails(projectId: string): Promise<void> {
    const requestId = ++projectDetailsRequestId;
    if (usingMockData.value) {
      loadMockProjectDetails(projectId);
      return;
    }
    if (profile === "projects") {
      clearProjectDetails();
      return;
    }
    loading.value = true;
    errorMessage.value = "";
    clearProjectDetails();
    try {
      if (profile === "entities") {
        const [entityResult, aliasResult] = await Promise.allSettled([
          api.geoAnalysis.entities(projectId),
          api.geoAnalysis.projectAliases(projectId),
        ]);
        if (!isCurrentProjectRequest(requestId, projectId)) return;
        const failures: string[] = [];
        entities.value = settledItems(entityResult, "Entities", failures);
        aliases.value = settledItems(aliasResult, "Aliases", failures);
        setPartialLoadError(failures);
      } else if (profile === "topics-queries") {
        const [topicResult, queryResult] = await Promise.allSettled([
          api.geoAnalysis.topics(projectId),
          api.geoAnalysis.queries(projectId),
        ]);
        if (!isCurrentProjectRequest(requestId, projectId)) return;
        const failures: string[] = [];
        topics.value = settledItems(topicResult, "Topics", failures);
        queries.value = settledItems(queryResult, "Queries", failures);
        setPartialLoadError(failures);
      } else if (profile === "platforms-schedules") {
        const [queryResult, platformResult] = await Promise.allSettled([
          api.geoAnalysis.queries(projectId),
          api.geoAnalysis.platforms(),
        ]);
        if (!isCurrentProjectRequest(requestId, projectId)) return;
        const failures: string[] = [];
        queries.value = settledItems(queryResult, "Queries", failures);
        platforms.value = platformItems(platformResult, failures);
        queryPlatforms.value = [];
        setPartialLoadError(failures);
      } else if (profile === "run-jobs") {
        const [queryResult, jobResult, platformResult] = await Promise.allSettled([
          api.geoAnalysis.queries(projectId),
          api.geoAnalysis.jobs(projectId),
          api.geoAnalysis.platforms(),
        ]);
        if (!isCurrentProjectRequest(requestId, projectId)) return;
        const failures: string[] = [];
        queries.value = settledItems(queryResult, "Queries", failures);
        jobs.value = settledItems(jobResult, "Jobs", failures);
        platforms.value = platformItems(platformResult, failures);
        setPartialLoadError(failures);
      }
    } catch (error) {
      if (!isCurrentProjectRequest(requestId, projectId)) return;
      errorMessage.value = getErrorMessage(error);
      clearProjectDetails();
      setMessage("專案資料載入失敗，請確認 geo-analysis-api 是否啟動。");
    } finally {
      if (requestId === projectDetailsRequestId) {
        loading.value = false;
      }
    }
  }

  function isCurrentProjectRequest(requestId: number, projectId: string): boolean {
    return requestId === projectDetailsRequestId && projectId === selectedProjectId.value;
  }

  function settledItems<T>(
    result: PromiseSettledResult<CollectionResponse<T>>,
    label: string,
    failures: string[],
  ): T[] {
    if (result.status === "fulfilled") return result.value.items;
    failures.push(label);
    return [];
  }

  function platformItems(
    result: PromiseSettledResult<CollectionResponse<GeoPlatformResource>>,
    failures: string[],
  ): GeoPlatform[] {
    return settledItems(result, "Platforms", failures).map((platform) => ({
      id: platform.id,
      name: platform.displayName,
      model: platform.defaultModel ?? "-",
      status: platform.status,
    }));
  }

  function setPartialLoadError(failures: string[]): void {
    errorMessage.value = failures.length
      ? `部分資料載入失敗：${failures.join("、")}。請稍後重新整理。`
      : "";
  }

  function clearProjectDetails(): void {
    entities.value = [];
    aliases.value = [];
    topics.value = [];
    queries.value = [];
    platforms.value = [];
    queryPlatforms.value = [];
    jobs.value = [];
  }

  function loadMockProjectDetails(projectId: string): void {
    clearProjectDetails();
    const mockQueries = fallback.queries
      .filter((query) => query.projectId === projectId)
      .map((query) => ({
        ...query,
        metadata: {},
        createdAt: "2026-06-01T00:00:00.000Z",
        updatedAt: "2026-06-01T00:00:00.000Z",
      }));
    if (profile === "entities") {
      entities.value = fallback.entities.filter((entity) => entity.projectId === projectId);
      aliases.value = fallback.aliases
        .filter((alias) => entities.value.some((entity) => entity.id === alias.entityId))
        .map((alias) => ({ ...alias, createdAt: "2026-06-01T00:00:00.000Z" }));
    } else if (profile === "topics-queries") {
      topics.value = fallback.topics.filter((topic) => topic.projectId === projectId) as GeoTopicResource[];
      queries.value = mockQueries;
    } else if (profile === "platforms-schedules") {
      queries.value = mockQueries;
      platforms.value = [...mockGeoPlatformCatalog];
      queryPlatforms.value = [];
    } else if (profile === "run-jobs") {
      queries.value = mockQueries;
      platforms.value = [...mockGeoPlatformCatalog];
      jobs.value = fallback.jobs
        .filter((job) => job.projectId === projectId)
        .map((job) => ({
          ...job,
          dispatchBackend: null,
          dispatchMessageId: null,
          lastErrorCode: null,
        }));
    }
  }

  async function runAction(action: () => Promise<void>): Promise<void> {
    actionLoading.value = true;
    try {
      await action();
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      actionLoading.value = false;
    }
  }

  async function createProject(input: GeoProjectRequest): Promise<boolean> {
    let created = false;
    await runAction(async () => {
      if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
      const project = await api.geoAnalysis.createProject(input);
      projects.value.unshift(enrichProject(project, customers.value));
      setStoredGeoProjectId(project.id);
      selectedProjectId.value = project.id;
      setMessage("已建立 GEO project。");
      created = true;
    });
    return created;
  }

  async function deleteProject(projectId: string): Promise<void> {
    await runAction(async () => {
      if (!usingMockData.value) await api.geoAnalysis.deleteProject(projectId);
      projects.value = projects.value.filter((project) => project.id !== projectId);
      selectedProjectId.value = resolveStoredGeoProjectId(projects.value);
      setMessage("已刪除 GEO project。");
    });
  }

  async function refreshProjectDetails(): Promise<void> {
    if (selectedProjectId.value) await loadProjectDetails(selectedProjectId.value);
  }

  return {
    actionLoading,
    aliases,
    customers,
    deleteProject,
    entities,
    errorMessage,
    formatDateInput,
    getErrorMessage,
    jobs,
    loading,
    loadProjects,
    localMessage,
    projects,
    queries,
    queryPlatforms,
    refreshProjectDetails,
    runAction,
    selectedProject,
    selectedProjectId,
    selectedProjectJobs,
    selectedProjectQueries,
    setMessage,
    tasks,
    topics,
    usingMockData,
    createProject,
    platforms,
  };
}
