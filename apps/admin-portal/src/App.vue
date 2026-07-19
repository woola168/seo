<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppToast from "./components/ui/AppToast.vue";
import Layout from "./layouts/Layout.vue";
import AccountRecoveryPage from "./pages/AccountRecoveryPage.vue";
import DashboardPage from "./pages/DashboardPage.vue";
import EmployeeInvitationPage from "./pages/EmployeeInvitationPage.vue";
import GeoDashboardReportDesignPage from "./pages/GeoDashboardReportDesignPage.vue";
import GeoEntitiesPage from "./pages/GeoEntitiesPage.vue";
import GeoFlowCheckPage from "./pages/GeoFlowCheckPage.vue";
import GeoPlatformsSchedulesPage from "./pages/GeoPlatformsSchedulesPage.vue";
import GeoProjectsPage from "./pages/GeoProjectsPage.vue";
import GeoRunJobsPage from "./pages/GeoRunJobsPage.vue";
import GeoStandardProjectsPage from "./pages/GeoStandardProjectsPage.vue";
import GeoProjectEditPage from "./pages/GeoProjectEditPage.vue";
import GeoQueryResearchPage from "./pages/GeoQueryResearchPage.vue";
import GeoTrackingPage from "./pages/GeoTrackingPage.vue";
import GeoTopicsQueriesPage from "./pages/GeoTopicsQueriesPage.vue";
import LoginPage from "./pages/LoginPage.vue";
import PermissionsPage from "./pages/PermissionsPage.vue";
import RoleCreationPage from "./pages/RoleCreationPage.vue";
import SessionLoadingPage from "./pages/SessionLoadingPage.vue";
import { getLoginRedirect, getRoutePage } from "./router/routes";
import { ApiError, api } from "./services/api";
import {
  clearSessionCapabilities,
  getSessionCapabilities,
  refreshSessionCapabilities,
  sessionHasRole,
} from "./services/session-capabilities";
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
import { buildGeoNavigation } from "./utils/geo-navigation";
import { filterAssignablePermissions } from "./utils/internal-permissions";
import { hasPermission } from "./utils/permissions";
import { removeRoleById } from "./utils/role-state";
import {
  shouldRestoreSession,
  type RecoveryMode,
} from "./utils/session-bootstrap";

const GeoOverviewPage = defineAsyncComponent(
  () => import("./pages/GeoOverviewPage.vue"),
);
const GeoStandardOverviewPage = defineAsyncComponent(
  () => import("./pages/GeoStandardOverviewPage.vue"),
);

const route = useRoute();
const router = useRouter();
const user = ref<SessionUser | null>(null);
const capabilities = ref<Capabilities | null>(null);
const roles = ref<Role[]>([]);
const users = ref<UserAccess[]>([]);
const permissions = ref<string[]>([]);
const customers = ref<CustomerSummary[]>([]);
const tasks = ref<TaskSummary[]>([]);
const departments = ref<Department[]>([]);
const decision = ref<AuthorizationDecision | null>(null);
const sidebarCollapsed = ref(false);
const globalSearch = ref("");
const loading = ref(false);
const loginError = ref("");
const toast = ref<ToastMessage | null>(null);
const activePage = computed<PageId>(() => getRoutePage(route.meta.page));
const currentTitle = computed(() => pageTitle());
const recoveryMode = computed<RecoveryMode>(() =>
  route.meta.recoveryMode === "request" ||
  route.meta.recoveryMode === "reset" ||
  route.meta.recoveryMode === "accept"
    ? route.meta.recoveryMode
    : null,
);
const recoveryToken = computed(() =>
  typeof route.query.token === "string" ? route.query.token : "",
);
const restoringSession = ref(
  shouldRestoreSession(recoveryMode.value, api.hasSession()),
);
let toastTimer: ReturnType<typeof setTimeout> | undefined;

type PortalDataKey =
  | "roles"
  | "users"
  | "permissions"
  | "departments"
  | "customers"
  | "tasks";
type PermissionTab = "members" | "roles" | "departments" | "evaluate";
const loadedData = ref<Set<PortalDataKey>>(new Set());
const pendingData = new Map<PortalDataKey, Promise<void>>();
const activePermissionTab = computed<PermissionTab>(() => {
  if (activePage.value === "permissions-roles") return "roles";
  if (activePage.value === "permissions-departments") return "departments";
  if (activePage.value === "permissions-authorization") return "evaluate";
  return "members";
});
const geoPageTitles: Partial<Record<PageId, string>> = {
  "geo-overview": "GEO Overview",
  "geo-projects": "GEO Projects",
  "geo-analysis-overview": "GEO Overview",
  "geo-analysis-projects": "GEO Projects",
  "geo-analysis-entities": "GEO Entities",
  "geo-analysis-queries": "GEO Topics & Queries",
  "geo-analysis-schedules": "GEO Platforms & Schedules",
  "geo-analysis-jobs": "GEO Run Jobs",
  "geo-analysis-report-design": "GEO Report Design",
  "geo-analysis-flow-check": "GEO Flow Check",
  "geo-analysis-query-research": "GEO Query Research",
  "geo-tracking": "GEO 跑題實驗室",
};
const isGeoTrackingPage = computed(
  () =>
    activePage.value === "geo-analysis-query-research" ||
    activePage.value === "geo-tracking",
);

function pageTitle(): string {
  if (route.name === "permission-user-new") return "新增員工";
  if (route.name === "permission-role-new") return "建立角色";
  const geoTitle = geoPageTitles[activePage.value];
  if (geoTitle) return geoTitle;
  if (activePage.value === "permissions-members") return "成員管理";
  if (activePage.value === "permissions-roles") return "角色管理";
  if (activePage.value === "permissions-departments") return "部門管理";
  if (activePage.value === "permissions-authorization") return "授權判斷";
  return "總覽";
}

const navigation = computed<NavigationItem[]>(() => [
  { id: "dashboard", label: "總覽", icon: "grid", page: "dashboard" },
  {
    id: "clients",
    label: "客戶",
    icon: "users",
    group: "專案管理",
    disabled: true,
  },
  {
    id: "tasks",
    label: "任務",
    icon: "briefcase",
    group: "專案管理",
    badge: "9",
    disabled: true,
  },
  ...buildGeoNavigation(capabilities.value?.permissions ?? []),
  {
    id: "strategy",
    label: "策略分析",
    icon: "sparkles",
    group: "分析工具",
    disabled: true,
  },
  {
    id: "notifications",
    label: "通知",
    icon: "bell",
    group: "系統",
    badge: "2",
    disabled: true,
  },
  {
    id: "profile",
    label: "個人設定",
    icon: "user",
    group: "系統",
    disabled: true,
  },
  {
    id: "permissions",
    label: "權限管理",
    icon: "shield",
    group: "系統",
    children: [
      {
        id: "permissions-members",
        label: "成員管理",
        icon: "users",
        page: "permissions-members",
      },
      {
        id: "permissions-roles",
        label: "角色管理",
        icon: "shield",
        page: "permissions-roles",
      },
      {
        id: "permissions-departments",
        label: "部門管理",
        icon: "briefcase",
        page: "permissions-departments",
      },
      {
        id: "permissions-authorization",
        label: "授權判斷",
        icon: "check-circle",
        page: "permissions-authorization",
      },
    ],
  },
  {
    id: "settings",
    label: "系統設定",
    icon: "settings",
    group: "系統",
    disabled: true,
  },
]);

onMounted(async () => {
  if (restoringSession.value) await restoreSession();
});

watch(
  () => route.meta.requiresAuth,
  (requiresAuth) => {
    if (requiresAuth && !user.value && api.hasSession()) {
      void restoreSession();
    }
  },
);

watch(
  [activePage, () => route.name, activePermissionTab, user, capabilities],
  () => {
    void loadCurrentViewData();
  },
  { immediate: true },
);

async function restoreSession(): Promise<void> {
  restoringSession.value = true;
  try {
    await loadSession();
  } finally {
    restoringSession.value = false;
  }
}

function openPasswordResetRequest(): void {
  void router.push({ name: "forgot-password" });
}

async function returnToLogin(): Promise<void> {
  loginError.value = "";
  await router.replace({ name: "login" });
}

async function submitRecovery(value: string): Promise<void> {
  loginError.value = "";
  await run(
    async () => {
      if (recoveryMode.value === "request") {
        await api.requestPasswordReset(value);
        notify("若帳號存在，密碼重設通知已建立並等待寄送。", "success");
      } else if (recoveryMode.value === "reset") {
        await api.resetPassword(recoveryToken.value, value);
        notify("密碼已重設，請重新登入。", "success");
      } else if (recoveryMode.value === "accept") {
        await api.acceptInvitation(recoveryToken.value, value);
        notify("帳號已啟用，請登入。", "success");
      }
      await returnToLogin();
    },
    (message) => {
      loginError.value = message;
    },
  );
}

async function login(email: string, password: string): Promise<void> {
  loginError.value = "";
  const redirect = getLoginRedirect(route.query.redirect);
  await run(
    async () => {
      clearSessionCapabilities();
      await api.login(email, password);
      await loadSessionData();
      await router.replace(redirect);
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
    await router.replace({ name: "login" });
  });
}

async function loadSession(): Promise<void> {
  const redirect = route.fullPath;
  await run(loadSessionData, () => {
    clearSession();
    loginError.value = "登入狀態已失效，請重新登入。";
  });
  if (!user.value) {
    await router.replace({
      name: "login",
      query: { redirect },
    });
  }
}

async function loadSessionData(): Promise<void> {
  const [currentUser, currentCapabilities] = await Promise.all([
    api.me(),
    getSessionCapabilities(),
  ]);
  user.value = currentUser;
  capabilities.value = currentCapabilities;
}

async function loadCurrentViewData(force = false): Promise<void> {
  await run(() => ensureCurrentViewData(force));
}

async function ensureCurrentViewData(force = false): Promise<void> {
  if (!user.value || !capabilities.value) return;
  if (route.name === "permission-user-new") {
    await loadPortalData(["roles", "departments", "customers", "tasks"], force);
    return;
  }
  if (route.name === "permission-role-new") {
    await loadPortalData(["permissions"], force);
    return;
  }
  if (isPermissionPage(activePage.value)) {
    await ensurePermissionTabData(activePermissionTab.value, force);
  }
}

function isPermissionPage(page: PageId): boolean {
  return (
    page === "permissions-members" ||
    page === "permissions-roles" ||
    page === "permissions-departments" ||
    page === "permissions-authorization"
  );
}

async function ensurePermissionTabData(
  tab: PermissionTab,
  force = false,
): Promise<void> {
  if (tab === "roles") {
    await loadPortalData(["roles", "permissions"], force);
    return;
  }
  if (tab === "departments") {
    await loadPortalData(["departments"], force);
    return;
  }
  if (tab === "evaluate") {
    await loadPortalData(["users", "permissions", "customers", "tasks"], force);
    return;
  }
  const keys: PortalDataKey[] = ["users", "roles", "departments"];
  if (hasCapability("access-grants.manage")) {
    keys.push("customers", "tasks");
  }
  if (hasCapability("customers.create") || hasCapability("tasks.create")) {
    keys.push("customers");
  }
  await loadPortalData(keys, force);
}

async function loadPortalData(
  keys: PortalDataKey[],
  force = false,
): Promise<void> {
  await Promise.all(keys.map((key) => loadPortalDataItem(key, force)));
}

async function loadPortalDataItem(
  key: PortalDataKey,
  force = false,
): Promise<void> {
  if (!force && loadedData.value.has(key)) return;
  const pending = pendingData.get(key);
  if (!force && pending) {
    await pending;
    return;
  }
  const request = fetchPortalDataItem(key)
    .then(() => markDataLoaded(key))
    .finally(() => pendingData.delete(key));
  pendingData.set(key, request);
  await request;
}

async function fetchPortalDataItem(key: PortalDataKey): Promise<void> {
  if (key === "roles") {
    if (!hasCapability("roles.read")) {
      roles.value = [];
      return;
    }
    roles.value = await api.roles();
    return;
  }
  if (key === "users") {
    if (!hasCapability("users.read")) {
      users.value = [];
      return;
    }
    users.value = await api.users();
    return;
  }
  if (key === "permissions") {
    if (!capabilities.value) return;
    if (!hasCapability("permissions.read")) {
      permissions.value = filterAssignablePermissions(
        capabilities.value.permissions,
      );
      return;
    }
    permissions.value = await api.permissions();
    return;
  }
  if (key === "departments") {
    if (!hasCapability("departments.read")) {
      departments.value = [];
      return;
    }
    departments.value = await api.departments().catch(() => []);
    return;
  }
  if (key === "customers") {
    if (!hasCapability("customers.read")) {
      customers.value = [];
      return;
    }
    customers.value = await api.customers().then((value) => value.items).catch(() => []);
    return;
  }
  if (!hasCapability("tasks.read")) {
    tasks.value = [];
    return;
  }
  tasks.value = await api.tasks().then((value) => value.items).catch(() => []);
}

function markDataLoaded(key: PortalDataKey): void {
  loadedData.value = new Set([...loadedData.value, key]);
}

function forgetLoadedData(keys: PortalDataKey[]): void {
  loadedData.value = new Set(
    [...loadedData.value].filter((key) => !keys.includes(key)),
  );
}

function hasCapability(permission: string): boolean {
  return Boolean(
    capabilities.value && hasPermission(capabilities.value.permissions, permission),
  );
}

async function reloadSessionCapabilities(): Promise<void> {
  capabilities.value = null;
  capabilities.value = await refreshSessionCapabilities();
}

async function refresh(): Promise<void> {
  await run(async () => {
    if (!user.value) return;
    const currentCapabilities = await getSessionCapabilities(true);
    capabilities.value = currentCapabilities;
    forgetLoadedData([
      "roles",
      "users",
      "permissions",
      "departments",
      "customers",
      "tasks",
    ]);
    await ensureCurrentViewData(true);
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
  const affectsCurrentSession = sessionHasRole(user.value, roleId);
  await run(async () => {
    const updated = await api.updateRolePermissions(
      roleId,
      selectedPermissions,
    );
    roles.value = roles.value.map((role) =>
      role.id === updated.id ? updated : role,
    );
    if (affectsCurrentSession) {
      await reloadSessionCapabilities();
    }
    notify("角色權限已更新", "success");
  });
}

async function deleteRole(roleId: string): Promise<void> {
  await run(async () => {
    await api.deleteRole(roleId);
    roles.value = removeRoleById(roles.value, roleId);
    notify("角色已刪除", "success");
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
    notify("部門已刪除", "success");
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
    if (user.value?.id === updated.id) {
      user.value = updated;
      await reloadSessionCapabilities();
    }
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
  clearSessionCapabilities();
  user.value = null;
  capabilities.value = null;
  roles.value = [];
  users.value = [];
  permissions.value = [];
  customers.value = [];
  tasks.value = [];
  departments.value = [];
  decision.value = null;
  globalSearch.value = "";
  loadedData.value = new Set();
  pendingData.clear();
}

function navigate(page: PageId): void {
  void router.push({ name: page });
}

function openEmployeeInvitation(): void {
  void router.push({ name: "permission-user-new" });
}

function closeEmployeeInvitation(): void {
  void router.replace({ name: "permissions-members" });
}

function openRoleCreation(): void {
  void router.push({ name: "permission-role-new" });
}

function closeRoleCreation(): void {
  void router.replace({ name: "permissions-roles" });
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

  <SessionLoadingPage v-else-if="restoringSession" />

  <GeoTrackingPage
    v-else-if="route.name === 'geo-tracking' && (!user || !capabilities)"
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
    :current-title="currentTitle"
    :navigation="navigation"
    :collapsed="sidebarCollapsed"
    :search="globalSearch"
    @navigate="navigate"
    @logout="logout"
    @refresh="refresh"
    @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
    @update:search="globalSearch = $event"
    @unavailable="unavailable"
  >
    <EmployeeInvitationPage
      v-if="route.name === 'permission-user-new'"
      :capabilities="capabilities"
      :roles="roles"
      :departments="departments"
      :customers="customers"
      :tasks="tasks"
      :loading="loading"
      @back="closeEmployeeInvitation"
      @submit="inviteUser"
    />
    <RoleCreationPage
      v-else-if="route.name === 'permission-role-new'"
      :capabilities="capabilities"
      :permissions="permissions"
      :loading="loading"
      @back="closeRoleCreation"
      @submit="createRole"
    />
    <DashboardPage
      v-else-if="activePage === 'dashboard'"
      :capabilities="capabilities"
      :search="globalSearch"
      @unavailable="unavailable"
    />
    <GeoOverviewPage v-else-if="activePage === 'geo-analysis-overview'" />
    <GeoProjectsPage v-else-if="activePage === 'geo-analysis-projects'" />
    <GeoStandardOverviewPage v-else-if="activePage === 'geo-overview'" />
    <GeoProjectEditPage
      v-else-if="route.name === 'geo-project-new' || route.name === 'geo-project-edit'"
      :permissions="capabilities.permissions"
      @notify="notify"
    />
    <GeoQueryResearchPage
      v-else-if="route.name === 'geo-query-research'"
      :permissions="capabilities.permissions"
      @notify="notify"
    />
    <GeoStandardProjectsPage
      v-else-if="activePage === 'geo-projects'"
      :permissions="capabilities.permissions"
      @notify="notify"
    />
    <GeoEntitiesPage v-else-if="activePage === 'geo-analysis-entities'" />
    <GeoTopicsQueriesPage v-else-if="activePage === 'geo-analysis-queries'" />
    <GeoPlatformsSchedulesPage v-else-if="activePage === 'geo-analysis-schedules'" />
    <GeoRunJobsPage v-else-if="activePage === 'geo-analysis-jobs'" />
    <GeoDashboardReportDesignPage
      v-else-if="activePage === 'geo-analysis-report-design'"
    />
    <GeoFlowCheckPage v-else-if="activePage === 'geo-analysis-flow-check'" />
    <GeoTrackingPage v-else-if="isGeoTrackingPage" />
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
      :active-page="activePage"
      @unavailable="unavailable"
      @open-role-creation="openRoleCreation"
      @update-role="updateRole"
      @delete-role="deleteRole"
      @update-user-roles="updateUserRoles"
      @update-customers="updateCustomerGrants"
      @update-tasks="updateTaskGrants"
      @open-invitation="openEmployeeInvitation"
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
