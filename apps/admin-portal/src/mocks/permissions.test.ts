import { describe, expect, it } from "vitest";

import { mergeMemberMetadata } from "./permissions";
import type { Role, UserAccess } from "../types";

describe("mergeMemberMetadata", () => {
  it("maps lifecycle metadata and department names from API fields", () => {
    const users: UserAccess[] = [
      {
        id: "user-1",
        email: "admin@example.com",
        displayName: "SEO Admin",
        status: "active",
        roleIds: ["role-1"],
        customerIds: ["customer-1"],
        taskIds: ["task-1"],
        departmentId: "department-1",
        authProvider: "password",
        lastLoginAt: "2026-06-12T02:30:00Z",
      },
    ];
    const roles: Role[] = [
      {
        id: "role-1",
        name: "admin",
        permissions: ["users.read"],
        isSystem: true,
        hasGlobalResourceAccess: true,
      },
    ];

    const [member] = mergeMemberMetadata(
      users,
      roles,
      new Map([["department-1", "工程部"]]),
    );

    expect(member).toMatchObject({
      email: "admin@example.com",
      roleNames: ["admin"],
      customerIds: ["customer-1"],
      department: "工程部",
      source: "workspace",
    });
    expect(member?.lastLogin).not.toBeNull();
  });
});
