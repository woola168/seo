<script setup lang="ts">
import { computed, nextTick, reactive, ref } from "vue";
import type { Department } from "../../types";
import { getFocusTargetIndex } from "../../utils/focus-trap";
import AppIcon from "../ui/AppIcon.vue";

const props = defineProps<{
  departments: Department[];
  canManage: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  create: [name: string, description: string, onSuccess: () => void];
  update: [
    departmentId: string,
    name: string,
    description: string,
    onSuccess: () => void,
  ];
  delete: [departmentId: string];
}>();

const modalMode = ref<"create" | "edit" | null>(null);
const selectedDepartmentId = ref("");
const form = reactive({ name: "", description: "" });
const search = ref("");
const deleteTarget = ref<Department | null>(null);
const deleteCloseButton = ref<HTMLButtonElement | null>(null);
const deleteCancelButton = ref<HTMLButtonElement | null>(null);
const deleteConfirmButton = ref<HTMLButtonElement | null>(null);
const filteredDepartments = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  if (!keyword) return props.departments;
  return props.departments.filter(
    (department) =>
      department.name.toLowerCase().includes(keyword) ||
      department.description.toLowerCase().includes(keyword),
  );
});
type DialogFocusElement = HTMLButtonElement;

function openCreate(): void {
  selectedDepartmentId.value = "";
  form.name = "";
  form.description = "";
  modalMode.value = "create";
}

function openEdit(department: Department): void {
  selectedDepartmentId.value = department.id;
  form.name = department.name;
  form.description = department.description;
  modalMode.value = "edit";
}

function submit(): void {
  const name = form.name.trim();
  if (!name) return;
  if (modalMode.value === "edit") {
    emit(
      "update",
      selectedDepartmentId.value,
      name,
      form.description.trim(),
      closeModal,
    );
  } else {
    emit("create", name, form.description.trim(), closeModal);
  }
}

function closeModal(): void {
  modalMode.value = null;
}

function requestDelete(department: Department): void {
  if (!props.canManage || props.loading || department.memberCount > 0) return;
  deleteTarget.value = department;
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
        <input v-model="search" type="search" placeholder="搜尋部門名稱、描述..." />
      </label>
      <span class="permission-record-count">共 {{ departments.length }} 個</span>
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
        @click="openCreate"
      >
        <AppIcon name="plus" :size="16" />新增部門
      </button>
    </div>
    <div class="table-scroll card table-card department-table-card">
      <table class="data-table department-table">
        <thead>
          <tr>
            <th>部門名稱</th>
            <th>描述</th>
            <th>成員數</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="department in filteredDepartments" :key="department.id">
            <td class="department-name">{{ department.name }}</td>
            <td class="department-description">
              {{ department.description || "尚未填寫部門說明。" }}
            </td>
            <td class="department-member-count">{{ department.memberCount }}</td>
            <td>
              <div v-if="canManage" class="row-actions">
                <button
                  class="icon-button row-action-button"
                  type="button"
                  :aria-label="`編輯 ${department.name}`"
                  @click="openEdit(department)"
                >
                  <AppIcon name="edit" :size="15" />
                </button>
                <button
                  class="icon-button row-action-button danger"
                  type="button"
                  :disabled="loading || department.memberCount > 0"
                  :aria-label="`刪除 ${department.name}`"
                  @click="requestDelete(department)"
                >
                  <AppIcon name="trash" :size="15" />
                </button>
              </div>
              <span v-else class="muted">無可用操作</span>
            </td>
          </tr>
          <tr v-if="!filteredDepartments.length && departments.length">
            <td colspan="4">
              <div class="empty-state">
                <AppIcon name="search" :size="28" />
                <strong>找不到符合條件的部門</strong>
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
            </td>
          </tr>
          <tr v-else-if="!departments.length">
            <td colspan="4">
              <div class="empty-state">
                <AppIcon name="users" :size="28" />
                <strong>尚未建立部門</strong>
                <span>新增部門後即可在員工資料中指派歸屬。</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div
      v-if="modalMode"
      class="modal-backdrop"
      @click.self="modalMode = null"
      @keydown.esc.prevent="modalMode = null"
    >
      <form class="modal modal-compact" @submit.prevent="submit">
        <header class="modal-header">
          <div>
            <h2>{{ modalMode === "create" ? "新增部門" : "編輯部門" }}</h2>
            <p>設定員工歸屬使用的部門資料。</p>
          </div>
          <button class="icon-button" type="button" @click="modalMode = null">
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="modal-body">
          <label class="form-field">
            <span>部門名稱</span>
            <input v-model="form.name" required maxlength="120" />
          </label>
          <label class="form-field">
            <span>說明</span>
            <textarea v-model="form.description" rows="3"></textarea>
          </label>
          <div class="modal-actions">
            <button
              class="button button-secondary"
              type="button"
              @click="modalMode = null"
            >
              取消
            </button>
            <button
              class="button button-primary"
              type="submit"
              :disabled="loading || !form.name.trim()"
            >
              儲存
            </button>
          </div>
        </div>
      </form>
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
        aria-labelledby="delete-department-title"
      >
        <header class="modal-header">
          <div>
            <h2 id="delete-department-title">刪除部門</h2>
            <p>刪除後無法復原；仍有成員的部門不可刪除。</p>
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
              刪除部門
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
