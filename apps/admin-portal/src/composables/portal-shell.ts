import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { NavigationItem, PageId } from "../types";
import { getRoutePage } from "../router/routes";
import { buildPortalNavigation } from "../utils/portal-navigation";
import {
  useAccessAdministration,
  usePortalNotifications,
  usePortalSession,
  usePortalShellState,
} from "./portal-context";

export function usePortalShell() {
  const route = useRoute();
  const router = useRouter();
  const session = usePortalSession();
  const notifications = usePortalNotifications();
  const access = useAccessAdministration();
  const shell = usePortalShellState();
  const activePage = computed<PageId>(() => getRoutePage(route.meta.page));
  const currentTitle = computed(() =>
    typeof route.meta.title === "string" ? route.meta.title : "總覽",
  );
  const navigation = computed<NavigationItem[]>(() =>
    buildPortalNavigation(session.capabilities.value?.permissions ?? []),
  );

  onMounted(async () => {
    if (session.user.value || !session.hasSession()) return;
    if (!(await session.restore())) await router.replace({ name: "login" });
  });

  async function logout(): Promise<void> {
    if (await session.logout()) await router.replace({ name: "login" });
  }

  async function refresh(): Promise<void> {
    try {
      await session.refreshCapabilities();
      await access.refreshActiveView();
      notifications.notify("資料已重新整理", "success");
    } catch (caught) {
      notifications.notify(
        caught instanceof Error ? caught.message : "系統發生未預期錯誤。",
        "error",
      );
    }
  }

  function navigate(page: PageId): void {
    void router.push({ name: page });
  }

  function unavailable(label: string): void {
    notifications.notify(`${label}尚未開放，待 API 完成後提供。`, "warning");
  }

  return {
    ...shell,
    user: session.user,
    capabilities: session.capabilities,
    restoring: session.restoring,
    activePage,
    currentTitle,
    navigation,
    navigate,
    logout,
    refresh,
    unavailable,
  };
}
