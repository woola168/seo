import type { App, InjectionKey } from "vue";
import { inject, ref } from "vue";

import type { PortalAccessApi } from "./access-administration";
import { createAccessAdministration } from "./access-administration";
import { createPortalNotifications } from "./portal-notifications";
import type { PortalSessionApi } from "./portal-session";
import { createPortalSession } from "./portal-session";

export type PortalApi = PortalSessionApi & PortalAccessApi;

export function createPortalContext(api: PortalApi) {
  const notifications = createPortalNotifications();
  const shell = {
    sidebarCollapsed: ref(false),
    search: ref(""),
  };
  let clearSessionState = () => {
    shell.search.value = "";
  };
  const session = createPortalSession(api, notifications, () => clearSessionState());
  const access = createAccessAdministration(api, session, notifications);
  clearSessionState = () => {
    access.clear();
    shell.search.value = "";
  };
  return { session, notifications, access, shell };
}

export type PortalContext = ReturnType<typeof createPortalContext>;

const portalContextKey: InjectionKey<PortalContext> = Symbol("portal-context");

export function providePortalContext(app: App, context: PortalContext): void {
  app.provide(portalContextKey, context);
}

export function usePortalContext(): PortalContext {
  const context = inject(portalContextKey);
  if (!context) throw new Error("Portal context 尚未安裝。");
  return context;
}

export function usePortalSession() {
  return usePortalContext().session;
}

export function usePortalNotifications() {
  return usePortalContext().notifications;
}

export function useAccessAdministration() {
  return usePortalContext().access;
}

export function usePortalShellState() {
  return usePortalContext().shell;
}
