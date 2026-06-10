<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { ApiError, api } from "./services/api";
import type {
  AuthorizationDecision,
  Capabilities,
  Role,
  SessionUser,
  UserAccess,
} from "./types";
import { hasPermission } from "./utils/permissions";

const email = ref("");
const password = ref("");
const user = ref<SessionUser | null>(null);
const capabilities = ref<Capabilities | null>(null);
const roles = ref<Role[]>([]);
const users = ref<UserAccess[]>([]);
const permissions = ref<string[]>([]);
const loading = ref(false);
const error = ref("");
const activePanel = ref<"overview" | "roles" | "evaluate">("overview");
const roleName = ref("");
const selectedPermissions = ref<string[]>(["customers.read", "tasks.read"]);
const evaluatePermission = ref("tasks.update");
const resourceType = ref<"customer" | "task">("task");
const customerId = ref("");
const taskId = ref("");
const decision = ref<AuthorizationDecision | null>(null);

const isAdmin = computed(
  () => capabilities.value?.hasGlobalResourceAccess ?? false,
);
const canManageRoles = computed(
  () => hasPermission(capabilities.value?.permissions ?? [], "roles.manage"),
);

onMounted(async () => {
  if (api.hasSession()) await loadSession();
});

async function login(): Promise<void> {
  await run(async () => {
    await api.login(email.value, password.value);
    await loadSession();
  });
}

async function logout(): Promise<void> {
  await api.logout();
  user.value = null;
  capabilities.value = null;
  roles.value = [];
  users.value = [];
  permissions.value = [];
}

async function loadSession(): Promise<void> {
  await run(async () => {
    const [currentUser, currentCapabilities] = await Promise.all([
      api.me(),
      api.capabilities(),
    ]);
    user.value = currentUser;
    capabilities.value = currentCapabilities;
    await loadAccessibleData();
  });
}

async function loadAccessibleData(): Promise<void> {
  const permissionSet = new Set(capabilities.value?.permissions ?? []);
  const calls: Promise<void>[] = [];
  if (hasPermission([...permissionSet], "roles.read")) {
    calls.push(api.roles().then((value) => void (roles.value = value)));
  }
  if (hasPermission([...permissionSet], "users.read")) {
    calls.push(api.users().then((value) => void (users.value = value)));
  }
  if (hasPermission([...permissionSet], "permissions.read")) {
    calls.push(
      api.permissions().then((value) => void (permissions.value = value)),
    );
  }
  await Promise.all(calls);
}

async function createRole(): Promise<void> {
  if (!roleName.value.trim()) return;
  await run(async () => {
    await api.createRole(roleName.value.trim(), selectedPermissions.value);
    roleName.value = "";
    roles.value = await api.roles();
  });
}

async function evaluate(): Promise<void> {
  if (!user.value) return;
  await run(async () => {
    decision.value = await api.evaluate(
      user.value!.id,
      evaluatePermission.value,
      resourceType.value === "customer"
        ? { type: "customer", id: customerId.value }
        : {
            type: "task",
            id: taskId.value,
            customerId: customerId.value,
          },
    );
  });
}

async function run(action: () => Promise<void>): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    await action();
  } catch (caught) {
    error.value =
      caught instanceof ApiError ? caught.message : "操作失敗，請稍後再試。";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main v-if="!user" class="login-shell">
    <section class="login-card">
      <div class="brand-mark">YL</div>
      <p class="eyebrow">Younilab SEO</p>
      <h1>權限控管展示中心</h1>
      <p class="muted">
        使用不同角色登入，立即檢視功能權限與客戶／任務資料範圍。
      </p>
      <label>
        Email
        <input v-model="email" type="email" autocomplete="username" />
      </label>
      <label>
        密碼
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          @keyup.enter="login"
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="primary" :disabled="loading" type="button" @click="login">
        {{ loading ? "登入中..." : "登入" }}
      </button>
    </section>
  </main>

  <div v-else class="app-shell">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <div class="brand-mark small">YL</div>
        <div>
          <strong>SEO Control</strong>
          <span>Access Center</span>
        </div>
      </div>
      <nav>
        <button
          :class="{ active: activePanel === 'overview' }"
          @click="activePanel = 'overview'"
        >
          總覽
        </button>
        <button
          v-if="capabilities?.permissions.includes('roles.read')"
          :class="{ active: activePanel === 'roles' }"
          @click="activePanel = 'roles'"
        >
          角色與權限
        </button>
        <button
          :class="{ active: activePanel === 'evaluate' }"
          @click="activePanel = 'evaluate'"
        >
          授權測試器
        </button>
      </nav>
      <div class="profile">
        <span class="avatar">{{ user.displayName.slice(0, 1) }}</span>
        <div>
          <strong>{{ user.displayName }}</strong>
          <span>{{ user.email }}</span>
        </div>
        <button type="button" @click="logout">登出</button>
      </div>
    </aside>

    <section class="content">
      <header class="topbar">
        <div>
          <p class="eyebrow">Access control POC</p>
          <h1>
            {{
              activePanel === "overview"
                ? "權限總覽"
                : activePanel === "roles"
                  ? "角色與權限"
                  : "授權測試器"
            }}
          </h1>
        </div>
        <span :class="['status-pill', isAdmin ? 'admin' : 'scoped']">
          {{ isAdmin ? "全域存取" : "限定資料範圍" }}
        </span>
      </header>

      <p v-if="error" class="error banner">{{ error }}</p>

      <template v-if="activePanel === 'overview'">
        <div class="metric-grid">
          <article class="metric-card">
            <span>有效功能權限</span>
            <strong>{{ capabilities?.permissions.length ?? 0 }}</strong>
            <small>由所有角色權限聯集計算</small>
          </article>
          <article class="metric-card">
            <span>可存取客戶</span>
            <strong>{{ isAdmin ? "全部" : capabilities?.customerIds.length }}</strong>
            <small>客戶授權包含其所有任務</small>
          </article>
          <article class="metric-card">
            <span>單獨授權任務</span>
            <strong>{{ isAdmin ? "全部" : capabilities?.taskIds.length }}</strong>
            <small>不會擴張至同客戶其他任務</small>
          </article>
        </div>

        <div class="two-column">
          <article class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Capabilities</p>
                <h2>目前功能權限</h2>
              </div>
              <span>{{ capabilities?.permissions.length }}</span>
            </div>
            <div class="chip-list">
              <span
                v-for="permission in capabilities?.permissions"
                :key="permission"
                class="chip"
              >
                {{ permission }}
              </span>
            </div>
          </article>

          <article class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Data scope</p>
                <h2>資料存取範圍</h2>
              </div>
            </div>
            <template v-if="isAdmin">
              <div class="global-access">
                <strong>Admin 全域存取</strong>
                <p>不需逐筆指派客戶或任務。</p>
              </div>
            </template>
            <template v-else>
              <p class="scope-label">客戶</p>
              <code v-for="id in capabilities?.customerIds" :key="id">{{ id }}</code>
              <p class="scope-label">任務</p>
              <code v-for="id in capabilities?.taskIds" :key="id">{{ id }}</code>
            </template>
          </article>
        </div>

        <article v-if="users.length" class="panel">
          <div class="panel-heading">
            <div>
              <p class="eyebrow">Users</p>
              <h2>後台帳號</h2>
            </div>
            <span>{{ users.length }}</span>
          </div>
          <div class="table">
            <div class="table-row table-head">
              <span>使用者</span><span>狀態</span><span>客戶</span><span>任務</span>
            </div>
            <div v-for="item in users" :key="item.id" class="table-row">
              <span><strong>{{ item.displayName }}</strong><small>{{ item.email }}</small></span>
              <span>{{ item.status }}</span>
              <span>{{ item.customerIds.length || "全域／未指派" }}</span>
              <span>{{ item.taskIds.length || "全域／未指派" }}</span>
            </div>
          </div>
        </article>
      </template>

      <template v-else-if="activePanel === 'roles'">
        <div class="two-column roles-layout">
          <article class="panel">
            <div class="panel-heading">
              <div>
                <p class="eyebrow">Roles</p>
                <h2>現有角色</h2>
              </div>
              <span>{{ roles.length }}</span>
            </div>
            <div v-for="role in roles" :key="role.id" class="role-card">
              <div>
                <strong>{{ role.name }}</strong>
                <span v-if="role.isSystem">系統角色</span>
              </div>
              <small>{{ role.permissions.length }} 項權限</small>
              <div class="chip-list compact">
                <span v-for="permission in role.permissions" :key="permission" class="chip">
                  {{ permission }}
                </span>
              </div>
            </div>
          </article>

          <article v-if="canManageRoles" class="panel sticky-panel">
            <p class="eyebrow">Create role</p>
            <h2>建立展示角色</h2>
            <label>
              角色名稱
              <input v-model="roleName" placeholder="例如 Content Reviewer" />
            </label>
            <fieldset>
              <legend>選擇權限</legend>
              <label v-for="permission in permissions" :key="permission" class="check">
                <input v-model="selectedPermissions" type="checkbox" :value="permission" />
                <span>{{ permission }}</span>
              </label>
            </fieldset>
            <button class="primary" :disabled="loading" @click="createRole">
              建立角色
            </button>
          </article>
        </div>
      </template>

      <template v-else>
        <div class="two-column">
          <article class="panel">
            <p class="eyebrow">Policy input</p>
            <h2>模擬資源操作</h2>
            <label>
              Permission
              <select v-model="evaluatePermission">
                <option v-for="item in capabilities?.permissions" :key="item" :value="item">
                  {{ item }}
                </option>
                <option value="tasks.delete">tasks.delete</option>
              </select>
            </label>
            <label>
              資源類型
              <select v-model="resourceType">
                <option value="customer">Customer</option>
                <option value="task">Task</option>
              </select>
            </label>
            <label>
              Customer ID
              <input v-model="customerId" />
            </label>
            <label v-if="resourceType === 'task'">
              Task ID
              <input v-model="taskId" />
            </label>
            <button class="primary" :disabled="loading" @click="evaluate">
              執行授權判斷
            </button>
          </article>

          <article class="panel decision-panel">
            <p class="eyebrow">Policy result</p>
            <template v-if="decision">
              <div :class="['decision-icon', decision.allowed ? 'allowed' : 'denied']">
                {{ decision.allowed ? "✓" : "×" }}
              </div>
              <h2>{{ decision.allowed ? "允許操作" : "拒絕操作" }}</h2>
              <code>{{ decision.reasonCode }}</code>
              <p class="muted">判斷同時考慮角色功能權限與客戶／任務資料範圍。</p>
            </template>
            <template v-else>
              <div class="decision-empty">等待測試</div>
              <p class="muted">送出左側條件後，結果會顯示於此。</p>
            </template>
          </article>
        </div>
      </template>
    </section>
  </div>
</template>
