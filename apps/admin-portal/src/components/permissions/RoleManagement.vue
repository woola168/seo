<script setup lang="ts">
import { ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import { useRoleCreationForm } from "../../composables/role-creation-form";
import type { Role } from "../../types";

const props = defineProps<{
  roles: Role[];
  permissions: string[];
  canManage: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  create: [
    name: string,
    permissions: string[],
    onSuccess: () => void,
  ];
  update: [roleId: string, permissions: string[]];
}>();

const {
  roleName,
  selectedPermissions,
  submit: submitRoleCreation,
} = useRoleCreationForm();
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

function createRole(): void {
  submitRoleCreation((name, permissions, onSuccess) => {
    emit("create", name, permissions, onSuccess);
  });
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
        <span v-if="role.isSystem" class="badge badge-role">系統角色</span>
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
      <div v-if="editingRoleId" class="permission-grid">
        <label
          v-for="permission in permissions"
          :key="permission"
          class="permission-choice"
        >
          <input
            v-model="editingPermissions"
            type="checkbox"
            :value="permission"
            :disabled="!canManage"
          />
          <span>{{ permission }}</span>
        </label>
      </div>
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

    <section class="card create-role-card">
      <header class="card-header">
        <div>
          <h2>建立角色</h2>
          <p>建立後可再調整角色權限。</p>
        </div>
      </header>
      <label class="form-field">
        <span>角色名稱</span>
        <input v-model="roleName" placeholder="例如：Content Reviewer" />
      </label>
      <div class="permission-grid compact-permissions">
        <label
          v-for="permission in permissions"
          :key="permission"
          class="permission-choice"
        >
          <input
            v-model="selectedPermissions"
            type="checkbox"
            :value="permission"
            :disabled="!canManage"
          />
          <span>{{ permission }}</span>
        </label>
      </div>
      <button
        class="button button-primary"
        type="button"
        :disabled="!roleName.trim() || !canManage || loading"
        @click="createRole"
      >
        建立角色
      </button>
    </section>
  </div>
</template>
