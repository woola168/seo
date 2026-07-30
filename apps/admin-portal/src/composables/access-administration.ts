import { ref } from "vue";

import type {
  AuthorizationDecision,
  CreateInvitationInput,
  CustomerSummary,
  Department,
  PageResponse,
  Role,
  TaskSummary,
  UserAccess,
  UserInvitation,
} from "../types";
import { filterAssignablePermissions } from "../utils/internal-permissions";
import { hasPermission } from "../utils/permissions";
import { removeRoleById } from "../utils/role-state";
import type { PortalNotifications } from "./portal-notifications";
import type { PortalSession } from "./portal-session";

export interface PortalAccessApi {
  roles(): Promise<Role[]>;
  users(): Promise<UserAccess[]>;
  permissions(): Promise<string[]>;
  departments(): Promise<Department[]>;
  customers(): Promise<PageResponse<CustomerSummary>>;
  tasks(): Promise<PageResponse<TaskSummary>>;
  createRole(name: string, permissions: string[]): Promise<Role>;
  updateRolePermissions(roleId: string, permissions: string[]): Promise<Role>;
  deleteRole(roleId: string): Promise<void>;
  updateUserRoles(userId: string, roleIds: string[]): Promise<UserAccess>;
  updateCustomerGrants(userId: string, customerIds: string[]): Promise<UserAccess>;
  updateTaskGrants(userId: string, taskIds: string[]): Promise<UserAccess>;
  inviteUser(input: CreateInvitationInput): Promise<UserInvitation>;
  createDepartment(name: string, description: string): Promise<Department>;
  updateDepartment(id: string, name: string, description: string): Promise<Department>;
  deleteDepartment(id: string): Promise<void>;
  createCustomer(name: string): Promise<CustomerSummary>;
  createTask(customerId: string, name: string): Promise<TaskSummary>;
  evaluate(
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ): Promise<AuthorizationDecision>;
}

export type AccessView =
  | "members"
  | "roles"
  | "departments"
  | "authorization"
  | "invitation"
  | "role-creation";

type DataKey =
  | "roles"
  | "users"
  | "permissions"
  | "departments"
  | "customers"
  | "tasks";

export function createAccessAdministration(
  api: PortalAccessApi,
  session: PortalSession,
  notifications: PortalNotifications,
) {
  const roles = ref<Role[]>([]);
  const users = ref<UserAccess[]>([]);
  const permissions = ref<string[]>([]);
  const departments = ref<Department[]>([]);
  const customers = ref<CustomerSummary[]>([]);
  const tasks = ref<TaskSummary[]>([]);
  const decision = ref<AuthorizationDecision | null>(null);
  const loading = ref(false);
  const loaded = new Set<DataKey>();
  const pending = new Map<DataKey, Promise<void>>();
  let activeView: AccessView | null = null;
  let sessionGeneration = 0;

  function can(permission: string): boolean {
    return Boolean(
      session.capabilities.value &&
        hasPermission(session.capabilities.value.permissions, permission),
    );
  }

  async function ensureView(view: AccessView, force = false): Promise<void> {
    activeView = view;
    const keys = requiredData(view);
    await run(async () => {
      await Promise.all(keys.map((key) => load(key, force)));
    });
  }

  function requiredData(view: AccessView): DataKey[] {
    if (view === "roles") return ["roles", "permissions"];
    if (view === "departments") return ["departments"];
    if (view === "authorization") {
      return ["users", "permissions", "customers", "tasks"];
    }
    if (view === "invitation") {
      return ["roles", "departments", "customers", "tasks"];
    }
    if (view === "role-creation") return ["permissions"];
    const keys: DataKey[] = ["users", "roles", "departments"];
    if (can("access-grants.manage")) keys.push("customers", "tasks");
    if (can("customers.create") || can("tasks.create")) keys.push("customers");
    return [...new Set(keys)];
  }

  async function load(key: DataKey, force: boolean): Promise<void> {
    if (!force && loaded.has(key)) return;
    const existing = pending.get(key);
    if (!force && existing) return existing;
    const generation = sessionGeneration;
    const request = fetchData(key, generation)
      .then(() => {
        if (generation === sessionGeneration) loaded.add(key);
      })
      .finally(() => {
        if (pending.get(key) === request) pending.delete(key);
      });
    pending.set(key, request);
    await request;
  }

  async function fetchData(key: DataKey, generation: number): Promise<void> {
    if (key === "roles") {
      const value = can("roles.read") ? await api.roles() : [];
      if (generation === sessionGeneration) roles.value = value;
    } else if (key === "users") {
      const value = can("users.read") ? await api.users() : [];
      if (generation === sessionGeneration) users.value = value;
    } else if (key === "permissions") {
      const value = can("permissions.read")
        ? await api.permissions()
        : filterAssignablePermissions(session.capabilities.value?.permissions ?? []);
      if (generation === sessionGeneration) permissions.value = value;
    } else if (key === "departments") {
      const value = can("departments.read")
        ? await api.departments().catch(() => [])
        : [];
      if (generation === sessionGeneration) departments.value = value;
    } else if (key === "customers") {
      const value = can("customers.read")
        ? await api.customers().then((value) => value.items).catch(() => [])
        : [];
      if (generation === sessionGeneration) customers.value = value;
    } else {
      const value = can("tasks.read")
        ? await api.tasks().then((value) => value.items).catch(() => [])
        : [];
      if (generation === sessionGeneration) tasks.value = value;
    }
  }

  function clear(): void {
    sessionGeneration += 1;
    roles.value = [];
    users.value = [];
    permissions.value = [];
    departments.value = [];
    customers.value = [];
    tasks.value = [];
    decision.value = null;
    loading.value = false;
    loaded.clear();
    pending.clear();
    activeView = null;
  }

  async function refreshActiveView(): Promise<void> {
    loaded.clear();
    if (activeView) await ensureView(activeView, true);
  }

  async function createRole(name: string, selected: string[]): Promise<boolean> {
    return Boolean(await run(async () => {
      roles.value = [...roles.value, await api.createRole(name, selected)];
      notifications.notify("角色已建立", "success");
      return true;
    }));
  }

  async function updateRole(roleId: string, selected: string[]): Promise<void> {
    await run(async () => {
      const affectsSession = session.user.value?.roleIds.includes(roleId) ?? false;
      const updated = await api.updateRolePermissions(roleId, selected);
      roles.value = roles.value.map((role) => role.id === updated.id ? updated : role);
      if (affectsSession) await session.refreshCapabilities();
      notifications.notify("角色權限已更新", "success");
    });
  }

  async function deleteRole(roleId: string): Promise<void> {
    await run(async () => {
      await api.deleteRole(roleId);
      roles.value = removeRoleById(roles.value, roleId);
      notifications.notify("角色已刪除", "success");
    });
  }

  async function updateUser(
    request: () => Promise<UserAccess>,
    message: string,
  ): Promise<void> {
    await run(async () => {
      const updated = await request();
      users.value = users.value.map((item) => item.id === updated.id ? updated : item);
      if (session.user.value?.id === updated.id) {
        session.updateCurrentUser(updated);
        await session.refreshCapabilities();
      }
      notifications.notify(message, "success");
    });
  }

  const updateUserRoles = (userId: string, roleIds: string[]) =>
    updateUser(() => api.updateUserRoles(userId, roleIds), "使用者角色已更新");
  const updateCustomerGrants = (userId: string, ids: string[]) =>
    updateUser(() => api.updateCustomerGrants(userId, ids), "客戶存取範圍已更新");
  const updateTaskGrants = (userId: string, ids: string[]) =>
    updateUser(() => api.updateTaskGrants(userId, ids), "任務存取範圍已更新");

  async function inviteUser(input: CreateInvitationInput): Promise<boolean> {
    return Boolean(await run(async () => {
      await api.inviteUser(input);
      users.value = can("users.read") ? await api.users() : [];
      notifications.notify("邀請已建立", "success");
      return true;
    }));
  }

  async function createDepartment(name: string, description: string): Promise<boolean> {
    return Boolean(await run(async () => {
      departments.value = [...departments.value, await api.createDepartment(name, description)];
      notifications.notify("部門已新增", "success");
      return true;
    }));
  }

  async function updateDepartment(id: string, name: string, description: string): Promise<boolean> {
    return Boolean(await run(async () => {
      const updated = await api.updateDepartment(id, name, description);
      departments.value = departments.value.map((item) => item.id === updated.id ? updated : item);
      notifications.notify("部門已更新", "success");
      return true;
    }));
  }

  async function deleteDepartment(id: string): Promise<void> {
    await run(async () => {
      await api.deleteDepartment(id);
      departments.value = departments.value.filter((item) => item.id !== id);
      notifications.notify("部門已刪除", "success");
    });
  }

  async function createCustomer(name: string): Promise<boolean> {
    return Boolean(await run(async () => {
      customers.value = [...customers.value, await api.createCustomer(name)];
      notifications.notify("客戶已新增，但尚未建立對應任務。", "success");
      return true;
    }));
  }

  async function createTask(customerId: string, name: string): Promise<boolean> {
    return Boolean(await run(async () => {
      tasks.value = [...tasks.value, await api.createTask(customerId, name)];
      notifications.notify("任務已新增，但尚未建立對應專案。", "success");
      return true;
    }));
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

  async function run<T>(action: () => Promise<T>): Promise<T | null> {
    loading.value = true;
    try {
      return await action();
    } catch (caught) {
      notifications.notify(
        caught instanceof Error ? caught.message : "系統發生未預期錯誤。",
        "error",
      );
      return null;
    } finally {
      loading.value = false;
    }
  }

  return {
    roles,
    users,
    permissions,
    departments,
    customers,
    tasks,
    decision,
    loading,
    clear,
    ensureView,
    refreshActiveView,
    createRole,
    updateRole,
    deleteRole,
    updateUserRoles,
    updateCustomerGrants,
    updateTaskGrants,
    inviteUser,
    createDepartment,
    updateDepartment,
    deleteDepartment,
    createCustomer,
    createTask,
    evaluate,
  };
}

export type AccessAdministration = ReturnType<typeof createAccessAdministration>;
