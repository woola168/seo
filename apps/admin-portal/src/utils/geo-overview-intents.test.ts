import { describe, expect, it } from "vitest";

import { geoOverviewIntentLabel } from "./geo-overview-intents";

describe("GEO Overview intent groups", () => {
  it("uses the agreed Chinese labels for all report groups", () => {
    expect([
      geoOverviewIntentLabel("navigational"),
      geoOverviewIntentLabel("informational"),
      geoOverviewIntentLabel("commercial_investigation"),
      geoOverviewIntentLabel("transactional"),
      geoOverviewIntentLabel("unclassified"),
    ]).toEqual(["導航型", "資訊型", "商業評估", "交易型", "未分類"]);
  });
});
