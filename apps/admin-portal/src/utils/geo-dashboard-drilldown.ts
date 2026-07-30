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

export function filterOwnBrandSentiments(
  sentiments: GeoRunResultSentimentFact[],
): GeoRunResultSentimentFact[] {
  return sentiments.filter((sentiment) => sentiment.entityRole === "own_brand");
}

export function highlightEvidenceInHtml(
  sanitizedHtml: string,
  highlights: EvidenceHighlight[],
): string {
  const replacementByText = new Map<
    string,
    EvidenceHighlight["sentiment"]
  >();
  const replacements = highlights
    .filter((highlight) => highlight.found)
    .map((highlight) => ({
      text: renderedMarkdownText(highlight.text),
      sentiment: highlight.sentiment,
    }))
    .filter((highlight) => highlight.text.length > 0)
    .sort((left, right) => {
      const lengthDifference = right.text.length - left.text.length;
      if (lengthDifference !== 0) return lengthDifference;
      return left.sentiment === right.sentiment
        ? 0
        : left.sentiment === "negative"
          ? -1
          : 1;
    });
  for (const replacement of replacements) {
    if (!replacementByText.has(replacement.text)) {
      replacementByText.set(replacement.text, replacement.sentiment);
    }
  }
  if (replacementByText.size === 0) return sanitizedHtml;

  const segments = htmlTextSegments(sanitizedHtml);
  const visibleHtml = segments.map((segment) => segment.text).join("");
  const ranges = selectHighlightRanges(visibleHtml, replacementByText);
  if (ranges.length === 0) return sanitizedHtml;

  let visibleOffset = 0;
  let htmlOffset = 0;
  let highlightedHtml = "";
  for (const segment of segments) {
    highlightedHtml += sanitizedHtml.slice(htmlOffset, segment.htmlStart);
    const segmentStart = visibleOffset;
    const segmentEnd = segmentStart + segment.text.length;
    highlightedHtml += highlightTextSegment(
      segment.text,
      segmentStart,
      segmentEnd,
      ranges,
    );
    visibleOffset = segmentEnd;
    htmlOffset = segment.htmlEnd;
  }
  return highlightedHtml + sanitizedHtml.slice(htmlOffset);
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

interface HtmlTextSegment {
  text: string;
  htmlStart: number;
  htmlEnd: number;
}

interface HighlightRange {
  start: number;
  end: number;
  sentiment: EvidenceHighlight["sentiment"];
}

function renderedMarkdownText(raw: string): string {
  return renderSafeMarkdown(raw).replace(/<[^>]+>/g, "").trim();
}

function htmlTextSegments(html: string): HtmlTextSegment[] {
  const segments: HtmlTextSegment[] = [];
  for (const match of html.matchAll(/<[^>]*>|[^<]+/g)) {
    const text = match[0];
    if (text.startsWith("<")) continue;
    const htmlStart = match.index;
    const htmlEnd = htmlStart + text.length;
    segments.push({ text, htmlStart, htmlEnd });
  }
  return segments;
}

function selectHighlightRanges(
  text: string,
  replacements: Map<string, EvidenceHighlight["sentiment"]>,
): HighlightRange[] {
  const selected: HighlightRange[] = [];
  for (const [evidence, sentiment] of replacements.entries()) {
    let start = text.indexOf(evidence);
    while (start >= 0) {
      const candidate = { start, end: start + evidence.length, sentiment };
      if (
        !selected.some(
          (range) => candidate.start < range.end && candidate.end > range.start,
        )
      ) {
        selected.push(candidate);
      }
      start = text.indexOf(evidence, start + evidence.length);
    }
  }
  return selected.sort((left, right) => left.start - right.start);
}

function highlightTextSegment(
  text: string,
  segmentStart: number,
  segmentEnd: number,
  ranges: HighlightRange[],
): string {
  let offset = 0;
  let highlighted = "";
  for (const range of ranges) {
    const start = Math.max(range.start, segmentStart);
    const end = Math.min(range.end, segmentEnd);
    if (start >= end) continue;
    const localStart = start - segmentStart;
    const localEnd = end - segmentStart;
    highlighted += text.slice(offset, localStart);
    highlighted += `<mark class="sentiment-highlight sentiment-highlight-${range.sentiment}">${text.slice(localStart, localEnd)}</mark>`;
    offset = localEnd;
  }
  return highlighted + text.slice(offset);
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
