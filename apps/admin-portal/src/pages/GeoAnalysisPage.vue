<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { createGeoMockState } from "../mocks/geo-analysis";
import type {
  GeoEntity,
  GeoJob,
  GeoProject,
  GeoQuery,
  GeoSchedule,
  GeoTopic,
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

const state = reactive(createGeoMockState());
const activeTab = computed(() => props.activeTab ?? "overview");
const selectedProjectId = ref(state.projects[0]?.id ?? "");
const localMessage = ref("目前所有操作皆為前端記憶體中的 Mock 操作。");

const projectForm = reactive({
  name: "",
  customerName: "",
  seoTaskName: "",
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
  isBranded: false,
  priority: "normal" as GeoQuery["priority"],
});

const scheduleForm = reactive({
  queryId: "",
  platformId: "geo-platform-chatgpt",
  frequency: "daily" as GeoSchedule["frequency"],
  priority: "normal" as GeoSchedule["priority"],
  timezone: "Asia/Taipei",
  nextRunAt: "2026-06-24T09:00",
});

const jobForm = reactive({
  queryId: "",
  platformId: "geo-platform-chatgpt",
  priority: "normal" as GeoJob["priority"],
});

const selectedProject = computed(() =>
  state.projects.find((project) => project.id === selectedProjectId.value),
);

const projectMarkets = computed(() =>
  state.markets.filter((market) => market.projectId === selectedProjectId.value),
);

const projectEntities = computed(() =>
  state.entities.filter((entity) => entity.projectId === selectedProjectId.value),
);

const projectTopics = computed(() =>
  state.topics.filter((topic) => topic.projectId === selectedProjectId.value),
);

const projectQueries = computed(() =>
  state.queries.filter((query) => query.projectId === selectedProjectId.value),
);

const projectSchedules = computed(() =>
  state.schedules.filter((schedule) =>
    projectQueries.value.some((query) => query.id === schedule.queryId),
  ),
);

const projectJobs = computed(() =>
  state.jobs
    .filter((job) => job.projectId === selectedProjectId.value)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
);

const activeQueryCount = computed(
  () => projectQueries.value.filter((query) => query.status === "active").length,
);

const activeScheduleCount = computed(
  () =>
    projectSchedules.value.filter((schedule) => schedule.status === "active")
      .length,
);

const runningJobCount = computed(
  () =>
    projectJobs.value.filter(
      (job) => job.status === "published" || job.status === "running_external",
    ).length,
);

const failedJobCount = computed(
  () => projectJobs.value.filter((job) => job.status === "failed").length,
);

const overviewStats = computed(() => [
  {
    label: "Projects",
    value: state.projects.length,
    detail: `${state.projects.filter((project) => project.status === "active").length} active`,
    tone: "tone-info",
  },
  {
    label: "Active Queries",
    value: activeQueryCount.value,
    detail: `${projectTopics.value.length} topics`,
    tone: "tone-success",
  },
  {
    label: "Schedules",
    value: activeScheduleCount.value,
    detail: "Pub/Sub publisher 待實作",
    tone: "tone-warning",
  },
  {
    label: "Running Jobs",
    value: runningJobCount.value,
    detail: `${failedJobCount.value} failed mock jobs`,
    tone: failedJobCount.value > 0 ? "tone-error" : "tone-info",
  },
]);

const projectPlatforms = computed(() =>
  state.platforms.map((platform) => ({
    ...platform,
    assignmentCount: state.queryPlatforms.filter(
      (item) =>
        item.platformId === platform.id &&
        projectQueries.value.some((query) => query.id === item.queryId),
    ).length,
  })),
);

function setMessage(message: string): void {
  localMessage.value = message;
}

function newId(prefix: string): string {
  return `geo-${prefix}-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

function toIsoFromLocal(value: string): string | null {
  return value ? new Date(value).toISOString() : null;
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

function getQuery(queryId: string): GeoQuery | undefined {
  return state.queries.find((query) => query.id === queryId);
}

function getTopic(topicId: string | null): GeoTopic | undefined {
  return topicId ? state.topics.find((topic) => topic.id === topicId) : undefined;
}

function getPlatform(platformId: string): string {
  return state.platforms.find((platform) => platform.id === platformId)?.name ?? "-";
}

function getAliases(entityId: string): string {
  const values = state.aliases
    .filter((alias) => alias.entityId === entityId)
    .map((alias) => alias.alias);
  return values.length > 0 ? values.join("、") : "尚未設定";
}

function badgeClass(status: string): string {
  if (["active", "succeeded"].includes(status)) return "badge badge-success";
  if (["paused", "pending", "published", "running_external"].includes(status)) {
    return "badge badge-warning";
  }
  if (["failed"].includes(status)) return "badge badge-error";
  return "badge badge-muted";
}

function resetMockData(): void {
  Object.assign(state, createGeoMockState());
  selectedProjectId.value = state.projects[0]?.id ?? "";
  setMessage("示意資料已重置，頁面回到預設 mock 狀態。");
}

function createProject(): void {
  if (!projectForm.name.trim() || !projectForm.customerName.trim()) return;
  const now = nowIso();
  const project: GeoProject = {
    id: newId("project"),
    customerId: newId("customer"),
    customerName: projectForm.customerName.trim(),
    seoTaskId: projectForm.seoTaskName ? newId("seo-task") : null,
    seoTaskName: projectForm.seoTaskName.trim() || null,
    name: projectForm.name.trim(),
    defaultRegion: projectForm.defaultRegion.trim() || "TW",
    defaultLanguage: projectForm.defaultLanguage.trim() || "zh-TW",
    status: "active",
    dailyRunBudget: Number(projectForm.dailyRunBudget) || 0,
    createdAt: now,
    updatedAt: now,
  };
  state.projects.unshift(project);
  selectedProjectId.value = project.id;
  projectForm.name = "";
  projectForm.customerName = "";
  projectForm.seoTaskName = "";
  setMessage("已建立 mock GEO project。");
}

function updateProjectStatus(projectId: string, status: GeoProject["status"]): void {
  const project = state.projects.find((item) => item.id === projectId);
  if (!project) return;
  project.status = status;
  project.updatedAt = nowIso();
  setMessage(`已將 ${project.name} 更新為 ${status}。`);
}

function deleteProject(projectId: string): void {
  state.projects = state.projects.filter((project) => project.id !== projectId);
  state.markets = state.markets.filter((market) => market.projectId !== projectId);
  state.entities = state.entities.filter((entity) => entity.projectId !== projectId);
  state.topics = state.topics.filter((topic) => topic.projectId !== projectId);
  state.queries = state.queries.filter((query) => query.projectId !== projectId);
  state.jobs = state.jobs.filter((job) => job.projectId !== projectId);
  selectedProjectId.value = state.projects[0]?.id ?? "";
  setMessage("已刪除 mock project 與相關頁面資料。");
}

function createEntity(): void {
  if (!selectedProject.value || !entityForm.name.trim()) return;
  const entity: GeoEntity = {
    id: newId("entity"),
    projectId: selectedProject.value.id,
    entityType: entityForm.entityType,
    name: entityForm.name.trim(),
    websiteUrl: entityForm.websiteUrl.trim() || null,
    description: entityForm.description.trim(),
    status: "active",
  };
  state.entities.unshift(entity);
  if (entityForm.alias.trim()) {
    state.aliases.unshift({
      id: newId("alias"),
      entityId: entity.id,
      alias: entityForm.alias.trim(),
      matchType: "contains",
    });
  }
  entityForm.name = "";
  entityForm.websiteUrl = "";
  entityForm.description = "";
  entityForm.alias = "";
  setMessage("已建立 mock entity。");
}

function deleteEntity(entityId: string): void {
  state.entities = state.entities.filter((entity) => entity.id !== entityId);
  state.aliases = state.aliases.filter((alias) => alias.entityId !== entityId);
  setMessage("已刪除 mock entity。");
}

function createTopic(): void {
  if (!selectedProject.value || !topicForm.name.trim()) return;
  const topic: GeoTopic = {
    id: newId("topic"),
    projectId: selectedProject.value.id,
    name: topicForm.name.trim(),
    description: topicForm.description.trim(),
    status: "active",
  };
  state.topics.unshift(topic);
  queryForm.topicId = topic.id;
  topicForm.name = "";
  topicForm.description = "";
  setMessage("已建立 mock topic。");
}

function createQuery(): void {
  if (!selectedProject.value || !queryForm.queryText.trim()) return;
  const query: GeoQuery = {
    id: newId("query"),
    projectId: selectedProject.value.id,
    topicId: queryForm.topicId || null,
    queryText: queryForm.queryText.trim(),
    region: selectedProject.value.defaultRegion,
    language: selectedProject.value.defaultLanguage,
    intent: queryForm.intent.trim() || "recommendation",
    buyerStage: queryForm.buyerStage.trim() || "consideration",
    isBranded: queryForm.isBranded,
    priority: queryForm.priority,
    status: "active",
  };
  state.queries.unshift(query);
  queryForm.queryText = "";
  queryForm.isBranded = false;
  setMessage("已建立 mock query。");
}

function deleteQuery(queryId: string): void {
  state.queries = state.queries.filter((query) => query.id !== queryId);
  state.queryPlatforms = state.queryPlatforms.filter(
    (item) => item.queryId !== queryId,
  );
  state.schedules = state.schedules.filter((schedule) => schedule.queryId !== queryId);
  state.jobs = state.jobs.filter((job) => job.queryId !== queryId);
  setMessage("已刪除 mock query 與相關排程。");
}

function createSchedule(): void {
  const query = getQuery(scheduleForm.queryId);
  if (!query) return;
  const platform = state.platforms.find(
    (item) => item.id === scheduleForm.platformId,
  );
  const schedule: GeoSchedule = {
    id: newId("schedule"),
    queryId: query.id,
    platformId: scheduleForm.platformId,
    frequency: scheduleForm.frequency,
    priority: scheduleForm.priority,
    timezone: scheduleForm.timezone.trim() || "Asia/Taipei",
    nextRunAt: toIsoFromLocal(scheduleForm.nextRunAt),
    status: "active",
  };
  state.schedules.unshift(schedule);
  if (
    platform &&
    !state.queryPlatforms.some(
      (item) => item.queryId === query.id && item.platformId === platform.id,
    )
  ) {
    state.queryPlatforms.unshift({
      id: newId("query-platform"),
      queryId: query.id,
      platformId: platform.id,
      model: platform.model,
      status: "active",
    });
  }
  setMessage("已建立 mock schedule。");
}

function toggleSchedule(schedule: GeoSchedule): void {
  schedule.status = schedule.status === "active" ? "paused" : "active";
  setMessage("已切換 mock schedule 狀態。");
}

function deleteSchedule(scheduleId: string): void {
  state.schedules = state.schedules.filter((schedule) => schedule.id !== scheduleId);
  setMessage("已刪除 mock schedule。");
}

function createManualJob(): void {
  const query = getQuery(jobForm.queryId);
  if (!query || !selectedProject.value) return;
  const scheduledFor = nowIso();
  const normalized = scheduledFor.replace(".000Z", "Z");
  const job: GeoJob = {
    id: newId("job"),
    projectId: selectedProject.value.id,
    queryId: query.id,
    platformId: jobForm.platformId,
    scheduleId: null,
    jobType: "manual_run",
    priority: jobForm.priority,
    scheduledFor,
    status: "pending",
    attemptCount: 0,
    maxAttempts: 3,
    dedupeKey: `${selectedProject.value.id}:${query.id}:${jobForm.platformId}:${normalized}`,
    externalRunId: null,
    lastErrorMessage: null,
    createdAt: scheduledFor,
    updatedAt: scheduledFor,
  };
  state.jobs.unshift(job);
  setMessage("已建立 manual run mock job；publisher 尚未實作，因此不會送出。");
}

function cancelJob(job: GeoJob): void {
  if (["succeeded", "failed", "cancelled"].includes(job.status)) {
    setMessage("terminal job 無法取消，這裡模擬 API 409 行為。");
    return;
  }
  job.status = "cancelled";
  job.updatedAt = nowIso();
  setMessage("已取消 mock job。");
}

function openCreateProject(): void {
  setMessage("請從左側 GEO 子選單切換到 Projects 後建立專案。");
}

function useFirstQuery(): void {
  const firstQuery = projectQueries.value[0];
  if (!firstQuery) return;
  scheduleForm.queryId = firstQuery.id;
  jobForm.queryId = firstQuery.id;
}
</script>

<template>
  <section class="page geo-page geo-analysis-page">
    <header class="page-header">
      <div>
        <p class="page-kicker">Mock Preview</p>
        <h1>GEO 分析</h1>
        <p>
          以 mock data 盤點 GEO 分析後台需要的功能，後續 DB、API、正式分析資料完成後再替換。
        </p>
      </div>
      <div class="page-actions">
        <select v-model="selectedProjectId" class="geo-project-select" @change="useFirstQuery">
          <option
            v-for="project in state.projects"
            :key="project.id"
            :value="project.id"
          >
            {{ project.name }}
          </option>
        </select>
        <button class="button button-primary" type="button" @click="openCreateProject">
          <AppIcon name="plus" :size="16" />建立專案
        </button>
        <button class="button button-secondary" type="button" @click="resetMockData">
          <AppIcon name="refresh" :size="16" />重置示意資料
        </button>
      </div>
    </header>

    <div class="mock-notice">
      <AppIcon name="alert-circle" :size="17" />
      目前為「示意資料 / Mock 操作」。本頁不會呼叫 /api/geo，操作只更新前端 local state。
    </div>

    <div class="geo-local-message">{{ localMessage }}</div>

    <div v-if="!selectedProject" class="empty-state">
      <AppIcon name="layers" />
      <strong>尚未建立 GEO 專案</strong>
      <span>請先建立 mock project，後續再接正式 project API。</span>
    </div>

    <template v-else>
      <section v-if="activeTab === 'overview'" class="geo-section-stack">
        <div class="stat-grid">
          <article
            v-for="stat in overviewStats"
            :key="stat.label"
            class="stat-card"
          >
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
                <h2>Mock 趨勢</h2>
                <p>示意資料，後續接正式分析資料</p>
              </div>
              <span class="badge badge-warning">Mock</span>
            </header>
            <div class="geo-trend">
              <div
                v-for="point in state.trendPoints"
                :key="point.label"
                class="geo-trend-point"
              >
                <span
                  class="geo-trend-bar"
                  :style="{ height: `${point.visibility}%` }"
                />
                <small>{{ point.label }}</small>
              </div>
            </div>
          </article>

          <article class="card">
            <header class="card-header">
              <div>
                <h2>近期 Jobs</h2>
                <p>只顯示目前選取專案的 mock jobs</p>
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
                  <tr v-for="job in projectJobs.slice(0, 5)" :key="job.id">
                    <td>{{ getQuery(job.queryId)?.queryText ?? "-" }}</td>
                    <td>{{ getPlatform(job.platformId) }}</td>
                    <td><span :class="badgeClass(job.status)">{{ job.status }}</span></td>
                    <td>{{ formatDate(job.scheduledFor) }}</td>
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
              <p>Project / customer / task / region / language / budget mock CRUD</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createProject">
            <label>
              專案名稱
              <input v-model="projectForm.name" type="text" placeholder="例如：品牌 GEO 追蹤" />
            </label>
            <label>
              客戶名稱
              <input v-model="projectForm.customerName" type="text" placeholder="客戶名稱" />
            </label>
            <label>
              SEO 任務
              <input v-model="projectForm.seoTaskName" type="text" placeholder="可留空" />
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
              Daily run budget
              <input v-model.number="projectForm.dailyRunBudget" type="number" min="0" />
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit">新增 mock project</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header">
            <h2>Projects</h2>
          </header>
          <div class="table-scroll">
            <table class="data-table geo-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Customer / Task</th>
                  <th>Locale</th>
                  <th>Budget</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="project in state.projects" :key="project.id">
                  <td>
                    <strong>{{ project.name }}</strong>
                    <small>{{ project.id }}</small>
                  </td>
                  <td>{{ project.customerName }} / {{ project.seoTaskName ?? "未綁定" }}</td>
                  <td>{{ project.defaultRegion }} · {{ project.defaultLanguage }}</td>
                  <td>{{ project.dailyRunBudget }}</td>
                  <td><span :class="badgeClass(project.status)">{{ project.status }}</span></td>
                  <td>
                    <div class="row-actions">
                      <button class="text-button" type="button" @click="selectedProjectId = project.id">選取</button>
                      <button class="text-button" type="button" @click="updateProjectStatus(project.id, project.status === 'active' ? 'paused' : 'active')">切換</button>
                      <button class="text-button text-error" type="button" @click="deleteProject(project.id)">刪除</button>
                    </div>
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
            <div>
              <h2>Entities & Aliases</h2>
              <p>品牌、競品、網站與 alias mock CRUD</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createEntity">
            <label>
              類型
              <select v-model="entityForm.entityType">
                <option value="brand">brand</option>
                <option value="competitor">competitor</option>
                <option value="website">website</option>
                <option value="partner">partner</option>
              </select>
            </label>
            <label>
              名稱
              <input v-model="entityForm.name" type="text" placeholder="品牌或競品名稱" />
            </label>
            <label>
              Website URL
              <input v-model="entityForm.websiteUrl" type="url" placeholder="https://example.com" />
            </label>
            <label>
              Alias
              <input v-model="entityForm.alias" type="text" placeholder="可留空" />
            </label>
            <label class="geo-form-full">
              描述
              <textarea v-model="entityForm.description" rows="3" placeholder="追蹤目的或辨識規則"></textarea>
            </label>
            <div class="geo-form-actions">
              <button class="button button-primary" type="submit">新增 mock entity</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header">
            <h2>Entity List</h2>
          </header>
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
                <tr v-for="entity in projectEntities" :key="entity.id">
                  <td>{{ entity.name }}</td>
                  <td>{{ entity.entityType }}</td>
                  <td>{{ getAliases(entity.id) }}</td>
                  <td>{{ entity.websiteUrl ?? "-" }}</td>
                  <td><span :class="badgeClass(entity.status)">{{ entity.status }}</span></td>
                  <td>
                    <button class="text-button text-error" type="button" @click="deleteEntity(entity.id)">刪除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'queries'" class="geo-section-stack">
        <div class="geo-two-column">
          <article class="card geo-form-card">
            <header class="card-header">
              <h2>Topics</h2>
            </header>
            <form class="geo-compact-form" @submit.prevent="createTopic">
              <label>
                Topic
                <input v-model="topicForm.name" type="text" placeholder="例如：品牌比較" />
              </label>
              <label>
                Description
                <textarea v-model="topicForm.description" rows="3"></textarea>
              </label>
              <button class="button button-primary" type="submit">新增 topic</button>
            </form>
          </article>

          <article class="card geo-form-card">
            <header class="card-header">
              <h2>Queries</h2>
            </header>
            <form class="geo-form-grid" @submit.prevent="createQuery">
              <label>
                Topic
                <select v-model="queryForm.topicId">
                  <option value="">不指定</option>
                  <option v-for="topic in projectTopics" :key="topic.id" :value="topic.id">
                    {{ topic.name }}
                  </option>
                </select>
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
                Buyer stage
                <input v-model="queryForm.buyerStage" type="text" />
              </label>
              <label class="geo-form-full">
                Query
                <textarea v-model="queryForm.queryText" rows="3" placeholder="使用者會在 Gemini / GPT 詢問的問題"></textarea>
              </label>
              <label class="geo-checkbox">
                <input v-model="queryForm.isBranded" type="checkbox" />
                Branded query
              </label>
              <div class="geo-form-actions">
                <button class="button button-primary" type="submit">新增 query</button>
              </div>
            </form>
          </article>
        </div>

        <article class="card">
          <header class="card-header">
            <h2>Query List</h2>
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
                <tr v-for="query in projectQueries" :key="query.id">
                  <td>{{ query.queryText }}</td>
                  <td>{{ getTopic(query.topicId)?.name ?? "-" }}</td>
                  <td>{{ query.intent }}</td>
                  <td>{{ query.buyerStage }}</td>
                  <td>{{ query.isBranded ? "是" : "否" }}</td>
                  <td>{{ query.priority }}</td>
                  <td>
                    <button class="text-button text-error" type="button" @click="deleteQuery(query.id)">刪除</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else-if="activeTab === 'schedules'" class="geo-section-stack">
        <div class="geo-platform-grid">
          <article
            v-for="platform in projectPlatforms"
            :key="platform.id"
            class="card geo-platform-card"
          >
            <strong>{{ platform.name }}</strong>
            <span>{{ platform.model }}</span>
            <small>{{ platform.assignmentCount }} query assignments</small>
            <span :class="badgeClass(platform.status)">{{ platform.status }}</span>
          </article>
        </div>

        <article class="card geo-form-card">
          <header class="card-header">
            <div>
              <h2>建立 Schedule</h2>
              <p>AI model assignment、frequency、timezone、next run mock 操作</p>
            </div>
          </header>
          <form class="geo-form-grid" @submit.prevent="createSchedule">
            <label>
              Query
              <select v-model="scheduleForm.queryId">
                <option value="">請選擇 query</option>
                <option v-for="query in projectQueries" :key="query.id" :value="query.id">
                  {{ query.queryText }}
                </option>
              </select>
            </label>
            <label>
              Platform
              <select v-model="scheduleForm.platformId">
                <option v-for="platform in state.platforms" :key="platform.id" :value="platform.id">
                  {{ platform.name }} · {{ platform.model }}
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
              <button class="button button-primary" type="submit">新增 mock schedule</button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header">
            <h2>Schedules</h2>
          </header>
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
                <tr v-for="schedule in projectSchedules" :key="schedule.id">
                  <td>{{ getQuery(schedule.queryId)?.queryText ?? "-" }}</td>
                  <td>{{ getPlatform(schedule.platformId) }}</td>
                  <td>{{ schedule.frequency }} · {{ schedule.timezone }}</td>
                  <td>{{ formatDate(schedule.nextRunAt) }}</td>
                  <td><span :class="badgeClass(schedule.status)">{{ schedule.status }}</span></td>
                  <td>
                    <div class="row-actions">
                      <button class="text-button" type="button" @click="toggleSchedule(schedule)">切換</button>
                      <button class="text-button text-error" type="button" @click="deleteSchedule(schedule.id)">刪除</button>
                    </div>
                  </td>
                </tr>
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
              <p>建立 mock job；dispatch disabled，後續 publisher 決定後再實作</p>
            </div>
            <span class="badge badge-warning">Publisher 待實作</span>
          </header>
          <form class="geo-form-grid" @submit.prevent="createManualJob">
            <label>
              Query
              <select v-model="jobForm.queryId">
                <option value="">請選擇 query</option>
                <option v-for="query in projectQueries" :key="query.id" :value="query.id">
                  {{ query.queryText }}
                </option>
              </select>
            </label>
            <label>
              Platform
              <select v-model="jobForm.platformId">
                <option v-for="platform in state.platforms" :key="platform.id" :value="platform.id">
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
              <button class="button button-primary" type="submit">建立 mock job</button>
              <button
                class="button button-secondary"
                type="button"
                @click="emit('unavailable', 'GEO job publisher')"
              >
                Dispatch disabled
              </button>
            </div>
          </form>
        </article>

        <article class="card">
          <header class="card-header">
            <h2>Jobs</h2>
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
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="job in projectJobs" :key="job.id">
                  <td>{{ getQuery(job.queryId)?.queryText ?? "-" }}</td>
                  <td>{{ getPlatform(job.platformId) }}</td>
                  <td><span :class="badgeClass(job.status)">{{ job.status }}</span></td>
                  <td><code>{{ job.dedupeKey }}</code></td>
                  <td>{{ job.attemptCount }} / {{ job.maxAttempts }}</td>
                  <td>
                    <button class="text-button" type="button" @click="cancelJob(job)">Cancel</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </section>

      <section v-else class="geo-section-stack">
        <div class="mock-notice subtle">
          <AppIcon name="alert-circle" :size="17" />
          Reports 目前皆為示意資料，後續接正式分析資料、指標演算法與 report API。
        </div>

        <div class="geo-report-grid">
          <article
            v-for="metric in state.reportMetrics"
            :key="metric.id"
            class="card geo-metric-card"
          >
            <span :class="`text-${metric.tone}`">{{ metric.delta }}</span>
            <strong>{{ metric.value }}</strong>
            <h2>{{ metric.label }}</h2>
            <p>{{ metric.description }}</p>
          </article>
        </div>

        <div class="geo-two-column">
          <article class="card">
            <header class="card-header">
              <div>
                <h2>Topic Performance</h2>
                <p>示意資料，後續接正式分析資料</p>
              </div>
            </header>
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
                  <tr v-for="topic in state.topicPerformance" :key="topic.topicId">
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
            <header class="card-header">
              <div>
                <h2>Recommendations</h2>
                <p>示意資料，後續接正式建議演算法</p>
              </div>
            </header>
            <div class="geo-list">
              <div
                v-for="item in state.recommendations"
                :key="item.id"
                class="geo-list-item"
              >
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
              <h2>AI Answer Samples</h2>
              <p>示意資料，後續接 AI answer analysis 與 citations</p>
            </div>
          </header>
          <div class="geo-answer-grid">
            <section
              v-for="sample in state.aiAnswerSamples"
              :key="sample.id"
              class="geo-answer-card"
            >
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
