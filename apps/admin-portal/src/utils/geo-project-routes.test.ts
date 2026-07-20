import { describe, expect, it } from "vitest";

import { getGeoProjectRouteNames } from "./geo-project-routes";

describe("GEO Project route context", () => {
  it("uses the standard GEO routes by default", () => {
    expect(getGeoProjectRouteNames(undefined)).toEqual({
      projects: "geo-projects",
      projectNew: "geo-project-new",
      projectEdit: "geo-project-edit",
      queryResearch: "geo-query-research",
      overview: "geo-overview",
    });
  });

  it("keeps the shared flow under GEO Analysis RD routes", () => {
    expect(getGeoProjectRouteNames("rd")).toEqual({
      projects: "geo-analysis-projects",
      projectNew: "geo-analysis-project-new",
      projectEdit: "geo-analysis-project-edit",
      queryResearch: "geo-analysis-project-query-research",
      overview: "geo-analysis-overview",
    });
  });
});
