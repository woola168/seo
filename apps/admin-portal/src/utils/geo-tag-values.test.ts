import { describe, expect, it } from "vitest";
import { parseGeoTagValues } from "./geo-tag-values";

describe("GEO tag values", () => {
  it("parses line breaks and Chinese or English commas into trimmed tags", () => {
    expect(parseGeoTagValues(" ERP\r\nCRM, 採購，\n\n供應商 ")).toEqual([
      "ERP",
      "CRM",
      "採購",
      "供應商",
    ]);
  });
});
