import { ref } from "vue";

import type { Capabilities, SessionUser } from "../types";
import { updateRememberedLoginEmail } from "../utils/remembered-login-email";
import type { RecoveryMode } from "../utils/session-bootstrap";
import type { PortalNotifications } from "./portal-notifications";

export interface PortalSessionApi {
  hasSession(): boolean;
  login(email: string, password: string): Promise<void>;
  logout(): Promise<void>;
  me(): Promise<SessionUser>;
  capabilities(): Promise<Capabilities>;
  requestPasswordReset(email: string): Promise<void>;
  resetPassword(token: string, newPassword: string): Promise<void>;
  acceptInvitation(token: string, newPassword: string): Promise<void>;
}

export function createPortalSession(
  api: PortalSessionApi,
  notifications: PortalNotifications,
) {
  const user = ref<SessionUser | null>(null);
  const capabilities = ref<Capabilities | null>(null);
  const loading = ref(false);
  const restoring = ref(api.hasSession());
  const error = ref("");
  let pendingCapabilities: Promise<Capabilities> | null = null;

  function hasSession(): boolean {
    return api.hasSession();
  }

  async function loadCapabilities(force = false): Promise<Capabilities> {
    if (!force && capabilities.value) return capabilities.value;
    if (!force && pendingCapabilities) return pendingCapabilities;
    const request = api.capabilities().then((value) => {
      if (pendingCapabilities === request) capabilities.value = value;
      return value;
    });
    pendingCapabilities = request;
    void request.then(
      () => {
        if (pendingCapabilities === request) pendingCapabilities = null;
      },
      () => {
        if (pendingCapabilities === request) pendingCapabilities = null;
      },
    );
    return request;
  }

  async function loadPermissionNames(): Promise<readonly string[]> {
    return (await loadCapabilities()).permissions;
  }

  async function loadSessionData(): Promise<void> {
    const [currentUser] = await Promise.all([api.me(), loadCapabilities()]);
    user.value = currentUser;
  }

  function clear(): void {
    user.value = null;
    capabilities.value = null;
    pendingCapabilities = null;
  }

  async function restore(): Promise<boolean> {
    restoring.value = true;
    error.value = "";
    try {
      await loadSessionData();
      return true;
    } catch {
      clear();
      error.value = "登入狀態已失效，請重新登入。";
      return false;
    } finally {
      restoring.value = false;
    }
  }

  async function login(
    email: string,
    password: string,
    rememberEmail: boolean,
  ): Promise<boolean> {
    error.value = "";
    loading.value = true;
    try {
      clear();
      await api.login(email, password);
      await loadSessionData();
      updateRememberedLoginEmail(email, rememberEmail);
      notifications.notify("登入成功", "success");
      return true;
    } catch (caught) {
      error.value = errorMessage(caught);
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<boolean> {
    loading.value = true;
    try {
      await api.logout();
      clear();
      return true;
    } catch (caught) {
      notifications.notify(errorMessage(caught), "error");
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function recover(
    mode: Exclude<RecoveryMode, null>,
    token: string,
    value: string,
  ): Promise<boolean> {
    error.value = "";
    loading.value = true;
    try {
      if (mode === "request") {
        await api.requestPasswordReset(value);
        notifications.notify("若帳號存在，密碼重設通知已建立並等待寄送。", "success");
      } else if (mode === "reset") {
        await api.resetPassword(token, value);
        notifications.notify("密碼已重設，請重新登入。", "success");
      } else {
        await api.acceptInvitation(token, value);
        notifications.notify("帳號已啟用，請登入。", "success");
      }
      return true;
    } catch (caught) {
      error.value = errorMessage(caught);
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function refreshCapabilities(): Promise<Capabilities> {
    pendingCapabilities = null;
    return loadCapabilities(true);
  }

  function updateCurrentUser(updated: SessionUser): void {
    if (user.value?.id === updated.id) user.value = updated;
  }

  return {
    user,
    capabilities,
    loading,
    restoring,
    error,
    hasSession,
    loadPermissionNames,
    restore,
    login,
    logout,
    recover,
    refreshCapabilities,
    updateCurrentUser,
    clear,
  };
}

function errorMessage(caught: unknown): string {
  return caught instanceof Error ? caught.message : "系統發生未預期錯誤。";
}

export type PortalSession = ReturnType<typeof createPortalSession>;
