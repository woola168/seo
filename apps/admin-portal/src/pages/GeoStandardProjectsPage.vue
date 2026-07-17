<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import GeoActionDrawer from "../components/geo/GeoActionDrawer.vue";
import GeoFilterDropdown from "../components/geo/GeoFilterDropdown.vue";
import GeoFormField from "../components/geo/GeoFormField.vue";
import GeoPageHeader from "../components/geo/GeoPageHeader.vue";
import GeoPagination from "../components/geo/GeoPagination.vue";
import GeoStatusBadge from "../components/geo/GeoStatusBadge.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useGeoFormErrors, type GeoFormValidationError } from "../composables/geo-form-errors";
import { useGeoProjectWorkspace } from "../composables/geo-project-workspace";
import type { GeoProject } from "../types";

const workspace = useGeoProjectWorkspace("projects");
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();
const search = ref("");
const drawerOpen = ref(false);
const viewProject = ref<GeoProject | null>(null);
const page = ref(1);
const perPage = 10;
const statusFilters = ref<string[]>([]);
const localeFilters = ref<string[]>([]);
const customerFilters = ref<string[]>([]);
const form = reactive({
  name: "",
  customerId: "",
  defaultRegion: "TW",
  defaultLanguage: "zh-TW",
  dailyRunBudget: 200,
});

const localeOptions = computed(() =>
  Array.from(new Set(workspace.projects.value.map((project) => `${project.defaultRegion} / ${project.defaultLanguage}`))),
);
const customerOptions = computed(() =>
  Array.from(new Set(workspace.projects.value.map((project) => project.customerName))),
);
const filteredProjects = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return workspace.projects.value.filter((project) => {
    const locale = `${project.defaultRegion} / ${project.defaultLanguage}`;
    const matchesKeyword =
      !keyword ||
      [project.name, project.customerName]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    return (
      matchesKeyword &&
      (!statusFilters.value.length || statusFilters.value.includes(project.status)) &&
      (!localeFilters.value.length || localeFilters.value.includes(locale)) &&
      (!customerFilters.value.length || customerFilters.value.includes(project.customerName))
    );
  });
});
const activeFilterCount = computed(
  () => statusFilters.value.length + localeFilters.value.length + customerFilters.value.length,
);
const pageRows = computed(() => filteredProjects.value.slice((page.value - 1) * perPage, page.value * perPage));

onMounted(() => {
  void workspace.loadProjects();
});

function openCreate(): void {
  resetForm();
  drawerOpen.value = true;
}

function closeDrawer(): void {
  drawerOpen.value = false;
  clearFormErrors();
}

function openProjectView(project: GeoProject): void {
  viewProject.value = project;
}

function closeProjectView(): void {
  viewProject.value = null;
}

function resetForm(): void {
  form.name = "";
  form.customerId = workspace.customers.value[0]?.id ?? "";
  form.defaultRegion = "TW";
  form.defaultLanguage = "zh-TW";
  form.dailyRunBudget = 200;
  clearFormErrors();
}

function validate(): boolean {
  const errors: GeoFormValidationError[] = [];
  if (!form.name.trim()) errors.push({ field: "name", message: "請輸入 Project 名稱。" });
  if (!form.customerId.trim()) errors.push({ field: "customerId", message: "請選擇或輸入 Customer。" });
  if (!form.defaultRegion.trim()) errors.push({ field: "defaultRegion", message: "請輸入 Region。" });
  if (!form.defaultLanguage.trim()) errors.push({ field: "defaultLanguage", message: "請輸入 Language。" });
  return setFormErrors(errors);
}

async function submit(): Promise<void> {
  if (!validate()) return;
  const created = await workspace.createProject({
    customerId: form.customerId.trim(),
    name: form.name.trim(),
    defaultRegion: form.defaultRegion.trim(),
    defaultLanguage: form.defaultLanguage.trim(),
    status: "active",
    dailyRunBudget: Number(form.dailyRunBudget) || 0,
  });
  if (created) closeDrawer();
}

function clearFilters(): void {
  statusFilters.value = [];
  localeFilters.value = [];
  customerFilters.value = [];
  search.value = "";
  page.value = 1;
}

</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader
      title="Projects"
      description="管理 GEO project 與客戶綁定。"
      :projects="workspace.projects.value"
      :selected-project-id="workspace.selectedProjectId.value"
      :loading="workspace.loading.value"
      action-label="新增專案"
      @update:selected-project-id="workspace.selectedProjectId.value = $event"
      @refresh="workspace.loadProjects"
      @action="openCreate"
    />

    <div v-if="workspace.usingMockData.value" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />
      API 無法使用，目前顯示示意資料；新增與刪除操作會提示未呼叫 API。
    </div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div class="geo-local-message">{{ workspace.localMessage.value }}</div>

    <article class="card geo-kinsan-card">
      <header class="geo-kinsan-card-header">
        <strong>Projects</strong>
        <span>共 {{ workspace.projects.value.length }} 筆</span>
      </header>
      <div class="geo-kinsan-toolbar">
        <label class="geo-search-field">
          <AppIcon name="search" :size="16" />
          <input v-model="search" type="search" placeholder="搜尋專案、客戶…" @input="page = 1" />
        </label>
        <GeoFilterDropdown label="Status" :options="['active', 'paused', 'archived']" :selected="statusFilters" @update:selected="statusFilters = $event; page = 1" />
        <GeoFilterDropdown label="Locale" :options="localeOptions" :selected="localeFilters" @update:selected="localeFilters = $event; page = 1" />
        <GeoFilterDropdown label="Customer" :options="customerOptions" :selected="customerFilters" @update:selected="customerFilters = $event; page = 1" />
        <span v-if="activeFilterCount || search" class="geo-clear-filters" @click="clearFilters">清除全部</span>
      </div>

      <div class="geo-kinsan-table-wrap">
        <table class="data-table geo-table geo-kinsan-table">
          <thead>
            <tr>
              <th>Project</th>
              <th>Customer</th>
              <th>Locale</th>
              <th>Budget</th>
              <th>Status</th>
              <th class="sticky-action">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in pageRows" :key="project.id">
              <td><strong>{{ project.name }}</strong></td>
              <td>{{ project.customerName }}</td>
              <td>{{ project.defaultRegion }} / {{ project.defaultLanguage }}</td>
              <td>{{ project.dailyRunBudget }}</td>
              <td><GeoStatusBadge :value="project.status" /></td>
              <td class="sticky-action">
                <div class="geo-row-actions">
                  <button class="geo-row-action" type="button" title="檢視 Project" @click.stop="openProjectView(project)">
                    <AppIcon name="edit" :size="14" />
                  </button>
                  <button class="geo-row-action danger" type="button" title="刪除" @click="workspace.deleteProject(project.id)">
                    <AppIcon name="trash" :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredProjects.length === 0"><td class="geo-table-empty" colspan="6">找不到符合條件的 project。</td></tr>
          </tbody>
        </table>
      </div>
      <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredProjects.length" />
    </article>

    <GeoActionDrawer :open="drawerOpen" title="建立 Project" description="建立要追蹤的 GEO 專案。" @close="closeDrawer">
      <form class="geo-drawer-form" @submit.prevent="submit">
        <GeoFormField label="Project 名稱" required :error="formErrors.name">
          <input v-model="form.name" type="text" :class="{ invalid: formErrors.name }" placeholder="例如：品牌 GEO 追蹤" @input="clearFieldError('name')" />
        </GeoFormField>
        <GeoFormField label="Customer" required :error="formErrors.customerId">
          <select v-if="workspace.customers.value.length" v-model="form.customerId" :class="{ invalid: formErrors.customerId }" @change="clearFieldError('customerId')">
            <option value="">請選擇 customer</option>
            <option v-for="customer in workspace.customers.value" :key="customer.id" :value="customer.id">{{ customer.name }}</option>
          </select>
          <input v-else v-model="form.customerId" type="text" :class="{ invalid: formErrors.customerId }" placeholder="customer UUID" @input="clearFieldError('customerId')" />
        </GeoFormField>
        <GeoFormField label="Region" required :error="formErrors.defaultRegion">
          <input v-model="form.defaultRegion" type="text" :class="{ invalid: formErrors.defaultRegion }" @input="clearFieldError('defaultRegion')" />
        </GeoFormField>
        <GeoFormField label="Language" required :error="formErrors.defaultLanguage">
          <input v-model="form.defaultLanguage" type="text" :class="{ invalid: formErrors.defaultLanguage }" @input="clearFieldError('defaultLanguage')" />
        </GeoFormField>
        <GeoFormField label="Daily Budget">
          <input v-model.number="form.dailyRunBudget" type="number" min="0" />
        </GeoFormField>
        <div class="geo-drawer-actions">
          <button class="button button-secondary" type="button" @click="closeDrawer">取消</button>
          <button class="button button-primary" type="submit" :disabled="workspace.actionLoading.value">建立 Project</button>
        </div>
      </form>
    </GeoActionDrawer>

    <GeoActionDrawer
      :open="Boolean(viewProject)"
      title="Project 詳細資料"
      description="目前為唯讀檢視，欄位配置與新增 Project 相同。"
      @close="closeProjectView"
    >
      <div v-if="viewProject" class="geo-drawer-form">
        <GeoFormField label="Project 名稱" required>
          <input :value="viewProject.name" type="text" readonly />
        </GeoFormField>
        <GeoFormField label="Customer" required>
          <input :value="viewProject.customerName" type="text" readonly />
        </GeoFormField>
        <GeoFormField label="Region" required>
          <input :value="viewProject.defaultRegion" type="text" readonly />
        </GeoFormField>
        <GeoFormField label="Language" required>
          <input :value="viewProject.defaultLanguage" type="text" readonly />
        </GeoFormField>
        <GeoFormField label="Daily Budget">
          <input :value="viewProject.dailyRunBudget" type="number" readonly />
        </GeoFormField>
        <div class="geo-drawer-actions">
          <button class="button button-secondary" type="button" @click="closeProjectView">關閉</button>
        </div>
      </div>
    </GeoActionDrawer>
  </section>
</template>
