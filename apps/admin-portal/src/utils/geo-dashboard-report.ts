import type {
  GeoDashboardMetricValue,
  GeoDashboardReportQuery,
  GeoDashboardReport,
  GeoDashboardOverviewCard,
  SemanticTone,
} from "../types";

type DashboardMetricName = GeoDashboardOverviewCard["metricName"];

const metricLabels: Record<DashboardMetricName, string> = {
  visibility: "能見度",
  mentions: "提及次數",
  sov: "聲量佔比",
  average_position: "平均排名",
};

const metricTooltips: Record<DashboardMetricName, string> = {
  visibility:
    "品牌在已完成回答中被提及的比例。計算方式：被提及的回答數 ÷ 已完成回答總數 × 100%。",
  mentions:
    "品牌或競品在回答中被判定為有提及的次數。計算方式：符合 entity mention fact 的筆數加總。",
  sov: "Share of Voice，品牌在所有實體提及中的佔比。計算方式：該實體提及次數 ÷ 全部實體提及次數 × 100%。",
  average_position:
    "品牌第一次出現在回答中的平均順位。計算方式：firstMentionOrder 加總 ÷ 有提及的回答數；數字越小代表越早被提到。",
};

const enumLabels: Record<string, string> = {
  own_brand: "自有品牌",
  competitor: "競品",
  owned: "自有資產",
  other: "外部來源",
  owned_site: "自有網站",
  unknown: "未知來源",
  positive: "正向",
  negative: "負向",
};

export const geoDashboardReportTooltips = {
  project: "選擇要查看 GEO 報表的專案。Live API 模式會用此專案 ID 查詢後端資料。",
  dataSource:
    "Mock Data 會顯示完整示意資料；Live API 會呼叫實際 dashboard report API，無資料時顯示空狀態。",
  periodStart: "報表統計區間的開始時間，只納入此時間之後完成的 run result。",
  periodEnd: "報表統計區間的結束時間，只納入此時間之前完成的 run result。",
  comparisonStart:
    "比較區間的開始時間，用來計算右上角的變化量與正負向提示。",
  comparisonEnd: "比較區間的結束時間，需與比較開始時間一起送出。",
  provider: "可選的 AI provider 篩選，例如 gemini；留空代表不限制 provider。",
  region: "可選的地區篩選，例如 TW；留空代表不限制地區。",
  language: "可選的語言篩選，例如 zh-TW；留空代表不限制語言。",
  citationCount:
    "引用次數。計算方式：報表區間內引用此 URL 或網域的 citation fact 筆數加總。",
  usedPercent:
    "使用率。計算方式：有使用此 URL 或網域的回答數 ÷ 已完成回答總數 × 100%。",
  sharePercent:
    "引用佔比。計算方式：此 URL 或網域的引用次數 ÷ 全部引用次數 × 100%。",
  sentiment:
    "情緒句數。計算方式：semantic analysis 產生的 positive 或 negative sentiment fact 筆數加總。",
} as const;

export interface GeoDashboardReportFilterInput {
  periodStart: string;
  periodEnd: string;
  comparisonStart: string;
  comparisonEnd: string;
  provider?: string;
  region?: string;
  language?: string;
}

export function buildDefaultGeoDashboardReportFilters(
  now = new Date(),
): GeoDashboardReportFilterInput {
  const year = now.getFullYear();
  const month = now.getMonth();
  return {
    periodStart: toDateTimeLocalMinute(new Date(year, month, 1, 0, 0)),
    periodEnd: toDateTimeLocalMinute(new Date(year, month + 1, 0, 23, 59)),
    comparisonStart: toDateTimeLocalMinute(new Date(year, month - 1, 1, 0, 0)),
    comparisonEnd: toDateTimeLocalMinute(new Date(year, month, 0, 23, 59)),
    provider: "",
    region: "",
    language: "",
  };
}

export function isGeoDashboardReportEmpty(
  report: GeoDashboardReport | null,
): boolean {
  if (!report) return true;
  return (
    report.overview.length === 0 &&
    report.entities.length === 0 &&
    report.citationUrls.length === 0 &&
    report.citationDomains.length === 0 &&
    report.sentiments.length === 0
  );
}

export function formatGeoDashboardMetric(
  metric: GeoDashboardMetricValue,
): string {
  const value =
    Number.isInteger(metric.value) || metric.unit === "count"
      ? metric.value.toLocaleString()
      : metric.value.toFixed(1);
  if (metric.unit === "percent") return `${value}%`;
  if (metric.unit === "position") return `#${value}`;
  return value;
}

export function formatGeoDashboardDelta(
  metric: GeoDashboardMetricValue,
): string {
  if (metric.delta === null || metric.deltaUnit === null) return "無比較資料";
  const sign = metric.delta > 0 ? "+" : "";
  const value = Number.isInteger(metric.delta)
    ? metric.delta.toLocaleString()
    : metric.delta.toFixed(1);
  if (metric.deltaUnit === "pp") return `${sign}${value} 百分點`;
  if (metric.deltaUnit === "position") return `${sign}${value} 名`;
  return `${sign}${value}`;
}

export function geoDashboardMetricLabel(metricName: string): string {
  return metricLabels[metricName as DashboardMetricName] ?? metricName;
}

export function geoDashboardMetricTooltip(metricName: string): string {
  return (
    metricTooltips[metricName as DashboardMetricName] ??
    "此指標由 dashboard report API 回傳。"
  );
}

export function geoDashboardEnumLabel(value: string | null | undefined): string {
  if (!value) return "-";
  return enumLabels[value] ?? value;
}

export function geoDashboardDeltaTone(
  metric: GeoDashboardMetricValue,
): SemanticTone {
  return geoDashboardDirectionalDeltaTone(metric);
}

export function geoDashboardSentimentDeltaTone(
  sentiment: "positive" | "negative",
  metric: GeoDashboardMetricValue,
): SemanticTone {
  return geoDashboardDirectionalDeltaTone(metric, {
    lowerIsBetter: sentiment === "negative",
  });
}

export function toGeoDashboardApiDateTime(value: string): string {
  if (!value) return "";
  return value.endsWith("Z") ? value : `${value}:00Z`;
}

export function buildGeoDashboardReportQuery(
  input: GeoDashboardReportFilterInput,
): GeoDashboardReportQuery | null {
  const periodStart = toGeoDashboardApiDateTime(input.periodStart);
  const periodEnd = toGeoDashboardApiDateTime(input.periodEnd);
  const comparisonStart = toGeoDashboardApiDateTime(input.comparisonStart);
  const comparisonEnd = toGeoDashboardApiDateTime(input.comparisonEnd);
  if (!periodStart || !periodEnd || !comparisonStart || !comparisonEnd) {
    return null;
  }
  return {
    periodStart,
    periodEnd,
    comparisonStart,
    comparisonEnd,
    provider: input.provider || undefined,
    region: input.region || undefined,
    language: input.language || undefined,
  };
}

function geoDashboardDirectionalDeltaTone(
  metric: GeoDashboardMetricValue,
  options: { lowerIsBetter?: boolean } = {},
): SemanticTone {
  if (metric.delta === null || metric.delta === 0) return "muted";
  const lowerIsBetter = options.lowerIsBetter ?? metric.unit === "position";
  if (metric.delta > 0) return lowerIsBetter ? "error" : "success";
  if (metric.delta < 0) return lowerIsBetter ? "success" : "error";
  return "muted";
}

function toDateTimeLocalMinute(value: Date): string {
  const pad = (part: number) => part.toString().padStart(2, "0");
  return [
    value.getFullYear(),
    "-",
    pad(value.getMonth() + 1),
    "-",
    pad(value.getDate()),
    "T",
    pad(value.getHours()),
    ":",
    pad(value.getMinutes()),
  ].join("");
}
