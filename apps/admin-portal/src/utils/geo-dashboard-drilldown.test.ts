import { describe, expect, it } from "vitest";

import type {
  GeoAnalysisRunResult,
  GeoQueryResource,
  GeoRunResultSentimentFact,
} from "../types";
import {
  buildEvidenceHighlights,
  buildRunResultRows,
  filterOwnBrandSentiments,
  filterRunResultRows,
  highlightEvidenceInHtml,
  paginateItems,
  renderSafeMarkdown,
} from "./geo-dashboard-drilldown";

describe("geo dashboard drilldown helpers", () => {
  it("joins run results with query text and falls back to query id", () => {
    const rows = buildRunResultRows(
      [_result({ queryId: "query-1" }), _result({ id: "result-2", queryId: "query-missing" })],
      [_query({ id: "query-1", queryText: "哪個 ERP 供應商適合 B2B 採購？" })],
    );

    expect(rows[0].queryText).toBe("哪個 ERP 供應商適合 B2B 採購？");
    expect(rows[0].topicId).toBe("topic-1");
    expect(rows[1].queryText).toBe("query-missing");
  });

  it("filters run result rows by report filters", () => {
    const rows = buildRunResultRows(
      [
        _result({ id: "result-1", queryId: "query-1", provider: "gemini" }),
        _result({
          id: "result-2",
          queryId: "query-2",
          provider: "google_aio",
          runAt: "2026-08-01T00:00:00Z",
        }),
      ],
      [
        _query({ id: "query-1", topicId: "topic-1" }),
        _query({ id: "query-2", topicId: "topic-2" }),
      ],
    );

    expect(
      filterRunResultRows(rows, {
        periodStart: "2026-07-01T00:00:00Z",
        periodEnd: "2026-07-31T23:59:59Z",
        provider: "gemini",
        topicId: "topic-1",
      }).map((row) => row.result.id),
    ).toEqual(["result-1"]);
  });

  it("paginates items and clamps out-of-range pages", () => {
    const result = paginateItems([1, 2, 3, 4, 5], { page: 3, pageSize: 2 });

    expect(result.items).toEqual([5]);
    expect(result.total).toBe(5);
    expect(result.totalPages).toBe(3);
    expect(paginateItems([1], { page: 99, pageSize: 10 }).page).toBe(1);
  });

  it("renders markdown and removes unsafe HTML", () => {
    const html = renderSafeMarkdown(
      "# 標題\n\n- 項目\n\n[連結](https://example.com)\n\n![tracking](https://tracker.example/pixel.png)\n\n<script>alert(1)</script><a href=\"javascript:alert(1)\" onclick=\"x()\">bad</a>",
    );

    expect(html).toContain("<h1>標題</h1>");
    expect(html).toContain("<li>項目</li>");
    expect(html).toContain("https://example.com");
    expect(html).not.toContain("<img");
    expect(html).not.toContain("tracker.example");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("javascript:alert");
    expect(html).not.toContain("onclick");
  });

  it("builds sentiment evidence highlight state from raw response", () => {
    const highlights = buildEvidenceHighlights("Acme is recommended.", [
      _sentiment({
        sentiment: "positive",
        evidenceText: "Acme is recommended.",
      }),
      _sentiment({
        sentiment: "negative",
        evidenceText: "Not in response",
      }),
    ]);

    expect(highlights).toEqual([
      {
        text: "Acme is recommended.",
        sentiment: "positive",
        found: true,
      },
      {
        text: "Not in response",
        sentiment: "negative",
        found: false,
      },
    ]);
  });

  it("highlights found evidence inside sanitized markdown html", () => {
    const html = highlightEvidenceInHtml("<p>Acme is recommended.</p>", [
      {
        text: "Acme is recommended.",
        sentiment: "positive",
        found: true,
      },
    ]);

    expect(html).toContain("sentiment-highlight-positive");
    expect(html).toContain("<mark");
  });

  it("highlights evidence that contains inline markdown formatting", () => {
    const rawResponse =
      "若貴司重視供應鏈透明度，**善存**是目前風險係數最低的採購對象；";
    const evidenceText =
      "若貴司重視供應鏈透明度，**善存**是目前風險係數最低的採購對象；";

    const html = highlightEvidenceInHtml(
      renderSafeMarkdown(rawResponse),
      buildEvidenceHighlights(rawResponse, [
        _sentiment({ evidenceText, sentiment: "positive" }),
      ]),
    );

    expect(html).toContain("sentiment-highlight-positive");
    expect(html).toContain(
      '<strong><mark class="sentiment-highlight sentiment-highlight-positive">善存</mark></strong>',
    );
  });

  it("highlights evidence that is a markdown list item", () => {
    const rawResponse = "建議如下：\n\n* **Acme ERP** 適合製造業。";
    const evidenceText = "* **Acme ERP** 適合製造業。";

    const html = highlightEvidenceInHtml(
      renderSafeMarkdown(rawResponse),
      buildEvidenceHighlights(rawResponse, [
        _sentiment({ evidenceText, sentiment: "positive" }),
      ]),
    );

    expect(html).toContain("sentiment-highlight-positive");
    expect(html).toContain(
      '<strong><mark class="sentiment-highlight sentiment-highlight-positive">Acme ERP</mark></strong>',
    );
  });

  it.each([
    ["blockquote", "前言\n\n> Acme ERP 適合製造業。", "> Acme ERP 適合製造業。"],
    ["heading", "## Acme ERP 適合製造業。", "## Acme ERP 適合製造業。"],
  ])(
    "highlights evidence that is a markdown %s",
    (_, rawResponse, evidenceText) => {
      const html = highlightEvidenceInHtml(
        renderSafeMarkdown(rawResponse),
        buildEvidenceHighlights(rawResponse, [
          _sentiment({ evidenceText, sentiment: "positive" }),
        ]),
      );

      expect(html).toContain("sentiment-highlight-positive");
    },
  );

  it("does not highlight evidence inside html attributes", () => {
    const html = highlightEvidenceInHtml(
      '<p><a href="https://example.com/Acme">Acme</a></p>',
      [
        {
          text: "Acme",
          sentiment: "positive",
          found: true,
        },
      ],
    );

    expect(html).toContain('href="https://example.com/Acme"');
    expect(html).toContain(">Acme</mark></a>");
  });

  it("uses the longest evidence once when highlights overlap", () => {
    const html = highlightEvidenceInHtml("<p>Acme is recommended.</p>", [
      {
        text: "Acme",
        sentiment: "negative",
        found: true,
      },
      {
        text: "Acme is recommended.",
        sentiment: "positive",
        found: true,
      },
    ]);

    expect(html).toBe(
      '<p><mark class="sentiment-highlight sentiment-highlight-positive">Acme is recommended.</mark></p>',
    );
  });

  it("does not nest marks when overlapping evidence both contain markdown", () => {
    const rawResponse = "Acme is **recommended**.";
    const html = highlightEvidenceInHtml(renderSafeMarkdown(rawResponse), [
      {
        text: "Acme is **recommended**.",
        sentiment: "positive",
        found: true,
      },
      {
        text: "**recommended**",
        sentiment: "negative",
        found: true,
      },
    ]);

    expect(html).toContain("sentiment-highlight-positive");
    expect(html).not.toContain("sentiment-highlight-negative");
    expect(html).not.toMatch(/<mark[^>]*>\s*<mark/);
  });

  it("uses negative sentiment when duplicate evidence conflicts", () => {
    const html = highlightEvidenceInHtml("<p>Acme</p>", [
      { text: "Acme", sentiment: "positive", found: true },
      { text: "Acme", sentiment: "negative", found: true },
    ]);

    expect(html).toContain("sentiment-highlight-negative");
    expect(html.match(/<mark/g)).toHaveLength(1);
  });

  it("ignores blank and missing evidence without changing markdown", () => {
    const rawResponse = "Acme is recommended.";
    const highlights = buildEvidenceHighlights(rawResponse, [
      _sentiment({ evidenceText: "  " }),
      _sentiment({ evidenceText: null }),
      _sentiment({ evidenceText: "Missing sentence" }),
    ]);

    expect(highlights).toEqual([
      { text: "Missing sentence", sentiment: "positive", found: false },
    ]);
    expect(highlightEvidenceInHtml(renderSafeMarkdown(rawResponse), highlights)).toBe(
      renderSafeMarkdown(rawResponse),
    );
  });

  it("keeps only own-brand sentiment facts for Overview annotations", () => {
    const ownBrand = _sentiment({ entityId: "own-brand" });
    const competitor = _sentiment({
      entityId: "competitor",
      entityRole: "competitor",
      entityName: "Competitor",
    });

    expect(filterOwnBrandSentiments([competitor, ownBrand])).toEqual([ownBrand]);
  });
});

function _query(overrides: Partial<GeoQueryResource> = {}): GeoQueryResource {
  return {
    id: "query-1",
    projectId: "project-1",
    topicId: "topic-1",
    queryText: "Query text",
    region: "TW",
    language: "zh-TW",
    marketType: "b2b_procurement",
    intent: null,
    buyerStage: null,
    isBranded: false,
    priority: "normal",
    status: "active",
    metadata: {},
    createdAt: "2026-07-01T00:00:00Z",
    updatedAt: "2026-07-01T00:00:00Z",
    ...overrides,
  };
}

function _result(overrides: Partial<GeoAnalysisRunResult> = {}): GeoAnalysisRunResult {
  return {
    id: "result-1",
    jobId: "job-1",
    queryId: "query-1",
    provider: "gemini",
    surface: "Gemini",
    model: "gemini-2.5-flash",
    region: "TW",
    language: "zh-TW",
    status: "completed",
    rawResponse: "Acme is recommended.",
    references: [],
    error: null,
    runAt: "2026-07-15T00:00:00Z",
    analysisStatus: "completed",
    analysisErrorCode: null,
    analysisErrorMessage: null,
    ...overrides,
  };
}

function _sentiment(
  overrides: Partial<GeoRunResultSentimentFact> = {},
): GeoRunResultSentimentFact {
  return {
    entityId: "entity-1",
    entityRole: "own_brand",
    entityName: "Acme",
    sentiment: "positive",
    theme: "供應商比較",
    statement: "Acme is recommended.",
    evidenceText: "Acme is recommended.",
    confidence: 0.9,
    ...overrides,
  };
}
