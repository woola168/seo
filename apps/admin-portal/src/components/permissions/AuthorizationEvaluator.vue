<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import {
  selectAvailablePermission,
  selectAvailableUserId,
} from "../../composables/authorization-selection";
import { permissionLabel } from "../../utils/permissions";
import type {
  AuthorizationDecision,
  CustomerSummary,
  SessionUser,
  TaskSummary,
  UserAccess,
} from "../../types";

const props = defineProps<{
  currentUser: SessionUser;
  users: UserAccess[];
  permissions: string[];
  decision: AuthorizationDecision | null;
  loading: boolean;
  canEvaluateOthers: boolean;
  customers: CustomerSummary[];
  tasks: TaskSummary[];
}>();

const emit = defineEmits<{
  evaluate: [
    userId: string,
    permission: string,
    resource:
      | { type: "customer"; id: string }
      | { type: "task"; id: string; customerId: string },
  ];
}>();

const userId = ref(props.currentUser.id);
const permission = ref("");
const resourceType = ref<"customer" | "task">("task");
const customerId = ref("");
const taskId = ref("");
const availableTasks = computed(() =>
  props.tasks.filter((task) => task.customerId === customerId.value),
);

watch(
  [
    () => props.currentUser.id,
    () => props.users.map((user) => user.id),
    () => props.canEvaluateOthers,
  ],
  () => {
    userId.value = selectAvailableUserId(
      userId.value,
      props.currentUser.id,
      props.users.map((user) => user.id),
      props.canEvaluateOthers,
    );
  },
  { immediate: true },
);

watch(
  () => props.customers,
  (customers) => {
    if (!customers.some((customer) => customer.id === customerId.value)) {
      customerId.value = customers[0]?.id ?? "";
    }
  },
  { deep: true, immediate: true },
);

watch(
  availableTasks,
  (tasks) => {
    if (!tasks.some((task) => task.id === taskId.value)) {
      taskId.value = tasks[0]?.id ?? "";
    }
  },
  { immediate: true },
);

watch(
  () => props.permissions,
  (availablePermissions) => {
    permission.value = selectAvailablePermission(
      permission.value,
      availablePermissions,
    );
  },
  { deep: true, immediate: true },
);

function evaluate(): void {
  const resource =
    resourceType.value === "customer"
      ? { type: "customer" as const, id: customerId.value.trim() }
      : {
          type: "task" as const,
          id: taskId.value.trim(),
          customerId: customerId.value.trim(),
        };
  emit("evaluate", userId.value, permission.value, resource);
}
</script>

<template>
  <div class="evaluator-grid">
    <section class="card">
      <header class="card-header">
        <div>
          <h2>授權條件</h2>
          <p>使用 access-control API 即時判斷指定操作。</p>
        </div>
      </header>
      <label class="form-field">
        <span>使用者</span>
        <select v-model="userId">
          <option :value="currentUser.id">{{ currentUser.displayName }}（目前帳號）</option>
          <option
            v-for="user in users.filter((item) => item.id !== currentUser.id)"
            :key="user.id"
            :value="user.id"
            :disabled="!canEvaluateOthers"
          >
            {{ user.displayName }}
          </option>
        </select>
      </label>
      <label class="form-field">
        <span>操作權限</span>
        <select v-model="permission">
          <option v-for="item in permissions" :key="item" :value="item">
            {{ permissionLabel(item) }}（{{ item }}）
          </option>
        </select>
      </label>
      <label class="form-field">
        <span>資源類型</span>
        <select v-model="resourceType">
          <option value="customer">Customer</option>
          <option value="task">Task</option>
        </select>
      </label>
      <label class="form-field">
        <span>Customer ID</span>
        <select v-model="customerId">
          <option value="">請選擇客戶</option>
          <option
            v-for="customer in customers"
            :key="customer.id"
            :value="customer.id"
          >
            {{ customer.name }}
          </option>
        </select>
      </label>
      <label v-if="resourceType === 'task'" class="form-field">
        <span>Task ID</span>
        <select v-model="taskId">
          <option value="">請選擇任務</option>
          <option v-for="task in availableTasks" :key="task.id" :value="task.id">
            {{ task.name }}
          </option>
        </select>
      </label>
      <button
        class="button button-primary"
        type="button"
        :disabled="loading || !permission || !customerId || (resourceType === 'task' && !taskId)"
        @click="evaluate"
      >
        執行授權判斷
      </button>
    </section>

    <section class="card decision-card">
      <template v-if="decision">
        <span
          class="decision-symbol"
          :class="decision.allowed ? 'allowed' : 'denied'"
        >
          <AppIcon :name="decision.allowed ? 'check' : 'x'" :size="32" />
        </span>
        <h2>{{ decision.allowed ? "允許操作" : "拒絕操作" }}</h2>
        <code>{{ decision.reasonCode }}</code>
        <p>結果由 access-control API 回傳。</p>
      </template>
      <template v-else>
        <span class="decision-placeholder"><AppIcon name="shield" :size="36" /></span>
        <h2>等待判斷</h2>
        <p>填寫左側條件後執行授權判斷。</p>
      </template>
    </section>
  </div>
</template>
