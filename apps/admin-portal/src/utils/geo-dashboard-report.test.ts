import { describe, expect, it } from "vitest";

import { mockGeoDashboardReport } from "../mocks/geo-dashboard-report";
import type { GeoDashboardReport } from "../types";
import {
  buildGeoDashboardReportQuery,
  formatGeoDashboardDelta,
  formatGeoDashboardMetric,
  geoDashboardDeltaTone,
  geoDashboardSentimentDeltaTone,
  isGeoDashboardReportEmpty,
  toGeoDashboardApiDateTime,
} from "./geo-dashboard-report";

describe("geo dashboard report helpers", () => {
  it("detects empty live API reports without treating mock reports as empty", () => {
    const emptyReport: GeoDashboardReport = {
      periodStart: "2026-06-01T00:00:00Z",
      periodEnd: "2026-06-30T23:59:59Z",
      comparisonStart: "2026-05-01T00:00:00Z",
      comparisonEnd: "2026-05-31T23:59:59Z",
      overview: [],
      entities: [],
      citationUrls: [],
      citationDomains: [],
      sentiments: [],
    };

    expect(isGeoDashboardReportEmpty(emptyReport)).toBe(true);
    expect(isGeoDashboardReportEmpty(mockGeoDashboardReport)).toBe(false);
    expect(isGeoDashboardReportEmpty(null)).toBe(true);
  });

  it("formats metric values for percent, count, and position units", () => {
    expect(
      formatGeoDashboardMetric({
        value: 68,
        unit: "percent",
        numerator: 34,
        denominator: 50,
        comparisonValue: 55,
        delta: 13,
        deltaUnit: "pp",
      }),
    ).toBe("68%");
    expect(
      formatGeoDashboardMetric({
        value: 142,
        unit: "count",
        numerator: 142,
        denominator: null,
        comparisonValue: null,
        delta: null,
        deltaUnit: null,
      }),
    ).toBe("142");
    expect(
      formatGeoDashboardMetric({
        value: 2.4,
        unit: "position",
        numerator: 82,
        denominator: 34,
        comparisonValue: null,
        delta: null,
        deltaUnit: null,
      }),
    ).toBe("#2.4");
  });

  it("formats delta values and semantic tones", () => {
    const positive = mockGeoDashboardReport.overview[0].metric;
    const negative = mockGeoDashboardReport.overview[2].metric;
    const missing = mockGeoDashboardReport.overview[3].metric;

    expect(formatGeoDashboardDelta(positive)).toBe("+13 pp");
    expect(geoDashboardDeltaTone(positive)).toBe("success");
    expect(formatGeoDashboardDelta(negative)).toBe("-4 pp");
    expect(geoDashboardDeltaTone(negative)).toBe("error");
    expect(formatGeoDashboardDelta(missing)).toBe("No comparison");
    expect(geoDashboardDeltaTone(missing)).toBe("muted");
  });

  it("treats lower position deltas as better", () => {
    expect(
      geoDashboardDeltaTone({
        value: 2.4,
        unit: "position",
        numerator: 82,
        denominator: 34,
        comparisonValue: 3.1,
        delta: -0.7,
        deltaUnit: "position",
      }),
    ).toBe("success");
    expect(
      geoDashboardDeltaTone({
        value: 3.4,
        unit: "position",
        numerator: 102,
        denominator: 30,
        comparisonValue: 2.8,
        delta: 0.6,
        deltaUnit: "position",
      }),
    ).toBe("error");
  });

  it("reverses tone for negative sentiment counts", () => {
    expect(
      geoDashboardSentimentDeltaTone("positive", {
        value: 39,
        unit: "count",
        numerator: 39,
        denominator: null,
        comparisonValue: 34,
        delta: 5,
        deltaUnit: "count",
      }),
    ).toBe("success");
    expect(
      geoDashboardSentimentDeltaTone("negative", {
        value: 9,
        unit: "count",
        numerator: 9,
        denominator: null,
        comparisonValue: 6,
        delta: 3,
        deltaUnit: "count",
      }),
    ).toBe("error");
    expect(
      geoDashboardSentimentDeltaTone("negative", {
        value: 4,
        unit: "count",
        numerator: 4,
        denominator: null,
        comparisonValue: 7,
        delta: -3,
        deltaUnit: "count",
      }),
    ).toBe("success");
  });

  it("does not format empty datetime values into invalid API timestamps", () => {
    expect(toGeoDashboardApiDateTime("")).toBe("");
    expect(toGeoDashboardApiDateTime("2026-06-01T00:00")).toBe(
      "2026-06-01T00:00:00Z",
    );
  });

  it("does not build a live API query when required date ranges are incomplete", () => {
    expect(
      buildGeoDashboardReportQuery({
        periodStart: "",
        periodEnd: "2026-06-30T23:59",
        comparisonStart: "2026-05-01T00:00",
        comparisonEnd: "2026-05-31T23:59",
      }),
    ).toBeNull();
    expect(
      buildGeoDashboardReportQuery({
        periodStart: "2026-06-01T00:00",
        periodEnd: "2026-06-30T23:59",
        comparisonStart: "2026-05-01T00:00",
        comparisonEnd: "2026-05-31T23:59",
        provider: "",
      }),
    ).toEqual({
      periodStart: "2026-06-01T00:00:00Z",
      periodEnd: "2026-06-30T23:59:00Z",
      comparisonStart: "2026-05-01T00:00:00Z",
      comparisonEnd: "2026-05-31T23:59:00Z",
      provider: undefined,
      region: undefined,
      language: undefined,
    });
  });
});
