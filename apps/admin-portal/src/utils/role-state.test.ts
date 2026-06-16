import { describe, expect, it } from "vitest";

import type { Role } from "../types";
import { removeRoleById } from "./role-state";

const roles: Role[] = [
  {
    id: "role-1",
    name: "Admin",
    permissions: ["roles.manage"],
    isSystem: false,
    hasGlobalResourceAccess: false,
  },
  {
    id: "role-2",
    name: "Viewer",
    permissions: ["roles.read"],
    isSystem: false,
    hasGlobalResourceAccess: false,
  },
];

describe("role state", () => {
  it("removes a role after a successful delete response", () => {
    expect(removeRoleById(roles, "role-1").map((role) => role.id)).toEqual([
      "role-2",
    ]);
  });

  it("keeps roles unchanged when the deleted id is absent", () => {
    expect(removeRoleById(roles, "missing")).toEqual(roles);
  });
});
