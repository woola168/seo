import { describe, expect, it } from "vitest";

import { hasPermission } from "./permissions";

describe("hasPermission", () => {
  it("只允許有效權限集合內的操作", () => {
    const permissions = ["customers.read", "tasks.read"];

    expect(hasPermission(permissions, "tasks.read")).toBe(true);
    expect(hasPermission(permissions, "tasks.delete")).toBe(false);
  });
});
