import {
  createRouter,
  type Router,
  type RouterHistory,
  type RouteRecordRaw,
} from "vue-router";

import type { PageId } from "../types";

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
      name: "permissions",
      component: () => import("../pages/PermissionsPage.vue"),
      meta: { requiresAuth: true, page: "permissions" },
    },
    {
      path: "/geo-analysis",
      redirect: "/geo-analysis/overview",
    },
    {
      path: "/geo-analysis/overview",
      name: "geo-analysis-overview",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-overview" },
    },
    {
      path: "/geo-analysis/projects",
      name: "geo-analysis-projects",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-projects" },
    },
    {
      path: "/geo-analysis/entities",
      name: "geo-analysis-entities",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-entities" },
    },
    {
      path: "/geo-analysis/topics-queries",
      name: "geo-analysis-queries",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-queries" },
    },
    {
      path: "/geo-analysis/platforms-schedules",
      name: "geo-analysis-schedules",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-schedules" },
    },
    {
      path: "/geo-analysis/run-jobs",
      name: "geo-analysis-jobs",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-jobs" },
    },
    {
      path: "/geo-analysis/reports",
      name: "geo-analysis-reports",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-reports" },
    },
    {
      path: "/geo-analysis/query-research",
      name: "geo-analysis-query-research",
      component: () => import("../pages/GeoTrackingPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis-query-research" },
    },
    {
      path: "/permissions/users/new",
      name: "permission-user-new",
      component: () => import("../pages/EmployeeInvitationPage.vue"),
      meta: { requiresAuth: true, page: "permissions" },
    },
    {
      path: "/permissions/roles/new",
      name: "permission-role-new",
      component: () => import("../pages/RoleCreationPage.vue"),
      meta: { requiresAuth: true, page: "permissions" },
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
): Router {
  const router = createRouter({
    history,
    routes: createRoutes(hasSession),
  });

  router.beforeEach((to) => {
    if (to.meta.requiresAuth && !hasSession()) {
      return {
        name: "login",
        query: { redirect: to.fullPath },
      };
    }

    if (to.name === "login" && hasSession()) {
      return { name: "dashboard" };
    }

    return true;
  });

  return router;
}

export function getRoutePage(page: unknown): PageId {
  if (page === "permissions") return "permissions";
  if (page === "geo-analysis-overview") return "geo-analysis-overview";
  if (page === "geo-analysis-projects") return "geo-analysis-projects";
  if (page === "geo-analysis-entities") return "geo-analysis-entities";
  if (page === "geo-analysis-queries") return "geo-analysis-queries";
  if (page === "geo-analysis-schedules") return "geo-analysis-schedules";
  if (page === "geo-analysis-jobs") return "geo-analysis-jobs";
  if (page === "geo-analysis-reports") return "geo-analysis-reports";
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
