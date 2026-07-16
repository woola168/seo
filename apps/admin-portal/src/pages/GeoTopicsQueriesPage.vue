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
import type { GeoMarketType, GeoQuery } from "../types";

const workspace = useGeoProjectWorkspace("topics-queries");
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();
const search = ref("");
const drawerOpen = ref(false);
const showTopicForm = ref(false);
const page = ref(1);
const perPage = 10;
const stageFilters = ref<string[]>([]);
const priorityFilters = ref<string[]>([]);
const form = reactive({
  queryText: "",
  topicId: "",
  newTopicName: "",
  newTopicDescription: "",
  intent: "recommendation",
  buyerStage: "consideration",
  marketType: "b2c" as GeoMarketType,
  isBranded: false,
  priority: "normal" as GeoQuery["priority"],
});

const filteredQueries = computed(() => {
  const keyword = search.value.trim().toLowerCase();
  return workspace.selectedProjectQueries.value.filter((query) => {
    const topicName = topicLabel(query.topicId);
    const matchesKeyword =
      !keyword ||
      [query.queryText, topicName, query.intent ?? ""].join(" ").toLowerCase().includes(keyword);
    return (
      matchesKeyword &&
      (!stageFilters.value.length || stageFilters.value.includes(query.buyerStage ?? "")) &&
      (!priorityFilters.value.length || priorityFilters.value.includes(query.priority))
    );
  });
});
const stageOptions = computed(() =>
  Array.from(new Set(workspace.selectedProjectQueries.value.map((query) => query.buyerStage ?? "-"))).filter((value) => value !== "-"),
);
const activeFilterCount = computed(() => stageFilters.value.length + priorityFilters.value.length);
const pageRows = computed(() => filteredQueries.value.slice((page.value - 1) * perPage, page.value * perPage));

onMounted(() => {
  void workspace.loadProjects();
});

function topicLabel(topicId: string | null): string {
  return topicId ? workspace.topics.value.find((topic) => topic.id === topicId)?.name ?? "-" : "-";
}

function openCreate(): void {
  form.queryText = "";
  form.topicId = workspace.topics.value[0]?.id ?? "";
  form.newTopicName = "";
  form.newTopicDescription = "";
  form.intent = "recommendation";
  form.buyerStage = "consideration";
  form.marketType = "b2c";
  form.isBranded = false;
  form.priority = "normal";
  showTopicForm.value = false;
  clearFormErrors();
  drawerOpen.value = true;
}

function closeDrawer(): void {
  drawerOpen.value = false;
  showTopicForm.value = false;
  clearFormErrors();
}

function validateQuery(): boolean {
  const errors: GeoFormValidationError[] = [];
  if (!form.queryText.trim()) errors.push({ field: "queryText", message: "請輸入 Query 內容。" });
  if (!form.topicId) errors.push({ field: "topicId", message: "請選擇或建立 Topic。" });
  return setFormErrors(errors);
}

async function createInlineTopic(): Promise<void> {
  const name = form.newTopicName.trim();
  const errors: GeoFormValidationError[] = [];
  if (!name) errors.push({ field: "newTopicName", message: "請輸入 Topic 名稱。" });
  if (workspace.topics.value.some((topic) => topic.name === name)) {
    errors.push({ field: "newTopicName", message: "Topic 名稱已存在。" });
  }
  if (!setFormErrors(errors)) return;
  const project = workspace.selectedProject.value;
  if (!project) return;
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const topic = await api.geoAnalysis.createTopic(project.id, {
      name,
      description: form.newTopicDescription.trim(),
      status: "active",
    });
    workspace.topics.value.push(topic);
    form.topicId = topic.id;
    form.newTopicName = "";
    form.newTopicDescription = "";
    showTopicForm.value = false;
    clearFormErrors();
  });
}

async function submit(): Promise<void> {
  if (!validateQuery()) return;
  const project = workspace.selectedProject.value;
  if (!project) return;
  await workspace.runAction(async () => {
    if (workspace.usingMockData.value) throw new Error("目前使用示意資料，未呼叫 API。");
    const query = await api.geoAnalysis.createQuery(project.id, {
      topicId: form.topicId,
      queryText: form.queryText.trim(),
      region: project.defaultRegion,
      language: project.defaultLanguage,
      marketType: form.marketType,
      intent: form.intent.trim() || null,
      buyerStage: form.buyerStage.trim() || null,
      isBranded: form.isBranded,
      priority: form.priority,
      status: "active",
      metadata: {},
    });
    workspace.queries.value.unshift(query);
    workspace.setMessage("已建立 query。");
    closeDrawer();
  });
}

async function deleteQuery(queryId: string): Promise<void> {
  await workspace.runAction(async () => {
    if (!workspace.usingMockData.value) await api.geoAnalysis.deleteQuery(queryId);
    workspace.queries.value = workspace.queries.value.filter((query) => query.id !== queryId);
    workspace.queryPlatforms.value = workspace.queryPlatforms.value.filter((item) => item.queryId !== queryId);
    workspace.setMessage("已刪除 query。");
  });
}

function clearFilters(): void {
  search.value = "";
  stageFilters.value = [];
  priorityFilters.value = [];
  page.value = 1;
}
</script>

<template>
  <section class="page geo-page geo-kinsan-page">
    <GeoPageHeader title="Topics & Queries" description="管理 Topic 分類與 Query 內容。" :projects="workspace.projects.value" :selected-project-id="workspace.selectedProjectId.value" :loading="workspace.loading.value" action-label="新增 Query" @update:selected-project-id="workspace.selectedProjectId.value = $event" @refresh="workspace.loadProjects" @action="openCreate" />
    <div v-if="workspace.usingMockData.value" class="mock-notice subtle"><AppIcon name="alert-circle" :size="17" />API 無法使用，目前顯示示意資料。</div>
    <div v-if="workspace.errorMessage.value" class="geo-error-message">{{ workspace.errorMessage.value }}</div>
    <div class="geo-local-message">{{ workspace.localMessage.value }}</div>
    <div v-if="workspace.loading.value && !workspace.selectedProject.value" class="empty-state">正在載入 GEO 資料</div>
    <div v-else-if="!workspace.selectedProject.value" class="empty-state">請先建立 GEO project。</div>

    <article v-else class="card geo-kinsan-card">
      <header class="geo-kinsan-card-header">
        <strong>Query List</strong>
        <span>共 {{ workspace.selectedProjectQueries.value.length }} 筆</span>
      </header>
      <div class="geo-kinsan-toolbar">
        <label class="geo-search-field"><AppIcon name="search" :size="16" /><input v-model="search" type="search" placeholder="搜尋 query、topic、intent…" @input="page = 1" /></label>
        <GeoFilterDropdown label="Stage" :options="stageOptions" :selected="stageFilters" @update:selected="stageFilters = $event; page = 1" />
        <GeoFilterDropdown label="Priority" :options="['high', 'normal', 'low']" :selected="priorityFilters" @update:selected="priorityFilters = $event; page = 1" />
        <span v-if="activeFilterCount || search" class="geo-clear-filters" @click="clearFilters">清除全部</span>
      </div>
      <div class="geo-kinsan-table-wrap">
        <table class="data-table geo-table geo-kinsan-table">
          <thead><tr><th>Query</th><th>Topic</th><th>Intent</th><th>Stage</th><th>Branded</th><th>Priority</th><th class="sticky-action">Actions</th></tr></thead>
          <tbody>
            <tr v-for="query in pageRows" :key="query.id">
              <td><strong>{{ query.queryText }}</strong><small>{{ query.region }} / {{ query.language }}</small></td>
              <td><span class="badge badge-muted">{{ topicLabel(query.topicId) }}</span></td>
              <td><code>{{ query.intent ?? "-" }}</code></td>
              <td>{{ query.buyerStage ?? "-" }}</td>
              <td>{{ query.isBranded ? "是" : "否" }}</td>
              <td><GeoStatusBadge :value="query.priority" /></td>
              <td class="sticky-action">
                <div class="geo-row-actions">
                  <button class="geo-row-action danger" type="button" title="刪除" @click="deleteQuery(query.id)">
                    <AppIcon name="trash" :size="14" />
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredQueries.length === 0"><td class="geo-table-empty" colspan="7">找不到符合條件的 query。</td></tr>
          </tbody>
        </table>
      </div>
      <GeoPagination v-model:page="page" :per-page="perPage" :total="filteredQueries.length" />
    </article>

    <GeoActionDrawer :open="drawerOpen" title="建立 Query" description="新增要追蹤的自然語言查詢。" @close="closeDrawer">
      <form class="geo-drawer-form" @submit.prevent="submit">
        <GeoFormField label="Query" required :error="formErrors.queryText" full><textarea v-model="form.queryText" rows="4" :class="{ invalid: formErrors.queryText }" placeholder="使用者會在 Gemini / GPT 詢問的問題" @input="clearFieldError('queryText')"></textarea></GeoFormField>
        <label class="geo-checkbox"><input v-model="form.isBranded" type="checkbox" />Branded query</label>
        <GeoFormField label="Topic" required :error="formErrors.topicId">
          <div v-if="!showTopicForm" class="geo-inline-row">
            <select v-model="form.topicId" :class="{ invalid: formErrors.topicId }" @change="clearFieldError('topicId')"><option value="">請選擇 Topic</option><option v-for="topic in workspace.topics.value" :key="topic.id" :value="topic.id">{{ topic.name }}</option></select>
            <button class="button button-secondary" type="button" @click="showTopicForm = true">新增 Topic</button>
          </div>
          <div v-else class="geo-inline-topic-form">
            <input v-model="form.newTopicName" :class="{ invalid: formErrors.newTopicName }" placeholder="例如：品牌比較" @input="clearFieldError('newTopicName')" />
            <input v-model="form.newTopicDescription" placeholder="描述（選填）" />
            <small v-if="formErrors.newTopicName" class="form-error">{{ formErrors.newTopicName }}</small>
            <div class="row-actions"><button class="button button-secondary" type="button" @click="showTopicForm = false">取消</button><button class="button button-primary" type="button" @click="createInlineTopic">建立並選用</button></div>
          </div>
        </GeoFormField>
        <GeoFormField label="Intent"><input v-model="form.intent" type="text" /></GeoFormField>
        <GeoFormField label="Stage"><input v-model="form.buyerStage" type="text" /></GeoFormField>
        <GeoFormField label="Market"><select v-model="form.marketType"><option value="b2c">B2C</option><option value="b2b_procurement">B2B procurement</option></select></GeoFormField>
        <GeoFormField label="Priority"><select v-model="form.priority"><option value="low">low</option><option value="normal">normal</option><option value="high">high</option></select></GeoFormField>
        <div class="geo-drawer-actions"><button class="button button-secondary" type="button" @click="closeDrawer">取消</button><button class="button button-primary" type="submit" :disabled="workspace.actionLoading.value">建立 Query</button></div>
      </form>
    </GeoActionDrawer>
  </section>
</template>
