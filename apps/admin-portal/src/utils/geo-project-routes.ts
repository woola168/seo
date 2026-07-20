export type GeoProjectArea = "standard" | "rd";

export interface GeoProjectRouteNames {
  projects: string;
  projectNew: string;
  projectEdit: string;
  queryResearch: string;
  overview: string;
}

const routeNames: Record<GeoProjectArea, GeoProjectRouteNames> = {
  standard: {
    projects: "geo-projects",
    projectNew: "geo-project-new",
    projectEdit: "geo-project-edit",
    queryResearch: "geo-query-research",
    overview: "geo-overview",
  },
  rd: {
    projects: "geo-analysis-projects",
    projectNew: "geo-analysis-project-new",
    projectEdit: "geo-analysis-project-edit",
    queryResearch: "geo-analysis-project-query-research",
    overview: "geo-analysis-overview",
  },
};

export function getGeoProjectRouteNames(area: unknown): GeoProjectRouteNames {
  return area === "rd" ? routeNames.rd : routeNames.standard;
}
