<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import AppIcon from "../ui/AppIcon.vue";
import AppPagination from "../ui/AppPagination.vue";
import { queryMembers } from "../../composables/member-query";
import type {
  MemberQuery,
  MemberSortField,
  MemberView,
  Role,
} from "../../types";

const props = defineProps<{
  members: MemberView[];
  roles: Role[];
  canEditRoles: boolean;
  canManageGrants: boolean;
  loading: boolean;
}>();

const emit = defineEmits<{
  "update-roles": [userId: string, roleIds: string[]];
  "update-customers": [userId: string, customerIds: string[]];
  "update-tasks": [userId: string, taskIds: string[]];
  unavailable: [label: string];
}>();

const query = reactive<MemberQuery>({
  search: "",
  role: "",
  department: "",
  status: "",
  sortField: "displayName",
  sortDirection: "asc",
  page: 1,
  pageSize: 8,
});
const selectedMemberId = ref("");
const editingRoleIds = ref<string[]>([]);
const customerIdsText = ref("");
const taskIdsText = ref("");

const result = computed(() => queryMembers(props.members, query));
const departments = computed(() =>
  [...new Set(props.members.map((member) => member.department).filter(Boolean))].sort(),
);
const statuses = computed(() =>
  [...new Set(props.members.map((member) => member.status))].sort(),
);
const selectedMember = computed(
  () => props.members.find((member) => member.id === selectedMemberId.value) ?? null,
);

watch(
  () => [
    query.search,
    query.role,
    query.department,
    query.status,
    query.sortField,
    query.sortDirection,
  ],
  () => {
    query.page = 1;
  },
);

watch(selectedMember, (member) => {
  editingRoleIds.value = member ? [...member.roleIds] : [];
  customerIdsText.value = member?.customerIds.join("\n") ?? "";
  taskIdsText.value = member?.taskIds.join("\n") ?? "";
});

function sort(field: MemberSortField): void {
  if (query.sortField === field) {
    query.sortDirection = query.sortDirection === "asc" ? "desc" : "asc";
  } else {
    query.sortField = field;
    query.sortDirection = "asc";
  }
}

function clearFilters(): void {
  query.search = "";
  query.role = "";
  query.department = "";
  query.status = "";
}

function parseIds(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
</script>

<template>
  <div class="permission-content">
    <div class="toolbar">
      <label class="filter-search">
        <AppIcon name="search" :size="16" />
        <input v-model="query.search" type="search" placeholder="搜尋姓名或 Email..." />
      </label>
      <select v-model="query.role" aria-label="角色篩選">
        <option value="">所有角色</option>
        <option v-for="role in roles" :key="role.id" :value="role.name">
          {{ role.name }}
        </option>
      </select>
      <select v-model="query.department" aria-label="部門篩選">
        <option value="">所有部門</option>
        <option v-for="department in departments" :key="department ?? ''">
          {{ department }}
        </option>
      </select>
      <select v-model="query.status" aria-label="狀態篩選">
        <option value="">所有狀態</option>
        <option v-for="status in statuses" :key="status" :value="status">
          {{ status }}
        </option>
      </select>
      <button class="button button-ghost" type="button" @click="clearFilters">
        清除篩選
      </button>
      <button
        class="button button-primary toolbar-primary"
        type="button"
        @click="$emit('unavailable', '新增員工')"
      >
        <AppIcon name="plus" :size="16" />新增員工
      </button>
    </div>

    <div class="mock-notice subtle">
      部門、最後登入與帳號來源為暫時補充資料；姓名、Email、狀態、角色與存取範圍來自 access-control API。
    </div>

    <div class="table-scroll card table-card">
      <table class="data-table member-table">
        <thead>
          <tr>
            <th><button type="button" @click="sort('displayName')">姓名</button></th>
            <th><button type="button" @click="sort('email')">Email</button></th>
            <th><button type="button" @click="sort('role')">角色</button></th>
            <th><button type="button" @click="sort('department')">部門</button></th>
            <th><button type="button" @click="sort('status')">狀態</button></th>
            <th><button type="button" @click="sort('lastLogin')">最後登入</button></th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in result.items" :key="member.id">
            <td>
              <div class="identity-cell">
                <span class="round-avatar" :style="{ background: member.color }">
                  {{ member.displayName.slice(0, 1) }}
                </span>
                <strong>{{ member.displayName }}</strong>
              </div>
            </td>
            <td>{{ member.email }}</td>
            <td>
              <span
                v-for="roleName in member.roleNames"
                :key="roleName"
                class="badge badge-role"
              >
                {{ roleName }}
              </span>
              <span v-if="!member.roleNames.length" class="muted">未指派</span>
            </td>
            <td>{{ member.department ?? "待 API 提供" }}</td>
            <td><span class="status-dot"></span>{{ member.status }}</td>
            <td>{{ member.lastLogin ?? "尚未登入" }}</td>
            <td>
              <div class="row-actions">
                <button
                  class="icon-button"
                  type="button"
                  aria-label="檢視與編輯權限"
                  @click="selectedMemberId = member.id"
                >
                  <AppIcon name="edit" :size="16" />
                </button>
                <button
                  class="icon-button"
                  type="button"
                  aria-label="更多操作"
                  @click="$emit('unavailable', `${member.displayName}帳號操作`)"
                >
                  <AppIcon name="more" :size="16" />
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!result.items.length">
            <td colspan="7">
              <div class="empty-state">
                <AppIcon name="search" :size="28" />
                <strong>沒有符合條件的員工</strong>
                <span>請調整搜尋或篩選條件。</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <AppPagination
        :page="result.page"
        :total-pages="result.totalPages"
        :total="result.total"
        @change="query.page = $event"
      />
    </div>

    <div v-if="selectedMember" class="modal-backdrop" @click.self="selectedMemberId = ''">
      <section class="modal" role="dialog" aria-modal="true" aria-label="編輯員工權限">
        <header class="modal-header">
          <div>
            <h2>{{ selectedMember.displayName }}</h2>
            <p>{{ selectedMember.email }}</p>
          </div>
          <button class="icon-button" type="button" @click="selectedMemberId = ''">
            <AppIcon name="x" :size="18" />
          </button>
        </header>
        <div class="modal-body">
          <fieldset>
            <p v-if="!canEditRoles" class="form-help">
              需要 users.manage 與 roles.read 才能編輯角色。
            </p>
            <legend>角色</legend>
            <label v-for="role in roles" :key="role.id" class="checkbox-row">
              <input
                v-model="editingRoleIds"
                type="checkbox"
                :value="role.id"
                :disabled="!canEditRoles"
              />
              <span>{{ role.name }}</span>
            </label>
          </fieldset>
          <button
            class="button button-primary"
            type="button"
            :disabled="!canEditRoles || loading"
            @click="emit('update-roles', selectedMember.id, editingRoleIds)"
          >
            儲存角色
          </button>

          <label class="form-field">
            <span>客戶存取 ID（每行一筆 UUID）</span>
            <textarea
              v-model="customerIdsText"
              rows="4"
              :disabled="!canManageGrants"
            ></textarea>
          </label>
          <button
            class="button button-secondary"
            type="button"
            :disabled="!canManageGrants || loading"
            @click="
              emit(
                'update-customers',
                selectedMember.id,
                parseIds(customerIdsText),
              )
            "
          >
            儲存客戶範圍
          </button>

          <label class="form-field">
            <span>任務存取 ID（每行一筆 UUID）</span>
            <textarea
              v-model="taskIdsText"
              rows="4"
              :disabled="!canManageGrants"
            ></textarea>
          </label>
          <button
            class="button button-secondary"
            type="button"
            :disabled="!canManageGrants || loading"
            @click="
              emit('update-tasks', selectedMember.id, parseIds(taskIdsText))
            "
          >
            儲存任務範圍
          </button>
        </div>
      </section>
    </div>
  </div>
</template>
