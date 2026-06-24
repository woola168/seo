import { describe, expect, it } from "vitest";
import { createMemoryHistory } from "vue-router";

import {
  createPortalRouter,
  getLoginRedirect,
  getRoutePage,
} from "./routes";

describe("portal router", () => {
  it("redirects protected pages to login and preserves the destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/permissions");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe("/permissions");
  });

  it("redirects authenticated users away from login", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/login");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("dashboard");
  });

  it("keeps account recovery routes public", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/reset-password?token=example");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("reset-password");
    expect(router.currentRoute.value.query.token).toBe("example");
  });

  it("protects the GEO analysis page and preserves its destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/geo-analysis");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe("/geo-analysis");
  });

  it("keeps the GEO analysis route under GEO navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/geo-analysis");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-analysis");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-analysis",
    );
  });

  it("protects the new employee page and preserves its destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/permissions/users/new");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/permissions/users/new",
    );
  });

  it("keeps the new employee page under permissions navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions/users/new");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("permission-user-new");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "permissions",
    );
  });

  it("does not reopen the invitation page after replacing it on cancel", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions");
    await router.push("/permissions/users/new");
    await router.replace("/permissions");
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(router.currentRoute.value.name).toBe("permissions");
  });

  it("protects the new role page and preserves its destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/permissions/roles/new");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/permissions/roles/new",
    );
  });

  it("keeps the new role page under permissions navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions/roles/new");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("permission-role-new");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "permissions",
    );
  });

  it("returns to the role tab without reopening the new role page", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions?tab=roles");
    await router.push("/permissions/roles/new");
    await router.replace({ name: "permissions", query: { tab: "roles" } });
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(router.currentRoute.value.name).toBe("permissions");
    expect(router.currentRoute.value.query.tab).toBe("roles");
  });
});

describe("route helpers", () => {
  it("maps route metadata to an available portal page", () => {
    expect(getRoutePage("permissions")).toBe("permissions");
    expect(getRoutePage("geo-analysis")).toBe("geo-analysis");
    expect(getRoutePage(undefined)).toBe("dashboard");
  });

  it("accepts only local post-login redirects", () => {
    expect(getLoginRedirect("/permissions")).toBe("/permissions");
    expect(getLoginRedirect("https://example.com")).toBe("/dashboard");
    expect(getLoginRedirect("//example.com")).toBe("/dashboard");
  });
});
