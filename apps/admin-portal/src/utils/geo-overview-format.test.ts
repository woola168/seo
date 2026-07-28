import { describe, expect, it } from "vitest";

import { formatSentimentRatio } from "./geo-overview-format";

describe("GEO Overview formatting", () => {
  it("formats sentiment ratios with one decimal on both sides", () => {
    expect(formatSentimentRatio(4)).toBe("4.0:1.0");
    expect(formatSentimentRatio(4.06)).toBe("4.1:1.0");
    expect(formatSentimentRatio(null)).toBe("—");
  });
});
