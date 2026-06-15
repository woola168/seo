import { describe, expect, it } from "vitest";

import {
  describePermission,
  hasPermission,
  permissionLabel,
} from "./permissions";

describe("hasPermission", () => {
  it("checks whether a permission exists", () => {
    const permissions = ["customers.read", "tasks.read"];

    expect(hasPermission(permissions, "tasks.read")).toBe(true);
    expect(hasPermission(permissions, "tasks.delete")).toBe(false);
  });
});

describe("permission presentation", () => {
  it("provides Traditional Chinese labels and descriptions", () => {
    expect(permissionLabel("customers.create")).toBe("新增客戶");
    expect(describePermission("customers.create")).toEqual({
      key: "customers.create",
      label: "新增客戶",
      description: "建立新的客戶資料。",
    });
  });

  it("falls back to the permission key for unknown permissions", () => {
    expect(describePermission("reports.read")).toEqual({
      key: "reports.read",
      label: "reports.read",
      description: "尚未提供此權限的中文說明。",
    });
  });
});
