<script setup lang="ts">
import { reactive, ref } from "vue";
import type { Department } from "../../types";
import AppIcon from "../ui/AppIcon.vue";

defineProps<{
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
    emit("update", selectedDepartmentId.value, name, form.description.trim(), closeModal);
  } else {
    emit("create", name, form.description.trim(), closeModal);
  }
}

function closeModal(): void {
  modalMode.value = null;
}
</script>

<template>
  <div class="permission-content">
    <div class="toolbar department-toolbar">
      <p class="muted">部門可供新增員工與員工資料管理使用。</p>
      <button
        v-if="canManage"
        class="button button-primary toolbar-primary"
        type="button"
        @click="openCreate"
      >
        <AppIcon name="plus" :size="16" />新增部門
      </button>
    </div>
    <div class="department-grid">
      <article v-for="department in departments" :key="department.id" class="card">
        <div class="department-icon"><AppIcon name="users" :size="20" /></div>
        <h2>{{ department.name }}</h2>
        <p>{{ department.description || "尚未填寫部門說明。" }}</p>
        <span>{{ department.memberCount }} 位員工</span>
        <div v-if="canManage" class="department-actions">
          <button class="button button-secondary" type="button" @click="openEdit(department)">
            編輯
          </button>
          <button
            class="button button-danger"
            type="button"
            :disabled="loading || department.memberCount > 0"
            @click="$emit('delete', department.id)"
          >
            封存
          </button>
        </div>
      </article>
      <div v-if="!departments.length" class="card empty-state">
        <AppIcon name="users" :size="28" />
        <strong>尚未建立部門</strong>
      </div>
    </div>

    <div v-if="modalMode" class="modal-backdrop" @click.self="modalMode = null">
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
            <button class="button button-secondary" type="button" @click="modalMode = null">
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
  </div>
</template>
