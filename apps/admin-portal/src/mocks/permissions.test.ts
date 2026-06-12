import { describe, expect, it } from "vitest";

import { mergeMemberMetadata } from "./permissions";
import type { Role, UserAccess } from "../types";

describe("mergeMemberMetadata", () => {
  it("keeps API fields and adds temporary metadata", () => {
    const users: UserAccess[] = [
      {
        id: "user-1",
        email: "admin@example.com",
        displayName: "SEO Admin",
        status: "active",
        roleIds: ["role-1"],
        customerIds: ["customer-1"],
        taskIds: ["task-1"],
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

    const [member] = mergeMemberMetadata(users, roles);

    expect(member).toMatchObject({
      email: "admin@example.com",
      roleNames: ["admin"],
      customerIds: ["customer-1"],
      department: "決策層",
      source: "workspace",
    });
  });
});
