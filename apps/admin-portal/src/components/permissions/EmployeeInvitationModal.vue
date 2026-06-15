<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import type {
  CreateInvitationInput,
  CustomerSummary,
  Department,
  Role,
  TaskSummary,
} from "../../types";
import AppIcon from "../ui/AppIcon.vue";

const props = defineProps<{
  roles: Role[];
  departments: Department[];
  customers: CustomerSummary[];
  tasks: TaskSummary[];
  loading: boolean;
}>();

const emit = defineEmits<{
  close: [];
  submit: [input: CreateInvitationInput];
}>();

const form = reactive<CreateInvitationInput>({
  email: "",
  displayName: "",
  departmentId: null,
  roleIds: [],
  customerIds: [],
  taskIds: [],
  sendInvitation: true,
});

const availableTasks = computed(() =>
  form.customerIds.length
    ? props.tasks.filter((task) => form.customerIds.includes(task.customerId))
    : props.tasks,
);

watch(
  () => [...form.customerIds],
  () => {
    const availableTaskIds = new Set(availableTasks.value.map((task) => task.id));
    form.taskIds = form.taskIds.filter((taskId) => availableTaskIds.has(taskId));
  },
);

function submit(): void {
  if (!form.email.trim() || !form.displayName.trim() || !form.roleIds.length) {
    return;
  }
  emit("submit", {
    ...form,
    email: form.email.trim(),
    displayName: form.displayName.trim(),
  });
}
</script>

<template>
  <div class="modal-backdrop" @click.self="$emit('close')">
    <form class="modal" role="dialog" aria-modal="true" @submit.prevent="submit">
      <header class="modal-header">
        <div>
          <h2>新增員工</h2>
          <p>建立邀請後，員工可由邀請連結設定密碼並啟用帳號。</p>
        </div>
        <button class="icon-button" type="button" aria-label="關閉" @click="$emit('close')">
          <AppIcon name="x" :size="18" />
        </button>
      </header>
      <div class="modal-body">
        <div class="form-grid">
          <label class="form-field">
            <span>姓名</span>
            <input v-model="form.displayName" required maxlength="120" />
          </label>
          <label class="form-field">
            <span>Email</span>
            <input v-model="form.email" required type="email" />
          </label>
          <label class="form-field form-grid-full">
            <span>部門</span>
            <select v-model="form.departmentId">
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
        <fieldset>
          <legend>角色（至少一項）</legend>
          <label v-for="role in roles" :key="role.id" class="checkbox-row">
            <input v-model="form.roleIds" type="checkbox" :value="role.id" />
            <span>{{ role.name }}</span>
          </label>
        </fieldset>
        <fieldset>
          <legend>可存取客戶</legend>
          <label v-for="customer in customers" :key="customer.id" class="checkbox-row">
            <input v-model="form.customerIds" type="checkbox" :value="customer.id" />
            <span>{{ customer.name }}</span>
          </label>
          <p v-if="!customers.length" class="form-help">目前尚無客戶資料。</p>
        </fieldset>
        <fieldset>
          <legend>可存取任務</legend>
          <label v-for="task in availableTasks" :key="task.id" class="checkbox-row">
            <input v-model="form.taskIds" type="checkbox" :value="task.id" />
            <span>{{ task.customerName }} / {{ task.name }}</span>
          </label>
          <p v-if="!availableTasks.length" class="form-help">目前尚無可選任務。</p>
        </fieldset>
        <label class="checkbox-row">
          <input v-model="form.sendInvitation" type="checkbox" />
          <span>建立待寄送邀請通知</span>
        </label>
        <p class="form-help">
          目前通知會寫入 Outbox；串接外部寄信服務後即可自動寄送。
        </p>
        <div class="modal-actions">
          <button class="button button-secondary" type="button" @click="$emit('close')">
            取消
          </button>
          <button
            class="button button-primary"
            type="submit"
            :disabled="
              loading ||
              !form.email.trim() ||
              !form.displayName.trim() ||
              !form.roleIds.length
            "
          >
            建立邀請
          </button>
        </div>
      </div>
    </form>
  </div>
</template>
