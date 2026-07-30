import { describe, expect, it, vi } from "vitest";

import type { Capabilities, SessionUser } from "../types";
import { createPortalNotifications } from "./portal-notifications";
import { createPortalSession, type PortalSessionApi } from "./portal-session";

const user: SessionUser = {
  id: "user-1",
  email: "admin@example.com",
  displayName: "Admin",
  status: "active",
  roleIds: ["role-1"],
};

const capabilities: Capabilities = {
  permissions: ["geo.projects.read"],
  hasGlobalResourceAccess: false,
  customerIds: [],
  taskIds: [],
};

function createApi(): PortalSessionApi {
  return {
    hasSession: vi.fn(() => true),
    login: vi.fn(async () => undefined),
    logout: vi.fn(async () => undefined),
    me: vi.fn(async () => user),
    capabilities: vi.fn(async () => capabilities),
    requestPasswordReset: vi.fn(async () => undefined),
    resetPassword: vi.fn(async () => undefined),
    acceptInvitation: vi.fn(async () => undefined),
  };
}

describe("portal session", () => {
  it("restores the user and reuses the capability request", async () => {
    const api = createApi();
    const session = createPortalSession(api, createPortalNotifications());

    expect(await session.restore()).toBe(true);
    await expect(session.loadPermissionNames()).resolves.toEqual([
      "geo.projects.read",
    ]);

    expect(session.user.value).toEqual(user);
    expect(session.capabilities.value).toEqual(capabilities);
    expect(api.capabilities).toHaveBeenCalledTimes(1);
  });

  it("clears state when session restoration fails", async () => {
    const api = createApi();
    vi.mocked(api.me).mockRejectedValue(new Error("expired"));
    const session = createPortalSession(api, createPortalNotifications());

    expect(await session.restore()).toBe(false);

    expect(session.user.value).toBeNull();
    expect(session.capabilities.value).toBeNull();
    expect(session.error.value).toBe("登入狀態已失效，請重新登入。");
  });

  it("reloads capabilities when explicitly refreshed", async () => {
    const api = createApi();
    const session = createPortalSession(api, createPortalNotifications());
    await session.restore();
    const refreshed = { ...capabilities, permissions: ["roles.manage"] };
    vi.mocked(api.capabilities).mockResolvedValue(refreshed);

    await session.refreshCapabilities();

    expect(session.capabilities.value).toEqual(refreshed);
    expect(api.capabilities).toHaveBeenCalledTimes(2);
  });
});
