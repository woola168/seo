import { describe, expect, it } from "vitest";

import {
  buildPermissionGroups,
  permissionGroupState,
  togglePermissionGroup,
} from "./permission-groups";

describe("permission groups", () => {
  it("expands a group into its available permission keys", () => {
    const groups = buildPermissionGroups([
      "tasks.read",
      "tasks.create",
      "tasks.update",
      "tasks.delete",
    ]);

    expect(groups).toHaveLength(1);
    expect(groups[0]?.label).toBe("任務管理");
    expect(groups[0]?.permissions).toEqual([
      "tasks.read",
      "tasks.create",
      "tasks.update",
      "tasks.delete",
    ]);
  });

  it("selects every permission when a group is not fully selected", () => {
    const selected = togglePermissionGroup(
      ["tasks.read"],
      ["tasks.read", "tasks.create", "tasks.update", "tasks.delete"],
    );

    expect(selected).toEqual([
      "tasks.read",
      "tasks.create",
      "tasks.update",
      "tasks.delete",
    ]);
  });

  it("removes only the selected group when it is fully selected", () => {
    const selected = togglePermissionGroup(
      ["users.read", "tasks.read", "tasks.create"],
      ["tasks.read", "tasks.create"],
    );

    expect(selected).toEqual(["users.read"]);
  });

  it("reports partial state without changing the selected permissions", () => {
    const selected = ["tasks.read", "tasks.update"];

    expect(
      permissionGroupState(selected, [
        "tasks.read",
        "tasks.create",
        "tasks.update",
        "tasks.delete",
      ]),
    ).toBe("partial");
    expect(selected).toEqual(["tasks.read", "tasks.update"]);
  });

  it("keeps unknown permissions in an additional group", () => {
    const groups = buildPermissionGroups([
      "users.read",
      "reports.read",
      "reports.export",
    ]);

    expect(groups.at(-1)).toEqual({
      id: "other",
      label: "其他權限",
      description: "尚未分類的新功能權限。",
      permissions: ["reports.read", "reports.export"],
    });
  });
});
