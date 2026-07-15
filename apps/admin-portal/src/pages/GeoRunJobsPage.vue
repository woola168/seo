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
import { api } from "../services/api";
import type { GeoJob } from "../types";

const workspace = useGeoProjectWorkspace("run-jobs");
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();
const drawerOpen = ref(false);
const search = ref("");
const page = ref(1);
const perPage = 10;
const platformFilters = ref<string[]>([]);
const statusFilters = ref<string[]>([]);
const form = reactive({
  queryId: "",
  platformId: "",
  priority: "normal" as GeoJob["priority"],
});

const platformFilterOptions = computed(() => workspace.geoPlatformCatalog.map((platform) => platform.name));
const filteredJobs = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return workspace.selectedProjectJobs.value.filter((job) => {
    const query = queryLabel(job.queryId);
    const platform = platformName(job.platformId);
    const matchesKeyword =
      !keyword || [query, platform].join(" ").toLowerCase().includes(keyword);
    return (
      matchesKeyword &&
      (!platformFilters.value.length || platformFilters.value.includes(platform)) &&
      (!statusFilters.value.length || statusFilters.value.includes(job.status))
    );
  });
});
const activeFilterCount = computed(() => platformFilters.value.length + statusFilters.value.length);
const pageRows = computed(() => filteredJobs.value.slice((page.value - 1) * perPage, page.value * perPage));

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
  form.priority = "normal";
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
  return setFormErrors(errors);
}

async function submit(): Promise<void> {
  if (!validate()) return;
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const job = await api.geoAnalysis.createJob(form.queryId, {
      platformId: form.platformId,
      scheduledFor: null,
      priority: form.priority,
      jobType: "manual_run",
    });
    workspace.jobs.value.unshift(job);
    workspace.setMessage("已建立 manual run job。");
    closeDrawer();
  });
}

async function cancelJob(jobId: string): Promise<void> {
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const job = await api.geoAnalysis.cancelJob(jobId);
    workspace.jobs.value = workspace.jobs.value.map((item) => item.id === job.id ? job : item);
    workspace.setMessage("已取消 job。");
  });
}

function clearFilters(): void {
  search.value = "";
  platformFilters.value = [];
  statusFilters.value = [];
  page.value = 1;
}
</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader title="Run Jobs" description="建立與派發 GEO manual run jobs。" :projects="workspace.projects.value" :selected-project-id="workspace.selectedProjectId.value" :loading="workspace.loading.value" action-label="建立 Manual Run" @update:selected-project-id="workspace.selectedProjectId.value = $event" @refresh="workspace.loadProjects" @action="openCreate" />
    <div v-if="workspace.usingMockData.value" class="mock-notice subtle"><AppIcon name="alert-circle" :size="17" />API 無法使用，目前顯示示意資料。</div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div class="geo-local-message">{{ workspace.localMessage.value }}</div>
    <div v-if="workspace.loading.value && !workspace.selectedProject.value" class="empty-state">正在載入 GEO 資料</div>
    <div v-else-if="!workspace.selectedProject.value" class="empty-state">請先建立 GEO project。</div>

    <article v-else class="card geo-kinsan-card">
      <header class="geo-kinsan-card-header">
        <strong>Jobs</strong>
        <span>共 {{ workspace.selectedProjectJobs.value.length }} 筆</span>
      </header>
      <div class="geo-kinsan-toolbar">
        <label class="geo-search-field"><AppIcon name="search" :size="16" /><input v-model="search" type="search" placeholder="搜尋 query、platform…" @input="page = 1" /></label>
        <GeoFilterDropdown label="Platform" :options="platformFilterOptions" :selected="platformFilters" @update:selected="platformFilters = $event; page = 1" />
        <GeoFilterDropdown label="Status" :options="['succeeded', 'running', 'failed', 'queued', 'external', 'pending', 'published', 'running_external', 'cancelled']" :selected="statusFilters" @update:selected="statusFilters = $event; page = 1" />
        <span v-if="activeFilterCount || search" class="geo-clear-filters" @click="clearFilters">清除全部</span>
      </div>
      <div class="geo-kinsan-table-wrap">
        <table class="data-table geo-table geo-kinsan-table geo-job-table">
          <thead><tr><th>Query</th><th>Platform</th><th>Status</th><th>Attempts</th><th class="sticky-action">Actions</th></tr></thead>
          <tbody>
            <tr v-for="job in pageRows" :key="job.id">
              <td>{{ queryLabel(job.queryId) }}</td>
              <td>{{ platformName(job.platformId) }}</td>
              <td><GeoStatusBadge :value="job.status" /></td>
              <td>{{ job.attemptCount }} / {{ job.maxAttempts }}</td>
              <td class="sticky-action">
                <div class="geo-row-actions">
                  <button class="geo-row-action danger" type="button" title="Cancel" aria-label="Cancel job" @click="cancelJob(job.id)">
                    <AppIcon name="x" :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredJobs.length === 0"><td class="geo-table-empty" colspan="5">找不到符合條件的 job。</td></tr>
          </tbody>
        </table>
      </div>
      <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredJobs.length" />
    </article>

    <GeoActionDrawer :open="drawerOpen" title="建立 Manual Run" description="建立後可透過 Dispatch 呼叫 publisher。" @close="closeDrawer">
      <form class="geo-drawer-form" @submit.prevent="submit">
        <GeoFormField label="Query" required :error="formErrors.queryId"><select v-model="form.queryId" :class="{ invalid: formErrors.queryId }" @change="clearFieldError('queryId')"><option value="">請選擇 Query</option><option v-for="query in workspace.selectedProjectQueries.value" :key="query.id" :value="query.id">{{ query.queryText }}</option></select></GeoFormField>
        <GeoFormField label="Platform" required :error="formErrors.platformId"><select v-model="form.platformId" :class="{ invalid: formErrors.platformId }" @change="clearFieldError('platformId')"><option v-for="platform in workspace.geoPlatformCatalog" :key="platform.id" :value="platform.id">{{ platform.name }}</option></select></GeoFormField>
        <GeoFormField label="Priority"><select v-model="form.priority"><option value="low">low</option><option value="normal">normal</option><option value="high">high</option></select></GeoFormField>
        <div class="geo-drawer-actions"><button class="button button-secondary" type="button" @click="closeDrawer">取消</button><button class="button button-primary" type="submit" :disabled="workspace.actionLoading.value">建立 Manual Run</button></div>
      </form>
    </GeoActionDrawer>
  </section>
</template>
