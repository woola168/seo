<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import AppIcon from "../components/ui/AppIcon.vue";
import {
  mockGeoDashboardReport,
  mockGeoDashboardReportProject,
} from "../mocks/geo-dashboard-report";
import { ApiError, api } from "../services/api";
import type {
  GeoDashboardCitationRow,
  GeoDashboardMetricValue,
  GeoDashboardReport,
  GeoProjectResource,
} from "../types";
import {
  buildGeoDashboardReportQuery,
  formatGeoDashboardDelta,
  formatGeoDashboardMetric,
  geoDashboardDeltaTone,
  geoDashboardSentimentDeltaTone,
  isGeoDashboardReportEmpty,
} from "../utils/geo-dashboard-report";

type DataSource = "mock" | "live";

const route = useRoute();
const initialLiveProjectId =
  typeof route.query.projectId === "string" ? route.query.projectId : "";
const dataSource = ref<DataSource>("mock");
const projects = ref<GeoProjectResource[]>([]);
const selectedProjectId = ref(mockGeoDashboardReportProject.id);
const liveReport = ref<GeoDashboardReport | null>(null);
const liveLoading = ref(false);
const projectsLoading = ref(false);
const liveError = ref("");
const projectError = ref("");
const lastLoadedAt = ref<string | null>(null);
const citationView = ref<"urls" | "domains">("urls");

const filters = reactive({
  periodStart: "2026-06-01T00:00",
  periodEnd: "2026-06-30T23:59",
  comparisonStart: "2026-05-01T00:00",
  comparisonEnd: "2026-05-31T23:59",
  provider: "",
  region: "",
  language: "",
});

const projectOptions = computed(() =>
  dataSource.value === "mock" ? [mockGeoDashboardReportProject] : projects.value,
);
const selectedProject = computed(() =>
  projectOptions.value.find((project) => project.id === selectedProjectId.value),
);
const currentReport = computed(() =>
  dataSource.value === "mock" ? mockGeoDashboardReport : liveReport.value,
);
const reportIsEmpty = computed(() =>
  dataSource.value === "live" &&
  !liveLoading.value &&
  !liveError.value &&
  liveReport.value !== null &&
  isGeoDashboardReportEmpty(liveReport.value),
);
const visibleCitationRows = computed(() =>
  citationView.value === "urls"
    ? currentReport.value?.citationUrls ?? []
    : currentReport.value?.citationDomains ?? [],
);
const sourceLabel = computed(() =>
  dataSource.value === "mock" ? "Mock Data" : "Live API",
);

onMounted(() => {
  if (initialLiveProjectId) {
    dataSource.value = "live";
    selectedProjectId.value = initialLiveProjectId;
  }
  void loadProjects();
});

watch(dataSource, (source) => {
  if (source === "mock") {
    selectedProjectId.value = mockGeoDashboardReportProject.id;
    return;
  }
  if (projects.value.length === 0) {
    selectedProjectId.value = initialLiveProjectId;
    void loadProjects();
    return;
  }
  selectedProjectId.value = projects.value[0].id;
});

watch(selectedProjectId, () => {
  if (dataSource.value === "live" && selectedProjectId.value) {
    void loadLiveReport();
  }
});

async function loadProjects(): Promise<void> {
  projectsLoading.value = true;
  projectError.value = "";
  try {
    const response = await api.geoAnalysis.projects();
    projects.value = response.items;
    if (
      dataSource.value === "live" &&
      (!selectedProjectId.value ||
        !response.items.some((project) => project.id === selectedProjectId.value)) &&
      response.items[0]
    ) {
      selectedProjectId.value = response.items[0].id;
    }
  } catch (caught) {
    projectError.value =
      caught instanceof ApiError
        ? caught.message
        : "無法載入 GEO project 清單。";
  } finally {
    projectsLoading.value = false;
  }
}

async function loadLiveReport(): Promise<void> {
  liveError.value = "";
  if (!selectedProjectId.value) return;
  const query = dashboardQuery();
  if (query === null) {
    liveReport.value = null;
    liveError.value = "請先填完整 period 與 comparison 日期區間。";
    return;
  }
  liveLoading.value = true;
  try {
    liveReport.value = await api.geoAnalysis.dashboardReport(
      selectedProjectId.value,
      query,
    );
    lastLoadedAt.value = new Date().toISOString();
  } catch (caught) {
    liveReport.value = null;
    liveError.value =
      caught instanceof ApiError
        ? caught.message
        : "無法載入 dashboard report。";
  } finally {
    liveLoading.value = false;
  }
}

function dashboardQuery() {
  return buildGeoDashboardReportQuery(filters);
}

function refreshReport(): void {
  if (dataSource.value === "mock") return;
  void loadLiveReport();
}

function metricValue(metric: GeoDashboardMetricValue): string {
  return formatGeoDashboardMetric(metric);
}

function metricDelta(metric: GeoDashboardMetricValue): string {
  return formatGeoDashboardDelta(metric);
}

function metricTone(metric: GeoDashboardMetricValue): string {
  return `text-${geoDashboardDeltaTone(metric)}`;
}

function sentimentMetricTone(
  sentiment: "positive" | "negative",
  metric: GeoDashboardMetricValue,
): string {
  return `text-${geoDashboardSentimentDeltaTone(sentiment, metric)}`;
}

function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function citationMetric(row: GeoDashboardCitationRow): string {
  return `${metricValue(row.citationCount)} / ${metricValue(row.usedPercent)} used / ${metricValue(row.sharePercent)} share`;
}

function badgeClass(value: string): string {
  if (value === "own_brand" || value === "positive") return "badge badge-success";
  if (value === "competitor" || value === "negative") return "badge badge-warning";
  return "badge badge-muted";
}
</script>

<template>
  <section class="page geo-dashboard-report-page">
    <header class="page-header geo-dashboard-report-header">
      <div>
        <p class="page-kicker">GEO Report Design</p>
        <h1>Dashboard Report Sandbox</h1>
        <p>
          用完整 mock data、live API 與無資料狀態檢視 GEO dashboard report 的資料型態與版面需求。
        </p>
      </div>
      <div class="page-actions">
        <div class="segmented-control" aria-label="Data source">
          <button
            type="button"
            :class="{ active: dataSource === 'mock' }"
            @click="dataSource = 'mock'"
          >
            Mock Data
          </button>
          <button
            type="button"
            :class="{ active: dataSource === 'live' }"
            @click="dataSource = 'live'"
          >
            Live API
          </button>
        </div>
        <button
          class="button button-secondary"
          type="button"
          :disabled="dataSource === 'mock' || liveLoading || !selectedProjectId"
          @click="refreshReport"
        >
          <AppIcon name="refresh" :size="16" />Refresh
        </button>
      </div>
    </header>

    <section class="report-control-band">
      <label>
        Project
        <select
          v-model="selectedProjectId"
          :disabled="dataSource === 'live' && projectsLoading"
        >
          <option value="">Select a project</option>
          <option
            v-for="project in projectOptions"
            :key="project.id"
            :value="project.id"
          >
            {{ project.name }}
          </option>
        </select>
      </label>
      <label>
        Period start
        <input v-model="filters.periodStart" type="datetime-local" />
      </label>
      <label>
        Period end
        <input v-model="filters.periodEnd" type="datetime-local" />
      </label>
      <label>
        Comparison start
        <input v-model="filters.comparisonStart" type="datetime-local" />
      </label>
      <label>
        Comparison end
        <input v-model="filters.comparisonEnd" type="datetime-local" />
      </label>
      <label>
        Provider
        <input v-model="filters.provider" type="text" placeholder="gemini" />
      </label>
      <label>
        Region
        <input v-model="filters.region" type="text" placeholder="TW" />
      </label>
      <label>
        Language
        <input v-model="filters.language" type="text" placeholder="zh-TW" />
      </label>
    </section>

    <div class="report-status-strip">
      <span class="badge" :class="dataSource === 'mock' ? 'badge-warning' : 'badge-info'">
        {{ sourceLabel }}
      </span>
      <span>{{ selectedProject?.name ?? "No project selected" }}</span>
      <span>
        {{ currentReport ? formatDateTime(currentReport.periodStart) : "-" }}
        -
        {{ currentReport ? formatDateTime(currentReport.periodEnd) : "-" }}
      </span>
      <span v-if="lastLoadedAt">Last loaded {{ formatDateTime(lastLoadedAt) }}</span>
    </div>

    <div v-if="projectError" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />{{ projectError }}
    </div>
    <div v-if="liveError" class="geo-report-error">
      <AppIcon name="alert-circle" :size="17" />{{ liveError }}
    </div>

    <div
      v-if="dataSource === 'live' && !selectedProjectId"
      class="empty-state report-empty-state"
    >
      <AppIcon name="layers" />
      <strong>請先選擇 GEO project</strong>
      <span>Live API 模式需要 project 才會查詢 dashboard report。</span>
    </div>

    <div v-else-if="liveLoading" class="empty-state report-empty-state">
      <AppIcon name="refresh" />
      <strong>正在載入 dashboard report</strong>
      <span>系統正在向 live API 取得目前篩選條件的報表資料。</span>
    </div>

    <div v-else-if="reportIsEmpty" class="empty-state report-empty-state">
      <AppIcon name="grid" />
      <strong>此區間尚無 dashboard report 資料</strong>
      <span>這是正式無資料版型；不會自動切回 mock data。</span>
    </div>

    <template v-else-if="currentReport">
      <section class="report-overview-grid">
        <article
          v-for="card in currentReport.overview"
          :key="card.metricName"
          class="card report-kpi-card"
        >
          <div class="report-kpi-heading">
            <span>{{ card.label }}</span>
            <span :class="metricTone(card.metric)">{{ metricDelta(card.metric) }}</span>
          </div>
          <strong>{{ metricValue(card.metric) }}</strong>
          <p>
            Current {{ card.metric.numerator ?? "-" }} /
            {{ card.metric.denominator ?? "-" }}
            <span v-if="card.metric.comparisonValue !== null">
              · Previous {{ card.metric.comparisonValue }}
            </span>
          </p>
        </article>
      </section>

      <section class="card">
        <header class="card-header">
          <div>
            <h2>Entity Comparison</h2>
            <p>比較 own brand 與 competitors 的能見度、提及次數與平均位置。</p>
          </div>
        </header>
        <div class="table-scroll">
          <table class="data-table report-table">
            <thead>
              <tr>
                <th>Entity</th>
                <th>Role</th>
                <th>Visibility</th>
                <th>Mentions</th>
                <th>Average position</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entity in currentReport.entities" :key="entity.entityId">
                <td><strong>{{ entity.entityName }}</strong></td>
                <td><span :class="badgeClass(entity.entityRole)">{{ entity.entityRole }}</span></td>
                <td>
                  {{ metricValue(entity.visibility) }}
                  <small :class="metricTone(entity.visibility)">{{ metricDelta(entity.visibility) }}</small>
                </td>
                <td>
                  {{ metricValue(entity.mentions) }}
                  <small :class="metricTone(entity.mentions)">{{ metricDelta(entity.mentions) }}</small>
                </td>
                <td>
                  {{ metricValue(entity.averagePosition) }}
                  <small :class="metricTone(entity.averagePosition)">{{ metricDelta(entity.averagePosition) }}</small>
                </td>
              </tr>
              <tr v-if="currentReport.entities.length === 0">
                <td colspan="5">此區間沒有 entity comparison 資料。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="report-two-column">
        <article class="card">
          <header class="card-header report-card-tabs">
            <div>
              <h2>Citations</h2>
              <p>檢視 URL 與 domain 的引用量、使用率與 share。</p>
            </div>
            <div class="segmented-control">
              <button
                type="button"
                :class="{ active: citationView === 'urls' }"
                @click="citationView = 'urls'"
              >
                URLs
              </button>
              <button
                type="button"
                :class="{ active: citationView === 'domains' }"
                @click="citationView = 'domains'"
              >
                Domains
              </button>
            </div>
          </header>
          <div class="table-scroll">
            <table class="data-table report-table">
              <thead>
                <tr>
                  <th>{{ citationView === "urls" ? "URL" : "Domain" }}</th>
                  <th>Ownership</th>
                  <th>Source</th>
                  <th>Metrics</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="citation in visibleCitationRows" :key="citation.value">
                  <td>
                    <strong>{{ citation.label }}</strong>
                    <small>{{ citation.value }}</small>
                  </td>
                  <td>{{ citation.ownership ?? "-" }}</td>
                  <td>{{ citation.sourceType ?? "-" }}</td>
                  <td>{{ citationMetric(citation) }}</td>
                </tr>
                <tr v-if="visibleCitationRows.length === 0">
                  <td colspan="4">此區間沒有 citation {{ citationView }} 資料。</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="card">
          <header class="card-header">
            <div>
              <h2>Sentiment Breakdown</h2>
              <p>positive / negative statements 的數量與比較區間變化。</p>
            </div>
          </header>
          <div class="sentiment-stack">
            <div
              v-for="row in currentReport.sentiments"
              :key="row.sentiment"
              class="sentiment-row"
            >
              <span :class="badgeClass(row.sentiment)">{{ row.sentiment }}</span>
              <strong>{{ metricValue(row.statementCount) }}</strong>
              <small :class="sentimentMetricTone(row.sentiment, row.statementCount)">
                {{ metricDelta(row.statementCount) }}
              </small>
            </div>
            <div v-if="currentReport.sentiments.length === 0" class="empty-state">
              <AppIcon name="activity" />
              <strong>沒有 sentiment 資料</strong>
              <span>此區間沒有 positive 或 negative statement facts。</span>
            </div>
          </div>
        </article>
      </section>
    </template>
  </section>
</template>
