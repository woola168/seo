<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import GeoConfirmDialog from "../components/geo/GeoConfirmDialog.vue";
import GeoFilterDropdown from "../components/geo/GeoFilterDropdown.vue";
import GeoPageHeader from "../components/geo/GeoPageHeader.vue";
import GeoPagination from "../components/geo/GeoPagination.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import { useGeoProjectWorkspace } from "../composables/geo-project-workspace";
import { api } from "../services/api";
import { hasPermission } from "../utils/permissions";
import type { GeoProject, ToastTone } from "../types";

const props = defineProps<{ permissions: readonly string[] }>();
const emit = defineEmits<{ notify: [message: string, tone?: ToastTone] }>();
const router = useRouter();
const workspace = useGeoProjectWorkspace("projects");
const search = ref("");
const page = ref(1);
const perPage = 10;
const statusOptions = ["active", "paused", "archived"];
const statusLabels: Record<string, string> = {
  active: "進行中",
  paused: "已暫停",
  archived: "已下架",
};
const statusFilters = ref<string[]>([]);
const localeFilters = ref<string[]>([]);
const customerFilters = ref<string[]>([]);
const projectDetails = ref<Record<string, { domain: string; alias: string }>>({});
const archiveTarget = ref<GeoProject | null>(null);

const canCreate = computed(() => hasPermission(props.permissions, "geo.projects.create"));
const canUpdate = computed(() => hasPermission(props.permissions, "geo.projects.update"));
const canResearch = computed(() => hasPermission(props.permissions, "geo.queries.manage"));
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
    const detail = projectDetails.value[project.id];
    const matchesKeyword =
      !keyword ||
      [project.name, project.customerName, detail?.domain, detail?.alias]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(keyword);
    return matchesKeyword &&
      (!statusFilters.value.length || statusFilters.value.includes(project.status)) &&
      (!localeFilters.value.length || localeFilters.value.includes(locale)) &&
      (!customerFilters.value.length || customerFilters.value.includes(project.customerName));
  });
});
const activeFilterCount = computed(
  () => statusFilters.value.length + localeFilters.value.length + customerFilters.value.length,
);
const pageRows = computed(() => filteredProjects.value.slice((page.value - 1) * perPage, page.value * perPage));

function displayDomain(value: string | undefined): string {
  if (!value) return "—";
  try {
    return new URL(value.includes("://") ? value : `https://${value}`).host;
  } catch {
    return value.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
}

onMounted(() => void refresh());

async function refresh(): Promise<void> {
  await workspace.loadProjects();
  const results = await Promise.allSettled(
    workspace.projects.value.map(async (project) => {
      const [entities, aliases] = await Promise.all([
        api.geoAnalysis.entities(project.id),
        api.geoAnalysis.projectAliases(project.id),
      ]);
      const ownBrand = entities.items.find((entity) => entity.entityType === "own_brand");
      return {
        id: project.id,
        domain: ownBrand?.websiteUrl ?? "",
        alias: ownBrand
          ? aliases.items.filter((alias) => alias.entityId === ownBrand.id).map((alias) => alias.alias).join("、")
          : "",
      };
    }),
  );
  projectDetails.value = Object.fromEntries(
    results.flatMap((result) => result.status === "fulfilled" ? [[result.value.id, result.value]] : []),
  );
}

function clearFilters(): void {
  statusFilters.value = [];
  localeFilters.value = [];
  customerFilters.value = [];
  search.value = "";
  page.value = 1;
}

async function archiveProject(): Promise<void> {
  const project = archiveTarget.value;
  if (!project) return;
  try {
    await api.geoAnalysis.updateProject(project.id, {
      customerId: project.customerId,
      name: project.name,
      defaultRegion: project.defaultRegion,
      defaultLanguage: project.defaultLanguage,
      status: "archived",
      dailyRunBudget: project.dailyRunBudget,
    });
    archiveTarget.value = null;
    emit("notify", `「${project.name}」已下架。`, "success");
    await refresh();
  } catch (error) {
    emit("notify", error instanceof Error ? error.message : "Project 下架失敗。", "error");
  }
}
</script>

<template>
  <section class="page geo-page geo-kinsan-page geo-project-list-page">
    <GeoPageHeader
      title="Projects"
      description="管理 GEO 分析的專案，含 locale、預算與狀態"
      :projects="workspace.projects.value"
      :selected-project-id="workspace.selectedProjectId.value"
      :loading="workspace.loading.value"
      action-label="新增專案"
      :action-disabled="!canCreate"
      @update:selected-project-id="workspace.selectedProjectId.value = $event"
      @refresh="refresh"
      @action="router.push({ name: 'geo-project-new' })"
    />

    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <article class="card geo-kinsan-card">
      <div class="geo-kinsan-toolbar">
        <label class="geo-search-field">
          <AppIcon name="search" :size="16" />
          <input v-model="search" type="search" placeholder="搜尋專案、客戶…" @input="page = 1" />
        </label>
        <GeoFilterDropdown label="狀態" :options="statusOptions" :option-labels="statusLabels" :selected="statusFilters" show-select-all show-chevron @update:selected="statusFilters = $event; page = 1" />
        <GeoFilterDropdown label="地區" :options="localeOptions" :selected="localeFilters" show-select-all show-chevron @update:selected="localeFilters = $event; page = 1" />
        <GeoFilterDropdown label="客戶" :options="customerOptions" :selected="customerFilters" show-select-all show-chevron searchable @update:selected="customerFilters = $event; page = 1" />
        <button v-if="activeFilterCount || search" class="geo-clear-filters" type="button" @click="clearFilters">清除全部</button>
        <span class="geo-project-count">共 {{ filteredProjects.length }} 筆</span>
      </div>

      <div class="geo-kinsan-table-wrap">
        <table class="data-table geo-table geo-kinsan-table geo-project-table">
          <colgroup><col /><col class="customer-col" /><col class="locale-col" /><col class="alias-col" /><col class="status-col" /><col class="actions-col" /></colgroup>
          <thead><tr><th>Project</th><th>客戶</th><th>地區 / 語系</th><th>別名</th><th>狀態</th><th class="sticky-action">操作</th></tr></thead>
          <tbody>
            <tr v-for="project in pageRows" :key="project.id">
              <td><strong>{{ project.name }}</strong><small>{{ displayDomain(projectDetails[project.id]?.domain) }}</small></td>
              <td>{{ project.customerName }}</td>
              <td>{{ project.defaultRegion }}/{{ project.defaultLanguage }}</td>
              <td>{{ projectDetails[project.id]?.alias || '—' }}</td>
              <td><span class="geo-project-status" :class="`is-${project.status}`"><i></i>{{ statusLabels[project.status] ?? project.status }}</span></td>
              <td class="sticky-action"><div class="geo-row-actions">
                <button class="geo-row-action" type="button" title="編輯" :disabled="!canUpdate" @click.stop="router.push({ name: 'geo-project-edit', params: { projectId: project.id } })"><AppIcon name="edit" :size="14" /></button>
                <button class="geo-row-action" type="button" title="Query Search" :disabled="!canResearch" @click.stop="router.push({ name: 'geo-query-research', params: { projectId: project.id } })"><AppIcon name="search" :size="14" /></button>
                <button class="geo-row-action" type="button" :title="project.status === 'archived' ? '已下架' : '下架'" :disabled="!canUpdate || project.status === 'archived'" @click.stop="archiveTarget = project"><AppIcon name="x" :size="14" /></button>
              </div></td>
            </tr>
            <tr v-if="filteredProjects.length === 0"><td class="geo-table-empty" colspan="6">找不到符合條件的 Project。</td></tr>
          </tbody>
        </table>
      </div>
      <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredProjects.length" range-separator="–" />
    </article>

    <GeoConfirmDialog
      :open="Boolean(archiveTarget)"
      title="下架 Project"
      :message="`確定要下架「${archiveTarget?.name ?? ''}」嗎？下架後資料仍會保留。`"
      confirm-label="確定下架"
      @cancel="archiveTarget = null"
      @confirm="archiveProject"
    />
  </section>
</template>
