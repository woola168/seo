import {
  createRouter,
  type Router,
  type RouterHistory,
  type RouteRecordRaw,
} from "vue-router";

import type { PageId } from "../types";

type PermissionLoader = () => Promise<readonly string[]>;

function createRoutes(hasSession: () => boolean): RouteRecordRaw[] {
  const defaultRoute = () => (hasSession() ? "/dashboard" : "/login");

  return [
    {
      path: "/",
      redirect: defaultRoute,
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../pages/LoginPage.vue"),
      meta: { public: true },
    },
    {
      path: "/forgot-password",
      name: "forgot-password",
      component: () => import("../pages/AccountRecoveryPage.vue"),
      meta: { public: true, recoveryMode: "request" },
    },
    {
      path: "/reset-password",
      name: "reset-password",
      component: () => import("../pages/AccountRecoveryPage.vue"),
      meta: { public: true, recoveryMode: "reset" },
    },
    {
      path: "/accept-invitation",
      name: "accept-invitation",
      component: () => import("../pages/AccountRecoveryPage.vue"),
      meta: { public: true, recoveryMode: "accept" },
    },
    {
      path: "/dashboard",
      name: "dashboard",
      component: () => import("../pages/DashboardPage.vue"),
      meta: { requiresAuth: true, page: "dashboard" },
    },
    {
      path: "/geo-tracking",
      name: "geo-tracking",
      component: () => import("../pages/GeoTrackingPage.vue"),
      meta: { public: true, page: "geo-tracking" },
    },
    {
      path: "/permissions",
      redirect: "/permissions/members",
    },
    {
      path: "/permissions/members",
      name: "permissions-members",
      component: () => import("../pages/PermissionsPage.vue"),
      meta: { requiresAuth: true, page: "permissions-members" },
    },
    {
      path: "/permissions/roles",
      name: "permissions-roles",
      component: () => import("../pages/PermissionsPage.vue"),
      meta: { requiresAuth: true, page: "permissions-roles" },
    },
    {
      path: "/permissions/departments",
      name: "permissions-departments",
      component: () => import("../pages/PermissionsPage.vue"),
      meta: { requiresAuth: true, page: "permissions-departments" },
    },
    {
      path: "/permissions/authorization",
      name: "permissions-authorization",
      component: () => import("../pages/PermissionsPage.vue"),
      meta: { requiresAuth: true, page: "permissions-authorization" },
    },
    {
      path: "/geo",
      redirect: "/geo/overview",
    },
    {
      path: "/geo/overview",
      name: "geo-overview",
      component: () => import("../pages/GeoStandardOverviewPage.vue"),
      meta: {
        requiresAuth: true,
        requiredPermission: "geo.projects.read",
        page: "geo-overview",
      },
    },
    {
      path: "/geo/projects",
      name: "geo-projects",
      component: () => import("../pages/GeoStandardProjectsPage.vue"),
      meta: {
        requiresAuth: true,
        requiredPermission: "geo.projects.read",
        page: "geo-projects",
      },
    },
    {
      path: "/geo-analysis",
      redirect: "/geo-analysis/overview",
    },
    {
      path: "/geo-analysis/overview",
      name: "geo-analysis-overview",
      component: () => import("../pages/GeoOverviewPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-overview" },
    },
    {
      path: "/geo-analysis/projects",
      name: "geo-analysis-projects",
      component: () => import("../pages/GeoProjectsPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-projects" },
    },
    {
      path: "/geo-analysis/entities",
      name: "geo-analysis-entities",
      component: () => import("../pages/GeoEntitiesPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-entities" },
    },
    {
      path: "/geo-analysis/topics-queries",
      name: "geo-analysis-queries",
      component: () => import("../pages/GeoTopicsQueriesPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-queries" },
    },
    {
      path: "/geo-analysis/platforms-schedules",
      name: "geo-analysis-schedules",
      component: () => import("../pages/GeoPlatformsSchedulesPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-schedules" },
    },
    {
      path: "/geo-analysis/run-jobs",
      name: "geo-analysis-jobs",
      component: () => import("../pages/GeoRunJobsPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-jobs" },
    },
    {
      path: "/geo-analysis/report-design",
      name: "geo-analysis-report-design",
      component: () => import("../pages/GeoDashboardReportDesignPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-report-design" },
    },
    {
      path: "/geo-analysis/flow-check",
      name: "geo-analysis-flow-check",
      component: () => import("../pages/GeoFlowCheckPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-flow-check" },
    },
    {
      path: "/geo-analysis/query-research",
      name: "geo-analysis-query-research",
      component: () => import("../pages/GeoTrackingPage.vue"),
      meta: { requiresAuth: true, requiredPermission: "geo.admin.access", page: "geo-analysis-query-research" },
    },
    {
      path: "/permissions/users/new",
      name: "permission-user-new",
      component: () => import("../pages/EmployeeInvitationPage.vue"),
      meta: { requiresAuth: true, page: "permissions-members" },
    },
    {
      path: "/permissions/roles/new",
      name: "permission-role-new",
      component: () => import("../pages/RoleCreationPage.vue"),
      meta: { requiresAuth: true, page: "permissions-roles" },
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: defaultRoute,
    },
  ];
}

export function createPortalRouter(
  history: RouterHistory,
  hasSession: () => boolean,
  loadPermissions: PermissionLoader = async () => [],
): Router {
  const router = createRouter({
    history,
    routes: createRoutes(hasSession),
  });

  router.beforeEach(async (to) => {
    if (to.meta.requiresAuth && !hasSession()) {
      return {
        name: "login",
        query: { redirect: to.fullPath },
      };
    }

    if (to.name === "login" && hasSession()) {
      return { name: "dashboard" };
    }

    const requiredPermission = to.meta.requiredPermission;
    if (typeof requiredPermission === "string") {
      try {
        const permissions = await loadPermissions();
        if (!permissions.includes(requiredPermission)) {
          return { name: "dashboard" };
        }
      } catch {
        return hasSession()
          ? { name: "dashboard" }
          : { name: "login", query: { redirect: to.fullPath } };
      }
    }

    return true;
  });

  return router;
}

export function getRoutePage(page: unknown): PageId {
  if (page === "permissions-members") return "permissions-members";
  if (page === "permissions-roles") return "permissions-roles";
  if (page === "permissions-departments") return "permissions-departments";
  if (page === "permissions-authorization") {
    return "permissions-authorization";
  }
  if (page === "geo-overview") return "geo-overview";
  if (page === "geo-projects") return "geo-projects";
  if (page === "geo-analysis-overview") return "geo-analysis-overview";
  if (page === "geo-analysis-projects") return "geo-analysis-projects";
  if (page === "geo-analysis-entities") return "geo-analysis-entities";
  if (page === "geo-analysis-queries") return "geo-analysis-queries";
  if (page === "geo-analysis-schedules") return "geo-analysis-schedules";
  if (page === "geo-analysis-jobs") return "geo-analysis-jobs";
  if (page === "geo-analysis-report-design") {
    return "geo-analysis-report-design";
  }
  if (page === "geo-analysis-flow-check") return "geo-analysis-flow-check";
  if (page === "geo-analysis-query-research") {
    return "geo-analysis-query-research";
  }
  if (page === "geo-tracking") return "geo-tracking";
  return "dashboard";
}

export function getLoginRedirect(redirect: unknown): string {
  return typeof redirect === "string" &&
    redirect.startsWith("/") &&
    !redirect.startsWith("//")
    ? redirect
    : "/dashboard";
}
