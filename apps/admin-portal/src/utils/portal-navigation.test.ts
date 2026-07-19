import { describe, expect, it } from "vitest";

import { buildPortalNavigation } from "./portal-navigation";

function ids(permissions: readonly string[]): string[] {
  return buildPortalNavigation(permissions).map((item) => item.id);
}

describe("portal navigation", () => {
  it("keeps the dashboard entry visible but disabled", () => {
    const dashboard = buildPortalNavigation([]).find(
      (item) => item.id === "dashboard",
    );

    expect(dashboard).toMatchObject({ page: "dashboard", disabled: true });
  });

  it("always hides unavailable strategy, notification, and profile entries", () => {
    const navigationIds = ids([
      "customers.read",
      "tasks.read",
      "users.read",
      "roles.read",
      "departments.read",
      "authorization.evaluate",
    ]);

    expect(navigationIds).not.toContain("strategy");
    expect(navigationIds).not.toContain("notifications");
    expect(navigationIds).not.toContain("profile");
  });

  it("shows customer and task entries independently for any domain permission", () => {
    expect(ids(["customers.update"])).toContain("clients");
    expect(ids(["customers.update"])).not.toContain("tasks");
    expect(ids(["tasks.create"])).toContain("tasks");
    expect(ids(["tasks.create"])).not.toContain("clients");
  });

  it("filters permission children by their read or evaluation permission", () => {
    const permissions = buildPortalNavigation([
      "users.read",
      "departments.read",
      "authorization.evaluate",
    ]).find((item) => item.id === "permissions");

    expect(permissions?.children?.map((item) => item.id)).toEqual([
      "permissions-members",
      "permissions-departments",
      "permissions-authorization",
    ]);
  });

  it("does not expose a child when only its management permission exists", () => {
    expect(ids(["roles.manage", "permissions.read"])).not.toContain("permissions");
    expect(ids(["departments.manage"])).not.toContain("permissions");
  });

  it("hides permission management when no child is visible", () => {
    expect(ids([])).not.toContain("permissions");
  });
});
