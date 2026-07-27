import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

let settingsService: typeof import("./geo-project-query-settings");
let apiModule: typeof import("./api");

beforeAll(async () => {
  const values = new Map<string, string>();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  });
  settingsService = await import("./geo-project-query-settings");
  apiModule = await import("./api");
});

afterEach(() => vi.restoreAllMocks());

describe("GEO Project Query Settings", () => {
  it("normalizes newline and comma separated keywords case-insensitively", () => {
    expect(settingsService.normalizeQuerySettingsKeywords(" ERP\nerp, 採購，\nCRM ")).toEqual([
      "ERP",
      "採購",
      "CRM",
    ]);
  });

  it("maps Keyword tags back to normalized Query Settings text", () => {
    expect(settingsService.querySettingsKeywordTagsToText([
      " ERP ",
      "erp",
      "採購",
      "CRM\n供應商",
    ])).toBe("ERP\n採購\nCRM\n供應商");
  });

  it("maps a saved resource into the editable form", () => {
    expect(settingsService.querySettingsResourceToForm({
      projectId: "project-1",
      researchProvider: "gemini",
      runProvider: "gemini",
      keywords: ["ERP", "採購"],
      marketType: "b2b_procurement",
      maxQueries: 20,
      audience: { name: "採購主管", description: "負責供應商評估" },
      intent: { category: "商業評估", description: "比較供應商" },
      shouldMentionOwnBrand: true,
      shouldMentionCompetitor: false,
      updatedAt: "2026-07-19T00:00:00Z",
    })).toMatchObject({
      keywords: "ERP\n採購",
      maxQueries: 20,
      audienceName: "採購主管",
      intentCategory: "商業評估",
      shouldMentionCompetitor: false,
    });
  });

  it("validates all API length and range boundaries before creating a Project", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    form.keywords = Array.from({ length: 11 }, (_, index) => `keyword-${index}`).join("\n");
    form.maxQueries = 41;
    form.audienceName = "";
    form.intentDescription = "x".repeat(2001);

    expect(settingsService.validateQuerySettingsForm(form)).toEqual({
      keywords: "Keywords 最多 10 筆",
      maxQueries: "Max Queries 必須是 1–40 的整數",
      audienceName: "請輸入 Audience",
      intentDescription: "Intent 描述 最多 2000 字",
    });
  });

  it("returns field errors for required Query Research inputs", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    form.keywords = "";
    form.audienceName = "";
    form.audienceDescription = "";
    form.intentCategory = "";
    form.intentDescription = "";

    expect(settingsService.validateQueryResearchForm(form, [{ name: "  " }])).toEqual({
      keywords: "請至少輸入一個 Keyword。",
      audienceName: "請輸入 Audience",
      audienceDescription: "請輸入 Audience Description",
      intentCategory: "請輸入 Intent 分類",
      intentDescription: "請輸入 Intent 描述",
      topics: "請至少輸入一個 Topic。",
    });
  });

  it("uses product defaults without warning when settings do not exist", async () => {
    vi.spyOn(apiModule.api.geoAnalysis, "querySettings").mockRejectedValue(
      new apiModule.ApiError("project query settings not found", 404),
    );

    const result = await settingsService.loadProjectQuerySettings("project-1");

    expect(result.form).toEqual(settingsService.createDefaultQuerySettingsForm());
    expect(result.warning).toBe("");
  });

  it("keeps Query Search usable when settings temporarily fail", async () => {
    vi.spyOn(apiModule.api.geoAnalysis, "querySettings").mockRejectedValue(
      new apiModule.ApiError("service unavailable", 503),
    );

    const result = await settingsService.loadProjectQuerySettings("project-1");

    expect(result.form).toEqual(settingsService.createDefaultQuerySettingsForm());
    expect(result.warning).toContain("service unavailable");
  });
});
