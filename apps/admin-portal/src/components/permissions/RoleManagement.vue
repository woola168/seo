<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import PermissionGroupSelector from "./PermissionGroupSelector.vue";
import type { Role } from "../../types";
import { getFocusTargetIndex } from "../../utils/focus-trap";

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
const deleteTarget = ref<Role | null>(null);
const deleteCloseButton = ref<HTMLButtonElement | null>(null);
const deleteCancelButton = ref<HTMLButtonElement | null>(null);
const deleteConfirmButton = ref<HTMLButtonElement | null>(null);

watch(
  () => props.roles,
  (roles) => {
    const current = roles.find((role) => role.id === editingRoleId.value);
    if (current) {
      editingPermissions.value = [...current.permissions];
    } else if (roles[0]) {
      selectRole(roles[0]);
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
  editingPermissions.value = [...role.permissions];
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
      <div
        v-for="role in roles"
        :key="role.id"
        class="role-item"
        :class="{ active: role.id === editingRoleId }"
      >
        <button class="role-select" type="button" @click="selectRole(role)">
          <span>
            <strong>{{ role.name }}</strong>
            <small>{{ role.permissions.length }} 個權限</small>
          </span>
          <span v-if="role.isSystem" class="badge badge-purple">系統角色</span>
          <AppIcon v-else name="chevron-right" :size="16" />
        </button>
        <button
          v-if="canManage && !role.isSystem"
          class="icon-button role-delete-button"
          type="button"
          :disabled="loading"
          :aria-label="`刪除 ${role.name}`"
          @click="requestDelete(role)"
        >
          <AppIcon name="trash" :size="15" />
        </button>
      </div>
    </section>

    <section class="card role-editor">
      <header class="card-header">
        <div>
          <h2>角色權限</h2>
          <p>選擇角色後調整可使用的功能群組。</p>
        </div>
      </header>
      <PermissionGroupSelector
        v-if="editingRoleId"
        :permissions="permissions"
        :selected-permissions="editingPermissions"
        :disabled="!canManage"
        @update:selected-permissions="editingPermissions = $event"
      />
      <div v-else class="empty-state">目前沒有可編輯的角色。</div>
      <button
        class="button button-primary"
        type="button"
        :disabled="!editingRoleId || !canManage || loading"
        @click="emit('update', editingRoleId, editingPermissions)"
      >
        儲存角色權限
      </button>
    </section>

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
