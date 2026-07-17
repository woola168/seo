<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import PermissionGroupSelector from "./PermissionGroupSelector.vue";
import type { Role } from "../../types";
import { getFocusTargetIndex } from "../../utils/focus-trap";
import { filterAssignablePermissions } from "../../utils/internal-permissions";

type DialogFocusElement = HTMLButtonElement;

const props = defineProps<{
  roles: Role[];
  permissions: string[];
  canManage: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  "open-create": [];
  update: [roleId: string, permissions: string[]];
  delete: [roleId: string];
}>();

const editingRoleId = ref("");
const editingPermissions = ref<string[]>([]);
const search = ref("");
const deleteTarget = ref<Role | null>(null);
const deleteCloseButton = ref<HTMLButtonElement | null>(null);
const deleteCancelButton = ref<HTMLButtonElement | null>(null);
const deleteConfirmButton = ref<HTMLButtonElement | null>(null);
const selectedRole = computed(
  () => props.roles.find((role) => role.id === editingRoleId.value) ?? null,
);
const rolePermissions = (role: Role): string[] =>
  filterAssignablePermissions(role.permissions);
const filteredRoles = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return props.roles;
  return props.roles.filter((role) =>
    role.name.toLowerCase().includes(keyword) ||
    rolePermissions(role).some((permission) =>
      permission.toLowerCase().includes(keyword),
    ),
  );
});

watch(
  () => props.roles,
  (roles) => {
    const current = roles.find((role) => role.id === editingRoleId.value);
    if (current) {
      editingPermissions.value = rolePermissions(current);
    } else {
      editingRoleId.value = "";
      editingPermissions.value = [];
    }
    if (
      deleteTarget.value &&
      !roles.some((role) => role.id === deleteTarget.value?.id)
    ) {
      closeDeleteDialog();
    }
  },
  { immediate: true },
);

function selectRole(role: Role): void {
  editingRoleId.value = role.id;
  editingPermissions.value = rolePermissions(role);
}

function closeEditor(): void {
  editingRoleId.value = "";
  editingPermissions.value = [];
}

function saveRole(): void {
  if (!editingRoleId.value) return;
  emit("update", editingRoleId.value, editingPermissions.value);
  closeEditor();
}

function requestDelete(role: Role): void {
  if (!props.canManage || role.isSystem) return;
  deleteTarget.value = role;
  void nextTick(() => deleteCancelButton.value?.focus());
}

function confirmDelete(): void {
  if (!deleteTarget.value) return;
  emit("delete", deleteTarget.value.id);
  closeDeleteDialog();
}

function closeDeleteDialog(): void {
  deleteTarget.value = null;
}

function trapDeleteDialogFocus(event: KeyboardEvent): void {
  const focusableItems = [
    deleteCloseButton.value,
    deleteCancelButton.value,
    deleteConfirmButton.value,
  ].filter((item): item is DialogFocusElement => Boolean(item));
  if (!focusableItems.length) return;
  event.preventDefault();
  const currentIndex = focusableItems.indexOf(
    document.activeElement as DialogFocusElement,
  );
  const targetIndex = getFocusTargetIndex(
    currentIndex,
    focusableItems.length,
    event.shiftKey,
  );
  focusableItems[targetIndex]?.focus();
}
</script>

<template>
  <div class="permission-content">
    <div class="toolbar permission-table-toolbar">
      <label class="filter-search">
        <AppIcon name="search" :size="16" />
        <input v-model="search" type="search" placeholder="搜尋角色名稱、權限..." />
      </label>
      <span class="permission-record-count">共 {{ roles.length }} 個</span>
      <button
        v-if="search"
        class="button button-ghost"
        type="button"
        @click="search = ''"
      >
        清除搜尋
      </button>
      <button
        v-if="canManage"
        class="button button-primary toolbar-primary"
        type="button"
        @click="emit('open-create')"
      >
        <AppIcon name="plus" :size="16" />
        新增角色
      </button>
    </div>

    <section class="role-card-grid">
      <article
        v-for="role in filteredRoles"
        :key="role.id"
        class="card role-card"
      >
        <header class="role-card-head">
          <span class="role-avatar">{{ role.name.slice(0, 1) }}</span>
          <div class="role-card-actions">
            <span v-if="role.isSystem" class="badge badge-purple">系統角色</span>
            <button
              v-if="canManage && !role.isSystem"
              class="icon-button row-action-button"
              type="button"
              :disabled="loading"
              :aria-label="`刪除 ${role.name}`"
              @click="requestDelete(role)"
            >
              <AppIcon name="trash" :size="15" />
            </button>
          </div>
        </header>
        <h2>{{ role.name }}</h2>
        <p>
          {{ role.isSystem ? "系統內建角色，保留核心管理權限。" : "自訂角色，可依職責調整權限範圍。" }}
        </p>
        <footer>
          <span>{{ rolePermissions(role).length }} 項權限</span>
          <button
            class="button button-secondary"
            type="button"
            :disabled="!canManage"
            @click="selectRole(role)"
          >
            編輯權限
          </button>
        </footer>
      </article>
      <div v-if="!filteredRoles.length" class="card empty-state">
        <AppIcon name="search" :size="28" />
        <strong>找不到符合條件的角色</strong>
        <span>試試調整關鍵字或清除搜尋條件。</span>
        <button
          v-if="search"
          class="button button-secondary"
          type="button"
          @click="search = ''"
        >
          清除搜尋
        </button>
      </div>
    </section>

    <div
      v-if="selectedRole"
      class="modal-backdrop"
      @click.self="closeEditor"
      @keydown.esc.prevent="closeEditor"
    >
      <section class="modal role-permission-modal" role="dialog" aria-modal="true">
        <header class="modal-header">
          <div>
            <h2>編輯角色權限</h2>
            <p>{{ selectedRole.name }} · {{ selectedRole.permissions.length }} 項目前權限</p>
          </div>
          <button class="icon-button" type="button" @click="closeEditor">
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="modal-body">
          <PermissionGroupSelector
            :permissions="permissions"
            :selected-permissions="editingPermissions"
            :disabled="!canManage"
            @update:selected-permissions="editingPermissions = $event"
          />
          <div class="modal-actions">
            <button class="button button-secondary" type="button" @click="closeEditor">
              取消
            </button>
            <button
              class="button button-primary"
              type="button"
              :disabled="!canManage || loading"
              @click="saveRole"
            >
              儲存角色權限
            </button>
          </div>
        </div>
      </section>
    </div>

    <div
      v-if="deleteTarget"
      class="modal-backdrop"
      @click.self="closeDeleteDialog"
      @keydown.esc.prevent="closeDeleteDialog"
      @keydown.tab="trapDeleteDialogFocus"
    >
      <section
        class="modal modal-compact"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-role-title"
      >
        <header class="modal-header">
          <div>
            <h2 id="delete-role-title">刪除角色</h2>
            <p>刪除後無法復原，且仍有使用者套用的角色會由 API 阻擋。</p>
          </div>
          <button
            ref="deleteCloseButton"
            class="icon-button"
            type="button"
            @click="closeDeleteDialog"
          >
            <AppIcon name="x" :size="16" />
          </button>
        </header>
        <div class="modal-body">
          <p>
            確定要刪除
            <strong>{{ deleteTarget.name }}</strong>
            嗎？
          </p>
          <div class="modal-actions">
            <button
              ref="deleteCancelButton"
              class="button button-secondary"
              type="button"
              @click="closeDeleteDialog"
            >
              取消
            </button>
            <button
              ref="deleteConfirmButton"
              class="button button-danger"
              type="button"
              :disabled="loading"
              @click="confirmDelete"
            >
              刪除角色
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
