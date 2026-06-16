<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import AuthorizationEvaluator from "../components/permissions/AuthorizationEvaluator.vue";
import DepartmentManagement from "../components/permissions/DepartmentManagement.vue";
import MemberManagement from "../components/permissions/MemberManagement.vue";
import RoleManagement from "../components/permissions/RoleManagement.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { mergeMemberMetadata } from "../mocks/permissions";
import type {
  AuthorizationDecision,
  Capabilities,
  CustomerSummary,
  Department,
  Role,
  SessionUser,
  TaskSummary,
  UserAccess,
} from "../types";
import { canManageUserRoles } from "../utils/permission-guards";
import { hasPermission } from "../utils/permissions";

const props = defineProps<{
  currentUser: SessionUser;
  capabilities: Capabilities;
  users: UserAccess[];
  roles: Role[];
  permissions: string[];
  customers: CustomerSummary[];
  tasks: TaskSummary[];
  departments: Department[];
  decision: AuthorizationDecision | null;
  loading: boolean;
  initialTab?: PermissionTab;
}>();

const emit = defineEmits<{
  unavailable: [label: string];
  "open-role-creation": [];
  "update-role": [roleId: string, permissions: string[]];
  "delete-role": [roleId: string];
  "update-user-roles": [userId: string, roleIds: string[]];
  "update-customers": [userId: string, customerIds: string[]];
  "update-tasks": [userId: string, taskIds: string[]];
  "open-invitation": [];
  "create-department": [name: string, description: string, onSuccess: () => void];
  "update-department": [
    departmentId: string,
    name: string,
    description: string,
    onSuccess: () => void,
  ];
  "delete-department": [departmentId: string];
  "create-customer": [name: string, onSuccess: () => void];
  "create-task": [customerId: string, name: string, onSuccess: () => void];
  evaluate: [
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ];
}>();

type PermissionTab = "members" | "roles" | "departments" | "evaluate";
const activeTab = ref<PermissionTab>(props.initialTab ?? "members");
const resourceModal = ref<"customer" | "task" | null>(null);
const resourceForm = reactive({ name: "", customerId: "" });

const departmentNames = computed(
  () => new Map(props.departments.map((department) => [department.id, department.name])),
);
const members = computed(() =>
  mergeMemberMetadata(props.users, props.roles, departmentNames.value),
);
const canReadUsers = computed(() =>
  hasPermission(props.capabilities.permissions, "users.read"),
);
const canEditMemberRoles = computed(() =>
  canManageUserRoles(props.capabilities.permissions),
);
const canReadRoles = computed(() =>
  hasPermission(props.capabilities.permissions, "roles.read"),
);
const canManageRoles = computed(() =>
  hasPermission(props.capabilities.permissions, "roles.manage"),
);
const canManageGrants = computed(() =>
  hasPermission(props.capabilities.permissions, "access-grants.manage"),
);
const canInviteUsers = computed(() =>
  hasPermission(props.capabilities.permissions, "users.manage") &&
  hasPermission(props.capabilities.permissions, "roles.read"),
);
const canReadDepartments = computed(() =>
  hasPermission(props.capabilities.permissions, "departments.read"),
);
const canManageDepartments = computed(() =>
  hasPermission(props.capabilities.permissions, "departments.manage"),
);
const canCreateCustomers = computed(() =>
  hasPermission(props.capabilities.permissions, "customers.create"),
);
const canCreateTasks = computed(() =>
  hasPermission(props.capabilities.permissions, "tasks.create"),
);
const canEvaluateOthers = computed(() =>
  hasPermission(props.capabilities.permissions, "authorization.evaluate"),
);

const tabs: Array<{ id: PermissionTab; label: string }> = [
  { id: "members", label: "員工管理" },
  { id: "roles", label: "角色管理" },
  { id: "departments", label: "部門管理" },
  { id: "evaluate", label: "授權判斷" },
];

watch(
  () => props.initialTab,
  (tab) => {
    if (tab) activeTab.value = tab;
  },
);

function updateUserRoles(userId: string, roleIds: string[]): void {
  emit("update-user-roles", userId, roleIds);
}

function updateCustomers(userId: string, customerIds: string[]): void {
  emit("update-customers", userId, customerIds);
}

function updateTasks(userId: string, taskIds: string[]): void {
  emit("update-tasks", userId, taskIds);
}

function updateRole(roleId: string, selectedPermissions: string[]): void {
  emit("update-role", roleId, selectedPermissions);
}

function deleteRole(roleId: string): void {
  emit("delete-role", roleId);
}

function evaluate(
  userId: string,
  permission: string,
  resource:
    | { type: "customer"; id: string }
    | { type: "task"; id: string; customerId: string },
): void {
  emit("evaluate", userId, permission, resource);
}

function openResourceModal(type: "customer" | "task"): void {
  resourceForm.name = "";
  resourceForm.customerId = props.customers[0]?.id ?? "";
  resourceModal.value = type;
}

function submitResource(): void {
  const name = resourceForm.name.trim();
  if (!name) return;
  if (resourceModal.value === "customer") {
    emit("create-customer", name, () => {
      resourceModal.value = null;
    });
  } else if (resourceModal.value === "task" && resourceForm.customerId) {
    emit("create-task", resourceForm.customerId, name, () => {
      resourceModal.value = null;
    });
  }
}

function createDepartment(
  name: string,
  description: string,
  onSuccess: () => void,
): void {
  emit("create-department", name, description, onSuccess);
}

function updateDepartment(
  departmentId: string,
  name: string,
  description: string,
  onSuccess: () => void,
): void {
  emit("update-department", departmentId, name, description, onSuccess);
}
</script>

<template>
  <section class="page permission-page">
    <header class="page-header">
      <div>
        <h1>權限管理</h1>
        <p>管理員工帳號、部門架構、角色權限與授權判斷。</p>
      </div>
      <div class="page-actions">
        <button
          v-if="canCreateCustomers"
          class="button button-secondary"
          type="button"
          @click="openResourceModal('customer')"
        >
          <AppIcon name="plus" :size="16" />新增客戶
        </button>
        <button
          v-if="canCreateTasks"
          class="button button-secondary"
          type="button"
          :disabled="!customers.length"
          @click="openResourceModal('task')"
        >
          <AppIcon name="plus" :size="16" />新增任務
        </button>
      </div>
    </header>

    <div class="tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: activeTab === tab.id }"
        role="tab"
        :aria-selected="activeTab === tab.id"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <MemberManagement
      v-if="activeTab === 'members' && canReadUsers"
      :members="members"
      :roles="roles"
      :can-edit-roles="canEditMemberRoles"
      :can-manage-grants="canManageGrants"
      :can-invite="canInviteUsers"
      :customers="customers"
      :tasks="tasks"
      :loading="loading"
      @update-roles="updateUserRoles"
      @update-customers="updateCustomers"
      @update-tasks="updateTasks"
      @invite="$emit('open-invitation')"
      @unavailable="$emit('unavailable', $event)"
    />
    <RoleManagement
      v-else-if="activeTab === 'roles' && canReadRoles"
      :roles="roles"
      :permissions="permissions"
      :can-manage="canManageRoles"
      :loading="loading"
      @open-create="$emit('open-role-creation')"
      @update="updateRole"
      @delete="deleteRole"
    />
    <DepartmentManagement
      v-else-if="activeTab === 'departments' && canReadDepartments"
      :departments="departments"
      :can-manage="canManageDepartments"
      :loading="loading"
      @create="createDepartment"
      @update="updateDepartment"
      @delete="$emit('delete-department', $event)"
    />
    <AuthorizationEvaluator
      v-else-if="activeTab === 'evaluate'"
      :current-user="currentUser"
      :users="users"
      :permissions="permissions.length ? permissions : capabilities.permissions"
      :customers="customers"
      :tasks="tasks"
      :decision="decision"
      :loading="loading"
      :can-evaluate-others="canEvaluateOthers"
      @evaluate="evaluate"
    />
    <div v-else class="card empty-state">
      <AppIcon name="lock" :size="32" />
      <strong>沒有檢視此區域的權限</strong>
      <span>請聯絡系統管理員調整 access-control 權限。</span>
    </div>

    <div v-if="resourceModal" class="modal-backdrop" @click.self="resourceModal = null">
      <form class="modal modal-compact" @submit.prevent="submitResource">
        <header class="modal-header">
          <div>
            <h2>{{ resourceModal === "customer" ? "新增客戶" : "新增任務" }}</h2>
            <p>新增後可立即用於員工資源權限設定。</p>
          </div>
          <button class="icon-button" type="button" @click="resourceModal = null">
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="modal-body">
          <label v-if="resourceModal === 'task'" class="form-field">
            <span>客戶</span>
            <select v-model="resourceForm.customerId" required>
              <option v-for="customer in customers" :key="customer.id" :value="customer.id">
                {{ customer.name }}
              </option>
            </select>
          </label>
          <label class="form-field">
            <span>名稱</span>
            <input v-model="resourceForm.name" required maxlength="200" autofocus />
          </label>
          <div class="modal-actions">
            <button class="button button-secondary" type="button" @click="resourceModal = null">
              取消
            </button>
            <button
              class="button button-primary"
              type="submit"
              :disabled="
                loading ||
                !resourceForm.name.trim() ||
                (resourceModal === 'task' && !resourceForm.customerId)
              "
            >
              新增
            </button>
          </div>
        </div>
      </form>
    </div>
  </section>
</template>
