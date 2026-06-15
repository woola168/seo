import { describe, expect, it } from "vitest";

import { getMemberStatusDisplay } from "./member-status";

describe("member status display", () => {
  it.each([
    ["active", "啟用", "success"],
    ["disabled", "停用", "muted"],
    ["invited", "邀請中", "blue"],
  ] as const)("maps %s to a localized badge", (status, label, tone) => {
    expect(getMemberStatusDisplay(status)).toEqual({
      value: status,
      label,
      tone,
    });
  });

  it("keeps an unknown API status visible with a muted badge", () => {
    expect(getMemberStatusDisplay("locked")).toEqual({
      value: "locked",
      label: "locked",
      tone: "muted",
    });
  });
});
