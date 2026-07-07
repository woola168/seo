<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import { geoPlatformCatalog } from "../mocks/geo-analysis";
import { ApiError, api } from "../services/api";
import type {
  GeoAnalysisRunResult,
  GeoEntityResource,
  GeoJobResource,
  GeoMarketType,
  GeoProjectResource,
  GeoProvider,
  GeoQueryDraftResource,
  GeoQueryGenerationRunResource,
  GeoQueryProvider,
  GeoQueryResearchRunResource,
  GeoQueryResource,
  GeoRegion,
  GeoTopicInput,
} from "../types";
import {
  toFieldErrorMap,
  validateGenerationStep,
  validateProjectStep,
  validateResearchStep,
  type GeoFlowValidationError,
} from "../utils/geo-flow-validation";
import {
  buildFlowEntityRequests,
  parseCompetitorEntityInputs,
} from "../utils/geo-flow-entities";

type StepKey = "project" | "library" | "setup" | "research" | "drafts" | "dispatch" | "results";
type ModalState =
  | { kind: "query"; item: GeoQueryResource }
  | { kind: "job"; item: GeoJobResource }
  | { kind: "result"; item: GeoAnalysisRunResult }
  | null;

const steps: Array<{ key: StepKey; label: string }> = [
  { key: "project", label: "Project" },
  { key: "library", label: "既有資料" },
  { key: "setup", label: "Query 設定" },
  { key: "research", label: "Research" },
  { key: "drafts", label: "Drafts" },
  { key: "dispatch", label: "Dispatch" },
  { key: "results", label: "Results" },
];

const platformOptions = [
  {
    provider: "gemini" as GeoProvider,
    platformId: "11111111-1111-4111-8111-111111111102",
    label: "Gemini",
  },
  {
    provider: "google_aio" as GeoProvider,
    platformId: "11111111-1111-4111-8111-111111111105",
    label: "Google AIO",
  },
];

const intentCategoryOptions = [
  {
    value: "navigational",
    label: "導航型",
    description: "使用者想找到特定品牌、產品、官網、門市或已知服務的查詢。",
  },
  {
    value: "informational",
    label: "資訊型",
    description: "使用者想理解概念、規格、比較條件、操作方式或常見問題的查詢。",
  },
  {
    value: "commercial_investigation",
    label: "商業評估",
    description: "使用者正在比較供應商、產品方案、導入條件或採購評估的查詢。",
  },
  {
    value: "transactional",
    label: "交易型",
    description: "使用者已接近詢價、購買、預約、下載或聯繫業務的查詢。",
  },
];

const activeStep = ref<StepKey>("project");
const router = useRouter();
const loading = ref(false);
const polling = ref(false);
const actionError = ref("");
const validationErrors = ref<GeoFlowValidationError[]>([]);
const projects = ref<GeoProjectResource[]>([]);
const selectedProjectId = ref("");
const savedQueries = ref<GeoQueryResource[]>([]);
const savedJobs = ref<GeoJobResource[]>([]);
const savedRunResults = ref<GeoAnalysisRunResult[]>([]);
const savedEntities = ref<GeoEntityResource[]>([]);
const selectedQueryIds = ref<string[]>([]);
const selectedDraftIds = ref<string[]>([]);
const acceptedQueries = ref<GeoQueryResource[]>([]);
const dispatchedJobs = ref<GeoJobResource[]>([]);
const jobResults = ref<Record<string, GeoAnalysisRunResult[]>>({});
const researchRun = ref<GeoQueryResearchRunResource | null>(null);
const generationRun = ref<GeoQueryGenerationRunResource | null>(null);
const modal = ref<ModalState>(null);
const kmindhubStatus = ref<"unknown" | "ready" | "missing" | "error">("unknown");
const kmindhubMessage = ref("");
let pollTimer: ReturnType<typeof setTimeout> | undefined;
let pollAttempts = 0;

const projectForm = reactive({
  name: "GEO Flow Check",
  customerId: "",
  seoTaskId: "",
  defaultRegion: "TW" as GeoRegion,
  defaultLanguage: "zh-TW",
});

const queryForm = reactive({
  provider: "gemini" as GeoQueryProvider,
  runProvider: "gemini" as GeoProvider,
  brandName: "",
  brandWebsiteUrl: "",
  competitorBrands: "",
  keywords: "",
  region: "TW" as GeoRegion,
  language: "zh-TW",
  marketType: "b2b_procurement" as GeoMarketType,
  topics: [{ name: "", description: "" }] as GeoTopicInput[],
  intentCategory: "commercial_investigation",
  intentDescription: "比較供應商、產品方案或導入條件",
  audienceName: "B2B 採購",
  audienceDescription: "正在評估供應商、產品規格與導入風險的採購或決策者",
  shouldMentionOwnBrand: true,
  shouldMentionCompetitor: true,
  maxQueries: 8,
});

const selectedProject = computed(() =>
  projects.value.find((project) => project.id === selectedProjectId.value),
);
const selectedPlatform = computed(
  () =>
    platformOptions.find((option) => option.provider === queryForm.runProvider) ??
    platformOptions[0],
);
const normalizedKeywords = computed(() => splitValues(queryForm.keywords));
const normalizedCompetitors = computed(() =>
  parseCompetitorEntityInputs(queryForm.competitorBrands).map((item) => item.name),
);
const reportEntitySummary = computed(() => {
  const requests = buildFlowEntityRequests({
    brandName: queryForm.brandName,
    brandWebsiteUrl: queryForm.brandWebsiteUrl,
    competitorBrands: queryForm.competitorBrands,
    existingEntities: savedEntities.value,
  });
  return {
    ownBrandName: requests.ownBrand?.request.name ?? "",
    competitorCount: requests.competitors.length,
  };
});
const normalizedTopics = computed<GeoTopicInput[]>(() =>
  queryForm.topics
    .map((topic) => ({
      name: topic.name.trim(),
      description: topic.description.trim(),
    }))
    .filter((topic) => topic.name),
);
const fieldErrors = computed(() => toFieldErrorMap(validationErrors.value));
const validationSummary = computed(() => validationErrors.value.map((error) => error.message));
const selectedQueries = computed(() =>
  savedQueries.value.filter((query) => selectedQueryIds.value.includes(query.id)),
);
const acceptedOrSelectedQueries = computed(() =>
  acceptedQueries.value.length ? acceptedQueries.value : selectedQueries.value,
);
const dispatchedJobIds = computed(() => dispatchedJobs.value.map((job) => job.id));
const allDispatchedJobsDone = computed(() =>
  dispatchedJobs.value.length > 0 &&
  dispatchedJobs.value.every((job) => ["succeeded", "failed", "cancelled"].includes(job.status)),
);

onMounted(() => {
  void loadProjects();
  void refreshKmindhubStatus();
});

onBeforeUnmount(() => {
  stopPolling();
});

async function loadProjects(): Promise<void> {
  await runAction(async () => {
    const response = await api.geoAnalysis.projects();
    projects.value = response.items;
    if (!selectedProjectId.value && response.items.length) {
      selectProject(response.items[0].id);
    }
  });
}

function selectProject(projectId: string): void {
  selectedProjectId.value = projectId;
  const project = projects.value.find((item) => item.id === projectId);
  if (project) fillProjectForm(project);
  resetProjectData();
  if (projectId) void refreshProjectData(projectId);
}

async function saveProjectAndContinue(): Promise<void> {
  const errors = validateProjectStep({
    projectId: selectedProjectId.value,
    projectName: projectForm.name,
  });
  if (projectForm.seoTaskId.trim() && !projectForm.customerId.trim()) {
    errors.push({ field: "customerId", message: "填寫 seoTaskId 時也請填 customerId" });
  }
  if (!setValidation(errors)) return;

  await runAction(async () => {
    const project = selectedProjectId.value
      ? await api.geoAnalysis.updateProject(selectedProjectId.value, projectRequestFromForm())
      : await api.geoAnalysis.createProject(projectRequestFromForm());
    projects.value = selectedProjectId.value
      ? projects.value.map((item) => (item.id === project.id ? project : item))
      : [project, ...projects.value];
    selectedProjectId.value = project.id;
    fillProjectForm(project);
    await refreshProjectData(project.id);
    activeStep.value = "library";
  });
}

async function refreshProjectData(projectId = selectedProjectId.value): Promise<void> {
  if (!projectId) return;
  const [queries, jobs, results, entities] = await Promise.all([
    api.geoAnalysis.queries(projectId),
    api.geoAnalysis.jobs(projectId),
    api.geoAnalysis.runResults(projectId),
    api.geoAnalysis.entities(projectId),
  ]);
  savedQueries.value = queries.items;
  savedJobs.value = jobs.items;
  savedRunResults.value = results.items;
  savedEntities.value = entities.items;
  selectedQueryIds.value = selectedQueryIds.value.filter((id) =>
    queries.items.some((query) => query.id === id),
  );
}

async function refreshKmindhubStatus(): Promise<void> {
  kmindhubStatus.value = "unknown";
  kmindhubMessage.value = "";
  try {
    const mapping = await api.geoAnalysis.kmindhubWorkspace();
    kmindhubStatus.value = "ready";
    kmindhubMessage.value = `${mapping.displayName} / ${shortId(mapping.workspaceId)}`;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      kmindhubStatus.value = "missing";
      kmindhubMessage.value =
        "KMindHub workspace 尚未綁定，新版 semantic analysis 會無法產生報表 facts。";
      return;
    }
    kmindhubStatus.value = "error";
    kmindhubMessage.value = getErrorMessage(error);
  }
}

function startNewQueryFlow(): void {
  validationErrors.value = [];
  actionError.value = "";
  researchRun.value = null;
  generationRun.value = null;
  selectedDraftIds.value = [];
  acceptedQueries.value = [];
  dispatchedJobs.value = [];
  jobResults.value = {};
  activeStep.value = "setup";
}

function toggleQuery(queryId: string): void {
  selectedQueryIds.value = selectedQueryIds.value.includes(queryId)
    ? selectedQueryIds.value.filter((id) => id !== queryId)
    : [...selectedQueryIds.value, queryId];
}

function toggleDraft(draftId: string): void {
  selectedDraftIds.value = selectedDraftIds.value.includes(draftId)
    ? selectedDraftIds.value.filter((id) => id !== draftId)
    : [...selectedDraftIds.value, draftId];
}

function addTopic(): void {
  queryForm.topics.push({ name: "", description: "" });
}

function removeTopic(index: number): void {
  if (queryForm.topics.length <= 1) return;
  queryForm.topics.splice(index, 1);
}

async function runResearch(): Promise<void> {
  if (!setValidation(researchValidation())) return;
  await runAction(async () => {
    await ensureReportEntities();
    researchRun.value = await api.geoAnalysis.runQueryResearch(selectedProjectId.value, {
      provider: queryForm.provider,
      brandName: queryForm.brandName.trim(),
      competitorBrands: normalizedCompetitors.value,
      keywords: normalizedKeywords.value,
      region: queryForm.region,
      language: valueOrNull(queryForm.language),
      marketType: queryForm.marketType,
      intents: [
        {
          category: queryForm.intentCategory.trim(),
          description: queryForm.intentDescription.trim(),
        },
      ],
      audience: {
        name: queryForm.audienceName.trim(),
        description: queryForm.audienceDescription.trim(),
      },
      brandMentionRules: {
        shouldMentionOwnBrand: queryForm.shouldMentionOwnBrand,
        shouldMentionCompetitor: queryForm.shouldMentionCompetitor,
      },
    });
    generationRun.value = null;
    selectedDraftIds.value = [];
    activeStep.value = "research";
  });
}

async function ensureReportEntities(): Promise<void> {
  if (!selectedProjectId.value) return;
  const requests = buildFlowEntityRequests({
    brandName: queryForm.brandName,
    brandWebsiteUrl: queryForm.brandWebsiteUrl,
    competitorBrands: queryForm.competitorBrands,
    existingEntities: savedEntities.value,
  });
  const upserts = [
    ...(requests.ownBrand ? [requests.ownBrand] : []),
    ...requests.competitors,
  ];
  for (const upsert of upserts) {
    if (upsert.existing) {
      await api.geoAnalysis.updateEntity(upsert.existing.id, upsert.request);
    } else {
      await api.geoAnalysis.createEntity(selectedProjectId.value, upsert.request);
    }
  }
  if (upserts.length) await refreshProjectData();
}

async function runGeneration(): Promise<void> {
  const errors = validateGenerationStep(generationValidationInput());
  if (!researchRun.value?.result?.researchContext) {
    errors.push({ field: "research", message: "請先完成 Query Research" });
  }
  if (!setValidation(errors)) return;
  await runAction(async () => {
    generationRun.value = await api.geoAnalysis.runQueryGeneration(selectedProjectId.value, {
      seoTaskId: projectForm.seoTaskId.trim(),
      provider: queryForm.provider,
      brandName: queryForm.brandName.trim(),
      competitorBrands: normalizedCompetitors.value,
      keywords: normalizedKeywords.value,
      region: queryForm.region,
      language: valueOrNull(queryForm.language),
      marketType: queryForm.marketType,
      topics: normalizedTopics.value,
      topicNames: normalizedTopics.value.map((topic) => topic.name),
      intents: [
        {
          category: queryForm.intentCategory.trim(),
          description: queryForm.intentDescription.trim(),
        },
      ],
      audience: {
        name: queryForm.audienceName.trim(),
        description: queryForm.audienceDescription.trim(),
      },
      brandMentionRules: {
        shouldMentionOwnBrand: queryForm.shouldMentionOwnBrand,
        shouldMentionCompetitor: queryForm.shouldMentionCompetitor,
      },
      researchContext: researchRun.value?.result?.researchContext ?? null,
      maxQueries: queryForm.maxQueries,
    });
    selectedDraftIds.value = generationRun.value.drafts.slice(0, 3).map((draft) => draft.id);
    activeStep.value = "drafts";
  });
}

async function acceptSelectedDrafts(): Promise<void> {
  if (!selectedDraftIds.value.length) {
    setValidation([{ field: "draft", message: "請至少選擇一筆 draft" }]);
    return;
  }
  await runAction(async () => {
    const accepted: GeoQueryResource[] = [];
    for (const draftId of selectedDraftIds.value) {
      const query = await api.geoAnalysis.acceptQueryDraft(draftId, {
        createTopicIfMissing: true,
        status: "active",
      });
      accepted.push(query);
    }
    acceptedQueries.value = accepted;
    selectedQueryIds.value = accepted.map((query) => query.id);
    await refreshProjectData();
    activeStep.value = "dispatch";
  });
}

async function dispatchSelectedQueries(): Promise<void> {
  const queries = acceptedOrSelectedQueries.value;
  if (!queries.length) {
    setValidation([{ field: "acceptedQuery", message: "請至少選擇一筆正式 query" }]);
    return;
  }
  const errors = queries.flatMap((query) =>
    validateDispatchInput(query.id).map((error) => ({
      ...error,
      message: `${shortId(query.id)}: ${error.message}`,
    })),
  );
  if (!setValidation(errors)) return;

  await runAction(async () => {
    const jobs: GeoJobResource[] = [];
    for (const query of queries) {
      await api.geoAnalysis.replaceQueryPlatforms(query.id, [
        {
          platformId: selectedPlatform.value.platformId,
          model: null,
          status: "active",
        },
      ]);
      const created = await api.geoAnalysis.createJob(query.id, {
        platformId: selectedPlatform.value.platformId,
        scheduledFor: null,
        priority: "normal",
        jobType: "manual_run",
      });
      const dispatched = await api.geoAnalysis.dispatchJob(created.id);
      jobs.push(dispatched);
    }
    dispatchedJobs.value = jobs;
    await refreshProjectData();
    activeStep.value = "results";
    startPolling();
  });
}

async function selectExistingJob(job: GeoJobResource): Promise<void> {
  dispatchedJobs.value = [job];
  jobResults.value = {
    [job.id]: (await api.geoAnalysis.jobRunResults(job.id)).items,
  };
  const query = savedQueries.value.find((item) => item.id === job.queryId);
  if (query) selectedQueryIds.value = [query.id];
  activeStep.value = "results";
}

async function refreshResults(): Promise<void> {
  await runAction(async () => {
    await refreshProjectData();
    for (const job of dispatchedJobs.value) {
      const refreshed = await api.geoAnalysis.job(job.id);
      dispatchedJobs.value = dispatchedJobs.value.map((item) =>
        item.id === refreshed.id ? refreshed : item,
      );
      jobResults.value[refreshed.id] = (await api.geoAnalysis.jobRunResults(refreshed.id)).items;
    }
  });
}

function startPolling(): void {
  stopPolling();
  polling.value = true;
  pollAttempts = 0;
  void pollOnce();
}

function stopPolling(): void {
  if (pollTimer) clearTimeout(pollTimer);
  pollTimer = undefined;
  polling.value = false;
}

async function pollOnce(): Promise<void> {
  if (!dispatchedJobs.value.length) {
    stopPolling();
    return;
  }
  try {
    const nextJobs: GeoJobResource[] = [];
    const nextResults: Record<string, GeoAnalysisRunResult[]> = {};
    for (const item of dispatchedJobs.value) {
      const refreshed = await api.geoAnalysis.job(item.id);
      nextJobs.push(refreshed);
      nextResults[refreshed.id] = (await api.geoAnalysis.jobRunResults(refreshed.id)).items;
    }
    dispatchedJobs.value = nextJobs;
    jobResults.value = { ...jobResults.value, ...nextResults };
    if (allDispatchedJobsDone.value) {
      await refreshProjectData();
      stopPolling();
      return;
    }
    pollAttempts += 1;
    if (pollAttempts >= 40) {
      await refreshProjectData();
      stopPolling();
      actionError.value = "輪詢已暫停，請稍後按重新整理查看最新 job 狀態。";
      return;
    }
    pollTimer = setTimeout(() => void pollOnce(), 3000);
  } catch (error) {
    stopPolling();
    actionError.value = getErrorMessage(error);
  }
}

function researchValidation(): GeoFlowValidationError[] {
  const errors = validateResearchStep({
    projectId: selectedProjectId.value,
    brandName: queryForm.brandName,
    keywords: normalizedKeywords.value,
    topics: normalizedTopics.value,
    intentDescription: queryForm.intentDescription,
    audienceName: queryForm.audienceName,
    audienceDescription: queryForm.audienceDescription,
  });
  return errors;
}

function generationValidationInput() {
  return {
    projectId: selectedProjectId.value,
    brandName: queryForm.brandName,
    keywords: normalizedKeywords.value,
    topics: normalizedTopics.value,
    intentDescription: queryForm.intentDescription,
    audienceName: queryForm.audienceName,
    audienceDescription: queryForm.audienceDescription,
    seoTaskId: projectForm.seoTaskId,
  };
}

function validateDispatchInput(queryId: string): GeoFlowValidationError[] {
  const errors: GeoFlowValidationError[] = [];
  if (!selectedProjectId.value) {
    errors.push({ field: "project", message: "請先選擇 project" });
  }
  if (!projectForm.seoTaskId.trim()) {
    errors.push({ field: "seoTaskId", message: "Dispatch 需要 seoTaskId" });
  }
  if (!queryId) {
    errors.push({ field: "acceptedQuery", message: "請先選擇 query" });
  }
  if (!selectedPlatform.value.platformId) {
    errors.push({ field: "platform", message: "請選擇 run provider" });
  }
  return errors;
}

function setValidation(errors: GeoFlowValidationError[]): boolean {
  validationErrors.value = errors;
  actionError.value = "";
  return errors.length === 0;
}

async function runAction(action: () => Promise<void>): Promise<void> {
  loading.value = true;
  actionError.value = "";
  try {
    await action();
  } catch (error) {
    actionError.value = getErrorMessage(error);
  } finally {
    loading.value = false;
  }
}

function resetProjectData(): void {
  savedQueries.value = [];
  savedJobs.value = [];
  savedRunResults.value = [];
  savedEntities.value = [];
  selectedQueryIds.value = [];
  selectedDraftIds.value = [];
  acceptedQueries.value = [];
  dispatchedJobs.value = [];
  jobResults.value = {};
  researchRun.value = null;
  generationRun.value = null;
  stopPolling();
}

function fillProjectForm(project: GeoProjectResource): void {
  projectForm.name = project.name;
  projectForm.customerId = project.customerId ?? "";
  projectForm.seoTaskId = project.seoTaskId ?? "";
  projectForm.defaultRegion = project.defaultRegion as GeoRegion;
  projectForm.defaultLanguage = project.defaultLanguage;
}

function projectRequestFromForm() {
  return {
    customerId: valueOrNull(projectForm.customerId),
    seoTaskId: valueOrNull(projectForm.seoTaskId),
    name: projectForm.name.trim(),
    defaultRegion: projectForm.defaultRegion,
    defaultLanguage: projectForm.defaultLanguage.trim() || "zh-TW",
    status: "active" as const,
    dailyRunBudget: 200,
  };
}

function splitValues(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function valueOrNull(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : "API 呼叫失敗";
}

function shortId(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function platformLabel(platformId: string): string {
  const platform = geoPlatformCatalog.find((item) => item.id === platformId);
  return platform ? `${platform.name} / ${platform.model}` : shortId(platformId);
}

function queryLabel(queryId: string): string {
  const query = savedQueries.value.find((item) => item.id === queryId);
  return query ? query.queryText : shortId(queryId);
}

function resultQueryLabel(result: GeoAnalysisRunResult): string {
  const job = savedJobs.value.find((item) => item.id === result.jobId);
  return job ? queryLabel(job.queryId) : "-";
}

function queryKeywords(query: GeoQueryResource): string[] {
  const keywords = query.metadata.keywords;
  return Array.isArray(keywords) ? keywords.filter((item): item is string => typeof item === "string") : [];
}

function intentCategoryLabel(category: string): string {
  return intentCategoryOptions.find((option) => option.value === category)?.label ?? category;
}

function intentCategoryCode(category: string | null): string {
  const codeByCategory: Record<string, string> = {
    navigational: "N",
    informational: "I",
    commercial_investigation: "C",
    transactional: "T",
  };
  return category ? (codeByCategory[category] ?? category) : "-";
}

function applyIntentDefaultDescription(): void {
  const selected = intentCategoryOptions.find((option) => option.value === queryForm.intentCategory);
  queryForm.intentDescription = selected?.description ?? "";
}

function statusBadgeClass(status: string): string {
  if (["succeeded", "completed", "accepted", "active"].includes(status)) return "badge-success";
  if (["failed", "cancelled", "rejected"].includes(status)) return "badge-error";
  if (["published", "pending", "publishing", "running_external", "shortlisted"].includes(status)) {
    return "badge-warning";
  }
  return "badge-muted";
}

function resultForJob(jobId: string): GeoAnalysisRunResult[] {
  return jobResults.value[jobId] ?? savedRunResults.value.filter((result) => result.jobId === jobId);
}

function semanticStatus(result: GeoAnalysisRunResult): string {
  return result.analysisStatus ?? "pending";
}

function semanticHint(result: GeoAnalysisRunResult): string {
  if (result.analysisErrorCode === "own_brand_missing") {
    return "找不到 active own_brand entity，請確認此 Project 已建立 own_brand。";
  }
  return result.analysisErrorMessage ?? result.analysisErrorCode ?? "";
}

function openReportDesign(): void {
  void router.push({
    name: "geo-analysis-report-design",
    query: selectedProjectId.value ? { projectId: selectedProjectId.value } : undefined,
  });
}
</script>

<template>
  <section class="flow-page">
    <header class="flow-header">
      <div>
        <p class="eyebrow">GEO Phase 1</p>
        <h1>Flow Check</h1>
        <p>用分步流程檢查 project、query research、query generation、dispatch 與 raw result。</p>
      </div>
      <button class="button button-secondary" type="button" :disabled="loading" @click="loadProjects">
        重新載入 Projects
      </button>
    </header>

    <nav class="flow-steps" aria-label="GEO flow steps">
      <button
        v-for="step in steps"
        :key="step.key"
        class="step-pill"
        :class="{ active: activeStep === step.key }"
        type="button"
        @click="activeStep = step.key"
      >
        {{ step.label }}
      </button>
    </nav>

    <div v-if="validationSummary.length" class="flow-alert validation">
      <strong>請先補齊欄位</strong>
      <ul>
        <li v-for="message in validationSummary" :key="message">{{ message }}</li>
      </ul>
    </div>
    <div v-if="actionError" class="flow-alert api-error">
      <strong>API 回應錯誤</strong>
      <p>{{ actionError }}</p>
    </div>

    <div class="flow-alert integration-status" :class="`integration-${kmindhubStatus}`">
      <div>
        <strong>KMindHub Workspace</strong>
        <p>{{ kmindhubMessage || "尚未檢查 KMindHub workspace 綁定狀態。" }}</p>
      </div>
      <button class="button button-secondary" type="button" :disabled="loading" @click="refreshKmindhubStatus">
        重新檢查
      </button>
    </div>

    <article v-if="activeStep === 'project'" class="flow-card">
      <header>
        <h2>1. 選擇或建立 Project</h2>
        <p>既有 project 也可以在這裡補上 customerId / seoTaskId，dispatch 會用到 seoTaskId。</p>
      </header>
      <label>
        既有 Project
        <select :value="selectedProjectId" @change="selectProject(($event.target as HTMLSelectElement).value)">
          <option value="">建立新 project</option>
          <option v-for="project in projects" :key="project.id" :value="project.id">
            {{ project.name }} / seoTaskId: {{ shortId(project.seoTaskId) }}
          </option>
        </select>
      </label>
      <label>
        Project 名稱
        <input v-model="projectForm.name" type="text" placeholder="例如 港香蘭 GEO" />
        <small v-if="fieldErrors.project">{{ fieldErrors.project }}</small>
      </label>
      <div class="two-column">
        <label>
          customerId
          <input v-model="projectForm.customerId" type="text" placeholder="可空；若填 seoTaskId 建議一併填" />
          <small v-if="fieldErrors.customerId">{{ fieldErrors.customerId }}</small>
        </label>
        <label>
          seoTaskId
          <input v-model="projectForm.seoTaskId" type="text" placeholder="dispatch 必填" />
          <small v-if="fieldErrors.seoTaskId">{{ fieldErrors.seoTaskId }}</small>
        </label>
      </div>
      <div class="button-row">
        <button class="button button-primary" type="button" :disabled="loading" @click="saveProjectAndContinue">
          {{ selectedProjectId ? "儲存並使用 Project" : "建立並使用 Project" }}
        </button>
      </div>
    </article>

    <article v-else-if="activeStep === 'library'" class="flow-card">
      <header>
        <h2>2. 目前 Project 既有資料</h2>
        <p>可以從既有 query 接續 dispatch；raw result 點查看會用彈窗顯示完整回應。</p>
      </header>
      <div class="context-row">
        <span>Project: {{ selectedProject?.name ?? "-" }}</span>
        <span>seoTaskId: {{ shortId(projectForm.seoTaskId) }}</span>
      </div>
      <div class="button-row">
        <button class="button button-secondary" type="button" :disabled="loading" @click="refreshProjectData()">
          重新整理列表
        </button>
        <button class="button button-primary" type="button" @click="startNewQueryFlow">
          新建 Query
        </button>
        <button
          class="button button-primary"
          type="button"
          :disabled="loading || !selectedQueries.length"
          @click="activeStep = 'dispatch'"
        >
          派送已選 Query
        </button>
      </div>
      <div class="flow-section-stack">
        <section class="table-card flow-table-card">
          <header class="table-section-header">
            <div>
              <h3>Queries</h3>
              <p>選取一筆或多筆正式 query 後，可直接進入 dispatch。</p>
            </div>
          </header>
          <p v-if="!savedQueries.length" class="empty-state">目前沒有正式 query。</p>
          <div v-else class="table-scroll">
            <table class="data-table flow-data-table">
              <thead>
                <tr>
                  <th scope="col">選取</th>
                  <th scope="col">Query</th>
                  <th scope="col">Keywords</th>
                  <th scope="col">Intent</th>
                  <th scope="col">Market</th>
                  <th scope="col">Status</th>
                  <th scope="col">ID</th>
                  <th scope="col">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="query in savedQueries" :key="query.id">
                  <td>
                    <input
                      class="table-checkbox"
                      type="checkbox"
                      :checked="selectedQueryIds.includes(query.id)"
                      :aria-label="`選取 ${query.queryText}`"
                      @change="toggleQuery(query.id)"
                    />
                  </td>
                  <td>
                    <div class="identity-cell flow-table-main">
                      <strong>{{ query.queryText }}</strong>
                    </div>
                  </td>
                  <td class="flow-table-query">
                    <span v-if="!queryKeywords(query).length">-</span>
                    <span v-else class="inline-tags">
                      <span v-for="keyword in queryKeywords(query)" :key="`${query.id}-${keyword}`" class="badge badge-muted">
                        {{ keyword }}
                      </span>
                    </span>
                  </td>
                  <td>{{ intentCategoryCode(query.intent) }}</td>
                  <td>{{ query.marketType }}</td>
                  <td><span class="badge" :class="statusBadgeClass(query.status)">{{ query.status }}</span></td>
                  <td>{{ shortId(query.id) }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="button button-secondary" type="button" @click="modal = { kind: 'query', item: query }">
                        查看
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="table-card flow-table-card">
          <header class="table-section-header">
            <div>
              <h3>Jobs</h3>
              <p>查看已建立或已派送的 job，必要時可接續輪詢結果。</p>
            </div>
          </header>
          <p v-if="!savedJobs.length" class="empty-state">目前沒有 job。</p>
          <div v-else class="table-scroll">
            <table class="data-table flow-data-table">
              <thead>
                <tr>
                  <th scope="col">Job</th>
                  <th scope="col">Query</th>
                  <th scope="col">Platform</th>
                  <th scope="col">Status</th>
                  <th scope="col">Updated</th>
                  <th scope="col">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in savedJobs" :key="item.id">
                  <td>{{ shortId(item.id) }}</td>
                  <td class="flow-table-query">{{ queryLabel(item.queryId) }}</td>
                  <td>{{ platformLabel(item.platformId) }}</td>
                  <td><span class="badge" :class="statusBadgeClass(item.status)">{{ item.status }}</span></td>
                  <td>{{ formatDate(item.updatedAt) }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="button button-secondary" type="button" @click="selectExistingJob(item)">
                        接續
                      </button>
                      <button class="button button-secondary" type="button" @click="modal = { kind: 'job', item }">
                        查看
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="table-card flow-table-card">
          <header class="table-section-header">
            <div>
              <h3>Run Results</h3>
              <p>已保存的 raw response 與 citations 可從這裡開啟檢視。</p>
            </div>
          </header>
          <p v-if="!savedRunResults.length" class="empty-state">目前沒有 raw result。</p>
          <div v-else class="table-scroll">
            <table class="data-table flow-data-table">
              <thead>
                <tr>
                  <th scope="col">Result</th>
                  <th scope="col">Query</th>
                  <th scope="col">Job</th>
                  <th scope="col">Provider</th>
                  <th scope="col">Status</th>
                  <th scope="col">Semantic</th>
                  <th scope="col">References</th>
                  <th scope="col">Run At</th>
                  <th scope="col">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in savedRunResults" :key="item.id">
                  <td>{{ shortId(item.id) }}</td>
                  <td class="flow-table-query">{{ resultQueryLabel(item) }}</td>
                  <td>{{ shortId(item.jobId) }}</td>
                  <td>{{ item.provider }}</td>
                  <td><span class="badge" :class="statusBadgeClass(item.status)">{{ item.status }}</span></td>
                  <td>
                    <span class="badge" :class="statusBadgeClass(semanticStatus(item))">
                      {{ semanticStatus(item) }}
                    </span>
                    <small v-if="semanticHint(item)">{{ semanticHint(item) }}</small>
                  </td>
                  <td>{{ item.references.length }}</td>
                  <td>{{ formatDate(item.runAt) }}</td>
                  <td>
                    <div class="row-actions">
                      <button class="button button-secondary" type="button" @click="modal = { kind: 'result', item }">
                        查看
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </article>

    <article v-else-if="activeStep === 'setup'" class="flow-card">
      <header>
        <h2>3. Query 設定</h2>
        <p>先填入 research/generation 需要的品牌、競品、keyword、topic 與受眾。</p>
      </header>
      <div class="two-column">
        <label>
          Research / Generation Provider
          <select v-model="queryForm.provider">
            <option value="gemini">Gemini</option>
            <option value="dummy">Dummy</option>
          </select>
        </label>
        <label>
          Run Provider
          <select v-model="queryForm.runProvider">
            <option value="gemini">Gemini</option>
            <option value="google_aio">Google AIO</option>
          </select>
        </label>
      </div>
      <label>
        品牌名稱
        <input v-model="queryForm.brandName" type="text" placeholder="例如 港香蘭應用生技股份有限公司" />
        <small v-if="fieldErrors.brandName">{{ fieldErrors.brandName }}</small>
      </label>
      <label>
        Own Brand Website URL
        <input v-model="queryForm.brandWebsiteUrl" type="url" placeholder="https://example.com" />
        <small>Flow Check 會用品牌名稱自動建立或更新 active own_brand entity。</small>
      </label>
      <label>
        競品品牌
        <textarea v-model="queryForm.competitorBrands" rows="3" placeholder="一行一個：競品名稱 | https://competitor.example；只有名稱也可以" />
        <small>將建立或更新 {{ reportEntitySummary.competitorCount }} 個 active competitor entities。</small>
      </label>
      <div class="two-column">
        <label>
          Keywords
          <textarea v-model="queryForm.keywords" rows="4" placeholder="一行一個 keyword" />
          <small v-if="fieldErrors.keywords">{{ fieldErrors.keywords }}</small>
        </label>
        <div class="topic-editor">
          <div class="topic-editor-header">
            <span>Topics</span>
            <button class="button button-secondary" type="button" @click="addTopic">
              新增 Topic
            </button>
          </div>
          <small v-if="fieldErrors.topics">{{ fieldErrors.topics }}</small>
          <div v-for="(topic, index) in queryForm.topics" :key="index" class="topic-row">
            <label>
              Topic 名稱
              <input v-model="topic.name" type="text" placeholder="例如 產品、採購評估、供應商比較" />
            </label>
            <label>
              Topic 描述
              <textarea v-model="topic.description" rows="3" />
            </label>
            <button
              class="button button-secondary"
              type="button"
              :disabled="queryForm.topics.length <= 1"
              @click="removeTopic(index)"
            >
              移除
            </button>
          </div>
        </div>
      </div>
      <div class="two-column">
        <label>
          Market Type
          <select v-model="queryForm.marketType">
            <option value="b2b_procurement">B2B 採購</option>
            <option value="b2c">B2C 消費</option>
          </select>
        </label>
        <label>
          Max Queries
          <input v-model.number="queryForm.maxQueries" type="number" min="1" max="20" />
        </label>
      </div>
      <div class="two-column">
        <label>
          Audience
          <input v-model="queryForm.audienceName" type="text" />
          <small v-if="fieldErrors.audienceName">{{ fieldErrors.audienceName }}</small>
        </label>
        <label>
          Audience Description
          <input v-model="queryForm.audienceDescription" type="text" />
          <small v-if="fieldErrors.audienceDescription">{{ fieldErrors.audienceDescription }}</small>
        </label>
      </div>
      <div class="two-column">
        <label>
          Intent 分類
          <select v-model="queryForm.intentCategory" @change="applyIntentDefaultDescription">
            <option v-for="option in intentCategoryOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label>
          Intent 描述
          <textarea v-model="queryForm.intentDescription" rows="3" />
          <small v-if="fieldErrors.intentDescription">{{ fieldErrors.intentDescription }}</small>
        </label>
      </div>
      <div class="toggle-grid">
        <label class="check-row">
          <input v-model="queryForm.shouldMentionOwnBrand" type="checkbox" />
          <span>query 需提及自身品牌</span>
        </label>
        <label class="check-row">
          <input v-model="queryForm.shouldMentionCompetitor" type="checkbox" />
          <span>query 需提及競品</span>
        </label>
      </div>
      <div class="button-row">
        <button class="button button-secondary" type="button" @click="activeStep = 'library'">返回既有資料</button>
        <button class="button button-primary" type="button" :disabled="loading" @click="runResearch">
          執行 Query Research
        </button>
      </div>
    </article>

    <article v-else-if="activeStep === 'research'" class="flow-card">
      <header>
        <h2>4. Query Research</h2>
        <p>確認 research context 後再產生 query drafts。</p>
      </header>
      <div v-if="researchRun" class="result-box">
        <strong>Status: {{ researchRun.status }}</strong>
        <p>{{ researchRun.result?.researchContext ?? researchRun.errorMessage }}</p>
        <dl class="detail-list compact-detail-list">
          <dt>Keywords</dt>
          <dd>
            <span
              v-for="keyword in researchRun.result?.searchedKeywords ?? normalizedKeywords"
              :key="keyword"
              class="badge badge-muted"
            >
              {{ keyword }}
            </span>
          </dd>
          <dt>Intent 分類</dt>
          <dd>
            <span class="badge badge-info">{{ intentCategoryLabel(queryForm.intentCategory) }}</span>
          </dd>
          <dt>Intent 描述</dt>
          <dd>{{ queryForm.intentDescription || "-" }}</dd>
          <dt>品牌提及</dt>
          <dd>
            自身品牌：{{ queryForm.shouldMentionOwnBrand ? "需要" : "不限制" }} /
            競品：{{ queryForm.shouldMentionCompetitor ? "需要" : "不限制" }}
          </dd>
        </dl>
        <h3>Source URLs</h3>
        <ul class="reference-list">
          <li v-for="url in researchRun.result?.sourceUrls ?? []" :key="url">
            <a :href="url" target="_blank" rel="noreferrer">{{ url }}</a>
          </li>
        </ul>
      </div>
      <div class="button-row">
        <button class="button button-secondary" type="button" @click="activeStep = 'setup'">回上一頁</button>
        <button class="button button-primary" type="button" :disabled="loading" @click="runGeneration">
          產生 Query Drafts
        </button>
      </div>
    </article>

    <article v-else-if="activeStep === 'drafts'" class="flow-card">
      <header>
        <h2>5. 選擇 Query Drafts</h2>
        <p>可多選 draft，接受後會建立正式 query，下一步可一起派送。</p>
      </header>
      <div v-if="generationRun?.status === 'failed'" class="flow-alert api-error">
        {{ generationRun.errorMessage ?? generationRun.errorCode ?? "Query generation failed" }}
      </div>
      <p v-if="generationRun && !generationRun.drafts.length" class="empty-state">沒有產生 query drafts。</p>
      <label v-for="draft in generationRun?.drafts ?? []" :key="draft.id" class="draft-row">
        <input
          type="checkbox"
          :checked="selectedDraftIds.includes(draft.id)"
          @change="toggleDraft(draft.id)"
        />
        <span>
          <strong>{{ draft.queryText }}</strong>
          <small>
            {{ draft.topicName || "未指定 topic" }} / {{ draft.marketType }} /
            Intent: {{ intentCategoryCode(draft.intent) }} / {{ draft.selectionStatus ?? "draft" }}
          </small>
          <span class="inline-tags">
            <span v-for="keyword in draft.keywords" :key="`${draft.id}-${keyword}`" class="badge badge-muted">
              {{ keyword }}
            </span>
          </span>
        </span>
      </label>
      <div class="button-row">
        <button class="button button-secondary" type="button" @click="activeStep = 'research'">回上一頁</button>
        <button class="button button-primary" type="button" :disabled="loading || !selectedDraftIds.length" @click="acceptSelectedDrafts">
          接受已選 Drafts
        </button>
      </div>
    </article>

    <article v-else-if="activeStep === 'dispatch'" class="flow-card">
      <header>
        <h2>6. 一鍵建立 Job 並 Dispatch</h2>
        <p>選擇 provider 後會自動為每筆 query 建立 manual job 並立即派送，不需要分開操作。</p>
      </header>
      <label>
        Run Provider
        <select v-model="queryForm.runProvider">
          <option value="gemini">Gemini</option>
          <option value="google_aio">Google AIO</option>
        </select>
      </label>
      <div class="selected-list">
        <strong>準備派送的 Queries</strong>
        <p v-if="!acceptedOrSelectedQueries.length" class="empty-state">請先從既有資料勾選 query，或接受 drafts。</p>
        <div v-for="query in acceptedOrSelectedQueries" :key="query.id" class="list-row">
          <span>
            <strong>{{ query.queryText }}</strong>
            <small>{{ query.marketType }} / {{ shortId(query.id) }}</small>
          </span>
        </div>
      </div>
      <div class="button-row">
        <button class="button button-secondary" type="button" @click="activeStep = 'library'">回既有資料</button>
        <button class="button button-primary" type="button" :disabled="loading || !acceptedOrSelectedQueries.length" @click="dispatchSelectedQueries">
          建立 Job 並 Dispatch
        </button>
      </div>
    </article>

    <article v-else class="flow-card">
      <header>
        <h2>7. Job 與 Raw Results</h2>
        <p>派送後會自動輪詢；完成後可點 result 查看 raw response 與 references。</p>
      </header>
      <div class="button-row">
        <button class="button button-secondary" type="button" :disabled="loading" @click="refreshResults">
          重新整理
        </button>
        <button class="button button-primary" type="button" :disabled="!selectedProjectId" @click="openReportDesign">
          前往 Report Design
        </button>
        <button class="button button-primary" type="button" @click="activeStep = 'library'">回既有資料</button>
      </div>
      <p v-if="polling" class="success-text">正在等待 worker 回寫結果...</p>
      <section v-for="item in dispatchedJobs" :key="item.id" class="job-panel">
        <header>
          <strong>{{ queryLabel(item.queryId) }}</strong>
          <small>{{ item.status }} / {{ platformLabel(item.platformId) }}</small>
          <small>Job ID: {{ item.id }}</small>
        </header>
        <p v-if="item.lastErrorMessage" class="error-text">{{ item.lastErrorMessage }}</p>
        <div v-if="!resultForJob(item.id).length" class="empty-state">尚未收到 run result。</div>
        <button
          v-for="result in resultForJob(item.id)"
          :key="result.id"
          class="result-row"
          type="button"
          @click="modal = { kind: 'result', item: result }"
        >
          <span>
            {{ result.provider }} / {{ result.status }} / semantic: {{ semanticStatus(result) }} /
            refs: {{ result.references.length }}
          </span>
          <small v-if="semanticHint(result)">{{ semanticHint(result) }}</small>
          <small>{{ formatDate(result.runAt) }}</small>
        </button>
      </section>
      <section v-if="!dispatchedJobs.length" class="table-card flow-table-card">
        <header class="table-section-header">
          <div>
            <h3>既有 Run Results</h3>
            <p>尚未從本頁 dispatch job 時，先列出目前 project 已保存的 raw result。</p>
          </div>
        </header>
        <p v-if="!savedRunResults.length" class="empty-state">目前沒有 raw result。</p>
        <div v-else class="table-scroll">
          <table class="data-table flow-data-table">
            <thead>
              <tr>
                <th scope="col">Result</th>
                <th scope="col">Query</th>
                <th scope="col">Job</th>
                <th scope="col">Provider</th>
                <th scope="col">Status</th>
                <th scope="col">Semantic</th>
                <th scope="col">References</th>
                <th scope="col">Run At</th>
                <th scope="col">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in savedRunResults" :key="item.id">
                <td>{{ shortId(item.id) }}</td>
                <td class="flow-table-query">{{ resultQueryLabel(item) }}</td>
                <td>{{ shortId(item.jobId) }}</td>
                <td>{{ item.provider }}</td>
                <td><span class="badge" :class="statusBadgeClass(item.status)">{{ item.status }}</span></td>
                <td>
                  <span class="badge" :class="statusBadgeClass(semanticStatus(item))">
                    {{ semanticStatus(item) }}
                  </span>
                  <small v-if="semanticHint(item)">{{ semanticHint(item) }}</small>
                </td>
                <td>{{ item.references.length }}</td>
                <td>{{ formatDate(item.runAt) }}</td>
                <td>
                  <div class="row-actions">
                    <button class="button button-secondary" type="button" @click="modal = { kind: 'result', item }">
                      查看
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>

    <div v-if="modal" class="modal-backdrop" @click.self="modal = null">
      <section class="modal flow-modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <div>
            <h2 v-if="modal.kind === 'query'">Query Detail</h2>
            <h2 v-else-if="modal.kind === 'job'">Job Detail</h2>
            <h2 v-else>Run Result</h2>
            <p v-if="modal.kind === 'query'">{{ shortId(modal.item.id) }}</p>
            <p v-else-if="modal.kind === 'job'">{{ shortId(modal.item.id) }}</p>
            <p v-else>{{ resultQueryLabel(modal.item) }}</p>
          </div>
          <button class="button button-secondary" type="button" @click="modal = null">關閉</button>
        </header>
        <div class="modal-body">
          <template v-if="modal.kind === 'query'">
            <p class="modal-title-copy">{{ modal.item.queryText }}</p>
            <dl class="detail-list">
              <dt>ID</dt>
              <dd>{{ modal.item.id }}</dd>
              <dt>Market</dt>
              <dd>{{ modal.item.marketType }}</dd>
              <dt>Status</dt>
              <dd><span class="badge" :class="statusBadgeClass(modal.item.status)">{{ modal.item.status }}</span></dd>
            </dl>
          </template>
          <template v-else-if="modal.kind === 'job'">
            <dl class="detail-list">
              <dt>ID</dt>
              <dd>{{ modal.item.id }}</dd>
              <dt>Query</dt>
              <dd>{{ queryLabel(modal.item.queryId) }}</dd>
              <dt>Status</dt>
              <dd><span class="badge" :class="statusBadgeClass(modal.item.status)">{{ modal.item.status }}</span></dd>
              <dt>Platform</dt>
              <dd>{{ platformLabel(modal.item.platformId) }}</dd>
              <dt>Error</dt>
              <dd>{{ modal.item.lastErrorMessage ?? "-" }}</dd>
            </dl>
          </template>
          <template v-else>
            <p class="modal-title-copy">{{ resultQueryLabel(modal.item) }}</p>
            <dl class="detail-list">
              <dt>Query</dt>
              <dd>{{ resultQueryLabel(modal.item) }}</dd>
              <dt>Provider</dt>
              <dd>{{ modal.item.provider }}</dd>
              <dt>Status</dt>
              <dd><span class="badge" :class="statusBadgeClass(modal.item.status)">{{ modal.item.status }}</span></dd>
              <dt>Semantic</dt>
              <dd>
                <span class="badge" :class="statusBadgeClass(semanticStatus(modal.item))">
                  {{ semanticStatus(modal.item) }}
                </span>
                <small v-if="semanticHint(modal.item)">{{ semanticHint(modal.item) }}</small>
              </dd>
              <dt>Model</dt>
              <dd>{{ modal.item.model }}</dd>
              <dt>References</dt>
              <dd>{{ modal.item.references.length }}</dd>
            </dl>
            <h3>Raw Response</h3>
            <pre class="modal-pre">{{ modal.item.rawResponse || modal.item.error }}</pre>
            <h3>References</h3>
            <ol v-if="modal.item.references.length" class="reference-list">
              <li v-for="reference in modal.item.references" :key="`${reference.position}-${reference.url}`">
                <a :href="reference.url" target="_blank" rel="noreferrer">
                  {{ reference.title ?? reference.domain ?? reference.url }}
                </a>
              </li>
            </ol>
            <p v-else class="empty-state compact-empty">目前沒有 references。</p>
          </template>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.flow-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.flow-header,
.flow-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px;
}

.flow-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow,
small {
  color: var(--text-muted);
}

.flow-steps,
.button-row,
.context-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.step-pill {
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  font: inherit;
  min-height: 36px;
  padding: 8px 12px;
}

.step-pill.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.step-pill:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.flow-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

input,
select,
textarea {
  border: 1px solid var(--border);
  border-radius: 8px;
  font: inherit;
  min-height: 38px;
  padding: 8px 10px;
}

textarea {
  resize: vertical;
}

.two-column,
.library-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.toggle-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.topic-editor {
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.topic-editor-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.topic-editor-header span {
  color: var(--text-primary);
  font-weight: 600;
}

.topic-row {
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: grid;
  gap: 10px;
  grid-template-columns: minmax(160px, 0.7fr) minmax(220px, 1fr) auto;
  padding: 10px;
}

.topic-row .button {
  align-self: end;
  margin-bottom: 0;
}

.check-row {
  align-items: center;
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  flex-direction: row;
  padding: 10px 12px;
}

.check-row input {
  min-height: auto;
  width: auto;
}

.inline-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.library-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.flow-section-stack {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.flow-table-card {
  border: 1px solid var(--border);
  border-radius: 8px;
}

.table-section-header {
  align-items: flex-start;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
}

.table-section-header h3 {
  margin: 0 0 4px;
}

.table-section-header p {
  color: var(--text-muted);
  margin: 0;
}

.flow-data-table {
  min-width: 860px;
}

.flow-table-main,
.flow-table-query {
  max-width: 360px;
  min-width: 220px;
  white-space: normal;
}

.flow-table-query {
  color: var(--text-primary);
}

.table-checkbox {
  min-height: auto;
  width: 18px;
}

.library-grid section,
.selected-list,
.job-panel {
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}

.list-row,
.draft-row,
.result-row {
  align-items: flex-start;
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: inherit;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  padding: 10px;
  text-align: left;
}

.selectable {
  cursor: pointer;
}

.list-row span,
.draft-row span,
.result-row span {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
}

.result-box,
.flow-alert,
.empty-state {
  border-radius: 8px;
  padding: 12px;
}

.result-box,
.empty-state {
  background: var(--surface-secondary);
  border: 1px solid var(--border);
}

.integration-status {
  align-items: center;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.integration-status p {
  margin: 4px 0 0;
}

.integration-ready {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
}

.integration-missing,
.integration-unknown {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
}

.integration-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.flow-alert.validation {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
}

.flow-alert.api-error,
.error-text {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.success-text {
  color: #047857;
  font-weight: 700;
}

.flow-modal {
  width: min(920px, 100%);
}

.modal-title-copy {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px;
}

.detail-list {
  display: grid;
  gap: 8px 12px;
  grid-template-columns: max-content minmax(0, 1fr);
  margin: 0 0 18px;
}

.compact-detail-list {
  margin-top: 14px;
}

dt {
  color: var(--text-muted);
}

.modal-pre {
  background: var(--surface-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

.reference-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
  word-break: break-word;
}

.compact-empty {
  min-height: auto;
  place-items: start;
  text-align: left;
}

@media (max-width: 900px) {
  .flow-header,
  .two-column,
  .toggle-grid,
  .topic-row,
  .library-grid {
    grid-template-columns: 1fr;
  }

  .flow-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
