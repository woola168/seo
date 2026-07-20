import type { NavigationItem } from "../types";
import { GEO_ADMIN_ACCESS } from "./internal-permissions";
import { hasPermission } from "./permissions";

export const GEO_STANDARD_ACCESS = "geo.projects.read";

const rdChildren: NavigationItem[] = [
  {
    id: "geo-analysis-overview",
    label: "Overview",
    icon: "grid",
    page: "geo-analysis-overview",
  },
  {
    id: "geo-analysis-projects",
    label: "Projects",
    icon: "briefcase",
    page: "geo-analysis-projects",
  },
  {
    id: "geo-analysis-entities",
    label: "Entities",
    icon: "users",
    page: "geo-analysis-entities",
  },
  {
    id: "geo-analysis-queries",
    label: "Topics & Queries",
    icon: "list",
    page: "geo-analysis-queries",
  },
  {
    id: "geo-analysis-schedules",
    label: "Platforms & Schedules",
    icon: "calendar",
    page: "geo-analysis-schedules",
  },
  {
    id: "geo-analysis-jobs",
    label: "Run Jobs",
    icon: "activity",
    page: "geo-analysis-jobs",
  },
  {
    id: "geo-analysis-report-design",
    label: "Report Design",
    icon: "eye",
    page: "geo-analysis-report-design",
  },
  {
    id: "geo-analysis-flow-check",
    label: "Flow Check",
    icon: "check-circle",
    page: "geo-analysis-flow-check",
  },
  {
    id: "geo-analysis-query-research",
    label: "Query Research",
    icon: "sparkles",
    page: "geo-analysis-query-research",
  },
];

const standardChildren: NavigationItem[] = [
  {
    id: "geo-overview",
    label: "Overview",
    icon: "grid",
    page: "geo-overview",
  },
  {
    id: "geo-projects",
    label: "Projects",
    icon: "briefcase",
    page: "geo-projects",
  },
  {
    id: "geo-query-research-coming-soon",
    label: "Query Research",
    icon: "sparkles",
    badge: "尚未開放",
    disabled: true,
  },
];

export function buildGeoNavigation(
  permissions: readonly string[],
): NavigationItem[] {
  const navigation: NavigationItem[] = [];
  if (hasPermission(permissions, GEO_ADMIN_ACCESS)) {
    const visibleRdChildren = rdChildren.filter(
      (item) => item.id !== "geo-analysis-projects" || hasPermission(permissions, GEO_STANDARD_ACCESS),
    );
    navigation.push({
      id: "geo-analysis-rd",
      label: "GEO分析-RD",
      icon: "activity",
      group: "分析工具",
      children: visibleRdChildren,
    });
  }
  if (hasPermission(permissions, GEO_STANDARD_ACCESS)) {
    navigation.push({
      id: "geo-standard",
      label: "GEO分析",
      icon: "activity",
      group: "分析工具",
      children: standardChildren,
    });
  }
  return navigation;
}
