import { describe, expect, it } from "vitest";

import { canManageUserRoles } from "./permission-guards";

describe("canManageUserRoles", () => {
  it("requires both users.manage and roles.read", () => {
    expect(canManageUserRoles(["users.manage"])).toBe(false);
    expect(canManageUserRoles(["roles.read"])).toBe(false);
    expect(canManageUserRoles(["users.manage", "roles.read"])).toBe(true);
  });
});
