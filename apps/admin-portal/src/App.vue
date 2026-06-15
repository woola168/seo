<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import AppToast from "./components/ui/AppToast.vue";
import Layout from "./layouts/Layout.vue";
import AccountRecoveryPage from "./pages/AccountRecoveryPage.vue";
import DashboardPage from "./pages/DashboardPage.vue";
import LoginPage from "./pages/LoginPage.vue";
import PermissionsPage from "./pages/PermissionsPage.vue";
import { ApiError, api } from "./services/api";
import type {
  AuthorizationDecision,
  Capabilities,
  CreateInvitationInput,
  CustomerSummary,
  Department,
  NavigationItem,
  PageId,
  Role,
  SessionUser,
  TaskSummary,
  ToastMessage,
  ToastTone,
  UserAccess,
} from "./types";
import { hasPermission } from "./utils/permissions";

const user = ref<SessionUser | null>(null);
const capabilities = ref<Capabilities | null>(null);
const roles = ref<Role[]>([]);
const users = ref<UserAccess[]>([]);
const permissions = ref<string[]>([]);
const customers = ref<CustomerSummary[]>([]);
const tasks = ref<TaskSummary[]>([]);
const departments = ref<Department[]>([]);
const decision = ref<AuthorizationDecision | null>(null);
const activePage = ref<PageId>("dashboard");
const sidebarCollapsed = ref(false);
const globalSearch = ref("");
const loading = ref(false);
const loginError = ref("");
const toast = ref<ToastMessage | null>(null);
const recoveryMode = ref<"request" | "reset" | "accept" | null>(
  window.location.pathname.endsWith("/reset-password")
    ? "reset"
    : window.location.pathname.endsWith("/accept-invitation")
      ? "accept"
      : null,
);
const recoveryToken = ref(
  new URLSearchParams(window.location.search).get("token") ?? "",
);
let toastTimer: ReturnType<typeof setTimeout> | undefined;

const navigation = computed<NavigationItem[]>(() => [
  { id: "dashboard", label: "總覽", icon: "grid", page: "dashboard" },
  { id: "clients", label: "客戶", icon: "users", disabled: true },
  { id: "tasks", label: "任務", icon: "briefcase", badge: "9", disabled: true },
  { id: "war-room", label: "戰情室", icon: "activity", disabled: true },
  { id: "strategy", label: "策略分析", icon: "sparkles", disabled: true },
  { id: "notifications", label: "通知", icon: "bell", badge: "2", disabled: true },
  { id: "profile", label: "個人設定", icon: "user", disabled: true },
  {
    id: "permissions",
    label: "權限管理",
    icon: "shield",
    page: "permissions",
  },
  { id: "settings", label: "系統設定", icon: "settings", disabled: true },
]);

onMounted(async () => {
  if (!recoveryMode.value && api.hasSession()) await loadSession();
});

function openPasswordResetRequest(): void {
  recoveryMode.value = "request";
  recoveryToken.value = "";
  window.history.pushState({}, "", "/forgot-password");
}

function returnToLogin(): void {
  recoveryMode.value = null;
  recoveryToken.value = "";
  loginError.value = "";
  window.history.replaceState({}, "", "/");
}

async function submitRecovery(value: string): Promise<void> {
  loginError.value = "";
  await run(
    async () => {
      if (recoveryMode.value === "request") {
        await api.requestPasswordReset(value);
        notify(
          "若帳號存在，密碼重設通知已建立並等待寄送。",
          "success",
        );
      } else if (recoveryMode.value === "reset") {
        await api.resetPassword(recoveryToken.value, value);
        notify("密碼已重設，請重新登入。", "success");
      } else if (recoveryMode.value === "accept") {
        await api.acceptInvitation(recoveryToken.value, value);
        notify("帳號已啟用，請登入。", "success");
      }
      returnToLogin();
    },
    (message) => {
      loginError.value = message;
    },
  );
}

async function login(email: string, password: string): Promise<void> {
  loginError.value = "";
  await run(
    async () => {
      await api.login(email, password);
      await loadSessionData();
      notify("登入成功", "success");
    },
    (message) => {
      loginError.value = message;
    },
  );
}

async function logout(): Promise<void> {
  await run(async () => {
    await api.logout();
    clearSession();
  });
}

async function loadSession(): Promise<void> {
  await run(
    loadSessionData,
    () => {
      clearSession();
      loginError.value = "登入狀態已失效，請重新登入。";
    },
  );
}

async function loadSessionData(): Promise<void> {
  const [currentUser, currentCapabilities] = await Promise.all([
    api.me(),
    api.capabilities(),
  ]);
  await loadAccessibleData(currentCapabilities);
  user.value = currentUser;
  capabilities.value = currentCapabilities;
}

async function loadAccessibleData(
  currentCapabilities = capabilities.value,
): Promise<void> {
  if (!currentCapabilities) return;
  const available = currentCapabilities.permissions;
  const calls: Promise<void>[] = [];

  if (hasPermission(available, "roles.read")) {
    calls.push(api.roles().then((value) => void (roles.value = value)));
  } else {
    roles.value = [];
  }
  if (hasPermission(available, "users.read")) {
    calls.push(api.users().then((value) => void (users.value = value)));
  } else {
    users.value = [];
  }
  if (hasPermission(available, "permissions.read")) {
    calls.push(
      api.permissions().then((value) => void (permissions.value = value)),
    );
  } else {
    permissions.value = [...available];
  }
  if (hasPermission(available, "departments.read")) {
    calls.push(
      api
        .departments()
        .then((value) => void (departments.value = value))
        .catch(() => void (departments.value = [])),
    );
  } else {
    departments.value = [];
  }
  if (hasPermission(available, "customers.read")) {
    calls.push(
      api
        .customers()
        .then((value) => void (customers.value = value.items))
        .catch(() => void (customers.value = [])),
    );
  } else {
    customers.value = [];
  }
  if (hasPermission(available, "tasks.read")) {
    calls.push(
      api
        .tasks()
        .then((value) => void (tasks.value = value.items))
        .catch(() => void (tasks.value = [])),
    );
  } else {
    tasks.value = [];
  }
  await Promise.all(calls);
}

async function refresh(): Promise<void> {
  await run(async () => {
    if (!user.value) return;
    const currentCapabilities = await api.capabilities();
    capabilities.value = currentCapabilities;
    await loadAccessibleData(currentCapabilities);
    notify("資料已重新整理", "success");
  });
}

async function createRole(
  name: string,
  selectedPermissions: string[],
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    const createdRole = await api.createRole(name, selectedPermissions);
    roles.value = [...roles.value, createdRole];
    onSuccess();
    notify("角色已建立", "success");
  });
}

async function updateRole(
  roleId: string,
  selectedPermissions: string[],
): Promise<void> {
  await run(async () => {
    const updated = await api.updateRolePermissions(
      roleId,
      selectedPermissions,
    );
    roles.value = roles.value.map((role) =>
      role.id === updated.id ? updated : role,
    );
    notify("角色權限已更新", "success");
  });
}

async function updateUserRoles(
  userId: string,
  roleIds: string[],
): Promise<void> {
  await updateUser(
    () => api.updateUserRoles(userId, roleIds),
    "使用者角色已更新",
  );
}

async function updateCustomerGrants(
  userId: string,
  customerIds: string[],
): Promise<void> {
  await updateUser(
    () => api.updateCustomerGrants(userId, customerIds),
    "客戶存取範圍已更新",
  );
}

async function updateTaskGrants(
  userId: string,
  taskIds: string[],
): Promise<void> {
  await updateUser(
    () => api.updateTaskGrants(userId, taskIds),
    "任務存取範圍已更新",
  );
}

async function inviteUser(
  input: CreateInvitationInput,
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    await api.inviteUser(input);
    users.value = await api.users();
    onSuccess();
    notify("員工邀請已建立", "success");
  });
}

async function createDepartment(
  name: string,
  description: string,
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    const created = await api.createDepartment(name, description);
    departments.value = [...departments.value, created];
    onSuccess();
    notify("部門已新增", "success");
  });
}

async function updateDepartment(
  departmentId: string,
  name: string,
  description: string,
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    const updated = await api.updateDepartment(departmentId, name, description);
    departments.value = departments.value.map((department) =>
      department.id === updated.id ? updated : department,
    );
    onSuccess();
    notify("部門已更新", "success");
  });
}

async function deleteDepartment(departmentId: string): Promise<void> {
  await run(async () => {
    await api.deleteDepartment(departmentId);
    departments.value = departments.value.filter(
      (department) => department.id !== departmentId,
    );
    notify("部門已封存", "success");
  });
}

async function createCustomer(
  name: string,
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    const created = await api.createCustomer(name);
    customers.value = [...customers.value, created];
    onSuccess();
    notify("客戶已新增，可立即設定權限", "success");
  });
}

async function createTask(
  customerId: string,
  name: string,
  onSuccess: () => void,
): Promise<void> {
  await run(async () => {
    const created = await api.createTask(customerId, name);
    tasks.value = [...tasks.value, created];
    onSuccess();
    notify("任務已新增，可立即設定權限", "success");
  });
}

async function updateUser(
  action: () => Promise<UserAccess>,
  successMessage: string,
): Promise<void> {
  await run(async () => {
    const updated = await action();
    users.value = users.value.map((item) =>
      item.id === updated.id ? updated : item,
    );
    notify(successMessage, "success");
  });
}

async function evaluate(
  userId: string,
  permission: string,
  resource:
    | { type: "customer"; id: string }
    | { type: "task"; id: string; customerId: string },
): Promise<void> {
  await run(async () => {
    decision.value = await api.evaluate(userId, permission, resource);
  });
}

async function run(
  action: () => Promise<void>,
  onError?: (message: string) => void,
): Promise<void> {
  loading.value = true;
  try {
    await action();
  } catch (caught) {
    const message =
      caught instanceof ApiError ? caught.message : "發生未預期的錯誤。";
    if (onError) onError(message);
    else notify(message, "error");
  } finally {
    loading.value = false;
  }
}

function clearSession(): void {
  user.value = null;
  capabilities.value = null;
  roles.value = [];
  users.value = [];
  permissions.value = [];
  customers.value = [];
  tasks.value = [];
  departments.value = [];
  decision.value = null;
  activePage.value = "dashboard";
  globalSearch.value = "";
}

function notify(message: string, tone: ToastTone = "info"): void {
  if (toastTimer) clearTimeout(toastTimer);
  toast.value = { id: Date.now(), message, tone };
  toastTimer = setTimeout(() => {
    toast.value = null;
  }, 3000);
}

function unavailable(label: string): void {
  notify(`${label}尚未開放，待 API 完成後提供。`, "warning");
}
</script>

<template>
  <AccountRecoveryPage
    v-if="recoveryMode"
    :mode="recoveryMode"
    :loading="loading"
    :error="loginError"
    @submit="submitRecovery"
    @back="returnToLogin"
  />

  <LoginPage
    v-else-if="!user || !capabilities"
    :loading="loading"
    :error="loginError"
    @login="login"
    @forgot="openPasswordResetRequest"
    @unavailable="unavailable"
  />

  <Layout
    v-else
    :user="user"
    :active-page="activePage"
    :navigation="navigation"
    :collapsed="sidebarCollapsed"
    :search="globalSearch"
    @navigate="activePage = $event"
    @logout="logout"
    @refresh="refresh"
    @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
    @update:search="globalSearch = $event"
    @unavailable="unavailable"
  >
    <DashboardPage
      v-if="activePage === 'dashboard'"
      :capabilities="capabilities"
      :search="globalSearch"
      @unavailable="unavailable"
    />
    <PermissionsPage
      v-else
      :current-user="user"
      :capabilities="capabilities"
      :users="users"
      :roles="roles"
      :permissions="permissions"
      :customers="customers"
      :tasks="tasks"
      :departments="departments"
      :decision="decision"
      :loading="loading"
      @unavailable="unavailable"
      @create-role="createRole"
      @update-role="updateRole"
      @update-user-roles="updateUserRoles"
      @update-customers="updateCustomerGrants"
      @update-tasks="updateTaskGrants"
      @invite-user="inviteUser"
      @create-department="createDepartment"
      @update-department="updateDepartment"
      @delete-department="deleteDepartment"
      @create-customer="createCustomer"
      @create-task="createTask"
      @evaluate="evaluate"
    />
  </Layout>

  <AppToast v-if="toast" :toast="toast" @close="toast = null" />
</template>
