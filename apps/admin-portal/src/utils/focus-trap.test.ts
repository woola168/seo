import { describe, expect, it } from "vitest";

import { getFocusTargetIndex } from "./focus-trap";

describe("focus trap", () => {
  it("wraps forward focus to the first item", () => {
    expect(getFocusTargetIndex(2, 3, false)).toBe(0);
  });

  it("wraps backward focus to the last item", () => {
    expect(getFocusTargetIndex(0, 3, true)).toBe(2);
  });

  it("chooses an edge when focus starts outside the dialog", () => {
    expect(getFocusTargetIndex(-1, 3, false)).toBe(0);
    expect(getFocusTargetIndex(-1, 3, true)).toBe(2);
  });
});
