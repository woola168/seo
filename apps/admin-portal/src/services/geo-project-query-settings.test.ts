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
    const form = settingsService.querySettingsResourceToForm({
      projectId: "project-1",
      researchProvider: "gemini",
      runProvider: "gemini",
      keywords: ["ERP", "採購"],
      marketType: "b2b_procurement",
      maxQueries: 20,
      audience: { name: "採購主管", description: "負責供應商評估" },
      intents: [
        { category: "informational", description: "了解產品" },
        { category: "transactional", description: "採取購買行動" },
      ],
      shouldMentionOwnBrand: true,
      shouldMentionCompetitor: false,
      updatedAt: "2026-07-19T00:00:00Z",
    });

    expect(form).toMatchObject({
      keywords: "ERP\n採購",
      maxQueries: 20,
      audienceName: "採購主管",
      shouldMentionCompetitor: false,
    });
    expect(form.intents.filter((intent) => intent.selected)).toEqual([
      expect.objectContaining({ category: "informational", selected: true }),
      expect.objectContaining({ category: "transactional", selected: true }),
    ]);
  });

  it("keeps OpenAI as the saved Query Research and Generation provider", () => {
    const form = settingsService.querySettingsResourceToForm({
      projectId: "project-1",
      researchProvider: "openai",
      runProvider: "gemini",
      keywords: ["ERP"],
      marketType: "b2b_procurement",
      maxQueries: 10,
      audience: { name: "採購主管", description: "負責供應商評估" },
      intents: [{ category: "transactional", description: "採取購買行動" }],
      shouldMentionOwnBrand: true,
      shouldMentionCompetitor: false,
      updatedAt: "2026-08-03T00:00:00Z",
    });

    expect(form.researchProvider).toBe("openai");
    expect(settingsService.querySettingsFormToRequest(form).researchProvider).toBe(
      "openai",
    );
  });

  it("sends only selected intents with stable category codes", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    form.intents = form.intents.map((intent) => ({
      ...intent,
      selected: ["navigational", "transactional"].includes(intent.category),
    }));

    expect(settingsService.querySettingsFormToRequest(form).intents).toEqual([
      expect.objectContaining({ category: "navigational" }),
      expect.objectContaining({ category: "transactional" }),
    ]);
  });

  it("maps saved intent codes and legacy labels to Chinese UI labels", () => {
    expect(settingsService.queryIntentLabel("navigational")).toBe("導航");
    expect(settingsService.queryIntentLabel("資訊型")).toBe("資訊");
    expect(settingsService.queryIntentLabel("commercial_investigation")).toBe("商業");
    expect(settingsService.queryIntentLabel("transactional")).toBe("交易");
    expect(settingsService.queryIntentLabel(null)).toBe("未分類");
  });

  it("validates all API length and range boundaries before creating a Project", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    form.keywords = Array.from({ length: 11 }, (_, index) => `keyword-${index}`).join("\n");
    form.maxQueries = 41;
    form.audienceName = "";
    form.intents = form.intents.map((intent) => intent.selected
      ? { ...intent, description: "x".repeat(2001) }
      : intent);

    expect(settingsService.validateQuerySettingsForm(form)).toEqual({
      keywords: "Keywords 最多 10 筆",
      maxQueries: "Max Queries 必須是 1–40 的整數",
      audienceName: "請輸入 Audience",
      intents: "每個 Intent 描述最多 2000 字",
    });
  });

  it("returns field errors for required Query Research inputs", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    form.keywords = "";
    form.audienceName = "";
    form.audienceDescription = "";
    form.intents = form.intents.map((intent) => ({ ...intent, selected: false }));

    expect(settingsService.validateQueryResearchForm(form, [{ name: "  " }])).toEqual({
      keywords: "請至少輸入一個 Keyword。",
      audienceName: "請輸入 Audience",
      audienceDescription: "請輸入 Audience Description",
      intents: "請至少選擇一個 Intent",
      topics: "請至少輸入一個 Topic。",
    });
  });

  it("rejects Query Research input with more than eight Topics", () => {
    const form = settingsService.createDefaultQuerySettingsForm();
    const topics = Array.from(
      { length: settingsService.MAX_GEO_TOPICS + 1 },
      (_, index) => ({ name: `Topic ${index + 1}` }),
    );

    expect(settingsService.validateQueryResearchForm(form, topics)).toMatchObject({
      topics: "Topics 最多 8 筆。",
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
