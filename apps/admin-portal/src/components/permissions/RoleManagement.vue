<script setup lang="ts">
import { ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import PermissionGroupSelector from "./PermissionGroupSelector.vue";
import type { Role } from "../../types";

const props = defineProps<{
  roles: Role[];
  permissions: string[];
  canManage: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  "open-create": [];
  update: [roleId: string, permissions: string[]];
}>();

const editingRoleId = ref("");
const editingPermissions = ref<string[]>([]);

watch(
  () => props.roles,
  (roles) => {
    if (!editingRoleId.value && roles[0]) selectRole(roles[0]);
  },
  { immediate: true },
);

function selectRole(role: Role): void {
  editingRoleId.value = role.id;
  editingPermissions.value = [...role.permissions];
}

</script>

<template>
  <div class="role-layout">
    <section class="card role-list">
      <header class="card-header">
        <div>
          <h2>角色列表</h2>
          <p>{{ roles.length }} 個角色</p>
        </div>
        <button
          v-if="canManage"
          class="button button-primary"
          type="button"
          @click="emit('open-create')"
        >
          <AppIcon name="plus" :size="16" />
          建立角色
        </button>
      </header>
      <button
        v-for="role in roles"
        :key="role.id"
        class="role-item"
        :class="{ active: role.id === editingRoleId }"
        type="button"
        @click="selectRole(role)"
      >
        <span>
          <strong>{{ role.name }}</strong>
          <small>{{ role.permissions.length }} 個權限</small>
        </span>
        <span v-if="role.isSystem" class="badge badge-purple">系統角色</span>
        <AppIcon v-else name="chevron-right" :size="16" />
      </button>
    </section>

    <section class="card role-editor">
      <header class="card-header">
        <div>
          <h2>角色權限</h2>
          <p>選擇角色後調整允許的操作。</p>
        </div>
      </header>
      <PermissionGroupSelector
        v-if="editingRoleId"
        :permissions="permissions"
        :selected-permissions="editingPermissions"
        :disabled="!canManage"
        @update:selected-permissions="editingPermissions = $event"
      />
      <div v-else class="empty-state">尚無可編輯的角色。</div>
      <button
        class="button button-primary"
        type="button"
        :disabled="!editingRoleId || !canManage || loading"
        @click="emit('update', editingRoleId, editingPermissions)"
      >
        儲存角色權限
      </button>
    </section>

  </div>
</template>
