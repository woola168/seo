import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type {
  GeoEntityAliasResource,
  GeoEntityResource,
  GeoProjectResource,
  GeoQueryResource,
  GeoTopicResource,
} from "../types";

let buildGeoProjectProfile: typeof import("./geo-project-profile")["buildGeoProjectProfile"];
let createGeoProjectWithQuerySettings: typeof import("./geo-project-profile")["createGeoProjectWithQuerySettings"];
let normalizeValues: typeof import("./geo-project-profile")["normalizeValues"];
let apiModule: typeof import("./api");

beforeAll(async () => {
  const values = new Map<string, string>();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
    clear: () => values.clear(),
  });
  const profileModule = await import("./geo-project-profile");
  buildGeoProjectProfile = profileModule.buildGeoProjectProfile;
  createGeoProjectWithQuerySettings = profileModule.createGeoProjectWithQuerySettings;
  normalizeValues = profileModule.normalizeValues;
  apiModule = await import("./api");
});

afterEach(() => vi.restoreAllMocks());

describe("GEO Project profile", () => {
  it("aggregates own-brand, aliases and competitors for the standard pages", () => {
    const project: GeoProjectResource = {
      id: "project-1",
      customerId: "customer-1",
      name: "善存",
      defaultRegion: "TW",
      defaultLanguage: "zh-TW",
      status: "active",
      dailyRunBudget: 200,
      createdAt: "2026-07-18T00:00:00Z",
      updatedAt: "2026-07-18T00:00:00Z",
    };
    const entities: GeoEntityResource[] = [
      entity("own-1", "own_brand", "善存", "https://centrum.com.tw"),
      entity("competitor-1", "competitor", "GNC", "https://gnc.com.tw"),
    ];
    const aliases: GeoEntityAliasResource[] = [
      alias("alias-1", "own-1", "Centrum"),
      alias("alias-2", "competitor-1", "健安喜"),
    ];

    const profile = buildGeoProjectProfile(
      project,
      [{ id: "customer-1", name: "客戶一" }],
      entities,
      aliases,
      [] as GeoTopicResource[],
      [] as GeoQueryResource[],
    );

    expect(profile.customerName).toBe("客戶一");
    expect(profile.ownBrand.websiteUrl).toBe("https://centrum.com.tw");
    expect(profile.ownBrand.aliases.map((item) => item.alias)).toEqual(["Centrum"]);
    expect(profile.competitors[0]).toMatchObject({ name: "GNC", websiteUrl: "https://gnc.com.tw" });
    expect(profile.competitors[0]?.aliases.map((item) => item.alias)).toEqual(["健安喜"]);
  });

  it("falls back to the Project name when own-brand has not been created", () => {
    const profile = buildGeoProjectProfile(
      {
        id: "project-1",
        customerId: null,
        name: "尚未設定品牌",
        defaultRegion: "TW",
        defaultLanguage: "zh-TW",
        status: "active",
        dailyRunBudget: 200,
        createdAt: "2026-07-18T00:00:00Z",
        updatedAt: "2026-07-18T00:00:00Z",
      },
      [],
      [],
      [],
      [],
      [],
    );
    expect(profile.ownBrand.name).toBe("尚未設定品牌");
    expect(profile.ownBrand.entity).toBeNull();
    expect(profile.customerName).toBe("未綁定 Customer");
  });

  it("normalizes tags without empty or duplicate values", () => {
    expect(normalizeValues([" GNC ", "", "GNC", "DHC"])).toEqual(["GNC", "DHC"]);
  });

  it("saves Query Settings after the Project profile and Topics", async () => {
    const calls = mockProjectCreation();

    const result = await createGeoProjectWithQuerySettings(
      projectInput(),
      querySettingsRequest(),
      true,
    );

    expect(result.querySettingsStatus).toBe("saved");
    expect(calls.createProject).toHaveBeenCalledTimes(1);
    expect(calls.updateQuerySettings).toHaveBeenCalledWith("project-1", querySettingsRequest());
    expect(calls.replaceAliases).toHaveBeenCalledWith("own-1", { items: [] });
    expect(calls.createProject.mock.invocationCallOrder[0]).toBeLessThan(
      calls.createEntity.mock.invocationCallOrder[0]!,
    );
    expect(calls.createEntity.mock.invocationCallOrder[0]).toBeLessThan(
      calls.createTopic.mock.invocationCallOrder[0]!,
    );
    expect(calls.createTopic.mock.invocationCallOrder[0]).toBeLessThan(
      calls.updateQuerySettings.mock.invocationCallOrder[0]!,
    );
  });

  it("replaces own-brand and competitor aliases once per Entity", async () => {
    const calls = mockProjectCreation();
    calls.createEntity
      .mockResolvedValueOnce(entity("own-1", "own_brand", "範例 Project", "https://example.com"))
      .mockResolvedValueOnce(entity("competitor-1", "competitor", "競品", "https://competitor.example"));
    const input = {
      ...projectInput(),
      aliases: ["Own", "Own TW"],
      competitors: [
        {
          id: null,
          name: "競品",
          websiteUrl: "https://competitor.example",
          aliases: ["Competitor", "競品別名"],
        },
      ],
    };

    await createGeoProjectWithQuerySettings(input, querySettingsRequest(), true);

    expect(calls.replaceAliases).toHaveBeenCalledTimes(2);
    expect(calls.replaceAliases).toHaveBeenNthCalledWith(1, "own-1", {
      items: [
        { alias: "Own", matchType: "exact" },
        { alias: "Own TW", matchType: "exact" },
      ],
    });
    expect(calls.replaceAliases).toHaveBeenNthCalledWith(2, "competitor-1", {
      items: [
        { alias: "Competitor", matchType: "exact" },
        { alias: "競品別名", matchType: "exact" },
      ],
    });
  });

  it("keeps the created Project when Query Settings saving fails", async () => {
    const calls = mockProjectCreation();
    calls.updateQuerySettings.mockRejectedValue(new Error("settings unavailable"));

    const result = await createGeoProjectWithQuerySettings(
      projectInput(),
      querySettingsRequest(),
      true,
    );

    expect(result).toMatchObject({
      project: { id: "project-1" },
      querySettingsStatus: "failed",
      querySettingsError: "settings unavailable",
    });
    expect(calls.createProject).toHaveBeenCalledTimes(1);
  });

  it("keeps the created Project and reports a batch Alias failure", async () => {
    const calls = mockProjectCreation();
    calls.replaceAliases.mockRejectedValueOnce(new Error("aliases unavailable"));

    await expect(
      createGeoProjectWithQuerySettings(projectInput(), querySettingsRequest(), true),
    ).rejects.toMatchObject({
      message: "aliases unavailable",
      project: { id: "project-1" },
    });
    expect(calls.createProject).toHaveBeenCalledTimes(1);
    expect(calls.updateQuerySettings).not.toHaveBeenCalled();
  });

  it("skips Query Settings when the user cannot update Projects", async () => {
    const calls = mockProjectCreation();

    const result = await createGeoProjectWithQuerySettings(
      projectInput(),
      querySettingsRequest(),
      false,
    );

    expect(result.querySettingsStatus).toBe("skipped");
    expect(calls.createProject).toHaveBeenCalledTimes(1);
    expect(calls.updateQuerySettings).not.toHaveBeenCalled();
  });
});

function mockProjectCreation() {
  const project = projectResource();
  const createProject = vi.spyOn(apiModule.api.geoAnalysis, "createProject").mockResolvedValue(project);
  const createEntity = vi.spyOn(apiModule.api.geoAnalysis, "createEntity").mockResolvedValue(
    entity("own-1", "own_brand", project.name, "https://example.com"),
  );
  const createTopic = vi.spyOn(apiModule.api.geoAnalysis, "createTopic").mockResolvedValue({
    id: "topic-1",
    projectId: project.id,
    name: "採購評估",
    description: "比較方案",
    status: "active",
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
  });
  const replaceAliases = vi.spyOn(apiModule.api.geoAnalysis, "replaceAliases").mockResolvedValue({
    items: [],
    total: 0,
  });
  const updateQuerySettings = vi.spyOn(apiModule.api.geoAnalysis, "updateQuerySettings").mockResolvedValue({
    projectId: project.id,
    ...querySettingsRequest(),
    updatedAt: "2026-07-19T00:00:00Z",
  });
  return { createProject, createEntity, createTopic, replaceAliases, updateQuerySettings };
}

function projectInput() {
  return {
    project: {
      customerId: "customer-1",
      name: "範例 Project",
      defaultRegion: "TW",
      defaultLanguage: "zh-TW",
      status: "active" as const,
      dailyRunBudget: 200,
    },
    websiteUrl: "https://example.com",
    aliases: [],
    competitors: [],
    topics: [{ name: "採購評估", description: "比較方案" }],
  };
}

function querySettingsRequest() {
  return {
    researchProvider: "gemini" as const,
    runProvider: "gemini" as const,
    keywords: ["ERP"],
    marketType: "b2b_procurement" as const,
    maxQueries: 8,
    audience: { name: "B2B 採購", description: "採購決策者" },
    intent: { category: "商業評估", description: "比較方案" },
    shouldMentionOwnBrand: true,
    shouldMentionCompetitor: true,
  };
}

function projectResource(): GeoProjectResource {
  return {
    id: "project-1",
    ...projectInput().project,
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
  };
}

function entity(
  id: string,
  entityType: GeoEntityResource["entityType"],
  name: string,
  websiteUrl: string,
): GeoEntityResource {
  return {
    id,
    projectId: "project-1",
    entityType,
    name,
    websiteUrl,
    description: "",
    status: "active",
    createdAt: "2026-07-18T00:00:00Z",
    updatedAt: "2026-07-18T00:00:00Z",
  };
}

function alias(id: string, entityId: string, value: string): GeoEntityAliasResource {
  return {
    id,
    entityId,
    alias: value,
    matchType: "exact",
    createdAt: "2026-07-18T00:00:00Z",
  };
}
