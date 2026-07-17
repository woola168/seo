import { beforeEach, describe, expect, it, vi } from "vitest";

const { capabilities } = vi.hoisted(() => ({ capabilities: vi.fn() }));

vi.mock("./api", () => ({ api: { capabilities } }));

import {
  clearSessionCapabilities,
  getSessionCapabilities,
  refreshSessionCapabilities,
  sessionHasRole,
} from "./session-capabilities";

describe("session capabilities", () => {
  beforeEach(() => {
    capabilities.mockReset();
    clearSessionCapabilities();
  });

  it("shares and caches the capabilities request", async () => {
    capabilities.mockResolvedValue({
      permissions: ["geo.projects.read"],
      hasGlobalResourceAccess: false,
      customerIds: [],
      taskIds: [],
    });

    const [first, second] = await Promise.all([
      getSessionCapabilities(),
      getSessionCapabilities(),
    ]);
    const cached = await getSessionCapabilities();

    expect(capabilities).toHaveBeenCalledTimes(1);
    expect(first).toBe(second);
    expect(cached).toBe(first);
  });

  it("reloads capabilities when forced", async () => {
    capabilities
      .mockResolvedValueOnce({ permissions: ["geo.projects.read"] })
      .mockResolvedValueOnce({ permissions: ["geo.admin.access"] });

    await getSessionCapabilities();
    const refreshed = await getSessionCapabilities(true);

    expect(capabilities).toHaveBeenCalledTimes(2);
    expect(refreshed.permissions).toEqual(["geo.admin.access"]);
  });

  it("clears the cached value before refreshing", async () => {
    capabilities
      .mockResolvedValueOnce({ permissions: ["geo.projects.read"] })
      .mockResolvedValueOnce({ permissions: [] });

    await getSessionCapabilities();
    const refreshed = await refreshSessionCapabilities();

    expect(capabilities).toHaveBeenCalledTimes(2);
    expect(refreshed.permissions).toEqual([]);
  });

  it("detects whether a role change affects the current session", () => {
    const currentUser = { roleIds: ["role-admin", "role-editor"] };

    expect(sessionHasRole(currentUser, "role-admin")).toBe(true);
    expect(sessionHasRole(currentUser, "role-viewer")).toBe(false);
    expect(sessionHasRole(null, "role-admin")).toBe(false);
  });
});
