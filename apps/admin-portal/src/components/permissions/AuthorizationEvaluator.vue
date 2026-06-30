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
const firstCustomer = computed(() => props.customers[0] ?? null);
const firstTask = computed(() => props.tasks[0] ?? null);
const otherUser = computed(
  () => props.users.find((user) => user.id !== props.currentUser.id) ?? null,
);
const quickScenarios = computed(() => {
  const taskPermission = selectScenarioPermission("tasks.read");
  const customerPermission = selectScenarioPermission("customers.read");
  const scenarios = [
    {
      id: "current-task-read",
      label: "目前帳號檢視任務",
      description: "用目前登入帳號測試第一筆任務資源。",
      userId: props.currentUser.id,
      permission: taskPermission,
      resourceType: "task" as const,
      customerId: firstTask.value?.customerId ?? "",
      taskId: firstTask.value?.id ?? "",
      disabled: !taskPermission || !firstTask.value,
    },
    {
      id: "current-customer-read",
      label: "目前帳號檢視客戶",
      description: "用目前登入帳號測試第一筆客戶資源。",
      userId: props.currentUser.id,
      permission: customerPermission,
      resourceType: "customer" as const,
      customerId: firstCustomer.value?.id ?? "",
      taskId: "",
      disabled: !customerPermission || !firstCustomer.value,
    },
    {
      id: "other-user-task-read",
      label: "其他使用者檢視任務",
      description: "用第一位其他使用者測試第一筆任務資源。",
      userId: otherUser.value?.id ?? props.currentUser.id,
      permission: taskPermission,
      resourceType: "task" as const,
      customerId: firstTask.value?.customerId ?? "",
      taskId: firstTask.value?.id ?? "",
      disabled:
        !props.canEvaluateOthers ||
        !otherUser.value ||
        !taskPermission ||
        !firstTask.value,
    },
  ];
  return scenarios;
});

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

function selectScenarioPermission(preferredPermission: string): string {
  return props.permissions.includes(preferredPermission)
    ? preferredPermission
    : (props.permissions[0] ?? "");
}

function applyScenario(scenario: (typeof quickScenarios.value)[number]): void {
  if (scenario.disabled) return;
  userId.value = scenario.userId;
  permission.value = scenario.permission;
  resourceType.value = scenario.resourceType;
  customerId.value = scenario.customerId;
  taskId.value = scenario.taskId;
}
</script>

<template>
  <div class="permission-content authorization-workspace">
    <div class="mock-notice subtle authorization-note">
      <AppIcon name="alert-circle" :size="16" />
      <span>此為測試工具，不會修改實際資料；結果由 access-control API 即時回傳。</span>
    </div>
    <div class="evaluator-grid">
      <section class="card authorization-card">
        <header class="card-header">
          <div>
            <h2>授權條件</h2>
            <p>填寫條件後點「執行授權判斷」，也可從快速範例載入測試案例。</p>
          </div>
        </header>
        <div class="authorization-scenarios">
          <span>快速範例</span>
          <button
            v-for="scenario in quickScenarios"
            :key="scenario.id"
            class="button button-secondary"
            type="button"
            :disabled="scenario.disabled"
            :title="scenario.description"
            @click="applyScenario(scenario)"
          >
            {{ scenario.label }}
          </button>
        </div>
        <label class="form-field">
          <span>使用者</span>
          <select v-model="userId">
            <option :value="currentUser.id">
              {{ currentUser.displayName }}（目前帳號）
            </option>
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
          {{ loading ? "判斷中..." : "執行授權判斷" }}
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
          <div class="decision-summary">
            <span>判斷摘要</span>
            <ul>
              <li>
                <strong>使用者</strong>
                <code>{{ userId }}</code>
              </li>
              <li>
                <strong>操作權限</strong>
                <code>{{ permission }}</code>
              </li>
              <li>
                <strong>資源</strong>
                <code>
                  {{ resourceType }}:{{
                    resourceType === "task" ? taskId : customerId
                  }}
                </code>
              </li>
            </ul>
          </div>
        </template>
        <template v-else>
          <span class="decision-placeholder">
            <AppIcon name="shield" :size="36" />
          </span>
          <h2>等待判斷</h2>
          <p>填寫左側條件後執行授權判斷。</p>
          <div class="authorization-use-case-card">
            <span>適用情境</span>
            <ul class="authorization-use-cases">
              <li>除錯使用者反映的權限問題</li>
              <li>驗證新建角色的權限設定</li>
              <li>確認資源範圍是否符合預期</li>
            </ul>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>
