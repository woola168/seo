<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../components/ui/AppIcon.vue";
import GeoFormField from "../components/geo/GeoFormField.vue";
import GeoTagInput from "../components/geo/GeoTagInput.vue";
import GeoQueryResearchPage from "./GeoQueryResearchPage.vue";
import { api } from "../services/api";
import {
  createDefaultQuerySettingsForm,
  normalizeQuerySettingsKeywords,
  querySettingsKeywordTagsToText,
  querySettingsFormToRequest,
  validateQuerySettingsForm,
} from "../services/geo-project-query-settings";
import {
  createGeoProjectWithQuerySettings,
  GeoProjectProfileSaveError,
  loadGeoProjectProfile,
  normalizeValues,
  updateGeoProjectProfile,
  type GeoProjectProfile,
} from "../services/geo-project-profile";
import type { CustomerSummary, ToastTone } from "../types";
import { getGeoProjectRouteNames } from "../utils/geo-project-routes";
import { hasPermission } from "../utils/permissions";

interface CompetitorDraft {
  clientId: string;
  id: string | null;
  name: string;
  websiteUrl: string;
  aliases: string[];
}

const emit = defineEmits<{ notify: [message: string, tone?: ToastTone] }>();
const props = defineProps<{ permissions: readonly string[] }>();
const route = useRoute();
const router = useRouter();
const projectRoutes = computed(() => getGeoProjectRouteNames(route.meta.geoProjectArea));
const projectId = computed(() => typeof route.params.projectId === "string" ? route.params.projectId : "");
const isEdit = computed(() => Boolean(projectId.value));
const canResearch = computed(() => hasPermission(props.permissions, "geo.queries.manage"));
const isRecoveringQueryResearch = computed(
  () =>
    route.query.mode === "query-research" &&
    Boolean(projectId.value) &&
    canResearch.value,
);
const step = ref<1 | 2>(1);
const loading = ref(false);
const errorMessage = ref("");
const customers = ref<CustomerSummary[]>([]);
const currentProfile = ref<GeoProjectProfile | null>(null);
const queryResearchProjectId = ref(
  isRecoveringQueryResearch.value ? projectId.value : "",
);
const autoRunQueryResearch = ref(false);
const errors = reactive<Record<string, string>>({});
const competitors = ref<CompetitorDraft[]>([]);
const competitorNames = computed<string[]>({
  get: () => competitors.value.map((competitor) => competitor.name),
  set: (names) => {
    const normalizedNames = normalizeValues(names);
    competitors.value = normalizedNames.map((name, index) => {
      const existing = competitors.value.find((competitor) => competitor.name === name);
      return existing ?? {
        clientId: `new-${Date.now()}-${index}`,
        id: null,
        name,
        websiteUrl: "",
        aliases: [],
      };
    });
    if (competitors.value.length) delete errors.competitors;
  },
});
const topics = ref<Array<{ name: string; description: string }>>([]);
const competitorModalOpen = ref(false);
const editingCompetitorId = ref("");
const competitorForm = reactive({ name: "", websiteUrl: "", aliases: [] as string[] });
const ownBrandAliases = ref<string[]>([]);
const form = reactive({
  name: "",
  websiteUrl: "",
  customerId: "",
  defaultRegion: "TW",
  defaultLanguage: "zh-TW",
  ...createDefaultQuerySettingsForm(),
});
const keywordTags = computed<string[]>({
  get: () => normalizeQuerySettingsKeywords(form.keywords),
  set: (tags) => {
    form.keywords = querySettingsKeywordTagsToText(tags);
    delete errors.keywords;
  },
});

onMounted(() => void load());

async function load(): Promise<void> {
  if (queryResearchProjectId.value) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    const customerResult = await api.customers().catch(() => ({ items: [], total: 0 }));
    customers.value = customerResult.items;
    if (!isEdit.value) {
      form.customerId = customers.value[0]?.id ?? "";
      return;
    }
    const profile = await loadGeoProjectProfile(projectId.value);
    currentProfile.value = profile;
    form.name = profile.project.name;
    form.websiteUrl = profile.ownBrand.websiteUrl;
    form.customerId = profile.project.customerId ?? "";
    form.defaultRegion = profile.project.defaultRegion;
    form.defaultLanguage = profile.project.defaultLanguage;
    ownBrandAliases.value = profile.ownBrand.aliases.map((alias) => alias.alias);
    competitors.value = profile.competitors.map((competitor) => ({
      clientId: competitor.clientId,
      id: competitor.entity?.id ?? null,
      name: competitor.name,
      websiteUrl: competitor.websiteUrl,
      aliases: competitor.aliases.map((alias) => alias.alias),
    }));
    topics.value = profile.topics.map((topic) => ({ name: topic.name, description: topic.description }));
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "無法載入 Project。";
  } finally {
    loading.value = false;
  }
}

function validateStepOne(): boolean {
  Object.keys(errors).forEach((key) => delete errors[key]);
  if (!form.name.trim()) errors.name = "請輸入名稱";
  if (!form.websiteUrl.trim()) errors.websiteUrl = "請輸入網址/網域";
  if (!form.customerId) errors.customerId = "請選擇客戶";
  if (!form.defaultRegion.trim()) errors.defaultRegion = "請輸入地區";
  if (!form.defaultLanguage.trim()) errors.defaultLanguage = "請輸入語系";
  if (!isEdit.value && !competitors.value.length) errors.competitors = "請至少輸入一個競品";
  return Object.keys(errors).length === 0;
}

function primaryAction(): void {
  if (!validateStepOne()) return;
  if (!isEdit.value && step.value === 1) {
    step.value = 2;
    return;
  }
  if (!isEdit.value && !validateStepTwo()) return;
  void save();
}

function validateStepTwo(): boolean {
  const settingsErrors = validateQuerySettingsForm(form);
  Object.assign(errors, settingsErrors);
  return Object.keys(settingsErrors).length === 0;
}

function secondaryAction(): void {
  if (!isEdit.value && step.value === 2) {
    step.value = 1;
    return;
  }
  void router.push({ name: projectRoutes.value.projects });
}

function openQueryResearch(): void {
  if (!projectId.value || !canResearch.value) return;
  void router.push({
    name: projectRoutes.value.queryResearch,
    params: { projectId: projectId.value },
  });
}

function forwardQueryResearchNotification(
  message: string,
  tone?: ToastTone,
): void {
  emit("notify", message, tone);
}

async function save(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";
  const input = {
    project: {
      customerId: form.customerId || null,
      name: form.name.trim(),
      defaultRegion: form.defaultRegion.trim(),
      defaultLanguage: form.defaultLanguage.trim(),
      status: currentProfile.value?.project.status ?? "active" as const,
      dailyRunBudget: currentProfile.value?.project.dailyRunBudget ?? 200,
    },
    websiteUrl: form.websiteUrl,
    aliases: normalizeValues(ownBrandAliases.value),
    competitors: competitors.value.map((competitor) => ({
      id: competitor.id,
      name: competitor.name.trim(),
      websiteUrl: competitor.websiteUrl,
      aliases: normalizeValues(competitor.aliases),
    })),
    topics: topics.value.map((topic) => ({ name: topic.name.trim(), description: topic.description.trim() })).filter((topic) => topic.name),
  };
  try {
    if (currentProfile.value) {
      await updateGeoProjectProfile(currentProfile.value, input);
      emit("notify", "Project 已更新。", "success");
    } else {
      const result = await createGeoProjectWithQuerySettings(
        input,
        querySettingsFormToRequest(form),
        hasPermission(props.permissions, "geo.projects.update"),
      );
      if (result.querySettingsStatus === "skipped") {
        emit("notify", "Project 已建立，但目前權限無法保存 Query Settings。", "warning");
        await router.push({ name: projectRoutes.value.projects });
        return;
      }
      if (result.querySettingsStatus === "failed") {
        emit("notify", `Project 已建立，但 Query Settings 保存失敗：${result.querySettingsError}`, "error");
        await router.push({ name: projectRoutes.value.projects });
        return;
      }
      if (!hasPermission(props.permissions, "geo.queries.manage")) {
        emit(
          "notify",
          "Project 與 Query Research 預設設定已建立，但目前權限無法執行 Query Research。",
          "warning",
        );
        await router.push({ name: projectRoutes.value.projects });
        return;
      }
      emit("notify", "Project 與 Query Research 預設設定已建立，正在執行 Query Research。", "success");
      await router.replace({
        name: projectRoutes.value.projectEdit,
        params: { projectId: result.project.id },
        query: { mode: "query-research", phase: "researching" },
      });
      autoRunQueryResearch.value = true;
      queryResearchProjectId.value = result.project.id;
      return;
    }
    await router.push({ name: projectRoutes.value.projects });
  } catch (error) {
    if (error instanceof GeoProjectProfileSaveError) {
      errorMessage.value = `Project 核心資料已保存，但部分關聯資料失敗：${error.message}`;
      emit("notify", errorMessage.value, "error");
      await router.replace({ name: projectRoutes.value.projectEdit, params: { projectId: error.project.id } });
      await load();
    } else {
      errorMessage.value = error instanceof Error ? error.message : "Project 保存失敗。";
    }
  } finally {
    loading.value = false;
  }
}

function openCompetitor(competitor?: CompetitorDraft): void {
  editingCompetitorId.value = competitor?.clientId ?? "";
  competitorForm.name = competitor?.name ?? "";
  competitorForm.websiteUrl = competitor?.websiteUrl ?? "";
  competitorForm.aliases = [...(competitor?.aliases ?? [])];
  competitorModalOpen.value = true;
}

function saveCompetitor(): void {
  if (!competitorForm.name.trim()) return;
  const existing = competitors.value.find((competitor) => competitor.clientId === editingCompetitorId.value);
  const next: CompetitorDraft = {
    clientId: existing?.clientId ?? `new-${Date.now()}`,
    id: existing?.id ?? null,
    name: competitorForm.name.trim(),
    websiteUrl: competitorForm.websiteUrl.trim(),
    aliases: normalizeValues(competitorForm.aliases),
  };
  competitors.value = existing
    ? competitors.value.map((competitor) => competitor.clientId === existing.clientId ? next : competitor)
    : [...competitors.value, next];
  competitorModalOpen.value = false;
  delete errors.competitors;
}

function addTopic(): void {
  topics.value.push({ name: "", description: "" });
}
</script>

<template>
  <GeoQueryResearchPage
    v-if="queryResearchProjectId"
    :permissions="permissions"
    :project-id="queryResearchProjectId"
    :auto-run="autoRunQueryResearch"
    recoverable
    :research-run-id="typeof route.query.researchRunId === 'string' ? route.query.researchRunId : ''"
    :generation-run-id="typeof route.query.generationRunId === 'string' ? route.query.generationRunId : ''"
    @notify="forwardQueryResearchNotification"
  />
  <main v-else class="geo-form-page">
    <div class="geo-form-shell">
      <header class="geo-form-page-header">
        <button class="geo-back-button" type="button" :title="!isEdit && step === 2 ? '上一步' : '返回'" @click="secondaryAction"><AppIcon name="chevron-left" :size="16" /></button>
        <div><h1>{{ isEdit ? "編輯 Project" : "新增 Project" }}</h1><p>{{ isEdit ? "修改專案基本資料與 Query list" : "填寫專案基本資料與 Query list" }}</p></div>
        <span class="geo-header-spacer"></span>
        <button class="button button-secondary" type="button" @click="secondaryAction">{{ !isEdit && step === 2 ? "上一步" : "取消" }}</button>
        <button v-if="isEdit" class="button button-secondary" type="button" :disabled="loading || !canResearch" @click="openQueryResearch"><AppIcon name="search" :size="14" />Query Research</button>
        <button class="button button-primary" type="button" :disabled="loading" @click="primaryAction">{{ isEdit ? "儲存" : step === 1 ? "下一步" : "Query Research" }}</button>
      </header>

      <div v-if="errorMessage" class="geo-error-message">{{ errorMessage }}</div>
      <div v-if="loading && !currentProfile && isEdit" class="geo-form-loading">正在載入 Project…</div>
      <div v-else class="geo-form-stack">
        <section v-if="isEdit || step === 1" class="geo-form-card">
          <header><strong>品牌基本資料</strong></header>
          <div class="geo-form-grid">
            <GeoFormField label="Project 名稱" required :error="errors.name"><input v-model="form.name" type="text" placeholder="請輸入名稱" :class="{ invalid: errors.name }" /></GeoFormField>
            <GeoFormField label="網址/網域" required :error="errors.websiteUrl"><input v-model="form.websiteUrl" type="text" placeholder="請輸入網址/網域" :class="{ invalid: errors.websiteUrl }" /></GeoFormField>
            <GeoFormField label="客戶" required :error="errors.customerId"><select v-model="form.customerId" :class="{ invalid: errors.customerId }"><option value="">請選擇客戶</option><option v-for="customer in customers" :key="customer.id" :value="customer.id">{{ customer.name }}</option></select></GeoFormField>
            <GeoFormField label="地區" required :error="errors.defaultRegion"><input v-model="form.defaultRegion" type="text" placeholder="例如：TW" /></GeoFormField>
            <GeoFormField label="語系" required :error="errors.defaultLanguage"><input v-model="form.defaultLanguage" type="text" placeholder="例如：zh-TW" /></GeoFormField>
            <GeoFormField label="別名">
              <GeoTagInput v-model="ownBrandAliases" placeholder="請輸入別名" />
              <small class="geo-form-helper" @click.prevent.stop>輸入別名後按 Enter 或逗號新增，可加入多組</small>
            </GeoFormField>
            <GeoFormField v-if="!isEdit" class="geo-form-full" label="競品" required :error="errors.competitors">
              <template #action><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button></template>
              <GeoTagInput v-model="competitorNames" placeholder="請輸入競品" :invalid="Boolean(errors.competitors)" />
              <small class="geo-form-helper" @click.prevent.stop>輸入品牌名稱後按 Enter 或逗號新增，可加入多組</small>
            </GeoFormField>
          </div>
        </section>

        <section v-if="isEdit" class="geo-form-card">
          <header><strong>競品</strong><button class="button button-secondary button-small" type="button" @click="openCompetitor()"><AppIcon name="plus" :size="14" />新增</button></header>
          <div class="geo-card-table-wrap"><table class="geo-project-settings-table geo-competitor-table"><colgroup><col class="competitor-name-col" /><col class="competitor-alias-col" /><col class="competitor-actions-col" /></colgroup><thead><tr><th>競品名稱 / 網址</th><th>別名</th><th>操作</th></tr></thead><tbody>
            <tr v-for="competitor in competitors" :key="competitor.clientId"><td><strong>{{ competitor.name }}</strong><small>{{ competitor.websiteUrl || "—" }}</small></td><td><div v-if="competitor.aliases.length" class="geo-alias-list"><span v-for="alias in competitor.aliases" :key="alias" class="geo-read-tag">{{ alias }}</span></div><span v-else class="geo-table-placeholder">—</span></td><td><div class="geo-row-actions"><button class="geo-row-action" type="button" title="編輯" @click="openCompetitor(competitor)"><AppIcon name="edit" :size="14" /></button><button class="geo-row-action" type="button" title="刪除" @click="competitors = competitors.filter((item) => item.clientId !== competitor.clientId)"><AppIcon name="trash" :size="14" /></button></div></td></tr>
            <tr v-if="!competitors.length"><td colspan="3" class="geo-table-empty">尚未新增競品，點右上「新增」開始</td></tr>
          </tbody></table></div>
        </section>

        <section v-if="isEdit" class="geo-form-card">
          <header><strong>Query list</strong><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button></header>
          <div class="geo-card-table-wrap geo-query-table-wrap"><table class="geo-project-settings-table geo-query-summary-table"><colgroup><col class="query-text-col" /><col class="query-topic-col" /><col class="query-intent-col" /><col class="query-stage-col" /><col class="query-branded-col" /><col class="query-priority-col" /></colgroup><thead><tr><th>Query</th><th>Topic</th><th>Intent</th><th>Stage</th><th>Branded</th><th>Priority</th></tr></thead><tbody>
            <tr v-for="query in currentProfile?.queries ?? []" :key="query.id"><td>{{ query.queryText }}</td><td>{{ currentProfile?.topics.find((topic) => topic.id === query.topicId)?.name || "—" }}</td><td>{{ query.intent || "—" }}</td><td>{{ query.buyerStage || "—" }}</td><td>{{ query.isBranded ? "是" : "否" }}</td><td>{{ query.priority }}</td></tr>
            <tr v-if="!currentProfile?.queries.length"><td colspan="6" class="geo-table-empty">尚未有任何 Query</td></tr>
          </tbody></table></div>
        </section>

        <template v-if="!isEdit && step === 2">
          <section class="geo-form-card"><header><strong>品牌基本資料</strong></header><div class="geo-read-grid"><div><span>Project 名稱</span><strong>{{ form.name }}</strong></div><div><span>網址/網域</span><strong>{{ form.websiteUrl }}</strong></div><div><span>客戶</span><strong>{{ customers.find((customer) => customer.id === form.customerId)?.name }}</strong></div><div><span>地區</span><strong>{{ form.defaultRegion }}</strong></div><div><span>語系</span><strong>{{ form.defaultLanguage }}</strong></div><div><span>別名</span><strong>{{ ownBrandAliases.join("、") || "—" }}</strong></div><div class="geo-read-full"><span>競品</span><div class="geo-read-tags"><span v-for="competitor in competitors" :key="competitor.clientId" class="geo-read-tag">{{ competitor.name }}</span></div></div></div></section>
          <section class="geo-form-card"><header><strong>Provider</strong></header><div class="geo-form-grid"><GeoFormField label="Research / Generation Provider"><select v-model="form.researchProvider"><option value="gemini">Gemini</option></select></GeoFormField><GeoFormField label="Run Provider"><select v-model="form.runProvider"><option value="gemini">Gemini</option></select></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Keywords</strong><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button></header><div class="geo-card-body"><GeoFormField label="Keywords" :error="errors.keywords"><GeoTagInput v-model="keywordTags" :invalid="Boolean(errors.keywords)" placeholder="請輸入 Keyword" /></GeoFormField><small>輸入後按 Enter 或逗號新增，最多 10 筆；也可貼上多行內容。</small></div></section>
          <section class="geo-form-card"><header><strong>Topics</strong><div><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button><button class="button button-secondary button-small" type="button" @click="addTopic">新增 Topic</button></div></header><div class="geo-card-body geo-topic-list"><div v-for="(topic, index) in topics" :key="index"><label><span>Topic 名稱</span><input v-model="topic.name" type="text" placeholder="例如 產品、採購評估、供應商" /></label><label><span>Topic 描述</span><input v-model="topic.description" type="text" placeholder="描述此 Topic" /></label><button class="button button-secondary button-small" type="button" @click="topics.splice(index, 1)">移除</button></div><p v-if="!topics.length">尚未新增 Topic，點右上「新增 Topic」開始</p></div></section>
          <section class="geo-form-card"><header><strong>市場與受眾</strong></header><div class="geo-form-grid"><GeoFormField label="Market Type"><select v-model="form.marketType"><option value="b2b_procurement">B2B 採購</option><option value="b2c">B2C 消費</option></select></GeoFormField><GeoFormField label="Max Queries" :error="errors.maxQueries"><input v-model.number="form.maxQueries" type="number" min="1" max="40" :class="{ invalid: errors.maxQueries }" /></GeoFormField><GeoFormField label="Audience" :error="errors.audienceName"><input v-model="form.audienceName" type="text" :class="{ invalid: errors.audienceName }" /></GeoFormField><GeoFormField label="Audience Description" :error="errors.audienceDescription"><input v-model="form.audienceDescription" type="text" :class="{ invalid: errors.audienceDescription }" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Intent 與提及規則</strong></header><div class="geo-form-grid"><GeoFormField label="Intent 分類" :error="errors.intentCategory"><select v-model="form.intentCategory" :class="{ invalid: errors.intentCategory }"><option>導航型</option><option>資訊型</option><option>商業評估</option></select></GeoFormField><GeoFormField label="Intent 描述" :error="errors.intentDescription"><input v-model="form.intentDescription" type="text" :class="{ invalid: errors.intentDescription }" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>提示詞風格</strong></header><div class="geo-toggle-list"><label><span class="geo-toggle-copy"><strong>提及自身品牌</strong><small>生成的 query 需包含自家品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionOwnBrand" type="checkbox" /><span aria-hidden="true"></span></span></label><label><span class="geo-toggle-copy"><strong>提及競品</strong><small>生成的 query 需包含競爭品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionCompetitor" type="checkbox" /><span aria-hidden="true"></span></span></label></div></section>
        </template>
      </div>
    </div>

    <Teleport to="body"><div v-if="competitorModalOpen" class="geo-dialog-backdrop geo-competitor-backdrop" @click.self="competitorModalOpen = false"><section class="geo-dialog geo-competitor-dialog"><header><strong>{{ editingCompetitorId ? "編輯競品" : "新增競品" }}</strong></header><div class="geo-dialog-form"><GeoFormField label="競品名稱" required><input v-model="competitorForm.name" type="text" placeholder="請輸入競品名稱" /></GeoFormField><GeoFormField label="網址"><input v-model="competitorForm.websiteUrl" type="text" placeholder="https://example.com" /></GeoFormField><GeoFormField label="別名"><GeoTagInput v-model="competitorForm.aliases" placeholder="請輸入別名" /><small class="geo-form-helper" @click.prevent.stop>輸入別名後按 Enter 或逗號新增，可加入多組</small></GeoFormField></div><footer><button class="button button-secondary" type="button" @click="competitorModalOpen = false">取消</button><button class="button button-primary" type="button" :disabled="!competitorForm.name.trim()" @click="saveCompetitor">儲存</button></footer></section></div></Teleport>
  </main>
</template>
