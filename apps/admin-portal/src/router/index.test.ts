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
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read"],
    );

    await router.push("/login");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-overview");
  });

  it("uses GEO Overview as the authenticated default route", async () => {
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read"],
    );

    await router.push("/");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-overview");
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
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.admin.access"],
    );

    await router.push("/geo-analysis");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-analysis-overview");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-analysis-overview",
    );
    expect(router.hasRoute("geo-analysis-reports")).toBe(false);
  });

  it("keeps GEO query research under GEO navigation", async () => {
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.admin.access"],
    );

    await router.push("/geo-analysis/query-research");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("geo-analysis-query-research");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-analysis-query-research",
    );
    expect(router.currentRoute.value.meta.title).toBe("GEO Query Research");
    expect(router.currentRoute.value.matched).toHaveLength(3);
  });

  it("removes the public GEO tracking route", async () => {
    const unauthenticated = createPortalRouter(createMemoryHistory(), () => false);
    await unauthenticated.push("/geo-tracking");
    await unauthenticated.isReady();
    expect(unauthenticated.currentRoute.value.name).toBe("login");

    const authenticated = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read"],
    );
    await authenticated.push("/geo-tracking");
    await authenticated.isReady();
    expect(authenticated.currentRoute.value.name).toBe("geo-overview");
    expect(authenticated.hasRoute("geo-tracking")).toBe(false);
  });

  it("protects GEO flow check and keeps it under GEO navigation", async () => {
    const unauthenticated = createPortalRouter(createMemoryHistory(), () => false);

    await unauthenticated.push("/geo-analysis/flow-check");
    await unauthenticated.isReady();

    expect(unauthenticated.currentRoute.value.name).toBe("login");
    expect(unauthenticated.currentRoute.value.query.redirect).toBe(
      "/geo-analysis/flow-check",
    );

    const authenticated = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.admin.access"],
    );

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

    const authenticated = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.admin.access"],
    );

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

  it("keeps standard GEO on separate pages for project readers", async () => {
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read"],
    );

    await router.push("/geo/overview");
    await router.isReady();
    expect(router.currentRoute.value.name).toBe("geo-overview");
    expect(getRoutePage(router.currentRoute.value.meta.page)).toBe(
      "geo-overview",
    );

    const rdComponent = router
      .getRoutes()
      .find((item) => item.name === "geo-analysis-overview")?.components
      ?.default;
    const standardComponent = router
      .getRoutes()
      .find((item) => item.name === "geo-overview")?.components?.default;
    expect(standardComponent).not.toBe(rdComponent);
    expect(router.hasRoute("geo-query-research")).toBe(true);
  });

  it("protects standard GEO write routes with their matching capabilities", async () => {
    const createRouter = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.create"],
    );
    await createRouter.push("/geo/projects/new");
    await createRouter.isReady();
    expect(createRouter.currentRoute.value.name).toBe("geo-project-new");

    const updateRouter = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read", "geo.projects.update"],
    );
    await updateRouter.push("/geo/projects/project-1/edit");
    await updateRouter.isReady();
    expect(updateRouter.currentRoute.value.name).toBe("geo-project-edit");

    const researchRouter = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read", "geo.queries.manage"],
    );
    await researchRouter.push("/geo/projects/project-1/query-research");
    await researchRouter.isReady();
    expect(researchRouter.currentRoute.value.name).toBe("geo-query-research");
    expect(getRoutePage(researchRouter.currentRoute.value.meta.page)).toBe("geo-projects");

    const missingRead = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.update", "geo.queries.manage"],
    );
    await missingRead.push("/geo/projects/project-1/edit");
    await missingRead.isReady();
    expect(missingRead.currentRoute.value.name).toBe("dashboard");
    await missingRead.push("/geo/projects/project-1/query-research");
    expect(missingRead.currentRoute.value.name).toBe("dashboard");
  });

  it("keeps the shared Project flow inside GEO Analysis RD and requires both permissions", async () => {
    const routes = [
      ["/geo-analysis/projects/new", "geo-analysis-project-new"],
      ["/geo-analysis/projects/project-1/edit", "geo-analysis-project-edit"],
      ["/geo-analysis/projects/project-1/query-research", "geo-analysis-project-query-research"],
    ] as const;
    const router = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => [
        "geo.admin.access",
        "geo.projects.read",
        "geo.projects.create",
        "geo.projects.update",
        "geo.queries.manage",
      ],
    );

    for (const [path, routeName] of routes) {
      await router.push(path);
      await router.isReady();
      expect(router.currentRoute.value.name).toBe(routeName);
      expect(getRoutePage(router.currentRoute.value.meta.page)).toBe("geo-analysis-projects");
      expect(router.currentRoute.value.meta.geoProjectArea).toBe("rd");
    }

    const missingAdmin = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.create"],
    );
    await missingAdmin.push("/geo-analysis/projects/new");
    await missingAdmin.isReady();
    expect(missingAdmin.currentRoute.value.name).toBe("dashboard");

    const missingCreate = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.admin.access"],
    );
    await missingCreate.push("/geo-analysis/projects/new");
    await missingCreate.isReady();
    expect(missingCreate.currentRoute.value.name).toBe("dashboard");

    const missingRead = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => [
        "geo.admin.access",
        "geo.projects.update",
        "geo.queries.manage",
      ],
    );
    await missingRead.push("/geo-analysis/projects/project-1/edit");
    await missingRead.isReady();
    expect(missingRead.currentRoute.value.name).toBe("dashboard");
    await missingRead.push("/geo-analysis/projects/project-1/query-research");
    expect(missingRead.currentRoute.value.name).toBe("dashboard");
  });

  it("redirects users without the required GEO capability", async () => {
    const standardRouter = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => [],
    );
    await standardRouter.push("/geo/projects");
    await standardRouter.isReady();
    expect(standardRouter.currentRoute.value.name).toBe("dashboard");

    const rdRouter = createPortalRouter(
      createMemoryHistory(),
      () => true,
      async () => ["geo.projects.read"],
    );
    await rdRouter.push("/geo-analysis/projects");
    await rdRouter.isReady();
    expect(rdRouter.currentRoute.value.name).toBe("dashboard");
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
    expect(getRoutePage("geo-overview")).toBe("geo-overview");
    expect(getRoutePage("geo-projects")).toBe("geo-projects");
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
    expect(getLoginRedirect("https://example.com")).toBe("/geo/overview");
    expect(getLoginRedirect("//example.com")).toBe("/geo/overview");
  });
});
