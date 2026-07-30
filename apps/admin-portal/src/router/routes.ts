import {
  createRouter,
  type Router,
  type RouterHistory,
  type RouteRecordRaw,
} from "vue-router";

import type { PageId } from "../types";

type PermissionLoader = () => Promise<readonly string[]>;
const DEFAULT_AUTHENTICATED_PATH = "/geo/overview";
const routeTitles: Record<string, string> = {
  login: "登入",
  "forgot-password": "忘記密碼",
  "reset-password": "重設密碼",
  "accept-invitation": "設定帳號密碼",
  dashboard: "總覽",
  "permissions-members": "成員管理",
  "permissions-roles": "角色管理",
  "permissions-departments": "部門管理",
  "permissions-authorization": "授權判斷",
  "permission-user-new": "新增員工",
  "permission-role-new": "建立角色",
  "geo-overview": "GEO Overview",
  "geo-projects": "GEO Projects",
  "geo-project-new": "新增 GEO Project",
  "geo-project-edit": "編輯 GEO Project",
  "geo-query-research": "GEO Query Research",
  "geo-analysis-overview": "GEO Overview",
  "geo-analysis-projects": "GEO Projects",
  "geo-analysis-project-new": "新增 GEO Project",
  "geo-analysis-project-edit": "編輯 GEO Project",
  "geo-analysis-project-query-research": "GEO Query Research",
  "geo-analysis-entities": "GEO Entities",
  "geo-analysis-queries": "GEO Topics & Queries",
  "geo-analysis-schedules": "GEO Platforms & Schedules",
  "geo-analysis-jobs": "GEO Run Jobs",
  "geo-analysis-report-design": "GEO Report Design",
  "geo-analysis-flow-check": "GEO Flow Check",
  "geo-analysis-query-research": "GEO Query Research",
};

function createRoutes(hasSession: () => boolean): RouteRecordRaw[] {
  const defaultRoute = () =>
    hasSession() ? DEFAULT_AUTHENTICATED_PATH : "/login";

  const pageRoutes: RouteRecordRaw[] = [
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
        geoProjectArea: "standard",
      },
    },
    {
      path: "/geo/projects/new",
      name: "geo-project-new",
      component: () => import("../pages/GeoProjectEditPage.vue"),
      meta: {
        requiresAuth: true,
        requiredPermission: "geo.projects.create",
        page: "geo-projects",
        geoProjectArea: "standard",
      },
    },
    {
      path: "/geo/projects/:projectId/edit",
      name: "geo-project-edit",
      component: () => import("../pages/GeoProjectEditPage.vue"),
      meta: {
        requiresAuth: true,
        requiredPermissions: ["geo.projects.read", "geo.projects.update"],
        page: "geo-projects",
        geoProjectArea: "standard",
      },
    },
    {
      path: "/geo/projects/:projectId/query-research",
      name: "geo-query-research",
      component: () => import("../pages/GeoQueryResearchPage.vue"),
      meta: {
        requiresAuth: true,
        requiredPermissions: ["geo.projects.read", "geo.queries.manage"],
        page: "geo-projects",
        geoProjectArea: "standard",
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
      component: () => import("../pages/GeoStandardProjectsPage.vue"),
      meta: { requiresAuth: true, requiredPermissions: ["geo.admin.access", "geo.projects.read"], page: "geo-analysis-projects", geoProjectArea: "rd" },
    },
    {
      path: "/geo-analysis/projects/new",
      name: "geo-analysis-project-new",
      component: () => import("../pages/GeoProjectEditPage.vue"),
      meta: { requiresAuth: true, requiredPermissions: ["geo.admin.access", "geo.projects.create"], page: "geo-analysis-projects", geoProjectArea: "rd" },
    },
    {
      path: "/geo-analysis/projects/:projectId/edit",
      name: "geo-analysis-project-edit",
      component: () => import("../pages/GeoProjectEditPage.vue"),
      meta: { requiresAuth: true, requiredPermissions: ["geo.admin.access", "geo.projects.read", "geo.projects.update"], page: "geo-analysis-projects", geoProjectArea: "rd" },
    },
    {
      path: "/geo-analysis/projects/:projectId/query-research",
      name: "geo-analysis-project-query-research",
      component: () => import("../pages/GeoQueryResearchPage.vue"),
      meta: { requiresAuth: true, requiredPermissions: ["geo.admin.access", "geo.projects.read", "geo.queries.manage"], page: "geo-analysis-projects", geoProjectArea: "rd" },
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
  ];

  const publicRoutes = pageRoutes
    .filter((route) => route.meta?.public)
    .map(nestedRoute);
  const protectedRoutes = pageRoutes
    .filter((route) => !route.meta?.public)
    .map(nestedRoute);

  return [
    {
      path: "/",
      component: () => import("../layouts/PortalRootLayout.vue"),
      children: [
        { path: "", redirect: defaultRoute },
        ...publicRoutes,
        {
          path: "",
          component: () => import("../layouts/Layout.vue"),
          children: protectedRoutes,
        },
        { path: ":pathMatch(.*)*", redirect: defaultRoute },
      ],
    },
  ];
}

function nestedRoute(route: RouteRecordRaw): RouteRecordRaw {
  const name = typeof route.name === "string" ? route.name : "";
  return {
    ...route,
    path: route.path.replace(/^\//, ""),
    meta: {
      ...route.meta,
      ...(routeTitles[name] ? { title: routeTitles[name] } : {}),
    },
  };
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
      return { name: "geo-overview" };
    }

    const requiredPermissions = [
      ...(typeof to.meta.requiredPermission === "string"
        ? [to.meta.requiredPermission]
        : []),
      ...(Array.isArray(to.meta.requiredPermissions)
        ? to.meta.requiredPermissions.filter(
          (permission): permission is string => typeof permission === "string",
        )
        : []),
    ];
    if (requiredPermissions.length) {
      try {
        const permissions = await loadPermissions();
        if (requiredPermissions.some((permission) => !permissions.includes(permission))) {
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
  return "dashboard";
}

export function getLoginRedirect(redirect: unknown): string {
  return typeof redirect === "string" &&
    redirect.startsWith("/") &&
    !redirect.startsWith("//")
    ? redirect
    : DEFAULT_AUTHENTICATED_PATH;
}
