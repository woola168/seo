import { describe, expect, it } from "vitest";

import { hasPermission } from "./permissions";

describe("hasPermission", () => {
  it("checks whether a permission exists", () => {
    const permissions = ["customers.read", "tasks.read"];

    expect(hasPermission(permissions, "tasks.read")).toBe(true);
    expect(hasPermission(permissions, "tasks.delete")).toBe(false);
  });
});
