import { describe, expect, it } from "vitest";

import { buildGeoNavigation } from "./geo-navigation";

describe("GEO navigation", () => {
  it("shows both navigation groups to an RD admin", () => {
    const navigation = buildGeoNavigation([
      "geo.admin.access",
      "geo.projects.read",
    ]);

    expect(navigation.map((item) => item.label)).toEqual([
      "GEO分析-RD",
      "GEO分析",
    ]);
  });

  it("shows only standard GEO to a project reader", () => {
    const navigation = buildGeoNavigation(["geo.projects.read"]);

    expect(navigation).toHaveLength(1);
    expect(navigation[0]?.id).toBe("geo-standard");
  });

  it("keeps standard Query Research disabled without a page", () => {
    const navigation = buildGeoNavigation(["geo.projects.read"]);
    const queryResearch = navigation[0]?.children?.find(
      (item) => item.id === "geo-query-research-coming-soon",
    );

    expect(queryResearch).toMatchObject({ disabled: true });
    expect(queryResearch?.page).toBeUndefined();
  });
});
