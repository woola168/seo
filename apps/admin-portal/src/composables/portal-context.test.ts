import { describe, expect, it } from "vitest";

import type { PortalApi } from "./portal-context";
import { createPortalContext } from "./portal-context";

describe("portal context", () => {
  it("clears session-scoped access and shell state together", () => {
    const context = createPortalContext({ hasSession: () => false } as PortalApi);
    context.access.roles.value = [
      { id: "role-1", name: "管理員", permissions: [] },
    ];
    context.shell.search.value = "敏感資料";

    context.session.clear();

    expect(context.access.roles.value).toEqual([]);
    expect(context.shell.search.value).toBe("");
  });
});
