import type { GeoOverviewIntentCategory } from "../types";

const intentLabels: Record<GeoOverviewIntentCategory, string> = {
  navigational: "導航型",
  informational: "資訊型",
  commercial_investigation: "商業評估",
  transactional: "交易型",
  unclassified: "未分類",
};

export function geoOverviewIntentLabel(category: GeoOverviewIntentCategory): string {
  return intentLabels[category];
}
