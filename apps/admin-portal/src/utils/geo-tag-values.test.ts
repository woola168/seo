import { describe, expect, it } from "vitest";
import { mergeGeoTagValues, parseGeoTagValues } from "./geo-tag-values";

describe("GEO tag values", () => {
  it("parses line breaks and Chinese or English commas into trimmed tags", () => {
    expect(parseGeoTagValues(" ERP\r\nCRM, 採購，\n\n供應商 ")).toEqual([
      "ERP",
      "CRM",
      "採購",
      "供應商",
    ]);
  });

  it("keeps only the first unique values up to the configured tag limit", () => {
    expect(mergeGeoTagValues(
      ["既有", "重複"],
      "重複, 新增一, 新增二, 新增三",
      4,
    )).toEqual(["既有", "重複", "新增一", "新增二"]);
  });
});
