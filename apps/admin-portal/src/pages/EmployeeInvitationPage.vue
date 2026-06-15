<script setup lang="ts">
import { computed } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useEmployeeInvitationForm } from "../composables/employee-invitation-form";
import type {
  Capabilities,
  CreateInvitationInput,
  CustomerSummary,
  Department,
  Role,
  TaskSummary,
} from "../types";
import { hasPermission } from "../utils/permissions";

const props = defineProps<{
  capabilities: Capabilities;
  roles: Role[];
  departments: Department[];
  customers: CustomerSummary[];
  tasks: TaskSummary[];
  loading: boolean;
}>();

const emit = defineEmits<{
  back: [];
  submit: [input: CreateInvitationInput, onSuccess: () => void];
}>();

const invitation = useEmployeeInvitationForm(() => props.tasks);
const canInvite = computed(
  () =>
    hasPermission(props.capabilities.permissions, "users.manage") &&
    hasPermission(props.capabilities.permissions, "roles.read"),
);

function submit(): void {
  const payload = invitation.createPayload();
  if (!payload || !canInvite.value) return;

  emit("submit", payload, () => {
    invitation.reset();
    emit("back");
  });
}
</script>

<template>
  <section class="page employee-invitation-page">
    <button class="form-back" type="button" @click="$emit('back')">
      <AppIcon name="chevron-left" :size="14" />
      返回員工列表
    </button>

    <header class="page-header">
      <div>
        <h1>新增員工</h1>
        <p>建立員工邀請並設定角色與可存取範圍。</p>
      </div>
    </header>

    <div v-if="!canInvite" class="card empty-state">
      <AppIcon name="lock" :size="32" />
      <strong>沒有新增員工的權限</strong>
      <span>需要 users.manage 與 roles.read 權限。</span>
    </div>

    <form v-else class="form-card" @submit.prevent="submit">
      <div class="form-card-inner">
        <div class="form-grid">
          <label class="form-field">
            <span>姓名 *</span>
            <input
              v-model="invitation.form.displayName"
              required
              maxlength="120"
              placeholder="王小明"
            />
          </label>
          <label class="form-field">
            <span>Email *</span>
            <input
              v-model="invitation.form.email"
              required
              type="email"
              placeholder="user@kinsan-seo.com"
            />
          </label>
          <label class="form-field form-grid-full">
            <span>部門</span>
            <select v-model="invitation.form.departmentId">
              <option :value="null">未指定</option>
              <option
                v-for="department in departments"
                :key="department.id"
                :value="department.id"
              >
                {{ department.name }}
              </option>
            </select>
          </label>
        </div>

        <fieldset class="form-section">
          <legend>角色 *</legend>
          <p class="form-help">至少選擇一個角色。</p>
          <div class="choice-grid">
            <label v-for="role in roles" :key="role.id" class="checkbox-row">
              <input
                v-model="invitation.form.roleIds"
                type="checkbox"
                :value="role.id"
              />
              <span>{{ role.name }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="form-section">
          <legend>可存取客戶</legend>
          <div class="choice-grid">
            <label
              v-for="customer in customers"
              :key="customer.id"
              class="checkbox-row"
            >
              <input
                v-model="invitation.form.customerIds"
                type="checkbox"
                :value="customer.id"
              />
              <span>{{ customer.name }}</span>
            </label>
          </div>
          <p v-if="!customers.length" class="form-help">目前尚無客戶資料。</p>
        </fieldset>

        <fieldset class="form-section">
          <legend>可存取任務</legend>
          <div class="choice-grid">
            <label
              v-for="task in invitation.availableTasks.value"
              :key="task.id"
              class="checkbox-row"
            >
              <input
                v-model="invitation.form.taskIds"
                type="checkbox"
                :value="task.id"
              />
              <span>{{ task.customerName }} / {{ task.name }}</span>
            </label>
          </div>
          <p v-if="!invitation.availableTasks.value.length" class="form-help">
            目前尚無可選任務。
          </p>
        </fieldset>

        <label class="checkbox-row invitation-notice-option">
          <input
            v-model="invitation.form.sendInvitation"
            type="checkbox"
          />
          <span>建立待寄送邀請通知</span>
        </label>
        <p class="form-help">
          員工將透過邀請連結自行設定密碼；目前通知會先寫入 Outbox。
        </p>

        <div class="form-actions">
          <button class="button button-secondary" type="button" @click="$emit('back')">
            取消
          </button>
          <button
            class="button button-primary"
            type="submit"
            :disabled="loading || !invitation.canSubmit.value"
          >
            {{ loading ? "建立中..." : "建立邀請" }}
          </button>
        </div>
      </div>
    </form>
  </section>
</template>
