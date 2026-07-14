<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import AppIcon from "../components/ui/AppIcon.vue";
import { ApiError, api } from "../services/api";
import type {
  GeoAnalysisRunResult,
  GeoDashboardCitationRow,
  GeoDashboardMetricValue,
  GeoDashboardReport,
  GeoProjectResource,
  GeoQueryResource,
  GeoRunResultSemanticAnalysis,
} from "../types";
import {
  buildEvidenceHighlights,
  buildRunResultRows,
  filterRunResultRows,
  highlightEvidenceInHtml,
  paginateItems,
  renderSafeMarkdown,
  type EvidenceHighlight,
  type GeoReportRunResultRow,
  type PaginationState,
} from "../utils/geo-dashboard-drilldown";
import {
  buildDefaultGeoDashboardReportFilters,
  buildGeoDashboardReportQuery,
  formatGeoDashboardDelta,
  formatGeoDashboardMetric,
  geoDashboardDeltaTone,
  geoDashboardEnumLabel,
  geoDashboardMetricLabel,
  geoDashboardMetricTooltip,
  geoDashboardReportTooltips,
  geoDashboardSentimentDeltaTone,
  isGeoDashboardReportEmpty,
} from "../utils/geo-dashboard-report";

const route = useRoute();
const initialLiveProjectId =
  typeof route.query.projectId === "string" ? route.query.projectId : "";
const projects = ref<GeoProjectResource[]>([]);
const selectedProjectId = ref(initialLiveProjectId);
const liveReport = ref<GeoDashboardReport | null>(null);
const liveQueries = ref<GeoQueryResource[]>([]);
const liveRunResults = ref<GeoAnalysisRunResult[]>([]);
const liveLoading = ref(false);
const drilldownLoading = ref(false);
const projectsLoading = ref(false);
const liveError = ref("");
const drilldownError = ref("");
const projectError = ref("");
const lastLoadedAt = ref<string | null>(null);
const citationView = ref<"urls" | "domains">("urls");
const selectedRunResultRow = ref<GeoReportRunResultRow | null>(null);
const semanticAnalysisCache = ref<Record<string, GeoRunResultSemanticAnalysis | null>>({});
const semanticAnalysisErrors = ref<Record<string, string>>({});
const semanticAnalysisLoadingIds = ref<Set<string>>(new Set());
const citationPagination = reactive<PaginationState>({ page: 1, pageSize: 10 });
const runResultPagination = reactive<PaginationState>({ page: 1, pageSize: 10 });

const filters = reactive(buildDefaultGeoDashboardReportFilters());

const selectedProject = computed(() =>
  projects.value.find((project) => project.id === selectedProjectId.value),
);
const currentReport = computed(() => liveReport.value);
const reportIsEmpty = computed(() =>
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
const paginatedCitationRows = computed(() =>
  paginateItems(visibleCitationRows.value, citationPagination),
);
const currentQueries = computed(() => liveQueries.value);
const currentRunResults = computed(() => liveRunResults.value);
const runResultRows = computed(() =>
  filterRunResultRows(
    buildRunResultRows(currentRunResults.value, currentQueries.value),
    {
      periodStart: dashboardQuery()?.periodStart ?? "",
      periodEnd: dashboardQuery()?.periodEnd ?? "",
      provider: filters.provider || undefined,
      region: filters.region || undefined,
      language: filters.language || undefined,
    },
  ),
);
const paginatedRunResultRows = computed(() =>
  paginateItems(runResultRows.value, runResultPagination),
);
const selectedSemanticAnalysis = computed(() => {
  if (!selectedRunResultRow.value) return null;
  const resultId = selectedRunResultRow.value.result.id;
  return semanticAnalysisCache.value[resultId] ?? null;
});
const selectedEvidenceHighlights = computed<EvidenceHighlight[]>(() => {
  if (!selectedRunResultRow.value || !selectedSemanticAnalysis.value) return [];
  return buildEvidenceHighlights(
    selectedRunResultRow.value.result.rawResponse,
    selectedSemanticAnalysis.value.sentiments,
  );
});
const selectedRawResponseHtml = computed(() => {
  if (!selectedRunResultRow.value) return "";
  const raw = selectedRunResultRow.value.result.rawResponse || selectedRunResultRow.value.result.error || "";
  return highlightEvidenceInHtml(
    renderSafeMarkdown(raw),
    selectedEvidenceHighlights.value,
  );
});
onMounted(() => {
  void loadProjects();
});

watch(selectedProjectId, () => {
  if (selectedProjectId.value) {
    void loadLiveReport();
  }
});

watch(citationView, () => {
  citationPagination.page = 1;
});

watch(selectedProjectId, () => {
  runResultPagination.page = 1;
  selectedRunResultRow.value = null;
});

watch(paginatedRunResultRows, (page) => {
  void loadSemanticAnalysesForRows(page.items);
});

async function loadProjects(): Promise<void> {
  projectsLoading.value = true;
  projectError.value = "";
  try {
    const response = await api.geoAnalysis.projects();
    projects.value = response.items;
    if (
      (!selectedProjectId.value ||
        !response.items.some((project) => project.id === selectedProjectId.value)) &&
      response.items[0]
    ) {
      selectedProjectId.value = response.items[0].id;
    }
  } catch (caught) {
    projectError.value =
      caught instanceof ApiError ? caught.message : "無法載入 GEO 專案清單。";
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
    liveError.value = "請填寫完整的統計區間與比較區間。";
    return;
  }
  liveLoading.value = true;
  try {
    const [report, queries, runResults] = await Promise.all([
      api.geoAnalysis.dashboardReport(selectedProjectId.value, query),
      api.geoAnalysis.queries(selectedProjectId.value),
      api.geoAnalysis.runResults(selectedProjectId.value),
    ]);
    liveReport.value = report;
    liveQueries.value = queries.items;
    liveRunResults.value = runResults.items;
    resetSemanticAnalysisState();
    lastLoadedAt.value = new Date().toISOString();
  } catch (caught) {
    liveReport.value = null;
    liveQueries.value = [];
    liveRunResults.value = [];
    resetSemanticAnalysisState();
    liveError.value =
      caught instanceof ApiError ? caught.message : "無法載入 dashboard report。";
  } finally {
    liveLoading.value = false;
  }
}

function dashboardQuery() {
  return buildGeoDashboardReportQuery(filters);
}

function refreshReport(): void {
  void loadLiveReport();
}

async function openRunResult(row: GeoReportRunResultRow): Promise<void> {
  selectedRunResultRow.value = row;
  drilldownError.value = "";
  if (row.result.id in semanticAnalysisCache.value) {
    return;
  }
  drilldownLoading.value = true;
  try {
    semanticAnalysisErrors.value = omitRecordKey(
      semanticAnalysisErrors.value,
      row.result.id,
    );
    await loadSemanticAnalysis(row.result.id, "modal");
  } catch (caught) {
    drilldownError.value =
      caught instanceof ApiError ? caught.message : "無法載入 semantic analysis。";
  } finally {
    drilldownLoading.value = false;
  }
}

function closeRunResultModal(): void {
  selectedRunResultRow.value = null;
  drilldownError.value = "";
}

function nextPage(pagination: PaginationState, totalPages: number): void {
  pagination.page = Math.min(totalPages, pagination.page + 1);
}

function previousPage(pagination: PaginationState): void {
  pagination.page = Math.max(1, pagination.page - 1);
}

async function loadSemanticAnalysesForRows(rows: GeoReportRunResultRow[]): Promise<void> {
  const missingRows = rows.filter((row) => {
    return (
      !(row.result.id in semanticAnalysisCache.value) &&
      !semanticAnalysisLoadingIds.value.has(row.result.id)
    );
  });
  if (missingRows.length === 0) return;
  for (const row of missingRows) {
    void loadSemanticAnalysis(row.result.id, "summary");
  }
}

async function loadSemanticAnalysis(
  resultId: string,
  mode: "summary" | "modal",
): Promise<void> {
  semanticAnalysisLoadingIds.value = new Set([
    ...semanticAnalysisLoadingIds.value,
    resultId,
  ]);
  try {
    const analysis = await api.geoAnalysis.runResultSemanticAnalysis(resultId);
    semanticAnalysisCache.value = {
      ...semanticAnalysisCache.value,
      [resultId]: analysis,
    };
    semanticAnalysisErrors.value = omitRecordKey(
      semanticAnalysisErrors.value,
      resultId,
    );
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) {
      semanticAnalysisCache.value = {
        ...semanticAnalysisCache.value,
        [resultId]: null,
      };
      semanticAnalysisErrors.value = omitRecordKey(
        semanticAnalysisErrors.value,
        resultId,
      );
      return;
    }
    semanticAnalysisErrors.value = {
      ...semanticAnalysisErrors.value,
      [resultId]:
        caught instanceof ApiError ? caught.message : "無法載入 semantic analysis。",
    };
    if (mode === "modal") throw caught;
  } finally {
    const nextIds = new Set(semanticAnalysisLoadingIds.value);
    nextIds.delete(resultId);
    semanticAnalysisLoadingIds.value = nextIds;
  }
}

function resetSemanticAnalysisState(): void {
  semanticAnalysisLoadingIds.value = new Set();
  semanticAnalysisCache.value = {};
  semanticAnalysisErrors.value = {};
}

function omitRecordKey<T>(record: Record<string, T>, keyToOmit: string): Record<string, T> {
  return Object.fromEntries(
    Object.entries(record).filter(([key]) => key !== keyToOmit),
  );
}

function rowSemanticAnalysis(
  row: GeoReportRunResultRow,
): GeoRunResultSemanticAnalysis | null | undefined {
  if (row.result.id in semanticAnalysisCache.value) {
    return semanticAnalysisCache.value[row.result.id];
  }
  return undefined;
}

function rowSentimentSummary(row: GeoReportRunResultRow): string {
  if (semanticAnalysisLoadingIds.value.has(row.result.id)) return "載入中";
  if (semanticAnalysisErrors.value[row.result.id]) return "載入失敗";
  const analysis = rowSemanticAnalysis(row);
  if (analysis === undefined) return "待載入";
  if (analysis === null) return "尚無分析";
  if (analysis.status === "failed") {
    return `分析失敗${analysis.errorCode ? `：${analysis.errorCode}` : ""}`;
  }
  const positiveCount = analysis.sentiments.filter(
    (sentiment) => sentiment.sentiment === "positive",
  ).length;
  const negativeCount = analysis.sentiments.filter(
    (sentiment) => sentiment.sentiment === "negative",
  ).length;
  if (positiveCount === 0 && negativeCount === 0) return "無正負面";
  return `正面 ${positiveCount} / 負面 ${negativeCount}`;
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
  return `引用次數 ${metricValue(row.citationCount)} / 使用率 ${metricValue(row.usedPercent)} / 佔比 ${metricValue(row.sharePercent)}`;
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
        <p class="page-kicker">GEO 報表設計</p>
        <h1>Dashboard Report 設計沙盒</h1>
        <p>
          使用 Live API 檢視目前專案的 GEO dashboard report 資料型態、空狀態與報表呈現方式。
        </p>
      </div>
      <div class="page-actions">
        <button
          class="button button-secondary"
          type="button"
          :disabled="liveLoading || !selectedProjectId"
          @click="refreshReport"
        >
          <AppIcon name="refresh" :size="16" />重新整理
        </button>
      </div>
    </header>

    <section class="report-control-band">
      <label>
        <span class="report-label-with-help">
          專案
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.project }}</span>
          </span>
        </span>
        <select
          v-model="selectedProjectId"
          :disabled="projectsLoading"
        >
          <option value="">選擇專案</option>
          <option
            v-for="project in projects"
            :key="project.id"
            :value="project.id"
          >
            {{ project.name }}
          </option>
        </select>
      </label>
      <label>
        <span class="report-label-with-help">
          統計開始
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.periodStart }}</span>
          </span>
        </span>
        <input v-model="filters.periodStart" type="datetime-local" />
      </label>
      <label>
        <span class="report-label-with-help">
          統計結束
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.periodEnd }}</span>
          </span>
        </span>
        <input v-model="filters.periodEnd" type="datetime-local" />
      </label>
      <label>
        <span class="report-label-with-help">
          比較開始
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.comparisonStart }}</span>
          </span>
        </span>
        <input v-model="filters.comparisonStart" type="datetime-local" />
      </label>
      <label>
        <span class="report-label-with-help">
          比較結束
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.comparisonEnd }}</span>
          </span>
        </span>
        <input v-model="filters.comparisonEnd" type="datetime-local" />
      </label>
      <label>
        <span class="report-label-with-help">
          Provider
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.provider }}</span>
          </span>
        </span>
        <input v-model="filters.provider" type="text" placeholder="gemini" />
      </label>
      <label>
        <span class="report-label-with-help">
          地區
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.region }}</span>
          </span>
        </span>
        <input v-model="filters.region" type="text" placeholder="TW" />
      </label>
      <label>
        <span class="report-label-with-help">
          語言
          <span class="report-tooltip-trigger" tabindex="0">
            <AppIcon name="info" :size="14" />
            <span class="report-tooltip">{{ geoDashboardReportTooltips.language }}</span>
          </span>
        </span>
        <input v-model="filters.language" type="text" placeholder="zh-TW" />
      </label>
    </section>

    <div class="report-status-strip">
      <span class="badge badge-info">
        資料來源：Live API
      </span>
      <span>{{ selectedProject?.name ?? "尚未選擇專案" }}</span>
      <span>
        統計區間：
        {{ currentReport ? formatDateTime(currentReport.periodStart) : "-" }}
        -
        {{ currentReport ? formatDateTime(currentReport.periodEnd) : "-" }}
      </span>
      <span v-if="lastLoadedAt">最後載入 {{ formatDateTime(lastLoadedAt) }}</span>
    </div>

    <div v-if="projectError" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />{{ projectError }}
    </div>
    <div v-if="liveError" class="geo-report-error">
      <AppIcon name="alert-circle" :size="17" />{{ liveError }}
    </div>

    <div v-if="!selectedProjectId" class="empty-state report-empty-state">
      <AppIcon name="layers" />
      <strong>請先選擇 GEO 專案</strong>
      <span>需要專案 ID 才能載入 dashboard report。</span>
    </div>

    <div v-else-if="liveLoading" class="empty-state report-empty-state">
      <AppIcon name="refresh" />
      <strong>正在載入 dashboard report</strong>
      <span>系統正在向 Live API 取得實際報表資料。</span>
    </div>

    <div v-else-if="reportIsEmpty" class="empty-state report-empty-state">
      <AppIcon name="grid" />
      <strong>此區間沒有 dashboard report 資料</strong>
      <span>Live API 已回傳空資料，這裡呈現正式無資料版型。</span>
    </div>

    <template v-else-if="currentReport">
      <section class="report-overview-grid">
        <article
          v-for="card in currentReport.overview"
          :key="card.metricName"
          class="card report-kpi-card"
        >
          <div class="report-kpi-heading">
            <span class="report-label-with-help">
              {{ geoDashboardMetricLabel(card.metricName) }}
              <span class="report-tooltip-trigger" tabindex="0">
                <AppIcon name="info" :size="14" />
                <span class="report-tooltip">{{ geoDashboardMetricTooltip(card.metricName) }}</span>
              </span>
            </span>
            <span :class="metricTone(card.metric)">{{ metricDelta(card.metric) }}</span>
          </div>
          <strong>{{ metricValue(card.metric) }}</strong>
          <p>
            本期 {{ card.metric.numerator ?? "-" }} /
            {{ card.metric.denominator ?? "-" }}
            <span v-if="card.metric.comparisonValue !== null">
              ，前期 {{ card.metric.comparisonValue }}
            </span>
          </p>
        </article>
      </section>

      <section class="card">
        <header class="card-header">
          <div>
            <h2>實體比較</h2>
            <p>比較自有品牌與競品在回答中的能見度、提及次數與平均排名。</p>
          </div>
        </header>
        <div class="table-scroll">
          <table class="data-table report-table">
            <thead>
              <tr>
                <th>實體</th>
                <th>角色</th>
                <th>
                  <span class="report-label-with-help">
                    能見度
                    <span class="report-tooltip-trigger" tabindex="0">
                      <AppIcon name="info" :size="14" />
                      <span class="report-tooltip">{{ geoDashboardMetricTooltip("visibility") }}</span>
                    </span>
                  </span>
                </th>
                <th>
                  <span class="report-label-with-help">
                    提及次數
                    <span class="report-tooltip-trigger" tabindex="0">
                      <AppIcon name="info" :size="14" />
                      <span class="report-tooltip">{{ geoDashboardMetricTooltip("mentions") }}</span>
                    </span>
                  </span>
                </th>
                <th>
                  <span class="report-label-with-help">
                    平均排名
                    <span class="report-tooltip-trigger" tabindex="0">
                      <AppIcon name="info" :size="14" />
                      <span class="report-tooltip">{{ geoDashboardMetricTooltip("average_position") }}</span>
                    </span>
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="entity in currentReport.entities" :key="entity.entityId">
                <td><strong>{{ entity.entityName }}</strong></td>
                <td>
                  <span :class="badgeClass(entity.entityRole)">
                    {{ geoDashboardEnumLabel(entity.entityRole) }}
                  </span>
                </td>
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
                <td colspan="5">此區間沒有實體比較資料。</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="report-two-column">
        <article class="card">
          <header class="card-header report-card-tabs">
            <div>
              <h2>引用來源</h2>
              <p>依 URL 或網域檢視回答引用來源的使用率與佔比。</p>
            </div>
            <div class="segmented-control">
              <button
                type="button"
                :class="{ active: citationView === 'urls' }"
                @click="citationView = 'urls'"
              >
                URL
              </button>
              <button
                type="button"
                :class="{ active: citationView === 'domains' }"
                @click="citationView = 'domains'"
              >
                網域
              </button>
            </div>
          </header>
          <div class="table-scroll">
            <table class="data-table report-table">
              <thead>
                <tr>
                  <th>{{ citationView === "urls" ? "URL" : "網域" }}</th>
                  <th>歸屬</th>
                  <th>來源類型</th>
                  <th>
                    <span class="report-label-with-help">
                      指標
                      <span class="report-tooltip-trigger" tabindex="0">
                        <AppIcon name="info" :size="14" />
                        <span class="report-tooltip">
                          {{ geoDashboardReportTooltips.citationCount }}
                          {{ geoDashboardReportTooltips.usedPercent }}
                          {{ geoDashboardReportTooltips.sharePercent }}
                        </span>
                      </span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="citation in paginatedCitationRows.items" :key="citation.value">
                  <td>
                    <strong>{{ citation.label }}</strong>
                    <small>{{ citation.value }}</small>
                  </td>
                  <td>{{ geoDashboardEnumLabel(citation.ownership) }}</td>
                  <td>{{ geoDashboardEnumLabel(citation.sourceType) }}</td>
                  <td>{{ citationMetric(citation) }}</td>
                </tr>
                <tr v-if="visibleCitationRows.length === 0">
                  <td colspan="4">此區間沒有 citation {{ citationView === "urls" ? "URL" : "網域" }} 資料。</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="report-pagination">
            <span>
              第 {{ paginatedCitationRows.page }} / {{ paginatedCitationRows.totalPages }} 頁，
              共 {{ paginatedCitationRows.total }} 筆
            </span>
            <div>
              <button
                class="button button-secondary"
                type="button"
                :disabled="paginatedCitationRows.page <= 1"
                @click="previousPage(citationPagination)"
              >
                上一頁
              </button>
              <button
                class="button button-secondary"
                type="button"
                :disabled="paginatedCitationRows.page >= paginatedCitationRows.totalPages"
                @click="nextPage(citationPagination, paginatedCitationRows.totalPages)"
              >
                下一頁
              </button>
            </div>
          </div>
        </article>

        <article class="card">
          <header class="card-header">
            <div>
              <h2>情緒分布</h2>
              <p>統計回答中正向與負向 statement facts 的數量。</p>
            </div>
          </header>
          <div class="sentiment-stack">
            <div
              v-for="row in currentReport.sentiments"
              :key="row.sentiment"
              class="sentiment-row"
            >
              <span :class="badgeClass(row.sentiment)">{{ geoDashboardEnumLabel(row.sentiment) }}</span>
              <strong>{{ metricValue(row.statementCount) }}</strong>
              <small :class="sentimentMetricTone(row.sentiment, row.statementCount)">
                {{ metricDelta(row.statementCount) }}
              </small>
              <span class="report-tooltip-trigger" tabindex="0">
                <AppIcon name="info" :size="14" />
                <span class="report-tooltip">{{ geoDashboardReportTooltips.sentiment }}</span>
              </span>
            </div>
            <div v-if="currentReport.sentiments.length === 0" class="empty-state">
              <AppIcon name="activity" />
              <strong>沒有情緒資料</strong>
              <span>此區間沒有 positive 或 negative sentiment facts。</span>
            </div>
          </div>
        </article>
      </section>

      <section class="card">
        <header class="card-header">
          <div>
            <h2>Query 回答紀錄</h2>
            <p>檢視報表區間內跑過的 query 與 provider，點擊後查看 raw response、citations 與情緒句標註。</p>
          </div>
        </header>
        <div class="table-scroll">
          <table class="data-table report-table">
            <thead>
              <tr>
                <th>Query</th>
                <th>Provider</th>
                <th>情緒</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in paginatedRunResultRows.items"
                :key="row.result.id"
              >
                <td>{{ row.queryText }}</td>
                <td>{{ row.provider }}</td>
                <td>
                  <span class="report-row-sentiment">
                    {{ rowSentimentSummary(row) }}
                  </span>
                </td>
                <td>
                  <button
                    class="button button-secondary button-small"
                    type="button"
                    @click="openRunResult(row)"
                  >
                    檢視
                  </button>
                </td>
              </tr>
              <tr v-if="runResultRows.length === 0">
                <td colspan="4">此區間沒有 query 回答紀錄。</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="report-pagination">
          <span>
            第 {{ paginatedRunResultRows.page }} / {{ paginatedRunResultRows.totalPages }} 頁，
            共 {{ paginatedRunResultRows.total }} 筆
          </span>
          <div>
            <button
              class="button button-secondary"
              type="button"
              :disabled="paginatedRunResultRows.page <= 1"
              @click="previousPage(runResultPagination)"
            >
              上一頁
            </button>
            <button
              class="button button-secondary"
              type="button"
              :disabled="paginatedRunResultRows.page >= paginatedRunResultRows.totalPages"
              @click="nextPage(runResultPagination, paginatedRunResultRows.totalPages)"
            >
              下一頁
            </button>
          </div>
        </div>
      </section>
    </template>

    <div
      v-if="selectedRunResultRow"
      class="modal-backdrop"
      @click.self="closeRunResultModal"
    >
      <section class="modal report-run-result-modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <div>
            <h2>{{ selectedRunResultRow.queryText }}</h2>
          </div>
          <button class="button button-secondary" type="button" @click="closeRunResultModal">
            關閉
          </button>
        </header>
        <div class="modal-body">
          <dl class="report-detail-list">
            <dt>Provider</dt>
            <dd>{{ selectedRunResultRow.result.provider }}</dd>
            <dt>Model</dt>
            <dd>{{ selectedRunResultRow.result.model }}</dd>
            <dt>Status</dt>
            <dd>
              <span :class="badgeClass(selectedRunResultRow.result.status)">
                {{ selectedRunResultRow.result.status }}
              </span>
            </dd>
            <dt>Run At</dt>
            <dd>{{ formatDateTime(selectedRunResultRow.result.runAt) }}</dd>
            <dt>Region / Language</dt>
            <dd>{{ selectedRunResultRow.result.region }} / {{ selectedRunResultRow.result.language }}</dd>
            <dt>Analysis</dt>
            <dd>{{ selectedSemanticAnalysis?.status ?? selectedRunResultRow.result.analysisStatus ?? "尚無 semantic analysis" }}</dd>
          </dl>

          <section class="modal-section">
            <h3>Raw Response</h3>
            <div class="markdown-response" v-html="selectedRawResponseHtml"></div>
          </section>

          <section class="modal-section">
            <h3>情緒句標註</h3>
            <p v-if="drilldownLoading" class="empty-state compact-empty">載入 semantic analysis 中。</p>
            <p v-else-if="drilldownError" class="empty-state compact-empty">{{ drilldownError }}</p>
            <p v-else-if="!selectedSemanticAnalysis" class="empty-state compact-empty">尚無 semantic analysis。</p>
            <ul v-else-if="selectedSemanticAnalysis.sentiments.length" class="sentiment-evidence-list">
              <li
                v-for="sentiment in selectedSemanticAnalysis.sentiments"
                :key="`${sentiment.entityId}-${sentiment.sentiment}-${sentiment.statement}`"
              >
                <span :class="badgeClass(sentiment.sentiment)">
                  {{ geoDashboardEnumLabel(sentiment.sentiment) }}
                </span>
                <strong>{{ sentiment.entityName }}</strong>
                <span>{{ sentiment.statement }}</span>
                <small>
                  {{ sentiment.evidenceText && selectedRunResultRow.result.rawResponse.includes(sentiment.evidenceText)
                    ? "已在原文標註"
                    : "未在原文定位" }}
                </small>
              </li>
            </ul>
            <p v-else class="empty-state compact-empty">此 response 沒有正負面情緒句。</p>
          </section>

          <section class="modal-section">
            <h3>Citations</h3>
            <ol v-if="selectedRunResultRow.result.references.length" class="reference-list">
              <li
                v-for="reference in selectedRunResultRow.result.references"
                :key="`${reference.position}-${reference.url}`"
              >
                <span>#{{ reference.position }}</span>
                <a :href="reference.url" target="_blank" rel="noreferrer">
                  {{ reference.title ?? reference.domain ?? reference.url }}
                </a>
              </li>
            </ol>
            <p v-else class="empty-state compact-empty">此 response 沒有 citations。</p>
          </section>
        </div>
      </section>
    </div>
  </section>
</template>
