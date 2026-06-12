<script setup lang="ts">
import { computed, ref } from "vue";
import AuthorizationEvaluator from "../components/permissions/AuthorizationEvaluator.vue";
import DepartmentManagement from "../components/permissions/DepartmentManagement.vue";
import MemberManagement from "../components/permissions/MemberManagement.vue";
import RoleManagement from "../components/permissions/RoleManagement.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { mergeMemberMetadata } from "../mocks/permissions";
import type {
  AuthorizationDecision,
  Capabilities,
  Role,
  SessionUser,
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
  decision: AuthorizationDecision | null;
  loading: boolean;
}>();

const emit = defineEmits<{
  unavailable: [label: string];
  "create-role": [
    name: string,
    permissions: string[],
    onSuccess: () => void,
  ];
  "update-role": [roleId: string, permissions: string[]];
  "update-user-roles": [userId: string, roleIds: string[]];
  "update-customers": [userId: string, customerIds: string[]];
  "update-tasks": [userId: string, taskIds: string[]];
  evaluate: [
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ];
}>();

type PermissionTab = "members" | "roles" | "departments" | "evaluate";
const activeTab = ref<PermissionTab>("members");

const members = computed(() => mergeMemberMetadata(props.users, props.roles));
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
const canEvaluateOthers = computed(() =>
  hasPermission(props.capabilities.permissions, "authorization.evaluate"),
);

const tabs: Array<{ id: PermissionTab; label: string }> = [
  { id: "members", label: "員工管理" },
  { id: "roles", label: "角色管理" },
  { id: "departments", label: "部門管理" },
  { id: "evaluate", label: "授權判斷" },
];

function updateUserRoles(userId: string, roleIds: string[]): void {
  emit("update-user-roles", userId, roleIds);
}

function updateCustomers(userId: string, customerIds: string[]): void {
  emit("update-customers", userId, customerIds);
}

function updateTasks(userId: string, taskIds: string[]): void {
  emit("update-tasks", userId, taskIds);
}

function createRole(
  name: string,
  selectedPermissions: string[],
  onSuccess: () => void,
): void {
  emit("create-role", name, selectedPermissions, onSuccess);
}

function updateRole(roleId: string, selectedPermissions: string[]): void {
  emit("update-role", roleId, selectedPermissions);
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
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <p class="page-kicker">儀表板 / 權限管理</p>
        <h1>權限管理</h1>
        <p>管理員工帳號、角色權限、資源範圍與授權判斷。</p>
      </div>
      <button
        class="button button-primary"
        type="button"
        @click="$emit('unavailable', '新增員工')"
      >
        <AppIcon name="plus" :size="17" />新增員工
      </button>
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
      :loading="loading"
      @update-roles="updateUserRoles"
      @update-customers="updateCustomers"
      @update-tasks="updateTasks"
      @unavailable="$emit('unavailable', $event)"
    />
    <RoleManagement
      v-else-if="activeTab === 'roles' && canReadRoles"
      :roles="roles"
      :permissions="permissions"
      :can-manage="canManageRoles"
      :loading="loading"
      @create="createRole"
      @update="updateRole"
    />
    <DepartmentManagement
      v-else-if="activeTab === 'departments'"
      @unavailable="$emit('unavailable', $event)"
    />
    <AuthorizationEvaluator
      v-else-if="activeTab === 'evaluate'"
      :current-user="currentUser"
      :users="users"
      :permissions="permissions.length ? permissions : capabilities.permissions"
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
  </section>
</template>
