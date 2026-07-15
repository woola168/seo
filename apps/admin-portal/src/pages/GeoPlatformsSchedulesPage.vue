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
import { formatDateInput, formatGeoDate, useGeoProjectWorkspace } from "../composables/geo-project-workspace";
import { api } from "../services/api";
import type { GeoSchedule } from "../types";

const workspace = useGeoProjectWorkspace();
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();
const drawerOpen = ref(false);
const search = ref("");
const page = ref(1);
const perPage = 10;
const platformFilters = ref<string[]>([]);
const frequencyFilters = ref<string[]>([]);
const statusFilters = ref<string[]>([]);
const form = reactive({
  queryId: "",
  platformId: "",
  frequency: "daily" as GeoSchedule["frequency"],
  priority: "normal" as GeoSchedule["priority"],
  timezone: "Asia/Taipei",
  nextRunAt: "2026-06-24T09:00",
});

const platformSummaries = computed(() =>
  workspace.geoPlatformCatalog.map((platform) => ({
    ...platform,
    assignmentCount: workspace.queryPlatforms.value.filter((item) => item.platformId === platform.id).length,
  })),
);
const platformFilterOptions = computed(() => workspace.geoPlatformCatalog.map((platform) => platform.name));
const filteredSchedules = computed(() =>
  workspace.schedules.value.filter((schedule) => {
    const keyword = search.value.trim().toLowerCase();
    const matchesKeyword =
      !keyword ||
      [queryLabel(schedule.queryId), platformName(schedule.platformId)]
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    return (
      matchesKeyword &&
      (!platformFilters.value.length || platformFilters.value.includes(platformName(schedule.platformId))) &&
      (!frequencyFilters.value.length || frequencyFilters.value.includes(schedule.frequency)) &&
      (!statusFilters.value.length || statusFilters.value.includes(schedule.status))
    );
  }),
);
const activeFilterCount = computed(() => platformFilters.value.length + frequencyFilters.value.length + statusFilters.value.length);
const pageRows = computed(() => filteredSchedules.value.slice((page.value - 1) * perPage, page.value * perPage));

onMounted(() => {
  void workspace.loadProjects();
});

function queryLabel(queryId: string): string {
  return workspace.queries.value.find((query) => query.id === queryId)?.queryText ?? "-";
}

function platformName(platformId: string): string {
  return workspace.geoPlatformCatalog.find((platform) => platform.id === platformId)?.name ?? platformId;
}

function openCreate(): void {
  form.queryId = workspace.selectedProjectQueries.value[0]?.id ?? "";
  form.platformId = workspace.geoPlatformCatalog[0]?.id ?? "";
  form.frequency = "daily";
  form.priority = "normal";
  form.timezone = "Asia/Taipei";
  form.nextRunAt = "2026-06-24T09:00";
  clearFormErrors();
  drawerOpen.value = true;
}

function closeDrawer(): void {
  drawerOpen.value = false;
  clearFormErrors();
}

function validate(): boolean {
  const errors: GeoFormValidationError[] = [];
  if (!form.queryId) errors.push({ field: "queryId", message: "請選擇 Query。" });
  if (!form.platformId) errors.push({ field: "platformId", message: "請選擇 Platform。" });
  if (!form.frequency) errors.push({ field: "frequency", message: "請選擇 Frequency。" });
  if (form.frequency !== "manual" && !form.nextRunAt) {
    errors.push({ field: "nextRunAt", message: "請設定 Next run。" });
  }
  return setFormErrors(errors);
}

async function submit(): Promise<void> {
  if (!validate()) return;
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const schedule = await api.geoAnalysis.createSchedule(form.queryId, {
      platformId: form.platformId,
      frequency: form.frequency,
      priority: form.priority,
      timezone: form.timezone.trim() || "Asia/Taipei",
      nextRunAt: form.frequency === "manual" ? null : formatDateInput(form.nextRunAt),
      status: "active",
    });
    workspace.schedules.value.unshift(schedule);
    workspace.setMessage("已建立 schedule。");
    closeDrawer();
  });
}

async function toggleSchedule(schedule: GeoSchedule): Promise<void> {
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const updated = await api.geoAnalysis.updateSchedule(schedule.id, {
      platformId: schedule.platformId,
      frequency: schedule.frequency,
      priority: schedule.priority,
      timezone: schedule.timezone,
      nextRunAt: schedule.nextRunAt,
      status: schedule.status === "active" ? "paused" : "active",
    });
    workspace.schedules.value = workspace.schedules.value.map((item) => item.id === updated.id ? updated : item);
    workspace.setMessage("已更新 schedule 狀態。");
  });
}

async function deleteSchedule(scheduleId: string): Promise<void> {
  await workspace.runAction(async () => {
    if (!workspace.usingMockData.value) await api.geoAnalysis.deleteSchedule(scheduleId);
    workspace.schedules.value = workspace.schedules.value.filter((schedule) => schedule.id !== scheduleId);
    workspace.setMessage("已刪除 schedule。");
  });
}

function clearFilters(): void {
  search.value = "";
  platformFilters.value = [];
  frequencyFilters.value = [];
  statusFilters.value = [];
  page.value = 1;
}
</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader title="Platforms & Schedules" description="AI 模型平台與 Schedule 管理。" :projects="workspace.projects.value" :selected-project-id="workspace.selectedProjectId.value" :loading="workspace.loading.value" action-label="新增 Schedule" @update:selected-project-id="workspace.selectedProjectId.value = $event" @refresh="workspace.loadProjects" @action="openCreate" />
    <div v-if="workspace.usingMockData.value" class="mock-notice subtle"><AppIcon name="alert-circle" :size="17" />API 無法使用，目前顯示示意資料。</div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div class="geo-local-message">{{ workspace.localMessage.value }}</div>
    <div v-if="workspace.loading.value && !workspace.selectedProject.value" class="empty-state">正在載入 GEO 資料</div>
    <div v-else-if="!workspace.selectedProject.value" class="empty-state">請先建立 GEO project。</div>

    <template v-else>
      <div class="geo-platform-grid">
        <article v-for="platform in platformSummaries" :key="platform.id" class="card geo-platform-card">
          <strong>{{ platform.name }}</strong>
          <span>{{ platform.model }}</span>
          <small>{{ platform.assignmentCount }} query assignments</small>
          <GeoStatusBadge :value="platform.status" />
        </article>
      </div>

      <article class="card geo-kinsan-card">
        <header class="geo-kinsan-card-header">
          <strong>Schedules</strong>
          <span>共 {{ workspace.schedules.value.length }} 筆</span>
        </header>
        <div class="geo-kinsan-toolbar">
          <label class="geo-search-field"><AppIcon name="search" :size="16" /><input v-model="search" type="search" placeholder="搜尋 query、platform…" @input="page = 1" /></label>
          <GeoFilterDropdown label="Platform" :options="platformFilterOptions" :selected="platformFilters" @update:selected="platformFilters = $event; page = 1" />
          <GeoFilterDropdown label="Frequency" :options="['daily', 'weekly', 'manual']" :selected="frequencyFilters" @update:selected="frequencyFilters = $event; page = 1" />
          <GeoFilterDropdown label="Status" :options="['active', 'paused']" :selected="statusFilters" @update:selected="statusFilters = $event; page = 1" />
          <span v-if="activeFilterCount || search" class="geo-clear-filters" @click="clearFilters">清除全部</span>
        </div>
        <div class="geo-kinsan-table-wrap">
          <table class="data-table geo-table geo-kinsan-table">
            <thead><tr><th>Query</th><th>Platform</th><th>Frequency</th><th>Next run</th><th>Status</th><th class="sticky-action">Actions</th></tr></thead>
            <tbody>
              <tr v-for="schedule in pageRows" :key="schedule.id">
                <td>{{ queryLabel(schedule.queryId) }}</td>
                <td>{{ platformName(schedule.platformId) }}</td>
                <td>{{ schedule.frequency }} <span class="text-muted">·</span> {{ schedule.timezone }}</td>
                <td>{{ formatGeoDate(schedule.nextRunAt) }}</td>
                <td><GeoStatusBadge :value="schedule.status" /></td>
                <td class="sticky-action">
                  <div class="geo-row-actions">
                    <button class="geo-row-action danger" type="button" title="刪除" @click="deleteSchedule(schedule.id)">
                      <AppIcon name="trash" :size="14" />
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredSchedules.length === 0"><td class="geo-table-empty" colspan="6">尚無 schedule。</td></tr>
            </tbody>
          </table>
        </div>
        <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredSchedules.length" />
      </article>
    </template>

    <GeoActionDrawer :open="drawerOpen" title="建立 Schedule" description="建立 query/platform 的週期排程。" @close="closeDrawer">
      <form class="geo-drawer-form" @submit.prevent="submit">
        <GeoFormField label="Query" required :error="formErrors.queryId"><select v-model="form.queryId" :class="{ invalid: formErrors.queryId }" @change="clearFieldError('queryId')"><option value="">請選擇 Query</option><option v-for="query in workspace.selectedProjectQueries.value" :key="query.id" :value="query.id">{{ query.queryText }}</option></select></GeoFormField>
        <GeoFormField label="Platform" required :error="formErrors.platformId"><select v-model="form.platformId" :class="{ invalid: formErrors.platformId }" @change="clearFieldError('platformId')"><option v-for="platform in workspace.geoPlatformCatalog" :key="platform.id" :value="platform.id">{{ platform.name }} / {{ platform.model }}</option></select></GeoFormField>
        <GeoFormField label="Frequency" required :error="formErrors.frequency"><select v-model="form.frequency" :class="{ invalid: formErrors.frequency }" @change="clearFieldError('frequency')"><option value="daily">daily</option><option value="weekly">weekly</option><option value="manual">manual</option></select></GeoFormField>
        <GeoFormField label="Priority"><select v-model="form.priority"><option value="low">low</option><option value="normal">normal</option><option value="high">high</option></select></GeoFormField>
        <GeoFormField label="Timezone"><input v-model="form.timezone" type="text" /></GeoFormField>
        <GeoFormField label="Next run" :required="form.frequency !== 'manual'" :error="formErrors.nextRunAt"><input v-model="form.nextRunAt" type="datetime-local" :class="{ invalid: formErrors.nextRunAt }" :disabled="form.frequency === 'manual'" @input="clearFieldError('nextRunAt')" /></GeoFormField>
        <div class="geo-drawer-actions"><button class="button button-secondary" type="button" @click="closeDrawer">取消</button><button class="button button-primary" type="submit" :disabled="workspace.actionLoading.value">建立 Schedule</button></div>
      </form>
    </GeoActionDrawer>
  </section>
</template>
