import DOMPurify from "dompurify";
import { marked } from "marked";

import type {
  GeoAnalysisRunResult,
  GeoQueryResource,
  GeoRunResultSentimentFact,
} from "../types";

export interface GeoReportRunResultRow {
  result: GeoAnalysisRunResult;
  queryText: string;
  provider: string;
  topicId: string | null;
}

export interface GeoRunResultDrilldownFilters {
  periodStart: string;
  periodEnd: string;
  queryId?: string;
  topicId?: string;
  provider?: string;
  region?: string;
  language?: string;
}

export interface PaginationState {
  page: number;
  pageSize: number;
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  totalPages: number;
  page: number;
}

export interface EvidenceHighlight {
  text: string;
  sentiment: "positive" | "negative";
  found: boolean;
}

export function buildRunResultRows(
  results: GeoAnalysisRunResult[],
  queries: GeoQueryResource[],
): GeoReportRunResultRow[] {
  const queryById = new Map(queries.map((query) => [query.id, query]));
  return results.map((result) => {
    const query = queryById.get(result.queryId);
    return {
      result,
      queryText: query?.queryText ?? result.queryId,
      provider: result.provider,
      topicId: query?.topicId ?? null,
    };
  });
}

export function filterRunResultRows(
  rows: GeoReportRunResultRow[],
  filters: GeoRunResultDrilldownFilters,
): GeoReportRunResultRow[] {
  const periodStart = Date.parse(filters.periodStart);
  const periodEnd = Date.parse(filters.periodEnd);
  return rows.filter((row) => {
    const runAt = Date.parse(row.result.runAt);
    if (!Number.isNaN(periodStart) && runAt < periodStart) return false;
    if (!Number.isNaN(periodEnd) && runAt > periodEnd) return false;
    if (filters.queryId && row.result.queryId !== filters.queryId) return false;
    if (filters.topicId && row.topicId !== filters.topicId) return false;
    if (filters.provider && row.result.provider !== filters.provider) return false;
    if (filters.region && row.result.region !== filters.region) return false;
    if (filters.language && row.result.language !== filters.language) return false;
    return true;
  });
}

export function paginateItems<T>(
  items: T[],
  pagination: PaginationState,
): PaginatedResult<T> {
  const totalPages = Math.max(1, Math.ceil(items.length / pagination.pageSize));
  const page = Math.min(Math.max(1, pagination.page), totalPages);
  const start = (page - 1) * pagination.pageSize;
  return {
    items: items.slice(start, start + pagination.pageSize),
    total: items.length,
    totalPages,
    page,
  };
}

export function renderSafeMarkdown(raw: string): string {
  const html = marked.parse(raw || "", {
    async: false,
    breaks: true,
    gfm: true,
  }) as string;
  return sanitizeHtml(html);
}

export function buildEvidenceHighlights(
  rawResponse: string,
  sentiments: GeoRunResultSentimentFact[],
): EvidenceHighlight[] {
  return sentiments
    .filter((sentiment) => Boolean(sentiment.evidenceText?.trim()))
    .map((sentiment) => {
      const text = sentiment.evidenceText?.trim() ?? "";
      return {
        text,
        sentiment: sentiment.sentiment,
        found: rawResponse.includes(text),
      };
    });
}

export function highlightEvidenceInHtml(
  sanitizedHtml: string,
  highlights: EvidenceHighlight[],
): string {
  const replacements = highlights
    .filter((highlight) => highlight.found)
    .map((highlight) => ({
      escapedText: escapeHtml(highlight.text),
      sentiment: highlight.sentiment,
    }))
    .filter((highlight) => highlight.escapedText.length > 0);
  if (replacements.length === 0) return sanitizedHtml;
  return sanitizedHtml
    .split(/(<[^>]+>)/g)
    .map((segment) => {
      if (segment.startsWith("<") && segment.endsWith(">")) return segment;
      return replacements.reduce((text, highlight) => {
        return text.replace(
          new RegExp(escapeRegExp(highlight.escapedText), "g"),
          `<mark class="sentiment-highlight sentiment-highlight-${highlight.sentiment}">${highlight.escapedText}</mark>`,
        );
      }, segment);
    })
    .join("");
}

function sanitizeHtml(html: string): string {
  if (typeof window === "undefined" || !DOMPurify.isSupported) {
    return fallbackSanitizeHtml(html);
  }
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [
      "a",
      "blockquote",
      "br",
      "code",
      "em",
      "h1",
      "h2",
      "h3",
      "h4",
      "li",
      "ol",
      "p",
      "pre",
      "strong",
      "ul",
    ],
    ALLOWED_ATTR: ["href"],
  });
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function fallbackSanitizeHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, "")
    .replace(/<img\b[^>]*>/gi, "")
    .replace(/\son\w+="[^"]*"/gi, "")
    .replace(/\son\w+='[^']*'/gi, "")
    .replace(/href\s*=\s*"javascript:[^"]*"/gi, 'href="#"')
    .replace(/href\s*=\s*'javascript:[^']*'/gi, "href='#'");
}
