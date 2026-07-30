import { describe, expect, it, vi } from "vitest";

import type { Capabilities } from "../types";
import { createAccessAdministration, type PortalAccessApi } from "./access-administration";
import { createPortalNotifications } from "./portal-notifications";
import { createPortalSession, type PortalSessionApi } from "./portal-session";

function createSession() {
  const capabilities: Capabilities = {
    permissions: ["roles.read", "permissions.read"],
    hasGlobalResourceAccess: false,
    customerIds: [],
    taskIds: [],
  };
  const api: PortalSessionApi = {
    hasSession: () => true,
    login: vi.fn(async () => undefined),
    logout: vi.fn(async () => undefined),
    me: vi.fn(async () => ({
      id: "user-1",
      email: "admin@example.com",
      displayName: "Admin",
      status: "active",
      roleIds: [],
    })),
    capabilities: vi.fn(async () => capabilities),
    requestPasswordReset: vi.fn(async () => undefined),
    resetPassword: vi.fn(async () => undefined),
    acceptInvitation: vi.fn(async () => undefined),
  };
  return createPortalSession(api, createPortalNotifications());
}

describe("access administration", () => {
  it("loads each required resource once for a route view", async () => {
    const session = createSession();
    await session.restore();
    const api = {
      roles: vi.fn(async () => []),
      permissions: vi.fn(async () => ["roles.read"]),
    } as unknown as PortalAccessApi;
    const access = createAccessAdministration(
      api,
      session,
      createPortalNotifications(),
    );

    await access.ensureView("roles");
    await access.ensureView("roles");

    expect(api.roles).toHaveBeenCalledTimes(1);
    expect(api.permissions).toHaveBeenCalledTimes(1);
  });
});
