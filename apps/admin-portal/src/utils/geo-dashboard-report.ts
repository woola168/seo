import type {
  GeoDashboardMetricValue,
  GeoDashboardReportQuery,
  GeoDashboardReport,
  SemanticTone,
} from "../types";

export interface GeoDashboardReportFilterInput {
  periodStart: string;
  periodEnd: string;
  comparisonStart: string;
  comparisonEnd: string;
  provider?: string;
  region?: string;
  language?: string;
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
  if (metric.delta === null || metric.deltaUnit === null) return "No comparison";
  const sign = metric.delta > 0 ? "+" : "";
  const value = Number.isInteger(metric.delta)
    ? metric.delta.toLocaleString()
    : metric.delta.toFixed(1);
  if (metric.deltaUnit === "pp") return `${sign}${value} pp`;
  if (metric.deltaUnit === "position") return `${sign}${value} positions`;
  return `${sign}${value}`;
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
