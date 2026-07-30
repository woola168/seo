import "vue-router";

import type { PageId } from "../types";

declare module "vue-router" {
  interface RouteMeta {
    public?: boolean;
    requiresAuth?: boolean;
    requiredPermission?: string;
    requiredPermissions?: string[];
    page?: PageId;
    title?: string;
    recoveryMode?: "request" | "reset" | "accept";
    geoProjectArea?: "standard" | "rd";
  }
}
