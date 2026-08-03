import { describe, expect, it } from "vitest";
import { findCompetitorOwnBrandConflicts } from "./geo-brand-identity";

describe("GEO brand identity conflicts", () => {
  it("matches names after width, whitespace and case normalization", () => {
    const conflicts = findCompetitorOwnBrandConflicts(
      { names: ["ＡＣＭＥ Taiwan"], aliases: [] },
      { name: " acme   TAIWAN ", aliases: [] },
    );

    expect(conflicts).toEqual([{ field: "name", value: "acme   TAIWAN" }]);
  });

  it("rejects a competitor name that matches an own-brand alias", () => {
    const conflicts = findCompetitorOwnBrandConflicts(
      { names: ["善存"], aliases: ["Centrum"] },
      { name: "CENTRUM", aliases: [] },
    );

    expect(conflicts).toEqual([{ field: "name", value: "CENTRUM" }]);
  });

  it("rejects competitor aliases that match the own-brand name or aliases", () => {
    const conflicts = findCompetitorOwnBrandConflicts(
      { names: ["善存"], aliases: ["Centrum"] },
      { name: "競品", aliases: ["善存", "centrum", "其他名稱"] },
    );

    expect(conflicts).toEqual([
      { field: "alias", value: "善存" },
      { field: "alias", value: "centrum" },
    ]);
  });

  it("allows unrelated competitor names and aliases", () => {
    expect(
      findCompetitorOwnBrandConflicts(
        { names: ["善存"], aliases: ["Centrum"] },
        { name: "GNC", aliases: ["健安喜"] },
      ),
    ).toEqual([]);
  });

  it("protects both current and pending own-brand names", () => {
    const currentNameConflict = findCompetitorOwnBrandConflicts(
      { names: ["目前品牌", "新的品牌名稱"], aliases: [] },
      { name: "目前品牌", aliases: [] },
    );
    const pendingNameConflict = findCompetitorOwnBrandConflicts(
      { names: ["目前品牌", "新的品牌名稱"], aliases: [] },
      { name: "新的品牌名稱", aliases: [] },
    );

    expect(currentNameConflict).toEqual([{ field: "name", value: "目前品牌" }]);
    expect(pendingNameConflict).toEqual([{ field: "name", value: "新的品牌名稱" }]);
  });
});
