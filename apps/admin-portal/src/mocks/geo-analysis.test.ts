import { describe, expect, it } from "vitest";
import { geoPlatformCatalog } from "./geo-analysis";

describe("geoPlatformCatalog", () => {
  it("keeps the Gemini display model aligned with the runtime model", () => {
    const gemini = geoPlatformCatalog.find((platform) => platform.name === "Gemini");

    expect(gemini?.model).toBe("gemini-3.1-flash-lite");
  });
});
