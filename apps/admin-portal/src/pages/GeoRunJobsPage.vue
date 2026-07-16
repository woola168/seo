<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import GeoFilterDropdown from "../components/geo/GeoFilterDropdown.vue";
import GeoPageHeader from "../components/geo/GeoPageHeader.vue";
import GeoPagination from "../components/geo/GeoPagination.vue";
import GeoStatusBadge from "../components/geo/GeoStatusBadge.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useGeoProjectWorkspace } from "../composables/geo-project-workspace";
import { api } from "../services/api";

const workspace = useGeoProjectWorkspace("run-jobs");
const search = ref("");
const page = ref(1);
const perPage = 10;
const platformFilters = ref<string[]>([]);
const statusFilters = ref<string[]>([]);

const platformFilterOptions = computed(() => workspace.platforms.value.map((platform) => platform.name));
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
  return workspace.platforms.value.find((platform) => platform.id === platformId)?.name ?? platformId;
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
    <GeoPageHeader title="Run Jobs" description="檢視每日自動排程與執行結果。" :projects="workspace.projects.value" :selected-project-id="workspace.selectedProjectId.value" :loading="workspace.loading.value" @update:selected-project-id="workspace.selectedProjectId.value = $event" @refresh="workspace.loadProjects" />
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

  </section>
</template>
