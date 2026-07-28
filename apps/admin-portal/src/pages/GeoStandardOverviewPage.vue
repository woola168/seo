<script setup lang="ts">
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "vue-chartjs";
import { computed, onMounted, reactive, ref, watch } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
import DateRangePicker from "../components/ui/DateRangePicker.vue";
import GeoDataPreparationNotice from "../components/geo/GeoDataPreparationNotice.vue";
import { ApiError, api } from "../services/api";
import type {
  GeoAnalysisRunResult,
  GeoOverviewCitationRow,
  GeoOverviewKpi,
  GeoOverviewQuery,
  GeoOverviewReport,
  GeoOverviewResponsePage,
  GeoOverviewResponseRow,
  GeoProjectResource,
  GeoRunResultSemanticAnalysis,
} from "../types";
import { renderSafeMarkdown } from "../utils/geo-dashboard-drilldown";
import {
  resolveStoredGeoProjectId,
  setStoredGeoProjectId,
} from "../utils/geo-project-selection-storage";
import { formatSentimentRatio } from "../utils/geo-overview-format";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Filler,
  Tooltip,
  Legend,
);

type TimePreset = "7d" | "14d" | "30d" | "this_month" | "last_month" | "custom";
type MentionStatus = "all" | "mentioned" | "not_mentioned";
type SentimentMode = "all" | "positive" | "negative";
type FilterMenu = "project" | "time" | "region" | "topics" | "platforms" | "metadata";

const projects = ref<GeoProjectResource[]>([]);
const selectedProjectId = ref("");
const report = ref<GeoOverviewReport | null>(null);
const responses = ref<GeoOverviewResponsePage | null>(null);
const selectedResponse = ref<GeoOverviewResponseRow | null>(null);
const selectedResult = ref<GeoAnalysisRunResult | null>(null);
const selectedAnalysis = ref<GeoRunResultSemanticAnalysis | null>(null);
const loading = ref(false);
const responsesLoading = ref(false);
const modalLoading = ref(false);
const errorMessage = ref("");
const modalError = ref("");
const expandedTopics = ref<Set<string>>(new Set());
const citationView = ref<"url" | "domain">("url");
const citationSearch = ref("");
const citationPage = ref(1);
const citationPageSize = 10;
const timePreset = ref<TimePreset>("7d");
const customStart = ref("");
const customEnd = ref("");
const customDatePickerOpen = ref(false);
const timePresetBeforeDatePicker = ref<TimePreset>("7d");
const responseQueryId = ref("");
const mentionStatus = ref<MentionStatus>("all");
const sentimentMode = ref<SentimentMode>("all");
const responsePage = ref(1);
const hiddenVisibilitySeries = ref<Set<string>>(new Set());
const openFilterMenu = ref<FilterMenu | null>(null);
let reportRequestId = 0;
let responseRequestId = 0;

const filters = reactive({
  region: "",
  topicIds: [] as string[],
  providers: [] as string[],
  metadataIndustry: [] as string[],
  metadataType: [] as string[],
});

const queryOptions = computed(() =>
  (report.value?.topics ?? []).flatMap((topic) => topic.queries),
);
const selectedProjectLabel = computed(() =>
  projects.value.find((project) => project.id === selectedProjectId.value)?.name ?? "選擇 Project",
);
const selectedRegionLabel = computed(() => filters.region || "地區：全部");
const responseQueryLabel = computed(() =>
  queryOptions.value.find((query) => query.queryId === responseQueryId.value)?.queryText ?? "全部 Query",
);
const citationRows = computed(() => {
  const rows = citationView.value === "url"
    ? report.value?.citationUrls ?? []
    : report.value?.citationDomains ?? [];
  const needle = citationSearch.value.trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter((row) =>
    [row.title, row.value].some((value) => value?.toLowerCase().includes(needle)),
  );
});
const citationPageCount = computed(() => Math.max(1, Math.ceil(citationRows.value.length / citationPageSize)));
const pagedCitationRows = computed(() => {
  const start = (citationPage.value - 1) * citationPageSize;
  return citationRows.value.slice(start, start + citationPageSize);
});
const periodDays = computed(() => {
  if (!report.value) return 7;
  return Math.max(
    1,
    Math.ceil(
      (new Date(report.value.periodEnd).getTime() - new Date(report.value.periodStart).getTime()) /
        86_400_000,
    ),
  );
});
const visibilityChartData = computed(() => ({
  labels: report.value?.visibilityTrend[0]?.points.map((point) => shortDate(point.date)) ?? [],
  datasets: (report.value?.visibilityTrend ?? [])
    .filter((series) => !hiddenVisibilitySeries.value.has(series.entityId))
    .map((series) => ({
      label: series.entityName,
      data: series.points.map((point) => point.value),
      borderColor: entityColor(series.entityId),
      backgroundColor: entityColor(series.entityId),
      borderWidth: 2.5,
      pointRadius: 0,
      pointHoverRadius: 5,
      tension: 0.3,
    })),
}));
const visibilityChartMax = computed(() => {
  const values = visibilityChartData.value.datasets.flatMap((dataset) => dataset.data);
  const maximum = Math.max(...values, 1);
  return Math.ceil((maximum * 1.2) / 5) * 5;
});
const sentimentChartData = computed(() => ({
  labels: (report.value?.sentimentTrend ?? []).map((point) => shortDate(point.date)),
  datasets: [
    {
      label: "正面提及",
      data: (report.value?.sentimentTrend ?? []).map((point) => point.positiveCount),
      borderColor: "#1677ff",
      backgroundColor: "#69b1ff",
      borderWidth: 2,
      borderRadius: 4,
      tension: 0.3,
    },
    {
      label: "負面提及",
      data: (report.value?.sentimentTrend ?? []).map((point) => point.negativeCount),
      borderColor: "#d68c24",
      backgroundColor: "#fdb338",
      borderWidth: 2,
      borderRadius: 4,
      tension: 0.3,
    },
  ].filter((_, index) => sentimentMode.value === "all" || (sentimentMode.value === "positive" ? index === 0 : index === 1)),
}));
const visibilityChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: "index" as const },
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: "#1f1f1f", padding: 12, usePointStyle: true },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { color: "#8c8c8c", maxTicksLimit: 10 } },
    y: { beginAtZero: true, max: visibilityChartMax.value, grid: { color: "#f0f0f0" }, border: { display: false }, ticks: { color: "#bfbfbf", callback: (value: string | number) => `${value}%` } },
  },
}));
const sentimentChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: "index" as const },
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: "#1f1f1f", padding: 10 },
  },
  scales: {
    x: { grid: { display: false }, border: { display: false }, ticks: { color: "#8c8c8c", maxTicksLimit: 12 } },
    y: { beginAtZero: true, grid: { color: "#f0f0f0" }, border: { display: false }, ticks: { color: "#bfbfbf", precision: 0 } },
  },
};
const ownMentionTotals = computed(() => {
  let positive = 0;
  let negative = 0;
  for (const point of report.value?.sentimentTrend ?? []) {
    positive += point.positiveCount;
    negative += point.negativeCount;
  }
  return { positive, negative, ratio: negative ? positive / negative : null };
});

const chartColors = ["#1677ff", "#52c41a", "#7c3aed", "#f5222d", "#d68c24", "#13c2c2"];

function entityColor(entityId: string): string {
  const index = report.value?.visibilityTrend.findIndex((series) => series.entityId === entityId) ?? 0;
  return chartColors[Math.max(0, index) % chartColors.length];
}

function toggleVisibilitySeries(entityId: string): void {
  const next = new Set(hiddenVisibilitySeries.value);
  if (next.has(entityId)) {
    next.delete(entityId);
  } else if (next.size < Math.max(0, (report.value?.visibilityTrend.length ?? 1) - 1)) {
    next.add(entityId);
  }
  hiddenVisibilitySeries.value = next;
}

onMounted(() => void loadProjects());

watch(selectedProjectId, (projectId) => {
  setStoredGeoProjectId(projectId);
  resetDimensionFilters();
  void loadOverview();
});
watch(
  () => [filters.region, ...filters.topicIds, ...filters.providers, ...filters.metadataIndustry, ...filters.metadataType],
  () => {
    responsePage.value = 1;
    void loadOverview();
  },
);
watch([responseQueryId, mentionStatus, responsePage], () => void loadResponses());
watch([citationView, citationSearch], () => {
  citationPage.value = 1;
});

async function loadProjects(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";
  try {
    const response = await api.geoAnalysis.projects();
    projects.value = response.items;
    selectedProjectId.value = resolveStoredGeoProjectId(response.items);
    if (!selectedProjectId.value) loading.value = false;
  } catch (caught) {
    loading.value = false;
    errorMessage.value = apiMessage(caught, "無法載入 GEO 專案。");
  }
}

async function loadOverview(): Promise<void> {
  if (!selectedProjectId.value || !periodQuery()) return;
  const requestId = ++reportRequestId;
  loading.value = true;
  errorMessage.value = "";
  try {
    const nextReport = await api.geoAnalysis.overviewReport(
      selectedProjectId.value,
      buildQuery(),
    );
    if (requestId !== reportRequestId) return;
    report.value = nextReport;
    citationPage.value = 1;
    sanitizeFilters();
    await loadResponses();
  } catch (caught) {
    if (requestId !== reportRequestId) return;
    report.value = null;
    responses.value = null;
    errorMessage.value = apiMessage(caught, "無法載入 Overview 報表。");
  } finally {
    if (requestId === reportRequestId) loading.value = false;
  }
}

async function loadResponses(): Promise<void> {
  if (!selectedProjectId.value || !periodQuery()) return;
  const requestId = ++responseRequestId;
  responsesLoading.value = true;
  try {
    const nextResponses = await api.geoAnalysis.overviewResponses(
      selectedProjectId.value,
      {
        ...buildQuery(),
        queryId: responseQueryId.value || undefined,
        mentionStatus: mentionStatus.value,
        page: responsePage.value,
        pageSize: 20,
      },
    );
    if (requestId === responseRequestId) responses.value = nextResponses;
  } catch (caught) {
    if (requestId === responseRequestId) {
      errorMessage.value = apiMessage(caught, "無法載入 Query 回答紀錄。");
    }
  } finally {
    if (requestId === responseRequestId) responsesLoading.value = false;
  }
}

function buildQuery(): GeoOverviewQuery {
  const period = periodQuery();
  if (!period) throw new Error("日期區間尚未完成");
  return {
    ...period,
    topicIds: filters.topicIds,
    providers: filters.providers,
    region: filters.region || undefined,
    metadataIndustry: filters.metadataIndustry,
    metadataType: filters.metadataType,
    timeZone: "Asia/Taipei",
  };
}

function periodQuery(): Pick<GeoOverviewQuery, "periodStart" | "periodEnd"> | null {
  const now = new Date();
  const start = startOfDay(now);
  let end = addDays(start, 1);
  if (timePreset.value === "custom") {
    if (!customStart.value || !customEnd.value) return null;
    const customEndExclusive = new Date(`${customEnd.value}T00:00:00+08:00`);
    customEndExclusive.setDate(customEndExclusive.getDate() + 1);
    return {
      periodStart: new Date(`${customStart.value}T00:00:00+08:00`).toISOString(),
      periodEnd: customEndExclusive.toISOString(),
    };
  }
  if (timePreset.value === "this_month") {
    start.setDate(1);
  } else if (timePreset.value === "last_month") {
    end = new Date(start.getFullYear(), start.getMonth(), 1);
    start.setDate(1);
    start.setMonth(start.getMonth() - 1);
  } else {
    const days = Number(timePreset.value.replace("d", ""));
    start.setDate(start.getDate() - days + 1);
  }
  return { periodStart: start.toISOString(), periodEnd: end.toISOString() };
}

function applyTimePreset(): void {
  if (timePreset.value !== "custom") void loadOverview();
}

function applyCustomRange(range: { start: string; end: string }): void {
  customStart.value = range.start;
  customEnd.value = range.end;
  customDatePickerOpen.value = false;
  void loadOverview();
}

function cancelCustomRange(): void {
  customDatePickerOpen.value = false;
  timePreset.value = timePresetBeforeDatePicker.value;
}

function resetFilters(): void {
  timePreset.value = "7d";
  customStart.value = "";
  customEnd.value = "";
  resetDimensionFilters();
  void loadOverview();
}

function resetDimensionFilters(): void {
  filters.region = "";
  filters.topicIds = [];
  filters.providers = [];
  filters.metadataIndustry = [];
  filters.metadataType = [];
  responseQueryId.value = "";
  mentionStatus.value = "all";
  responsePage.value = 1;
  expandedTopics.value = new Set();
  hiddenVisibilitySeries.value = new Set();
  sentimentMode.value = "all";
  openFilterMenu.value = null;
  customDatePickerOpen.value = false;
}

function sanitizeFilters(): void {
  if (!report.value) return;
  const validTopics = new Set(report.value.filterOptions.topics.map((item) => item.value));
  const validPlatforms = new Set(report.value.filterOptions.platforms.map((item) => item.value));
  const nextTopics = filters.topicIds.filter((item) => validTopics.has(item));
  const nextProviders = filters.providers.filter((item) => validPlatforms.has(item));
  if (nextTopics.length !== filters.topicIds.length) filters.topicIds = nextTopics;
  if (nextProviders.length !== filters.providers.length) filters.providers = nextProviders;
}

function toggleSelection(values: string[], value: string): void {
  const index = values.indexOf(value);
  if (index >= 0) values.splice(index, 1);
  else values.push(value);
}

function handleFilterMenuToggle(menu: FilterMenu, event: Event): void {
  const details = event.currentTarget as HTMLDetailsElement;
  if (details.open) {
    customDatePickerOpen.value = false;
    openFilterMenu.value = menu;
  } else if (openFilterMenu.value === menu) {
    openFilterMenu.value = null;
  }
}

function closeSingleFilter(event: Event): void {
  (event.currentTarget as HTMLElement).closest("details")?.removeAttribute("open");
  openFilterMenu.value = null;
}

function selectProject(projectId: string, event: Event): void {
  selectedProjectId.value = projectId;
  closeSingleFilter(event);
}

function selectTimePreset(preset: TimePreset, event: Event): void {
  if (preset === "custom") timePresetBeforeDatePicker.value = timePreset.value;
  timePreset.value = preset;
  closeSingleFilter(event);
  if (preset === "custom") {
    customDatePickerOpen.value = true;
    return;
  }
  customDatePickerOpen.value = false;
  applyTimePreset();
}

function selectRegion(region: string, event: Event): void {
  filters.region = region;
  closeSingleFilter(event);
}

function toggleTopic(topicKey: string): void {
  const next = new Set(expandedTopics.value);
  if (next.has(topicKey)) next.delete(topicKey);
  else next.add(topicKey);
  expandedTopics.value = next;
}

function selectResponseQuery(queryId: string, event: Event): void {
  responseQueryId.value = queryId;
  (event.currentTarget as HTMLElement).closest("details")?.removeAttribute("open");
}

function selectCitationView(view: "url" | "domain"): void {
  citationView.value = view;
  citationPage.value = 1;
}

async function openResponse(row: GeoOverviewResponseRow): Promise<void> {
  selectedResponse.value = row;
  selectedResult.value = null;
  selectedAnalysis.value = null;
  modalError.value = "";
  modalLoading.value = true;
  try {
    const [result, analysis] = await Promise.all([
      api.geoAnalysis.runResult(row.runResultId),
      api.geoAnalysis.runResultSemanticAnalysis(row.runResultId).catch((caught) => {
        if (caught instanceof ApiError && caught.status === 404) return null;
        throw caught;
      }),
    ]);
    selectedResult.value = result;
    selectedAnalysis.value = analysis;
  } catch (caught) {
    modalError.value = apiMessage(caught, "無法載入完整回答。");
  } finally {
    modalLoading.value = false;
  }
}

function closeModal(): void {
  selectedResponse.value = null;
  selectedResult.value = null;
  selectedAnalysis.value = null;
  modalError.value = "";
}

function kpi(name: GeoOverviewKpi["metricName"]): GeoOverviewKpi | undefined {
  return report.value?.overview.find((item) => item.metricName === name);
}

function kpiValue(item: GeoOverviewKpi | undefined): string {
  if (!item) return "-";
  if (item.unit === "count") return Math.round(item.value).toLocaleString("zh-TW");
  if (item.unit === "position") return item.value ? item.value.toFixed(1) : "-";
  return `${item.value.toFixed(1)}%`;
}

function secondaryValue(item: GeoOverviewKpi | undefined): string {
  if (!item || item.secondaryValue === null) return "尚無資料";
  if (item.secondaryUnit === "percent") return `${item.secondaryValue.toFixed(1)}%`;
  return item.secondaryValue.toFixed(1);
}

function percent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function signedPercent(value: number | null): string {
  if (value === null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}pp`;
}

function shortDate(value: string): string {
  const [, month, day] = value.split("-");
  return `${month}/${day}`;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("zh-TW", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatTaipeiDate(value: string): string {
  return new Intl.DateTimeFormat("zh-TW", {
    timeZone: "Asia/Taipei",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

function timePresetLabel(): string {
  if (timePreset.value === "custom") {
    return customStart.value && customEnd.value
      ? `${customStart.value} ~ ${customEnd.value}`
      : "自訂區間";
  }
  return {
    "7d": "最近 7 天",
    "14d": "最近 14 天",
    "30d": "最近 30 天",
    this_month: "本月",
    last_month: "上月",
  }[timePreset.value];
}

function entityInitial(name: string): string {
  return name.trim().slice(0, 1).toUpperCase() || "-";
}

function providerLabel(value: string): string {
  return report.value?.filterOptions.platforms.find((item) => item.value === value)?.label ?? value;
}

function mentionLabel(value: boolean | null): string {
  if (value === true) return "已提及";
  if (value === false) return "未提及";
  return "尚無分析";
}

function mentionClass(value: boolean | null): string {
  if (value === true) return "status-positive";
  if (value === false) return "status-muted";
  return "status-warning";
}

function citationType(row: GeoOverviewCitationRow): string {
  if (row.ownership === "owned") return "Owned";
  if (row.ownership === "other") return "Others";
  return "Mixed";
}

function citationHref(row: GeoOverviewCitationRow): string {
  return /^https?:\/\//i.test(row.value) ? row.value : `https://${row.value}`;
}

async function copyCitationValue(row: GeoOverviewCitationRow): Promise<void> {
  try {
    await navigator.clipboard.writeText(row.value);
  } catch {
    errorMessage.value = "無法複製引用連結，請稍後再試。";
  }
}

function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function addDays(value: Date, days: number): Date {
  const next = new Date(value);
  next.setDate(next.getDate() + days);
  return next;
}

function apiMessage(caught: unknown, fallback: string): string {
  return caught instanceof ApiError ? caught.message : fallback;
}
</script>

<template>
  <main class="geo-overview-page">
    <header class="overview-heading">
      <div>
        <h1>Overview</h1>
        <p>品牌在 AI 搜尋中的能見度、評價傾向與競品表現總覽。</p>
      </div>
    </header>

    <GeoDataPreparationNotice v-if="report?.isPreparing && !loading" />

    <section class="overview-toolbar" aria-label="Overview 查詢條件">
      <div class="filter-group">
      <details class="filter-menu single-filter project-filter" :open="openFilterMenu === 'project'" @toggle="handleFilterMenuToggle('project', $event)">
        <summary><span class="filter-menu-value">{{ selectedProjectLabel }}</span><AppIcon name="chevron-right" :size="13" /></summary>
        <div class="filter-menu-panel single-filter-options">
          <button v-for="project in projects" :key="project.id" :class="{ active: selectedProjectId === project.id }" type="button" @click="selectProject(project.id, $event)"><span>{{ project.name }}</span><AppIcon v-if="selectedProjectId === project.id" name="check" :size="13" /></button>
          <p v-if="!projects.length">尚無可檢視的 Project</p>
        </div>
      </details>

      <div class="time-filter-wrap">
        <details class="filter-menu single-filter time-filter" :open="openFilterMenu === 'time'" @toggle="handleFilterMenuToggle('time', $event)">
          <summary><span class="filter-menu-value">{{ timePresetLabel() }}</span><AppIcon name="chevron-right" :size="13" /></summary>
          <div class="filter-menu-panel single-filter-options">
            <button v-for="option in [{value:'7d',label:'最近 7 天'},{value:'14d',label:'最近 14 天'},{value:'30d',label:'最近 30 天'},{value:'this_month',label:'本月'},{value:'last_month',label:'上月'},{value:'custom',label:'自訂區間'}]" :key="option.value" :class="{ active: timePreset === option.value }" type="button" @click="selectTimePreset(option.value as TimePreset, $event)"><span>{{ option.label }}</span><AppIcon v-if="timePreset === option.value" name="check" :size="13" /></button>
          </div>
        </details>
        <DateRangePicker
          v-if="customDatePickerOpen"
          :start="customStart"
          :end="customEnd"
          @apply="applyCustomRange"
          @cancel="cancelCustomRange"
        />
      </div>

      <details class="filter-menu single-filter region-filter" :open="openFilterMenu === 'region'" @toggle="handleFilterMenuToggle('region', $event)">
        <summary><span class="filter-menu-value">{{ selectedRegionLabel }}</span><AppIcon name="chevron-right" :size="13" /></summary>
        <div class="filter-menu-panel single-filter-options">
          <button :class="{ active: filters.region === '' }" type="button" @click="selectRegion('', $event)"><span>全部地區</span><AppIcon v-if="filters.region === ''" name="check" :size="13" /></button>
          <button v-for="region in report?.filterOptions.regions ?? []" :key="region" :class="{ active: filters.region === region }" type="button" @click="selectRegion(region, $event)"><span>{{ region }}</span><AppIcon v-if="filters.region === region" name="check" :size="13" /></button>
        </div>
      </details>

      <details class="filter-menu" :open="openFilterMenu === 'topics'" @toggle="handleFilterMenuToggle('topics', $event)">
        <summary>主題<span v-if="filters.topicIds.length">{{ filters.topicIds.length }}</span><AppIcon name="chevron-right" :size="13" /></summary>
        <div class="filter-menu-panel">
          <label v-for="option in report?.filterOptions.topics ?? []" :key="option.value">
            <input
              type="checkbox"
              :checked="filters.topicIds.includes(option.value)"
              @change="toggleSelection(filters.topicIds, option.value)"
            />
            <span class="filter-checkbox"><AppIcon v-if="filters.topicIds.includes(option.value)" name="check" :size="10" /></span>
            <span>{{ option.label }}</span>
          </label>
          <p v-if="!report?.filterOptions.topics.length">尚無主題</p>
        </div>
      </details>

      <details class="filter-menu" :open="openFilterMenu === 'platforms'" @toggle="handleFilterMenuToggle('platforms', $event)">
        <summary>平台<span v-if="filters.providers.length">{{ filters.providers.length }}</span><AppIcon name="chevron-right" :size="13" /></summary>
        <div class="filter-menu-panel">
          <label v-for="option in report?.filterOptions.platforms ?? []" :key="option.value">
            <input
              type="checkbox"
              :checked="filters.providers.includes(option.value)"
              @change="toggleSelection(filters.providers, option.value)"
            />
            <span class="filter-checkbox"><AppIcon v-if="filters.providers.includes(option.value)" name="check" :size="10" /></span>
            <span>{{ option.label }}</span>
          </label>
          <p v-if="!report?.filterOptions.platforms.length">尚無平台資料</p>
        </div>
      </details>

      <details class="filter-menu metadata-menu" :open="openFilterMenu === 'metadata'" @toggle="handleFilterMenuToggle('metadata', $event)">
        <summary>Metadata<span v-if="filters.metadataIndustry.length + filters.metadataType.length">{{ filters.metadataIndustry.length + filters.metadataType.length }}</span><AppIcon name="chevron-right" :size="13" /></summary>
        <div class="filter-menu-panel">
          <strong>industry</strong>
          <label v-for="value in report?.filterOptions.metadataIndustries ?? []" :key="`industry-${value}`">
            <input type="checkbox" :checked="filters.metadataIndustry.includes(value)" @change="toggleSelection(filters.metadataIndustry, value)" />
            <span class="filter-checkbox"><AppIcon v-if="filters.metadataIndustry.includes(value)" name="check" :size="10" /></span>
            <span>{{ value }}</span>
          </label>
          <strong>type</strong>
          <label v-for="value in report?.filterOptions.metadataTypes ?? []" :key="`type-${value}`">
            <input type="checkbox" :checked="filters.metadataType.includes(value)" @change="toggleSelection(filters.metadataType, value)" />
            <span class="filter-checkbox"><AppIcon v-if="filters.metadataType.includes(value)" name="check" :size="10" /></span>
            <span>{{ value }}</span>
          </label>
          <p v-if="!(report?.filterOptions.metadataIndustries.length || report?.filterOptions.metadataTypes.length)">Query 尚未設定 Metadata</p>
        </div>
      </details>
      </div>

      <div class="toolbar-actions">
        <button class="secondary-button" type="button" @click="resetFilters">
          <AppIcon name="refresh" :size="14" />重置
        </button>
        <button class="secondary-button" type="button" disabled title="報告匯出功能尚未開放">
          <AppIcon name="download" :size="14" />匯出報告
        </button>
      </div>
    </section>

    <div v-if="errorMessage" class="overview-error">
      <AppIcon name="alert-circle" :size="17" />{{ errorMessage }}
    </div>
    <div v-if="loading && !report" class="overview-empty">
      <AppIcon name="refresh" :size="24" /><strong>正在載入 Overview</strong>
    </div>
    <div v-else-if="!selectedProjectId" class="overview-empty">
      <AppIcon name="briefcase" :size="24" /><strong>尚無可檢視的 GEO Project</strong>
    </div>

    <template v-else-if="report">
      <section class="kpi-grid">
        <article class="kpi-card">
          <div class="kpi-title"><span>品牌提及</span><span class="kpi-icon blue"><AppIcon name="user" /></span></div>
          <div class="kpi-value">{{ Math.round(kpi('mentions')?.value ?? 0) }}<small> / {{ Math.round(kpi('mentions')?.denominator ?? 0) }}</small></div>
          <div class="kpi-sub">覆蓋率 <strong>{{ secondaryValue(kpi('mentions')) }}</strong></div>
        </article>
        <article class="kpi-card">
          <div class="kpi-title"><span>平均排名</span><span class="kpi-icon green"><AppIcon name="activity" /></span></div>
          <div class="kpi-value">{{ kpiValue(kpi('average_position')) }}</div>
          <div class="kpi-sub">競品最佳 <strong>{{ secondaryValue(kpi('average_position')) }}</strong></div>
        </article>
        <article class="kpi-card">
          <div class="kpi-title"><span>能見度</span><span class="kpi-icon purple"><AppIcon name="eye" /></span></div>
          <div class="kpi-value">{{ kpiValue(kpi('visibility')) }}</div>
          <div class="kpi-sub">產業均值 <strong>尚無資料</strong></div>
        </article>
        <article class="kpi-card">
          <div class="kpi-title"><span>聲量佔有率</span><span class="kpi-icon gold"><AppIcon name="grid" /></span></div>
          <div class="kpi-value">{{ kpiValue(kpi('sov')) }}</div>
          <div class="kpi-sub">次高 <strong>{{ secondaryValue(kpi('sov')) }}</strong></div>
        </article>
        <article class="kpi-card citation-kpi-card">
          <div><span>自有引用份額</span><strong>{{ percent(report.citationSummary.ownedSharePercent) }}</strong></div>
          <i></i>
          <div><span>引用次數</span><strong>{{ report.citationSummary.citationCount.toLocaleString() }}</strong></div>
        </article>
      </section>

      <section class="overview-card chart-card">
        <header><div><h2>能見度分數趨勢</h2><p>點擊圖例可隱藏／顯示品牌，刻度會自動調整</p></div></header>
        <div v-if="report.visibilityTrend.length" class="chart-legend-chips">
          <button
            v-for="series in report.visibilityTrend"
            :key="series.entityId"
            :class="{ muted: hiddenVisibilitySeries.has(series.entityId) }"
            type="button"
            @click="toggleVisibilitySeries(series.entityId)"
          >
            <span :style="{ background: entityColor(series.entityId) }"></span>
            {{ series.entityName }}
            <b>{{ (series.points.reduce((sum, point) => sum + point.value, 0) / Math.max(1, series.points.length)).toFixed(1) }}%</b>
          </button>
        </div>
        <div class="chart-frame visibility-chart-frame">
          <Line v-if="report.visibilityTrend.length" :data="visibilityChartData" :options="visibilityChartOptions" />
          <div v-else class="inline-empty">此區間沒有能見度資料</div>
        </div>
      </section>

      <section class="overview-card chart-card">
        <header><div><h2>品牌評價傾向</h2><p>AI 回答中提及品牌時的正負向評價</p></div>
          <nav class="segmented-control" aria-label="情緒趨勢篩選">
            <button v-for="tab in [{value:'all',label:'全部'},{value:'positive',label:'正向'},{value:'negative',label:'負向'}]" :key="tab.value" :class="{ active: sentimentMode === tab.value }" type="button" @click="sentimentMode = tab.value as SentimentMode">{{ tab.label }}</button>
          </nav>
        </header>
        <div class="sentiment-totals">
          <span>正面提及 <b>{{ ownMentionTotals.positive }}</b></span>
          <i></i>
          <span>負面提及 <b>{{ ownMentionTotals.negative }}</b></span>
          <i></i>
          <span>正負比 <b>{{ formatSentimentRatio(ownMentionTotals.ratio) }}</b></span>
        </div>
        <div class="sentiment-legend">
          <span v-if="sentimentMode !== 'negative'"><i class="positive"></i>正向提及</span>
          <span v-if="sentimentMode !== 'positive'"><i class="negative"></i>負向提及</span>
        </div>
        <div class="chart-frame">
          <Bar v-if="periodDays <= 14" :data="sentimentChartData" :options="sentimentChartOptions" />
          <Line v-else :data="sentimentChartData" :options="sentimentChartOptions" />
        </div>
        <p v-if="periodDays > 14" class="chart-note">區間超過 14 天，已改以折線圖呈現趨勢。</p>
      </section>

      <section class="overview-card table-card">
        <header><div><h2>AI 搜尋品牌能見度</h2><p>本品牌與競品的能見度排名</p></div></header>
        <div class="table-scroll"><table><thead><tr><th>品牌</th><th>能見度</th><th>較上期</th><th>聲量佔有率</th><th>平均排名</th></tr></thead>
          <tbody>
            <tr v-for="entity in report.entities" :key="entity.entityId">
              <td><span class="brand-cell"><span class="brand-avatar" :style="{ background: entityColor(entity.entityId) }">{{ entityInitial(entity.entityName) }}</span><strong>{{ entity.entityName }}</strong><small v-if="entity.entityRole === 'own_brand'" class="self-badge">自身</small></span></td>
              <td>{{ percent(entity.visibilityPercent) }}</td><td :class="entity.visibilityDeltaPp !== null && entity.visibilityDeltaPp >= 0 ? 'positive-text' : 'negative-text'">{{ signedPercent(entity.visibilityDeltaPp) }}</td>
              <td>{{ percent(entity.sovPercent) }}</td><td>{{ entity.averagePosition ? entity.averagePosition.toFixed(1) : '-' }}</td>
            </tr>
            <tr v-if="!report.entities.length"><td colspan="5" class="empty-cell">此區間沒有品牌分析資料</td></tr>
          </tbody>
        </table></div>
      </section>

      <section class="overview-card table-card">
        <header><div><h2>追蹤問題分析</h2><p>了解個別追蹤問題的相關數據</p></div></header>
        <div class="table-scroll"><table class="topic-table"><thead><tr><th>主題</th><th>能見度</th><th>聲量佔有率</th><th>引用次數</th></tr></thead>
          <tbody v-for="topic in report.topics" :key="topic.topicId ?? 'none'">
            <tr class="topic-row" @click="toggleTopic(topic.topicId ?? 'none')">
              <td><AppIcon name="chevron-right" :class="{ 'topic-chevron-expanded': expandedTopics.has(topic.topicId ?? 'none') }" :size="15" /><span><strong>{{ topic.topicName }}</strong><small>{{ topic.queries.length }} 追蹤問題清單</small></span></td>
              <td>{{ percent(topic.visibilityPercent) }}</td><td>{{ percent(topic.sovPercent) }}</td><td>{{ topic.citationCount }}</td>
            </tr>
            <tr v-for="queryRow in expandedTopics.has(topic.topicId ?? 'none') ? topic.queries : []" :key="queryRow.queryId" class="query-child-row">
              <td>{{ queryRow.queryText }}</td><td>{{ percent(queryRow.visibilityPercent) }}</td><td>{{ percent(queryRow.sovPercent) }}</td><td>{{ queryRow.citationCount }}</td>
            </tr>
          </tbody>
        </table></div>
      </section>

      <section class="overview-card table-card">
        <header><div><h2>回應</h2><p>選擇查詢，並查看來自不同 LLM 模型的所有 AI 回應</p></div></header>
        <div class="response-controls">
          <details class="response-query-select">
            <summary><span>{{ responseQueryLabel }}</span><AppIcon name="chevron-right" :size="13" /></summary>
            <div class="response-query-options">
              <button :class="{ active: responseQueryId === '' }" type="button" @click="selectResponseQuery('', $event)"><span>全部 Query</span><AppIcon v-if="responseQueryId === ''" name="check" :size="13" /></button>
              <button v-for="queryRow in queryOptions" :key="queryRow.queryId" :class="{ active: responseQueryId === queryRow.queryId }" type="button" @click="selectResponseQuery(queryRow.queryId, $event)"><span>{{ queryRow.queryText }}</span><AppIcon v-if="responseQueryId === queryRow.queryId" name="check" :size="13" /></button>
            </div>
          </details>
        <nav class="segmented-control" aria-label="回答提及篩選">
          <button v-for="tab in [{value:'all',label:'全部'},{value:'mentioned',label:'已提及'},{value:'not_mentioned',label:'未提及'}]" :key="tab.value" :class="{ active: mentionStatus === tab.value }" type="button" @click="mentionStatus = tab.value as MentionStatus">{{ tab.label }}</button>
        </nav>
        </div>
        <div class="table-scroll"><table class="response-table">
          <colgroup><col /><col style="width:90px" /><col style="width:150px" /><col style="width:70px" /><col style="width:110px" /></colgroup>
          <thead><tr><th>回應</th><th>已提及</th><th>平台</th><th>地區</th><th>日期 (UTC+8)</th></tr></thead>
          <tbody>
            <tr v-for="row in responses?.items ?? []" :key="row.runResultId" class="clickable-row" @click="openResponse(row)">
              <td><span>{{ row.responseExcerpt }}</span></td><td><span :class="['mention-icon', mentionClass(row.mentioned)]"><AppIcon :name="row.mentioned ? 'check' : row.mentioned === false ? 'x' : 'more'" :size="16" /></span></td><td><span class="platform-pill">{{ providerLabel(row.provider) }}</span></td><td>{{ row.region }}</td><td>{{ formatTaipeiDate(row.completedAt) }}</td>
            </tr>
            <tr v-if="!responsesLoading && !responses?.items.length"><td colspan="5" class="empty-cell">此條件沒有 Query 回答</td></tr>
          </tbody>
        </table></div>
        <footer class="pagination"><span>共 {{ responses?.total ?? 0 }} 筆</span><div><button type="button" :disabled="responsePage <= 1" @click="responsePage--"><AppIcon name="chevron-left" :size="15" /></button><span>第 {{ responsePage }} 頁</span><button type="button" :disabled="responsePage * 20 >= (responses?.total ?? 0)" @click="responsePage++"><AppIcon name="chevron-right" :size="15" /></button></div></footer>
      </section>

      <section class="overview-card table-card citation-card">
        <header><div><h2>引用來源</h2><p>探索 AI 回答中最常被引用的網頁</p></div></header>
        <div class="citation-controls">
          <nav class="citation-view-switch" aria-label="引用來源檢視方式"><button :class="{ active: citationView === 'url' }" type="button" @click="selectCitationView('url')">By Url</button><button :class="{ active: citationView === 'domain' }" type="button" @click="selectCitationView('domain')">By Domain</button></nav>
          <div class="citation-search"><AppIcon name="search" :size="14" /><input v-model="citationSearch" type="search" placeholder="搜尋" /></div>
        </div>
        <div class="table-scroll"><table class="citation-table">
          <colgroup>
            <col style="width:48px" /><col style="width:300px" /><col style="width:90px" />
            <col style="width:110px" /><col style="width:80px" /><col style="width:90px" />
            <col style="width:90px" /><col style="width:120px" /><col style="width:100px" /><col style="width:160px" />
          </colgroup>
          <thead><tr><th>索引</th><th>{{ citationView === 'url' ? '頁面' : '網域' }}</th><th>引用次數</th><th>追蹤問題數量</th><th>引用率</th><th>引用份額</th><th>類型</th><th>標籤</th><th>在引用中提及</th><th>在引用中提及的競爭對手</th></tr></thead>
          <tbody>
            <tr v-for="(row, index) in pagedCitationRows" :key="row.value">
              <td>{{ (citationPage - 1) * citationPageSize + index + 1 }}</td>
              <td>
                <div class="citation-page-cell">
                  <span class="citation-globe"><AppIcon name="globe" :size="13" /></span>
                  <span class="citation-page-copy">
                    <strong>{{ citationView === 'url' ? (row.title ?? row.value) : row.value }}</strong>
                    <small v-if="citationView === 'url'">{{ row.value }}</small>
                  </span>
                  <span class="citation-row-actions">
                    <button type="button" title="複製連結" @click="copyCitationValue(row)"><AppIcon name="copy" :size="13" /></button>
                    <a :href="citationHref(row)" target="_blank" rel="noreferrer" title="開啟連結"><AppIcon name="external-link" :size="13" /></a>
                  </span>
                </div>
              </td>
              <td>{{ row.citationCount }}</td><td>{{ row.queryCount }}</td><td>{{ percent(row.citationRatePercent) }}</td><td>{{ percent(row.citationSharePercent) }}</td>
              <td><span :class="['source-pill', { owned: citationType(row) === 'Owned' }]">{{ citationType(row) }}</span></td>
              <td><span class="analysis-pill">未分析</span></td>
              <td><span class="unavailable-value">未分析</span></td>
              <td><span class="truncate-cell" title="尚無資料">尚無資料</span></td>
            </tr>
            <tr v-if="!citationRows.length"><td colspan="10" class="empty-cell">查無符合的資料</td></tr>
          </tbody>
        </table></div>
        <footer v-if="citationRows.length" class="pagination citation-pagination">
          <span>共 {{ citationRows.length }} 筆</span>
          <div><button type="button" :disabled="citationPage <= 1" title="上一頁" @click="citationPage--"><AppIcon name="chevron-left" :size="15" /></button><span>第 {{ citationPage }} / {{ citationPageCount }} 頁</span><button type="button" :disabled="citationPage >= citationPageCount" title="下一頁" @click="citationPage++"><AppIcon name="chevron-right" :size="15" /></button></div>
        </footer>
      </section>
    </template>

    <div v-if="selectedResponse" class="modal-backdrop" @click.self="closeModal">
      <section class="response-modal" role="dialog" aria-modal="true">
        <header><div><span>Query 回答</span><h2>{{ selectedResponse.queryText }}</h2></div><button class="icon-button" type="button" title="關閉" @click="closeModal"><AppIcon name="x" /></button></header>
        <div v-if="modalLoading" class="overview-empty"><strong>正在載入完整回答</strong></div>
        <div v-else class="modal-content">
          <div v-if="modalError" class="overview-error">{{ modalError }}</div>
          <dl><div><dt>平台</dt><dd>{{ providerLabel(selectedResponse.provider) }}</dd></div><div><dt>地區</dt><dd>{{ selectedResponse.region }}</dd></div><div><dt>時間</dt><dd>{{ formatDateTime(selectedResponse.completedAt) }}</dd></div><div><dt>品牌提及</dt><dd>{{ mentionLabel(selectedResponse.mentioned) }}</dd></div></dl>
          <article><h3>AI 回答</h3><div class="raw-response" v-html="renderSafeMarkdown(selectedResult?.rawResponse ?? selectedResponse.responseExcerpt)"></div></article>
          <article><h3>品牌與競品</h3><div class="fact-list"><span v-for="mention in selectedAnalysis?.entityMentions ?? []" :key="mention.entityId">{{ mention.entityName }}：{{ mention.mentioned ? `第 ${mention.firstMentionOrder ?? '-'} 順位` : '未提及' }}</span><span v-if="!selectedAnalysis?.entityMentions.length">尚無 semantic analysis</span></div></article>
          <article><h3>Citations</h3><ul><li v-for="reference in selectedResult?.references ?? []" :key="`${reference.url}-${reference.position}`"><a :href="reference.url" target="_blank" rel="noreferrer">{{ reference.title ?? reference.url }}</a></li></ul><p v-if="!selectedResult?.references.length">沒有 citations</p></article>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.geo-overview-page{min-height:100%;background:#f7f8fa;padding:24px 32px;color:#1f1f1f}.overview-heading{max-width:1200px;margin:0 auto 16px}.overview-heading h1{margin:0;font-size:20px;line-height:28px}.overview-heading p,.overview-card header p{margin:4px 0 0;color:#8c8c8c;font-size:13px}.overview-toolbar{max-width:1200px;margin:0 auto 20px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap}.filter-control{display:flex;flex-direction:column;gap:5px}.filter-control>span{font-size:11px;color:#8c8c8c}.filter-control select,.responses-header select{height:34px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;padding:0 30px 0 10px;color:#434343}.project-filter select{min-width:190px}.custom-range{display:flex;align-items:center;gap:6px;height:34px}.custom-range input{height:34px;border:1px solid #d9d9d9;border-radius:6px;padding:0 8px}.filter-menu{position:relative}.filter-menu summary{height:34px;display:flex;align-items:center;gap:6px;padding:0 10px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;font-size:13px;cursor:pointer;list-style:none}.filter-menu summary span{min-width:18px;height:18px;border-radius:9px;background:#e6f4ff;color:#0958d9;text-align:center;font-size:11px;line-height:18px}.filter-menu-panel{position:absolute;z-index:20;top:39px;left:0;min-width:210px;max-height:280px;overflow:auto;padding:10px;background:#fff;border:1px solid #e7eaec;border-radius:6px;box-shadow:0 8px 24px rgba(0,0,0,.12)}.filter-menu-panel label{display:flex;gap:8px;align-items:center;padding:7px 4px;font-size:13px}.filter-menu-panel strong{display:block;padding:8px 4px 3px;font-size:11px;color:#8c8c8c}.filter-menu-panel p{padding:6px;margin:0;color:#8c8c8c;font-size:12px}.toolbar-actions{display:flex;gap:8px;margin-left:auto}.secondary-button{height:34px;display:inline-flex;align-items:center;gap:6px;border:1px solid #d9d9d9;border-radius:6px;background:#fff;padding:0 12px;color:#595959;cursor:pointer}.secondary-button:disabled{opacity:.45;cursor:not-allowed}.icon-button{width:34px;height:34px;display:inline-grid;place-items:center;border:1px solid #d9d9d9;border-radius:6px;background:#fff;cursor:pointer}.overview-error,.overview-empty{max-width:1200px;margin:0 auto 16px;padding:14px 16px;border-radius:6px;display:flex;gap:8px;align-items:center}.overview-error{background:#fff2f0;color:#a8071a;border:1px solid #ffccc7}.overview-empty{min-height:160px;justify-content:center;flex-direction:column;background:#fff;border:1px dashed #d9d9d9}.kpi-grid,.overview-card{max-width:1200px;margin-left:auto;margin-right:auto}.kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-bottom:16px}.overview-card{box-sizing:border-box;background:#fff;border:1px solid #e7eaec;border-radius:8px;margin-bottom:16px}.kpi-card{padding:18px 20px}.kpi-label{display:flex;align-items:center;gap:10px;color:#8c8c8c;font-size:13px;margin-bottom:14px}.kpi-icon{width:36px;height:36px;border-radius:8px;display:grid;place-items:center}.kpi-icon.blue,.kpi-icon.cyan{background:#e6f4ff;color:#1677ff}.kpi-icon.green{background:#f6ffed;color:#389e0d}.kpi-icon.gold{background:#fffbe6;color:#d68c24}.kpi-card>strong{font-size:28px}.kpi-card>strong small{font-size:15px;color:#bfbfbf;font-weight:400}.kpi-card p{font-size:12px;color:#8c8c8c;margin:10px 0 0}.kpi-card p b{color:#434343}.citation-summary{display:grid;grid-template-columns:repeat(4,1fr);padding:16px 20px}.citation-summary div{display:flex;flex-direction:column;gap:5px;padding:0 20px;border-right:1px solid #f0f0f0}.citation-summary div:first-child{padding-left:0}.citation-summary div:last-child{border:0}.citation-summary span{font-size:12px;color:#8c8c8c}.citation-summary strong{font-size:20px}.chart-card,.table-card{padding:20px 24px}.overview-card header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px}.overview-card h2{font-size:16px;margin:0}.chart-frame{height:300px}.sentiment-totals{display:flex;gap:28px;margin-bottom:14px;font-size:13px;color:#8c8c8c}.sentiment-totals b{display:block;margin-top:3px;font-size:21px;color:#262626}.inline-empty,.empty-cell{text-align:center;color:#8c8c8c;padding:28px}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;min-width:720px}th{padding:10px 8px;text-align:left;color:#8c8c8c;font-size:12px;font-weight:500;background:#fafafa;border-bottom:1px solid #f0f0f0}td{padding:12px 8px;border-bottom:1px solid #f5f5f5;font-size:13px}td strong,td small{display:block}td small{color:#8c8c8c;margin-top:3px}.entity-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:7px;background:#7c3aed}.entity-dot.own_brand{background:#1677ff}.positive-text{color:#389e0d}.negative-text{color:#cf1322}.topic-row,.clickable-row{cursor:pointer}.topic-row:hover,.clickable-row:hover{background:#f5faff}.topic-row td:first-child{display:flex;align-items:center;gap:7px}.query-child-row td:first-child{padding-left:44px;color:#595959}.responses-header select{max-width:300px}.table-tabs{display:flex;gap:20px;border-bottom:1px solid #f0f0f0;margin-bottom:8px}.table-tabs button{border:0;background:transparent;padding:8px 2px;color:#8c8c8c;cursor:pointer;border-bottom:2px solid transparent}.table-tabs button.active{color:#1677ff;border-color:#1677ff}.clickable-row td:first-child{max-width:540px}.clickable-row td p{margin:4px 0 0;color:#8c8c8c;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.status-pill,.source-pill{display:inline-block;border-radius:999px;padding:3px 8px;font-size:11px}.status-positive{background:#f6ffed;color:#237804}.status-muted{background:#f5f5f5;color:#595959}.status-warning{background:#fffbe6;color:#ad6800}.source-pill{background:#e6f4ff;color:#0958d9}.pagination{display:flex;align-items:center;justify-content:space-between;padding-top:14px;color:#8c8c8c;font-size:12px}.pagination div{display:flex;align-items:center;gap:8px}.pagination button{width:30px;height:30px;border:1px solid #d9d9d9;border-radius:6px;background:#fff}.citation-search{display:flex;align-items:center;gap:6px;border:1px solid #d9d9d9;border-radius:6px;padding:0 8px}.citation-search input{height:32px;border:0;outline:0}.citation-table{min-width:1120px}.modal-backdrop{position:fixed;z-index:100;inset:0;background:rgba(0,0,0,.45);display:grid;place-items:center;padding:24px}.response-modal{width:min(920px,100%);max-height:90vh;overflow:hidden;background:#fff;border-radius:8px;box-shadow:0 16px 48px rgba(0,0,0,.2)}.response-modal>header{display:flex;justify-content:space-between;gap:20px;padding:18px 22px;border-bottom:1px solid #f0f0f0}.response-modal header span{font-size:12px;color:#8c8c8c}.response-modal h2{font-size:17px;margin:4px 0 0}.modal-content{padding:20px 22px;max-height:calc(90vh - 78px);overflow:auto}.modal-content dl{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:0 0 20px}.modal-content dl div{background:#fafafa;padding:10px;border-radius:6px}.modal-content dt{font-size:11px;color:#8c8c8c}.modal-content dd{margin:4px 0 0;font-size:13px}.modal-content article{margin-top:22px}.modal-content h3{font-size:14px}.raw-response{line-height:1.75;color:#434343}.fact-list{display:flex;flex-wrap:wrap;gap:8px}.fact-list span{padding:5px 9px;background:#f5f5f5;border-radius:6px;font-size:12px}.modal-content a{color:#1677ff;word-break:break-all}@media(max-width:1023px){.geo-overview-page{padding:20px}.kpi-grid{grid-template-columns:repeat(2,1fr)}.toolbar-actions{margin-left:0}.citation-summary{grid-template-columns:repeat(2,1fr);row-gap:18px}.citation-summary div:nth-child(2){border:0}.modal-content dl{grid-template-columns:repeat(2,1fr)}}@media(max-width:639px){.geo-overview-page{padding:16px}.kpi-grid{grid-template-columns:1fr}.overview-toolbar>*{width:100%}.filter-control select,.filter-menu summary{width:100%}.toolbar-actions{display:grid;grid-template-columns:1fr 1fr}.citation-summary{grid-template-columns:1fr}.citation-summary div{padding:0 0 12px;border-right:0;border-bottom:1px solid #f0f0f0}.chart-card,.table-card{padding:16px}.chart-frame{height:250px}.overview-card header,.responses-header{align-items:flex-start;flex-direction:column}.responses-header select,.citation-search{width:100%;max-width:none}.modal-content dl{grid-template-columns:1fr}}
.geo-overview-page{background:#f7f8fa}.overview-toolbar{align-items:center;justify-content:space-between}.filter-group{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.filter-select{height:36px;min-width:120px;position:relative;display:flex;align-items:center;border:1px solid #d9d9d9;border-radius:8px;background:#fff;color:#1f1f1f;overflow:hidden}.filter-select:focus-within{border-color:#0a2b41;box-shadow:0 0 0 3px rgba(10,43,65,.08)}.filter-select select{width:100%;height:100%;appearance:none;border:0;outline:0;background:transparent;padding:0 32px 0 12px;color:#1f1f1f;font-size:13px;cursor:pointer}.filter-select>.app-icon{position:absolute;right:10px;pointer-events:none;color:#8c8c8c;transform:rotate(90deg)}.project-filter{min-width:210px;max-width:260px}.custom-range{height:36px}.custom-range input{height:36px;border-radius:8px}.filter-menu summary{height:36px;min-width:100px;padding:0 10px 0 12px;border-radius:8px}.filter-menu summary>.app-icon{margin-left:auto;color:#8c8c8c;transform:rotate(90deg)}.filter-menu[open] summary{border-color:#0a2b41;box-shadow:0 0 0 3px rgba(10,43,65,.08)}.filter-menu[open] summary>.app-icon{transform:rotate(270deg)}.filter-menu summary span{background:#0a2b41;color:#fff}.filter-menu-panel{top:40px;z-index:120;border-color:#d9d9d9;border-radius:10px;padding:4px;box-shadow:0 4px 16px rgba(0,0,0,.08)}.filter-menu-panel label{padding:8px 10px;border-radius:6px}.filter-menu-panel label:has(input:checked){background:#e6f4ff}.filter-menu-panel input{accent-color:#0a2b41}.secondary-button{height:36px;border-radius:8px;font-weight:500}.overview-card{border-radius:12px}.kpi-icon{border-radius:9px}.citation-summary{padding:20px 24px}.citation-summary div{text-align:center;align-items:center}.citation-summary span{font-size:13px}.citation-summary strong{font-size:24px;font-weight:700}.overview-card header{align-items:flex-start;margin-bottom:18px}.chart-legend-chips{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}.chart-legend-chips button{height:30px;display:flex;align-items:center;gap:6px;border:1px solid #e7eaec;border-radius:6px;background:#fff;padding:0 10px;color:#595959;font-size:12px;cursor:pointer}.chart-legend-chips button span{width:8px;height:8px;border-radius:50%}.chart-legend-chips button b{color:#1f1f1f}.chart-legend-chips button.muted{opacity:.45;background:#fafafa}.chart-frame{height:240px}.segmented-control{display:flex;gap:2px;padding:2px;border-radius:8px;background:#f5f5f5}.segmented-control button{height:30px;border:0;border-radius:6px;background:transparent;padding:0 14px;color:#8c8c8c;font-size:13px;cursor:pointer}.segmented-control button.active{background:#fff;color:#0a2b41;font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,.06)}.sentiment-totals{align-items:center;gap:32px;margin:0 0 20px}.sentiment-totals>span{min-width:80px}.sentiment-totals>i{width:1px;height:40px;background:#f0f0f0}.sentiment-totals b{font-size:24px;font-weight:600}.sentiment-legend{display:flex;gap:18px;margin-bottom:10px;color:#8c8c8c;font-size:12px}.sentiment-legend span{display:flex;align-items:center;gap:6px}.sentiment-legend i{width:10px;height:10px;border-radius:3px}.sentiment-legend .positive{background:#69b1ff}.sentiment-legend .negative{background:#fdb338}.chart-note{margin:12px 0 0;color:#bfbfbf;font-size:12px}.table-card table{table-layout:fixed}.table-card th:not(:first-child),.table-card td:not(:first-child){text-align:right}.table-card th{background:transparent}.brand-cell{display:flex;align-items:center;gap:8px}.brand-avatar{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;color:#fff;font-size:11px;font-weight:600;flex:0 0 auto}.self-badge{display:inline-block!important;margin:0!important;padding:1px 6px;border:1px solid #91caff;border-radius:4px;background:#e6f4ff;color:#0958d9!important;font-size:11px}.topic-table th:nth-child(2),.topic-table td:nth-child(2){width:110px}.topic-table th:nth-child(3),.topic-table td:nth-child(3){width:120px}.topic-table th:nth-child(4),.topic-table td:nth-child(4){width:100px}.topic-row.expanded,.topic-row:has(.topic-chevron-expanded){background:#fafafa}.response-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:16px}.response-controls>select{width:min(320px,100%);height:36px;border:1px solid #d9d9d9;border-radius:8px;background:#fff;padding:0 32px 0 12px;color:#1f1f1f}.response-table th:nth-child(1){width:auto}.response-table th:nth-child(2){width:90px}.response-table th:nth-child(3){width:150px}.response-table th:nth-child(4){width:70px}.response-table th:nth-child(5){width:110px}.response-table th:nth-child(2),.response-table td:nth-child(2){text-align:center}.response-table th:nth-child(n+3),.response-table td:nth-child(n+3){text-align:left}.clickable-row td:first-child span{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#595959}.mention-icon{display:inline-flex;align-items:center;justify-content:center;background:transparent}.mention-icon.status-positive{color:#389e0d}.mention-icon.status-muted{color:#cf1322}.mention-icon.status-warning{color:#ad6800}.platform-pill{display:inline-block;padding:2px 8px;border:1px solid #91caff;border-radius:999px;background:#e6f4ff;color:#0958d9;font-size:11px;white-space:nowrap}.citation-card .table-tabs{gap:2px;width:max-content;padding:2px;border:0;border-radius:8px;background:#f5f5f5}.citation-card .table-tabs button{height:30px;padding:0 14px;border:0;border-radius:6px}.citation-card .table-tabs button.active{background:#fff;color:#0a2b41;box-shadow:0 1px 2px rgba(0,0,0,.06)}.response-modal{border-radius:12px}.topic-row :deep(.app-icon){transition:transform .18s ease}.topic-row :deep(.topic-chevron-expanded){transform:rotate(90deg)}
.kpi-grid{align-items:stretch}.kpi-card{box-sizing:border-box;min-width:0;margin:0;padding:18px 20px;border:1px solid #e7eaec;border-radius:12px;background:#fff}.kpi-title{display:flex;align-items:center;gap:10px;margin-bottom:14px;color:#8c8c8c;font-size:13px}.kpi-icon{width:36px;height:36px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;border-radius:9px}.kpi-value{margin-bottom:10px;color:#1f1f1f;font-size:28px;font-weight:600;line-height:1.1}.kpi-value small{color:#bfbfbf;font-size:15px;font-weight:400}.kpi-sub{color:#8c8c8c;font-size:12px}.kpi-sub strong{color:#434343;font-weight:600}.metric-group{box-sizing:border-box;max-width:1200px;margin:0 auto 16px;padding:20px 24px;border:1px solid #e7eaec;border-radius:12px;background:#fff;display:flex;justify-content:space-around;flex-wrap:wrap;gap:16px}.metric-group>div{min-width:110px;text-align:center}.metric-group span{display:block;margin-bottom:8px;color:#8c8c8c;font-size:13px}.metric-group strong{display:block;color:#1f1f1f;font-size:24px;font-weight:700}.response-table{min-width:760px}.response-table td:first-child{min-width:0;color:#595959}.response-table td:first-child span{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.citation-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;flex-wrap:wrap}.citation-search{box-sizing:border-box;height:36px;min-width:200px;padding:0 12px;border-radius:8px;color:#bfbfbf}.citation-search input{min-width:0;flex:1;height:auto;font-size:13px}.citation-table{min-width:1020px;table-layout:fixed}.citation-table th:nth-child(1),.citation-table td:nth-child(1){text-align:left}.citation-table th:nth-child(3),.citation-table td:nth-child(3),.citation-table th:nth-child(4),.citation-table td:nth-child(4),.citation-table th:nth-child(5),.citation-table td:nth-child(5),.citation-table th:nth-child(6),.citation-table td:nth-child(6){text-align:right}.citation-table th:nth-child(7),.citation-table td:nth-child(7),.citation-table th:nth-child(8),.citation-table td:nth-child(8),.citation-table th:nth-child(10),.citation-table td:nth-child(10){text-align:left}.citation-table th:nth-child(9),.citation-table td:nth-child(9){text-align:center}.citation-page-cell{display:flex;align-items:center;gap:8px;min-width:0}.citation-globe{width:24px;height:24px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;border-radius:6px;background:#f5f5f5;color:#8c8c8c}.citation-page-copy{min-width:0;flex:1}.citation-page-copy strong,.citation-page-copy small{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.citation-page-copy strong{color:#1f1f1f;font-weight:400}.citation-page-copy small{margin-top:2px;color:#8c8c8c;font-size:11px}.citation-row-actions{display:flex;gap:2px;flex:0 0 auto}.citation-row-actions button,.citation-row-actions a{width:24px;height:24px;display:flex;align-items:center;justify-content:center;border:0;border-radius:6px;background:transparent;color:#bfbfbf;cursor:pointer}.citation-row-actions button:hover,.citation-row-actions a:hover{background:#f5f5f5;color:#595959}.source-pill,.analysis-pill{display:inline-block;padding:2px 8px;border:1px solid #e7eaec;border-radius:999px;background:#f5f5f5;color:#595959;font-size:11px;white-space:nowrap}.source-pill.owned{border-color:#91caff;background:#e6f4ff;color:#0958d9}.unavailable-value{color:#8c8c8c;font-size:12px}.truncate-cell{display:block;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:#8c8c8c}
.response-query-select{position:relative;width:min(320px,100%)}.response-query-select summary{box-sizing:border-box;width:100%;height:36px;display:flex;align-items:center;gap:8px;padding:0 10px 0 12px;border:1px solid #d9d9d9;border-radius:8px;background:#fff;color:#1f1f1f;font-size:13px;cursor:pointer;list-style:none}.response-query-select summary::-webkit-details-marker{display:none}.response-query-select summary>span{min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.response-query-select summary>.app-icon{flex:0 0 auto;color:#8c8c8c;transform:rotate(90deg);transition:transform .15s}.response-query-select[open] summary{border-color:#0a2b41;box-shadow:0 0 0 3px rgba(10,43,65,.08)}.response-query-select[open] summary>.app-icon{transform:rotate(270deg)}.response-query-options{position:absolute;z-index:120;top:40px;left:0;box-sizing:border-box;width:100%;max-height:280px;overflow:auto;padding:4px;border:1px solid #d9d9d9;border-radius:10px;background:#fff;box-shadow:0 4px 16px rgba(0,0,0,.08)}.response-query-options button{width:100%;min-width:0;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 10px;border:0;border-radius:6px;background:transparent;color:#1f1f1f;font-size:13px;text-align:left;cursor:pointer}.response-query-options button:hover{background:#fafafa}.response-query-options button.active{background:#e7eaec;color:#0a2b41;font-weight:500}.response-query-options button span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.citation-view-switch{display:flex;gap:2px;padding:2px;border-radius:8px;background:#f5f5f5;flex:0 0 auto}.citation-view-switch button{height:30px;padding:0 16px;border:0;border-radius:6px;background:transparent;color:#8c8c8c;font-size:13px;cursor:pointer;white-space:nowrap}.citation-view-switch button.active{background:#fff;color:#0a2b41;font-weight:500;box-shadow:0 1px 2px rgba(0,0,0,.06)}.citation-pagination{border-top:1px solid #f0f0f0;margin-top:8px}.pagination button:disabled{opacity:.4;cursor:not-allowed}
.filter-menu-panel label{position:relative;cursor:pointer}.filter-menu-panel label>input{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}.filter-checkbox{width:16px;height:16px;display:flex;align-items:center;justify-content:center;flex:0 0 auto;box-sizing:border-box;border:1.5px solid #d9d9d9;border-radius:4px;background:transparent;color:#fff}.filter-menu-panel label:has(input:checked) .filter-checkbox{border-color:#0a2b41;background:#0a2b41}.filter-menu-panel label>span:last-child{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.citation-table th:nth-child(2),.citation-table td:nth-child(2){text-align:left}.citation-search{width:220px;min-width:200px;display:flex;align-items:center;gap:8px;overflow:hidden}.citation-search input{width:100%;padding:0;color:#1f1f1f;background:transparent}.citation-search input::placeholder{color:#bfbfbf}
.filter-menu-panel{min-width:170px}.metadata-menu .filter-menu-panel{min-width:190px}.visibility-chart-frame{height:250px}
.single-filter summary{box-sizing:border-box}.single-filter .filter-menu-value{min-width:0;height:auto;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border-radius:0;background:transparent;color:#1f1f1f;font-size:13px;line-height:normal;text-align:left}.project-filter{width:220px;min-width:220px;max-width:260px}.time-filter{width:130px}.region-filter{width:120px}.single-filter .filter-menu-panel{min-width:100%;box-sizing:border-box}.single-filter-options button{width:100%;min-width:0;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:8px 10px;border:0;border-radius:6px;background:transparent;color:#1f1f1f;font-size:13px;text-align:left;cursor:pointer}.single-filter-options button:hover{background:#fafafa}.single-filter-options button.active{background:#e7eaec;color:#0a2b41;font-weight:500}.single-filter-options button span{min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.single-filter-options button .app-icon{flex:0 0 auto}
.time-filter-wrap{position:relative}
/* 新版 Overview KPI：四張主指標加一張引用表現卡。 */
.kpi-grid{grid-template-columns:repeat(5,minmax(0,1fr))}.kpi-card{display:flex;flex-direction:column}.kpi-title{align-items:flex-start;justify-content:space-between;gap:8px}.kpi-title>span:first-child{padding-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.kpi-icon{border-radius:10px;color:#fff}.kpi-icon.blue{background:#1677ff;color:#fff}.kpi-icon.green{background:#0f8f83;color:#fff}.kpi-icon.purple{background:#7c3aed;color:#fff}.kpi-icon.gold{background:#d68c24;color:#fff}.kpi-value{margin-top:auto;margin-bottom:2px;line-height:34px}.kpi-sub{font-size:13px;line-height:20px}.citation-kpi-card{justify-content:space-evenly}.citation-kpi-card>div{display:flex;flex-direction:column;gap:4px}.citation-kpi-card span{overflow:hidden;color:#8c8c8c;font-size:13px;text-overflow:ellipsis;white-space:nowrap}.citation-kpi-card strong{color:#1f1f1f;font-size:24px;line-height:30px}.citation-kpi-card>i{height:1px;margin:4px 0;background:#f0f0f0}
@media(max-width:1023px){.overview-toolbar{align-items:flex-start}.toolbar-actions{margin-left:0}.chart-frame{height:260px}.visibility-chart-frame{height:250px}.kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:639px){.filter-group,.filter-select,.filter-menu,.filter-menu summary,.time-filter-wrap{width:100%}.project-filter{max-width:none}.toolbar-actions{width:100%}.sentiment-totals{gap:16px}.sentiment-totals>i{display:none}.segmented-control{width:100%}.segmented-control button{flex:1}.response-controls>select{width:100%}.kpi-grid{grid-template-columns:1fr}}
.geo-overview-page{padding:0!important;background:transparent}
.metadata-menu summary{min-width:120px}
@media(max-width:1023px){.geo-overview-page{padding:0!important}}
@media(max-width:639px){.geo-overview-page{padding:0!important}}
.overview-heading h1{font-weight:600}
.overview-heading p,.overview-card header p,.kpi-title,.citation-kpi-card span{line-height:20px}
.overview-card h2{font-weight:600}
.secondary-button{font-size:14px}
</style>
