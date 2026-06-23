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
      name: "geo-analysis",
      component: () => import("../pages/GeoAnalysisPage.vue"),
      meta: { requiresAuth: true, page: "geo-analysis" },
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
  if (page === "geo-analysis") return "geo-analysis";
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
