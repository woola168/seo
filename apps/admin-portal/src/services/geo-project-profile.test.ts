import { beforeAll, describe, expect, it, vi } from "vitest";
import type {
  GeoEntityAliasResource,
  GeoEntityResource,
  GeoProjectResource,
  GeoQueryResource,
  GeoTopicResource,
} from "../types";

let buildGeoProjectProfile: typeof import("./geo-project-profile")["buildGeoProjectProfile"];
let normalizeValues: typeof import("./geo-project-profile")["normalizeValues"];

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
  normalizeValues = profileModule.normalizeValues;
});

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
});

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
