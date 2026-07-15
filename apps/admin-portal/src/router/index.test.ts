import { beforeAll, describe, expect, it, vi } from "vitest";
import { createMemoryHistory } from "vue-router";

import {
  createPortalRouter,
  getLoginRedirect,
  getRoutePage,
} from "./routes";

beforeAll(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
  });
});

describe("portal router", () => {
  it("redirects protected pages to login and preserves the destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/permissions/members");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/permissions/members",
    );
  });

  it("protects all permission child pages", async () => {
    const pages = [
      "/permissions/members",
      "/permissions/roles",
      "/permissions/departments",
      "/permissions/authorization",
    ];

    for (const page of pages) {
      const router = createPortalRouter(createMemoryHistory(), () => false);

      await router.push(page);
      await router.isReady();

      expect(router.currentRoute.value.name).toBe("login");
      expect(router.currentRoute.value.query.redirect).toBe(page);
    }
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

    await router.push("/geo-analysis/overview");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe(
      "/geo-analysis/overview",
    );
  });

  it("keeps the GEO analysis route under GEO navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/geo-analysis");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-analysis-overview");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-analysis-overview",
    );
    expect(router.hasRoute("geo-analysis-reports")).toBe(false);
  });

  it("keeps GEO query research under GEO navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/geo-analysis/query-research");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-analysis-query-research");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-analysis-query-research",
    );
  });

  it("protects GEO flow check and keeps it under GEO navigation", async () => {
    const unauthenticated = createPortalRouter(createMemoryHistory(), () => false);

    await unauthenticated.push("/geo-analysis/flow-check");
    await unauthenticated.isReady();

    expect(unauthenticated.currentRoute.value.name).toBe("login");
    expect(unauthenticated.currentRoute.value.query.redirect).toBe(
      "/geo-analysis/flow-check",
    );

    const authenticated = createPortalRouter(createMemoryHistory(), () => true);

    await authenticated.push("/geo-analysis/flow-check");
    await authenticated.isReady();

    expect(authenticated.currentRoute.value.name).toBe("geo-analysis-flow-check");
    expect(getRoutePage(authenticated.currentRoute.value.meta.page)).toBe(
      "geo-analysis-flow-check",
    );
  });

  it("protects GEO report design and keeps it under GEO navigation", async () => {
    const unauthenticated = createPortalRouter(createMemoryHistory(), () => false);

    await unauthenticated.push("/geo-analysis/report-design");
    await unauthenticated.isReady();

    expect(unauthenticated.currentRoute.value.name).toBe("login");
    expect(unauthenticated.currentRoute.value.query.redirect).toBe(
      "/geo-analysis/report-design",
    );

    const authenticated = createPortalRouter(createMemoryHistory(), () => true);

    await authenticated.push("/geo-analysis/report-design");
    await authenticated.isReady();

    expect(authenticated.currentRoute.value.name).toBe(
      "geo-analysis-report-design",
    );
    expect(getRoutePage(authenticated.currentRoute.value.meta.page)).toBe(
      "geo-analysis-report-design",
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

  it("redirects the permissions root to member management", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("permissions-members");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "permissions-members",
    );
  });

  it("keeps permission child pages under permissions navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);
    const pages = [
      ["/permissions/members", "permissions-members"],
      ["/permissions/roles", "permissions-roles"],
      ["/permissions/departments", "permissions-departments"],
      ["/permissions/authorization", "permissions-authorization"],
    ] as const;

    for (const [path, page] of pages) {
      await router.push(path);
      await router.isReady();

      expect(router.currentRoute.value.name).toBe(page);
      expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(page);
    }
  });

  it("keeps the new employee page under permissions navigation", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions/users/new");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("permission-user-new");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "permissions-members",
    );
  });

  it("does not reopen the invitation page after replacing it on cancel", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions/members");
    await router.push("/permissions/users/new");
    await router.replace("/permissions/members");
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(router.currentRoute.value.name).toBe("permissions-members");
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
      "permissions-roles",
    );
  });

  it("returns to role management without reopening the new role page", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/permissions/roles");
    await router.push("/permissions/roles/new");
    await router.replace({ name: "permissions-roles" });
    router.back();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(router.currentRoute.value.name).toBe("permissions-roles");
  });
});

describe("route helpers", () => {
  it("maps route metadata to an available portal page", () => {
    expect(getRoutePage("permissions-members")).toBe("permissions-members");
    expect(getRoutePage("permissions-roles")).toBe("permissions-roles");
    expect(getRoutePage("permissions-departments")).toBe(
      "permissions-departments",
    );
    expect(getRoutePage("permissions-authorization")).toBe(
      "permissions-authorization",
    );
    expect(getRoutePage("geo-analysis-overview")).toBe(
      "geo-analysis-overview",
    );
    expect(getRoutePage("geo-analysis-query-research")).toBe(
      "geo-analysis-query-research",
    );
    expect(getRoutePage("geo-analysis-flow-check")).toBe(
      "geo-analysis-flow-check",
    );
    expect(getRoutePage("geo-analysis-report-design")).toBe(
      "geo-analysis-report-design",
    );
    expect(getRoutePage("geo-analysis-reports")).toBe("dashboard");
    expect(getRoutePage(undefined)).toBe("dashboard");
  });

  it("accepts only local post-login redirects", () => {
    expect(getLoginRedirect("/permissions/members")).toBe(
      "/permissions/members",
    );
    expect(getLoginRedirect("https://example.com")).toBe("/dashboard");
    expect(getLoginRedirect("//example.com")).toBe("/dashboard");
  });
});
