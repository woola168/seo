<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
import {
  createGeoMockState,
  geoPlatformCatalog,
} from "../mocks/geo-analysis";
import { api } from "../services/api";
import type {
  CustomerSummary,
  GeoAnalysisRunResult,
  GeoEntity,
  GeoEntityAliasResource,
  GeoEntityResource,
  GeoJob,
  GeoJobResource,
  GeoMarketType,
  GeoProject,
  GeoProjectResource,
  GeoQuery,
  GeoQueryPlatformResource,
  GeoQueryResource,
  GeoSchedule,
  GeoScheduleResource,
  GeoTopic,
  GeoTopicResource,
  TaskSummary,
} from "../types";

type GeoTab =
  | "overview"
  | "projects"
  | "entities"
  | "queries"
  | "schedules"
  | "jobs"
  | "reports";

const props = defineProps<{
  activeTab?: GeoTab;
}>();

const emit = defineEmits<{
  unavailable: [label: string];
}>();

const fallback = createGeoMockState();
const activeTab = computed(() => props.activeTab ?? "overview");
const tabTitles: Record<GeoTab, string> = {
  overview: "Overview",
  projects: "Projects",
  entities: "Entities",
  queries: "Topics & Queries",
  schedules: "Platforms & Schedules",
  jobs: "Run Jobs",
  reports: "Reports",
};
const pageTitle = computed(() => tabTitles[activeTab.value]);
const loading = ref(false);
const actionLoading = ref(false);
const usingMockData = ref(false);
const errorMessage = ref("");
const localMessage = ref("已連接 GEO Analysis API；缺少彙總 API 的區塊會標示為示意資料。");
const selectedProjectId = ref("");
const projectSearch = ref("");
const querySearch = ref("");
const jobSearch = ref("");
const queryStageFilter = ref("");
const queryPriorityFilter = ref("");
const jobPlatformFilter = ref("");
const jobStatusFilter = ref("");

const customers = ref<CustomerSummary[]>([]);
const tasks = ref<TaskSummary[]>([]);
const projects = ref<GeoProject[]>([]);
const entities = ref<GeoEntityResource[]>([]);
const aliases = ref<GeoEntityAliasResource[]>([]);
const topics = ref<GeoTopicResource[]>([]);
const queries = ref<GeoQueryResource[]>([]);
const queryPlatforms = ref<GeoQueryPlatformResource[]>([]);
const schedules = ref<GeoScheduleResource[]>([]);
const jobs = ref<GeoJobResource[]>([]);
const runResults = ref<GeoAnalysisRunResult[]>([]);
let projectDetailsRequestId = 0;

const projectForm = reactive({
  name: "",
  customerId: "",
  seoTaskId: "",
  defaultRegion: "TW",
  defaultLanguage: "zh-TW",
  dailyRunBudget: 200,
});

const entityForm = reactive({
  entityType: "brand" as GeoEntity["entityType"],
  name: "",
  websiteUrl: "",
  description: "",
  alias: "",
});

const topicForm = reactive({
  name: "",
  description: "",
});

const queryForm = reactive({
  topicId: "",
  queryText: "",
  intent: "recommendation",
  buyerStage: "consideration",
  marketType: "b2c" as GeoMarketType,
  isBranded: false,
  priority: "normal" as GeoQuery["priority"],
});

const scheduleForm = reactive({
  queryId: "",
  platformId: geoPlatformCatalog[0]?.id ?? "",
  frequency: "daily" as GeoSchedule["frequency"],
  priority: "normal" as GeoSchedule["priority"],
  timezone: "Asia/Taipei",
  nextRunAt: "2026-06-24T09:00",
});

const jobForm = reactive({
  queryId: "",
  platformId: geoPlatformCatalog[0]?.id ?? "",
  priority: "normal" as GeoJob["priority"],
});

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

const selectedProjectRunResults = computed(() =>
  runResults.value
    .filter((result) =>
      selectedProjectJobs.value.some((job) => job.id === result.jobId),
    )
    .sort((a, b) => b.runAt.localeCompare(a.runAt)),
);

const activeQueryCount = computed(
  () =>
    selectedProjectQueries.value.filter((query) => query.status === "active")
      .length,
);

const activeScheduleCount = computed(
  () => schedules.value.filter((schedule) => schedule.status === "active").length,
);

const runningJobCount = computed(
  () =>
    selectedProjectJobs.value.filter((job) =>
      ["pending", "published", "running_external"].includes(job.status),
    ).length,
);

const overviewStats = computed(() => [
  {
    label: "Projects",
    value: projects.value.length,
    detail: `${projects.value.filter((project) => project.status === "active").length} active`,
    tone: "tone-info",
  },
  {
    label: "Active Queries",
    value: activeQueryCount.value,
    detail: `${topics.value.length} topics`,
    tone: "tone-success",
  },
  {
    label: "Schedules",
    value: activeScheduleCount.value,
    detail: "目前由 query-level API 聚合",
    tone: "tone-warning",
  },
  {
    label: "Running Jobs",
    value: runningJobCount.value,
    detail: `${selectedProjectJobs.value.filter((job) => job.status === "failed").length} failed`,
    tone: "tone-info",
  },
]);

const filteredProjects = computed(() => {
  const keyword = projectSearch.value.trim().toLowerCase();
  if (!keyword) return projects.value;
  return projects.value.filter((project) =>
    [project.name, project.customerName, project.seoTaskName ?? ""]
      .join(" ")
      .toLowerCase()
      .includes(keyword),
  );
});

const filteredQueries = computed(() => {
  const keyword = querySearch.value.trim().toLowerCase();
  return selectedProjectQueries.value.filter((query) => {
    const topicName = getTopic(query.topicId)?.name ?? "";
    const matchesKeyword =
      !keyword ||
      [query.queryText, topicName, query.intent ?? "", query.buyerStage ?? ""]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    const matchesStage =
      !queryStageFilter.value || query.buyerStage === queryStageFilter.value;
    const matchesPriority =
      !queryPriorityFilter.value || query.priority === queryPriorityFilter.value;
    return matchesKeyword && matchesStage && matchesPriority;
  });
});

const filteredJobs = computed(() => {
  const keyword = jobSearch.value.trim().toLowerCase();
  return selectedProjectJobs.value.filter((job) => {
    const queryText = getQuery(job.queryId)?.queryText ?? "";
    const platform = getPlatform(job.platformId);
    const matchesKeyword =
      !keyword ||
      [queryText, platform, job.dedupeKey].join(" ").toLowerCase().includes(keyword);
    const matchesPlatform =
      !jobPlatformFilter.value || job.platformId === jobPlatformFilter.value;
    const matchesStatus = !jobStatusFilter.value || job.status === jobStatusFilter.value;
    return matchesKeyword && matchesPlatform && matchesStatus;
  });
});

const platformSummaries = computed(() =>
  geoPlatformCatalog.map((platform) => ({
    ...platform,
    assignmentCount: queryPlatforms.value.filter(
      (item) => item.platformId === platform.id,
    ).length,
    scheduleCount: schedules.value.filter(
      (schedule) => schedule.platformId === platform.id,
    ).length,
  })),
);

onMounted(() => {
  void loadProjects();
});

watch(selectedProjectId, (projectId) => {
  if (projectId) void loadProjectDetails(projectId);
});

function setMessage(message: string): void {
  localMessage.value = message;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "API 操作失敗";
}

function shortId(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function customerName(customerId: string | null): string {
  if (!customerId) return "未綁定 Customer";
  return (
    customers.value.find((customer) => customer.id === customerId)?.name ??
    `Customer ${shortId(customerId)}`
  );
}

function taskName(taskId: string | null): string | null {
  if (!taskId) return null;
  return tasks.value.find((task) => task.id === taskId)?.name ?? `Task ${shortId(taskId)}`;
}

function enrichProject(project: GeoProjectResource): GeoProject {
  return {
    ...project,
    customerName: customerName(project.customerId),
    seoTaskName: taskName(project.seoTaskId),
  };
}

function resourceQueryToView(query: GeoQueryResource): GeoQuery {
  return {
    ...query,
    intent: query.intent ?? "-",
    buyerStage: query.buyerStage ?? "-",
  };
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
    await loadLookups();
    const response = await api.geoAnalysis.projects();
    usingMockData.value = false;
    projects.value = response.items.map(enrichProject);
    const nextProjectId = projects.value[0]?.id ?? "";
    if (!projects.value.length) {
      clearProjectDetails();
      setMessage("目前 API 尚未建立 GEO project。");
    } else if (selectedProjectId.value === nextProjectId) {
      await loadProjectDetails(nextProjectId);
    } else {
      selectedProjectId.value = nextProjectId;
    }
  } catch (error) {
    usingMockData.value = true;
    errorMessage.value = getErrorMessage(error);
    projects.value = fallback.projects.map((project) => ({ ...project }));
    const nextProjectId = projects.value[0]?.id ?? "";
    selectedProjectId.value = nextProjectId;
    loadMockProjectDetails(nextProjectId);
    setMessage("無法連接 GEO Analysis API，已切換為示意資料。");
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
  loading.value = true;
  errorMessage.value = "";
  try {
    const [entityResult, topicResult, queryResult, jobResult, resultResult] =
      await Promise.all([
        api.geoAnalysis.entities(projectId),
        api.geoAnalysis.topics(projectId),
        api.geoAnalysis.queries(projectId),
        api.geoAnalysis.jobs(projectId),
        api.geoAnalysis.runResults(projectId),
      ]);
    if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
      return;
    }
    entities.value = entityResult.items;
    topics.value = topicResult.items;
    queries.value = queryResult.items;
    jobs.value = jobResult.items;
    runResults.value = resultResult.items;
    await loadNestedProjectDetails(projectId, requestId);
    if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
      return;
    }
    selectFirstQuery();
  } catch (error) {
    if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
      return;
    }
    errorMessage.value = getErrorMessage(error);
    clearProjectDetails();
    setMessage("專案資料載入失敗，請確認 geo-analysis-api 是否啟動。");
  } finally {
    if (requestId === projectDetailsRequestId) {
      loading.value = false;
    }
  }
}

async function loadNestedProjectDetails(
  projectId: string,
  requestId: number,
): Promise<void> {
  const aliasResults = await Promise.allSettled(
    entities.value.map((entity) => api.geoAnalysis.aliases(entity.id)),
  );
  if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
    return;
  }
  aliases.value = aliasResults.flatMap((result) =>
    result.status === "fulfilled" ? result.value.items : [],
  );

  const platformResults = await Promise.allSettled(
    queries.value.map((query) => api.geoAnalysis.queryPlatforms(query.id)),
  );
  if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
    return;
  }
  queryPlatforms.value = platformResults.flatMap((result) =>
    result.status === "fulfilled" ? result.value.items : [],
  );

  const scheduleResults = await Promise.allSettled(
    queries.value.map((query) => api.geoAnalysis.schedules(query.id)),
  );
  if (requestId !== projectDetailsRequestId || projectId !== selectedProjectId.value) {
    return;
  }
  schedules.value = scheduleResults.flatMap((result) =>
    result.status === "fulfilled" ? result.value.items : [],
  );
}

function clearProjectDetails(): void {
  entities.value = [];
  aliases.value = [];
  topics.value = [];
  queries.value = [];
  queryPlatforms.value = [];
  schedules.value = [];
  jobs.value = [];
  runResults.value = [];
}

function loadMockProjectDetails(projectId: string): void {
  entities.value = fallback.entities.filter(
    (entity) => entity.projectId === projectId,
  );
  aliases.value = fallback.aliases
    .filter((alias) => entities.value.some((entity) => entity.id === alias.entityId))
    .map((alias) => ({ ...alias, createdAt: "2026-06-01T00:00:00.000Z" }));
  topics.value = fallback.topics.filter((topic) => topic.projectId === projectId) as GeoTopicResource[];
  queries.value = fallback.queries.filter((query) => query.projectId === projectId).map((query) => ({
    ...query,
    metadata: {},
    createdAt: "2026-06-01T00:00:00.000Z",
    updatedAt: "2026-06-01T00:00:00.000Z",
  }));
  queryPlatforms.value = [];
  schedules.value = fallback.schedules as GeoScheduleResource[];
  jobs.value = fallback.jobs.map((job) => ({
    ...job,
    dispatchBackend: null,
    dispatchMessageId: null,
    lastErrorCode: null,
  }));
  runResults.value = fallback.runResults;
  selectFirstQuery();
}

function selectFirstQuery(): void {
  const firstQuery = queries.value[0];
  if (!firstQuery) return;
  scheduleForm.queryId = firstQuery.id;
  jobForm.queryId = firstQuery.id;
}

function formatDate(value: string | null): string {
  if (!value) return "未排程";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatDateInput(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
}

function getTopic(topicId: string | null): GeoTopic | undefined {
  return topicId ? topics.value.find((topic) => topic.id === topicId) : undefined;
}

function getQuery(queryId: string): GeoQuery | undefined {
  const query = queries.value.find((item) => item.id === queryId);
  return query ? resourceQueryToView(query) : undefined;
}

function getPlatform(platformId: string): string {
  return (
    geoPlatformCatalog.find((platform) => platform.id === platformId)?.name ??
    `Platform ${shortId(platformId)}`
  );
}

function getPlatformModel(platformId: string): string {
  return (
    geoPlatformCatalog.find((platform) => platform.id === platformId)?.model ??
    shortId(platformId)
  );
}

function getAliases(entityId: string): string {
  const values = aliases.value
    .filter((alias) => alias.entityId === entityId)
    .map((alias) => alias.alias);
  return values.length > 0 ? values.join("、") : "尚未設定";
}

function badgeClass(status: string): string {
  if (["active", "succeeded", "completed", "positive"].includes(status)) {
    return "badge badge-success";
  }
  if (
    ["paused", "pending", "published", "running_external", "running", "neutral"].includes(
      status,
    )
  ) {
    return "badge badge-warning";
  }
  if (["failed", "cancelled", "negative", "archived"].includes(status)) {
    return "badge badge-error";
  }
  if (["high"].includes(status)) return "badge badge-error";
  if (["normal"].includes(status)) return "badge badge-info";
  return "badge badge-muted";
}

function resetForms(): void {
  projectForm.name = "";
  projectForm.customerId = customers.value[0]?.id ?? "";
  projectForm.seoTaskId = "";
  projectForm.defaultRegion = "TW";
  projectForm.defaultLanguage = "zh-TW";
  projectForm.dailyRunBudget = 200;
  entityForm.name = "";
  entityForm.websiteUrl = "";
  entityForm.description = "";
  entityForm.alias = "";
  topicForm.name = "";
  topicForm.description = "";
  queryForm.topicId = topics.value[0]?.id ?? "";
  queryForm.queryText = "";
}

async function createProject(): Promise<void> {
  if (!projectForm.name.trim() || !projectForm.customerId.trim()) {
    setMessage("請輸入 project 名稱與 customerId。");
    return;
  }
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const project = await api.geoAnalysis.createProject({
      customerId: projectForm.customerId.trim(),
      seoTaskId: projectForm.seoTaskId.trim() || null,
      name: projectForm.name.trim(),
      defaultRegion: projectForm.defaultRegion.trim() || "TW",
      defaultLanguage: projectForm.defaultLanguage.trim() || "zh-TW",
      status: "active",
      dailyRunBudget: Number(projectForm.dailyRunBudget) || 0,
    });
    projects.value.unshift(enrichProject(project));
    selectedProjectId.value = project.id;
    resetForms();
    setMessage("已建立 GEO project。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function deleteProject(projectId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (!usingMockData.value) await api.geoAnalysis.deleteProject(projectId);
    projects.value = projects.value.filter((project) => project.id !== projectId);
    selectedProjectId.value = projects.value[0]?.id ?? "";
    setMessage("已刪除 GEO project。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function createEntity(): Promise<void> {
  if (!selectedProject.value || !entityForm.name.trim()) return;
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const entity = await api.geoAnalysis.createEntity(selectedProject.value.id, {
      entityType: entityForm.entityType,
      name: entityForm.name.trim(),
      websiteUrl: entityForm.websiteUrl.trim() || null,
      description: entityForm.description.trim(),
      status: "active",
    });
    entities.value.unshift(entity);
    if (entityForm.alias.trim()) {
      aliases.value.unshift(
        await api.geoAnalysis.createAlias(entity.id, {
          alias: entityForm.alias.trim(),
          matchType: "contains",
        }),
      );
    }
    entityForm.name = "";
    entityForm.websiteUrl = "";
    entityForm.description = "";
    entityForm.alias = "";
    setMessage("已建立 entity。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function deleteEntity(entityId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (!usingMockData.value) await api.geoAnalysis.deleteEntity(entityId);
    entities.value = entities.value.filter((entity) => entity.id !== entityId);
    aliases.value = aliases.value.filter((alias) => alias.entityId !== entityId);
    setMessage("已刪除 entity。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function createTopic(): Promise<void> {
  if (!selectedProject.value || !topicForm.name.trim()) return;
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const topic = await api.geoAnalysis.createTopic(selectedProject.value.id, {
      name: topicForm.name.trim(),
      description: topicForm.description.trim(),
      status: "active",
    });
    topics.value.push(topic);
    queryForm.topicId = topic.id;
    topicForm.name = "";
    topicForm.description = "";
    setMessage("已建立 topic。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function createQuery(): Promise<void> {
  if (!selectedProject.value || !queryForm.queryText.trim()) return;
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const query = await api.geoAnalysis.createQuery(selectedProject.value.id, {
      topicId: queryForm.topicId || null,
      queryText: queryForm.queryText.trim(),
      region: selectedProject.value.defaultRegion,
      language: selectedProject.value.defaultLanguage,
      marketType: queryForm.marketType,
      intent: queryForm.intent.trim() || null,
      buyerStage: queryForm.buyerStage.trim() || null,
      isBranded: queryForm.isBranded,
      priority: queryForm.priority,
      status: "active",
      metadata: {},
    });
    queries.value.unshift(query);
    queryForm.queryText = "";
    queryForm.isBranded = false;
    selectFirstQuery();
    setMessage("已建立 query。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function deleteQuery(queryId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (!usingMockData.value) await api.geoAnalysis.deleteQuery(queryId);
    queries.value = queries.value.filter((query) => query.id !== queryId);
    queryPlatforms.value = queryPlatforms.value.filter((item) => item.queryId !== queryId);
    schedules.value = schedules.value.filter((schedule) => schedule.queryId !== queryId);
    jobs.value = jobs.value.filter((job) => job.queryId !== queryId);
    setMessage("已刪除 query。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function createSchedule(): Promise<void> {
  if (!scheduleForm.queryId) return;
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const schedule = await api.geoAnalysis.createSchedule(scheduleForm.queryId, {
      platformId: scheduleForm.platformId,
      frequency: scheduleForm.frequency,
      priority: scheduleForm.priority,
      timezone: scheduleForm.timezone.trim() || "Asia/Taipei",
      nextRunAt: formatDateInput(scheduleForm.nextRunAt),
      status: "active",
    });
    schedules.value.unshift(schedule);
    setMessage("已建立 schedule。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function toggleSchedule(schedule: GeoScheduleResource): Promise<void> {
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const updated = await api.geoAnalysis.updateSchedule(schedule.id, {
      platformId: schedule.platformId,
      frequency: schedule.frequency,
      priority: schedule.priority,
      timezone: schedule.timezone,
      nextRunAt: schedule.nextRunAt,
      status: schedule.status === "active" ? "paused" : "active",
    });
    schedules.value = schedules.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    setMessage("已更新 schedule 狀態。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function deleteSchedule(scheduleId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (!usingMockData.value) await api.geoAnalysis.deleteSchedule(scheduleId);
    schedules.value = schedules.value.filter((schedule) => schedule.id !== scheduleId);
    setMessage("已刪除 schedule。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function createManualJob(): Promise<void> {
  if (!jobForm.queryId) return;
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const job = await api.geoAnalysis.createJob(jobForm.queryId, {
      platformId: jobForm.platformId,
      scheduledFor: null,
      priority: jobForm.priority,
      jobType: "manual_run",
    });
    jobs.value.unshift(job);
    setMessage("已建立 manual run job。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function dispatchJob(jobId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const job = await api.geoAnalysis.dispatchJob(jobId);
    jobs.value = jobs.value.map((item) => (item.id === job.id ? job : item));
    setMessage("已派發 job。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}

async function cancelJob(jobId: string): Promise<void> {
  actionLoading.value = true;
  try {
    if (usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const job = await api.geoAnalysis.cancelJob(jobId);
    jobs.value = jobs.value.map((item) => (item.id === job.id ? job : item));
    setMessage("已取消 job。");
  } catch (error) {
    setMessage(getErrorMessage(error));
  } finally {
    actionLoading.value = false;
  }
}
</script>

<template>
  <section class="page geo-page geo-analysis-page">
    <header class="page-header geo-analysis-header">
      <div>
        <p class="page-kicker">GEO Analysis</p>
        <h1>{{ pageTitle }}</h1>
        <p>
          管理 GEO project、entity、topic、query、排程與 run job；報表彙總區塊目前使用示意資料。
        </p>
      </div>
      <div class="page-actions">
        <select
          v-model="selectedProjectId"
          class="geo-project-select"
          :disabled="loading || projects.length === 0"
        >
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }}
          </option>
        </select>
        <button class="button button-secondary" type="button" :disabled="loading" @click="loadProjects">
          <AppIcon name="refresh" :size="16" />重新整理
        </button>
      </div>
    </header>

    <div v-if="usingMockData" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />
      API 無法使用，目前顯示示意資料；新增與派發操作會提示未呼叫 API。
    </div>
    <div v-else class="mock-notice">
      <AppIcon name="alert-circle" :size="17" />
      平台總表與 Reports KPI 尚缺 API，相關區塊以示意資料呈現。
    </div>
    <div v-if="errorMessage" class="geo-error-message">{{ errorMessage }}</div>

    <div v-if="loading && !selectedProject && activeTab !== 'projects'" class="empty-state">
      <AppIcon name="refresh" />
      <strong>正在載入 GEO 資料</strong>
      <span>請稍候。</span>
    </div>

    <div v-else-if="!selectedProject && activeTab !== 'projects'" class="empty-state">
      <AppIcon name="layers" />
      <strong>尚未建立 GEO project</strong>
      <span>請在 Projects 建立第一個專案。</span>
    </div>

    <template v-else>
      <section v-if="activeTab === 'overview'" class="geo-section-stack">
        <div class="stat-grid">
          <article v-for="stat in overviewStats" :key="stat.label" class="stat-card">
            <div class="stat-card-heading">
              <span class="stat-icon" :class="stat.tone">
                <AppIcon name="activity" :size="18" />
              </span>
              {{ stat.label }}
            </div>
            <strong>{{ stat.value }}</strong>
            <div class="stat-metrics">{{ stat.detail }}</div>
          </article>
        </div>

        <div class="geo-two-column">
          <article class="card">
            <header class="card-header">
              <div>
                <h2>Visibility Trend</h2>
                <p>示意資料，等待報表趨勢 API。</p>
              </div>
              <span class="badge badge-warning">Mock</span>
            </header>
            <div class="geo-trend">
              <div v-for="point in fallback.trendPoints" :key="point.label" class="geo-trend-point">
                <span class="geo-trend-bar" :style="{ height: `${point.visibility}%` }" />
                <small>{{ point.label }}</small>
              </div>
            </div>
          </article>

          <article class="card">
            <header class="card-header">
              <div>
                <h2>Recent Jobs</h2>
                <p>來自 `/api/geo/projects/{projectId}/jobs`。</p>
              </div>
            </header>
            <div class="table-scroll">
              <table class="data-table geo-table">
                <thead>
                  <tr>
                    <th>Query</th>
                    <th>Platform</th>
                    <th>Status</th>
                    <th>Scheduled</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="job in selectedProjectJobs.slice(0, 5)" :key="job.id">
                    <td>{{ getQuery(job.queryId)?.queryText ?? "-" }}</td>
                    <td>{{ getPlatform(job.platformId) }}</td>
                    <td><span :class="badgeClass(job.status)">{{ job.status }}</span></td>
                    <td>{{ formatDate(job.scheduledFor) }}</td>
                  </tr>
                  <tr v-if="selectedProjectJobs.length === 0">
                    <td colspan="4">尚無 job。</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>

      <section v-else-if="activeTab === 'projects'" class="geo-section-stack">
        <article class="card geo-form-card">
          <header class="card-header">
            <div>
              <h2>建立 Project</h2>
              <p>customer/task 顯示名稱由既有 customers/tasks API 補齊。</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createProject">
            <label>
              Project 名稱
              <input v-model="projectForm.name" type="text" placeholder="金山旅宿 GEO 追蹤" />
            </label>
            <label>
              Customer
              <select v-if="customers.length" v-model="projectForm.customerId">
                <option value="">請選擇 customer</option>
                <option v-for="customer in customers" :key="customer.id" :value="customer.id">
                  {{ customer.name }}
                </option>
              </select>
              <input v-else v-model="projectForm.customerId" type="text" placeholder="customer UUID" />
            </label>
            <label>
              SEO Task
              <select v-if="tasks.length" v-model="projectForm.seoTaskId">
                <option value="">不綁定 task</option>
                <option v-for="task in tasks" :key="task.id" :value="task.id">
                  {{ task.name }}
                </option>
              </select>
              <input v-else v-model="projectForm.seoTaskId" type="text" placeholder="seo task UUID，可留空" />
            </label>
            <label>
              Region
              <input v-model="projectForm.defaultRegion" type="text" />
            </label>
            <label>
              Language
              <input v-model="projectForm.defaultLanguage" type="text" />
            </label>
            <label>
              Daily Budget
              <input v-model.number="projectForm.dailyRunBudget" type="number" min="0" />
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit" :disabled="actionLoading">
                <AppIcon name="plus" :size="16" />建立 Project
              </button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header geo-card-toolbar">
            <div>
              <h2>Projects</h2>
              <p>共 {{ projects.length }} 筆。</p>
            </div>
            <label class="geo-search-field">
              <AppIcon name="search" :size="16" />
              <input v-model="projectSearch" type="search" placeholder="搜尋 project、customer、task" />
            </label>
          </header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Customer</th>
                  <th>Task</th>
                  <th>Locale</th>
                  <th>Status</th>
                  <th>Budget</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="project in filteredProjects" :key="project.id">
                  <td><strong>{{ project.name }}</strong><small>{{ shortId(project.id) }}</small></td>
                  <td>{{ project.customerName }}</td>
                  <td>{{ project.seoTaskName ?? "-" }}</td>
                  <td>{{ project.defaultRegion }} / {{ project.defaultLanguage }}</td>
                  <td><span :class="badgeClass(project.status)">{{ project.status }}</span></td>
                  <td>{{ project.dailyRunBudget }}</td>
                  <td>
                    <button class="text-button text-error" type="button" @click="deleteProject(project.id)">
                      刪除
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'entities'" class="geo-section-stack">
        <article class="card geo-form-card">
          <header class="card-header">
            <h2>建立 Entity</h2>
          </header>
          <form class="geo-form-grid" @submit.prevent="createEntity">
            <label>
              Type
              <select v-model="entityForm.entityType">
                <option value="brand">brand</option>
                <option value="competitor">competitor</option>
                <option value="website">website</option>
                <option value="partner">partner</option>
              </select>
            </label>
            <label>
              名稱
              <input v-model="entityForm.name" type="text" placeholder="金山旅宿" />
            </label>
            <label>
              Website URL
              <input v-model="entityForm.websiteUrl" type="url" placeholder="https://example.com" />
            </label>
            <label>
              Alias
              <input v-model="entityForm.alias" type="text" placeholder="品牌別名或網域" />
            </label>
            <label class="geo-form-full">
              描述
              <textarea v-model="entityForm.description" rows="3" placeholder="用於 mention extraction 的品牌描述"></textarea>
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit" :disabled="actionLoading">建立 Entity</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header"><h2>Entities</h2></header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Aliases</th>
                  <th>Website</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="entity in entities" :key="entity.id">
                  <td><strong>{{ entity.name }}</strong><small>{{ entity.description || "-" }}</small></td>
                  <td>{{ entity.entityType }}</td>
                  <td>{{ getAliases(entity.id) }}</td>
                  <td>{{ entity.websiteUrl ?? "-" }}</td>
                  <td><span :class="badgeClass(entity.status)">{{ entity.status }}</span></td>
                  <td>
                    <button class="text-button text-error" type="button" @click="deleteEntity(entity.id)">
                      刪除
                    </button>
                  </td>
                </tr>
                <tr v-if="entities.length === 0"><td colspan="6">尚無 entity。</td></tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'queries'" class="geo-section-stack">
        <div class="geo-two-column">
          <article class="card geo-form-card">
            <header class="card-header"><h2>Topics</h2></header>
            <form class="geo-compact-form" @submit.prevent="createTopic">
              <label>
                Topic
                <input v-model="topicForm.name" type="text" placeholder="溫泉住宿推薦" />
              </label>
              <label>
                Description
                <textarea v-model="topicForm.description" rows="3"></textarea>
              </label>
              <button class="button button-primary" type="submit" :disabled="actionLoading">建立 Topic</button>
            </form>
          </article>

          <article class="card geo-form-card">
            <header class="card-header"><h2>Queries</h2></header>
            <form class="geo-form-grid" @submit.prevent="createQuery">
              <label>
                Topic
                <select v-model="queryForm.topicId">
                  <option value="">不指定</option>
                  <option v-for="topic in topics" :key="topic.id" :value="topic.id">
                    {{ topic.name }}
                  </option>
                </select>
              </label>
              <label>
                Stage
                <input v-model="queryForm.buyerStage" type="text" />
              </label>
              <label>
                Priority
                <select v-model="queryForm.priority">
                  <option value="low">low</option>
                  <option value="normal">normal</option>
                  <option value="high">high</option>
                </select>
              </label>
              <label>
                Intent
                <input v-model="queryForm.intent" type="text" />
              </label>
              <label>
                Market
                <select v-model="queryForm.marketType">
                  <option value="b2c">B2C</option>
                  <option value="b2b_procurement">B2B procurement</option>
                </select>
              </label>
              <label class="geo-checkbox">
                <input v-model="queryForm.isBranded" type="checkbox" />
                Branded query
              </label>
              <label class="geo-form-full">
                Query
                <textarea v-model="queryForm.queryText" rows="3" placeholder="北海岸適合週末放鬆的溫泉住宿推薦"></textarea>
              </label>
              <div class="geo-form-actions">
                <button class="button button-primary" type="submit" :disabled="actionLoading">建立 Query</button>
              </div>
            </form>
          </article>
        </div>

        <article class="card">
          <header class="card-header geo-card-toolbar">
            <div>
              <h2>Query List</h2>
              <p>支援搜尋與 stage / priority 篩選。</p>
            </div>
            <div class="geo-toolbar-controls">
              <label class="geo-search-field">
                <AppIcon name="search" :size="16" />
                <input v-model="querySearch" type="search" placeholder="搜尋 query、topic、intent" />
              </label>
              <select v-model="queryStageFilter">
                <option value="">Stage</option>
                <option value="awareness">awareness</option>
                <option value="consideration">consideration</option>
                <option value="decision">decision</option>
              </select>
              <select v-model="queryPriorityFilter">
                <option value="">Priority</option>
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </div>
          </header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Topic</th>
                  <th>Intent</th>
                  <th>Stage</th>
                  <th>Branded</th>
                  <th>Priority</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="query in filteredQueries" :key="query.id">
                  <td><strong>{{ query.queryText }}</strong><small>{{ query.region }} / {{ query.language }}</small></td>
                  <td>{{ getTopic(query.topicId)?.name ?? "-" }}</td>
                  <td><code>{{ query.intent ?? "-" }}</code></td>
                  <td>{{ query.buyerStage ?? "-" }}</td>
                  <td>{{ query.isBranded ? "是" : "否" }}</td>
                  <td><span :class="badgeClass(query.priority)">{{ query.priority }}</span></td>
                  <td>
                    <button class="text-button text-error" type="button" @click="deleteQuery(query.id)">
                      刪除
                    </button>
                  </td>
                </tr>
                <tr v-if="filteredQueries.length === 0"><td colspan="7">找不到符合條件的 query。</td></tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'schedules'" class="geo-section-stack">
        <div class="geo-platform-grid">
          <article v-for="platform in platformSummaries" :key="platform.id" class="card geo-platform-card">
            <strong>{{ platform.name }}</strong>
            <span>{{ platform.model }}</span>
            <small>{{ platform.assignmentCount }} assignments / {{ platform.scheduleCount }} schedules</small>
            <span :class="badgeClass(platform.status)">{{ platform.status }}</span>
          </article>
        </div>

        <article class="card geo-form-card">
          <header class="card-header">
            <div>
              <h2>建立 Schedule</h2>
              <p>平台 ID 依後端 README 建議 seed；缺平台總表 API 已列入缺口文件。</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createSchedule">
            <label>
              Query
              <select v-model="scheduleForm.queryId">
                <option value="">請選擇 query</option>
                <option v-for="query in selectedProjectQueries" :key="query.id" :value="query.id">
                  {{ query.queryText }}
                </option>
              </select>
            </label>
            <label>
              Platform
              <select v-model="scheduleForm.platformId">
                <option v-for="platform in geoPlatformCatalog" :key="platform.id" :value="platform.id">
                  {{ platform.name }} / {{ platform.model }}
                </option>
              </select>
            </label>
            <label>
              Frequency
              <select v-model="scheduleForm.frequency">
                <option value="daily">daily</option>
                <option value="weekly">weekly</option>
                <option value="manual">manual</option>
              </select>
            </label>
            <label>
              Priority
              <select v-model="scheduleForm.priority">
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </label>
            <label>
              Timezone
              <input v-model="scheduleForm.timezone" type="text" />
            </label>
            <label>
              Next run
              <input v-model="scheduleForm.nextRunAt" type="datetime-local" />
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit" :disabled="actionLoading">建立 Schedule</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header"><h2>Schedules</h2></header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Platform</th>
                  <th>Frequency</th>
                  <th>Next run</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="schedule in schedules" :key="schedule.id">
                  <td>{{ getQuery(schedule.queryId)?.queryText ?? "-" }}</td>
                  <td>{{ getPlatform(schedule.platformId) }}</td>
                  <td>{{ schedule.frequency }} / {{ schedule.timezone }}</td>
                  <td>{{ formatDate(schedule.nextRunAt) }}</td>
                  <td><span :class="badgeClass(schedule.status)">{{ schedule.status }}</span></td>
                  <td>
                    <div class="row-actions">
                      <button class="text-button" type="button" @click="toggleSchedule(schedule)">切換</button>
                      <button class="text-button text-error" type="button" @click="deleteSchedule(schedule.id)">刪除</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="schedules.length === 0"><td colspan="6">尚無 schedule。</td></tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'jobs'" class="geo-section-stack">
        <article class="card geo-form-card">
          <header class="card-header">
            <div>
              <h2>Manual Run</h2>
              <p>建立 job 後可透過 Dispatch 呼叫 publisher。</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createManualJob">
            <label>
              Query
              <select v-model="jobForm.queryId">
                <option value="">請選擇 query</option>
                <option v-for="query in selectedProjectQueries" :key="query.id" :value="query.id">
                  {{ query.queryText }}
                </option>
              </select>
            </label>
            <label>
              Platform
              <select v-model="jobForm.platformId">
                <option v-for="platform in geoPlatformCatalog" :key="platform.id" :value="platform.id">
                  {{ platform.name }}
                </option>
              </select>
            </label>
            <label>
              Priority
              <select v-model="jobForm.priority">
                <option value="low">low</option>
                <option value="normal">normal</option>
                <option value="high">high</option>
              </select>
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit" :disabled="actionLoading">建立 Manual Run</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header geo-card-toolbar">
            <div>
              <h2>Jobs</h2>
              <p>共 {{ selectedProjectJobs.length }} 筆。</p>
            </div>
            <div class="geo-toolbar-controls">
              <label class="geo-search-field">
                <AppIcon name="search" :size="16" />
                <input v-model="jobSearch" type="search" placeholder="搜尋 query、platform、dedupe key" />
              </label>
              <select v-model="jobPlatformFilter">
                <option value="">Platform</option>
                <option v-for="platform in geoPlatformCatalog" :key="platform.id" :value="platform.id">
                  {{ platform.name }}
                </option>
              </select>
              <select v-model="jobStatusFilter">
                <option value="">Status</option>
                <option value="pending">pending</option>
                <option value="published">published</option>
                <option value="running_external">running_external</option>
                <option value="succeeded">succeeded</option>
                <option value="failed">failed</option>
                <option value="cancelled">cancelled</option>
              </select>
            </div>
          </header>
          <div class="table-scroll">
            <table class="data-table geo-table geo-job-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Platform</th>
                  <th>Status</th>
                  <th>Dedupe key</th>
                  <th>Attempts</th>
                  <th>Dispatch</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="job in filteredJobs" :key="job.id">
                  <td>{{ getQuery(job.queryId)?.queryText ?? "-" }}</td>
                  <td>{{ getPlatform(job.platformId) }}</td>
                  <td><span :class="badgeClass(job.status)">{{ job.status }}</span></td>
                  <td><code>{{ job.dedupeKey }}</code></td>
                  <td>{{ job.attemptCount }} / {{ job.maxAttempts }}</td>
                  <td>{{ job.dispatchBackend ?? "-" }} <small>{{ job.dispatchMessageId ?? "" }}</small></td>
                  <td>
                    <div class="row-actions">
                      <button class="text-button" type="button" @click="dispatchJob(job.id)">Dispatch</button>
                      <button class="text-button text-error" type="button" @click="cancelJob(job.id)">Cancel</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="filteredJobs.length === 0"><td colspan="7">找不到符合條件的 job。</td></tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else class="geo-section-stack">
        <div class="mock-notice subtle">
          <AppIcon name="alert-circle" :size="17" />
          Reports KPI、topic performance、recommendations 與 AI answer analysis 尚缺 API，以下使用示意資料。
        </div>

        <div class="geo-report-grid">
          <article v-for="metric in fallback.reportMetrics" :key="metric.id" class="card geo-metric-card">
            <span :class="`text-${metric.tone}`">{{ metric.delta }}</span>
            <strong>{{ metric.value }}</strong>
            <h2>{{ metric.label }}</h2>
            <p>{{ metric.description }}</p>
          </article>
        </div>

        <div class="geo-two-column">
          <article class="card">
            <header class="card-header"><h2>Topic Performance</h2></header>
            <div class="table-scroll">
              <table class="data-table geo-table">
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Visibility</th>
                    <th>SOV</th>
                    <th>Queries</th>
                    <th>Best platform</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="topic in fallback.topicPerformance" :key="topic.topicId">
                    <td>{{ topic.topicName }}</td>
                    <td>{{ topic.visibility }}%</td>
                    <td>{{ topic.sov }}%</td>
                    <td>{{ topic.queryCount }}</td>
                    <td>{{ topic.betterPerformer }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <article class="card">
            <header class="card-header"><h2>Recommendations</h2></header>
            <div class="geo-list">
              <div v-for="item in fallback.recommendations" :key="item.id" class="geo-list-item">
                <span :class="badgeClass(item.priority)">{{ item.priority }}</span>
                <strong>{{ item.title }}</strong>
                <p>{{ item.description }}</p>
              </div>
            </div>
          </article>
        </div>

        <article class="card">
          <header class="card-header">
            <div>
              <h2>Run Results</h2>
              <p>raw response 與 references 來自 API；分析摘要仍為後續功能。</p>
            </div>
          </header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Query</th>
                  <th>Provider</th>
                  <th>Status</th>
                  <th>Run at</th>
                  <th>References</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="result in selectedProjectRunResults" :key="result.id">
                  <td>{{ getQuery(result.queryId)?.queryText ?? "-" }}</td>
                  <td>{{ result.surface }} / {{ result.model }}</td>
                  <td><span :class="badgeClass(result.status)">{{ result.status }}</span></td>
                  <td>{{ formatDate(result.runAt) }}</td>
                  <td>{{ result.references.length }}</td>
                  <td>{{ result.error ?? "-" }}</td>
                </tr>
                <tr v-if="selectedProjectRunResults.length === 0"><td colspan="6">尚無 run result。</td></tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="card">
          <header class="card-header">
            <div>
              <h2>AI Answer Samples</h2>
              <p>示意資料，等待 answer analysis / citation analysis API。</p>
            </div>
          </header>
          <div class="geo-answer-grid">
            <section v-for="sample in fallback.aiAnswerSamples" :key="sample.id" class="geo-answer-card">
              <div class="geo-answer-head">
                <span class="badge badge-info">{{ sample.platform }}</span>
                <span :class="badgeClass(sample.sentiment)">{{ sample.sentiment }}</span>
              </div>
              <h3>{{ sample.queryText }}</h3>
              <p>{{ sample.answerSummary }}</p>
              <small>Mentions：{{ sample.mentionedEntities.join("、") }}</small>
              <small>Citations：{{ sample.citations.join("、") }}</small>
            </section>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>
