<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../components/ui/AppIcon.vue";
import GeoConfirmDialog from "../components/geo/GeoConfirmDialog.vue";
import GeoFormField from "../components/geo/GeoFormField.vue";
import GeoTagInput from "../components/geo/GeoTagInput.vue";
import { api } from "../services/api";
import {
  createDefaultQuerySettingsForm,
  loadProjectQuerySettings,
  normalizeQuerySettingsKeywords,
  querySettingsKeywordTagsToText,
  validateQueryResearchForm,
} from "../services/geo-project-query-settings";
import { useGeoFormErrors } from "../composables/geo-form-errors";
import { loadGeoProjectProfile, type GeoProjectProfile } from "../services/geo-project-profile";
import {
  generationRunsForResearch,
  latestGeoQueryRun,
  restoredDraftIds,
  runsStartedAtOrAfter,
} from "../services/geo-query-recovery";
import {
  reconcileAcceptedQueries,
  runAcceptedQueriesOnce,
  type GeoQueryFirstRunSummary,
} from "../services/geo-query-first-run";
import { setStoredGeoProjectId } from "../utils/geo-project-selection-storage";
import { getGeoProjectRouteNames } from "../utils/geo-project-routes";
import type {
  GeoQueryDraftResource,
  GeoQueryGenerationRunResource,
  GeoQueryResource,
  GeoQueryResearchRunResource,
  ToastTone,
} from "../types";

const emit = defineEmits<{ notify: [message: string, tone?: ToastTone] }>();
const props = withDefaults(
  defineProps<{
    permissions: readonly string[];
    projectId?: string;
    autoRun?: boolean;
    recoverable?: boolean;
    researchRunId?: string;
    generationRunId?: string;
  }>(),
  {
    projectId: "",
    autoRun: false,
    recoverable: false,
    researchRunId: "",
    generationRunId: "",
  },
);
const route = useRoute();
const router = useRouter();
const projectRoutes = computed(() => getGeoProjectRouteNames(route.meta.geoProjectArea));
const projectId = computed(() =>
  props.projectId ||
  (typeof route.params.projectId === "string" ? route.params.projectId : ""),
);
const profile = ref<GeoProjectProfile | null>(null);
const loading = ref(false);
const operationLoadingMessage = ref("");
const errorMessage = ref("");
const step = ref<1 | 2>(1);
const researchRun = ref<GeoQueryResearchRunResource | null>(null);
const generationRun = ref<GeoQueryGenerationRunResource | null>(null);
const researchStartedAt = ref(
  typeof route.query.researchStartedAt === "string"
    ? route.query.researchStartedAt
    : "",
);
const generationStartedAt = ref(
  typeof route.query.generationStartedAt === "string"
    ? route.query.generationStartedAt
    : "",
);
const selectedDraftIds = ref<string[]>([]);
const selectionUpdatingIds = ref<Set<string>>(new Set());
const showEmptyAlert = ref(false);
const topics = ref<Array<{ name: string; description: string }>>([]);
const form = reactive({
  ...createDefaultQuerySettingsForm(),
});
const { formErrors, setFormErrors, clearFieldError, clearFormErrors } = useGeoFormErrors();

const drafts = computed(() => generationRun.value?.drafts ?? []);
const selectableDrafts = computed(() => drafts.value.filter((draft) => !draft.acceptedQueryId));
const allChecked = computed(() => selectableDrafts.value.length > 0 && selectableDrafts.value.every((draft) => selectedDraftIds.value.includes(draft.id)));
const someChecked = computed(() => selectedDraftIds.value.length > 0 && !allChecked.value);
const selectionUpdating = computed(() => selectionUpdatingIds.value.size > 0);
const brandName = computed(() => profile.value?.ownBrand.name || profile.value?.project.name || "");
const competitorNames = computed(() => profile.value?.competitors.map((competitor) => competitor.name) ?? []);
const keywords = computed(() => normalizeQuerySettingsKeywords(form.keywords));
const keywordTags = computed<string[]>({
  get: () => keywords.value,
  set: (tags) => {
    form.keywords = querySettingsKeywordTagsToText(tags);
    clearFieldError("keywords");
  },
});
const standardIntentCategories = ["導航型", "資訊型", "商業評估"];
const canRunJobs = computed(() => props.permissions.includes("geo.jobs.run"));

onMounted(() => void load());

async function load(): Promise<void> {
  if (!projectId.value) {
    await router.replace({ name: projectRoutes.value.projects });
    return;
  }
  loading.value = true;
  errorMessage.value = "";
  try {
    const [loadedProfile, settings] = await Promise.all([
      loadGeoProjectProfile(projectId.value),
      loadProjectQuerySettings(projectId.value),
    ]);
    profile.value = loadedProfile;
    Object.assign(form, settings.form);
    if (settings.warning) emit("notify", settings.warning, "warning");
    topics.value = profile.value.topics.map((topic) => ({ name: topic.name, description: topic.description }));
    if (props.autoRun) await executeSearch();
    else if (props.recoverable) await restorePersistedRuns();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "無法載入 Project。";
  } finally {
    loading.value = false;
  }
}

function validate(): boolean {
  clearFormErrors();
  if (!brandName.value) {
    errorMessage.value = "Project 尚未設定主要品牌。";
    return false;
  }
  errorMessage.value = "";
  return setFormErrors(
    Object.entries(validateQueryResearchForm(form, topics.value)).map(([field, message]) => ({
      field,
      message,
    })),
  );
}

function addTopic(): void {
  topics.value.push({ name: "", description: "" });
}

function clearTopicError(): void {
  if (topics.value.some((topic) => topic.name.trim())) clearFieldError("topics");
}

async function executeSearch(): Promise<void> {
  if (!validate() || !profile.value) return;
  startOperationLoading("正在執行 Query Research 與生成 Query…");
  errorMessage.value = "";
  try {
    researchRun.value = null;
    generationRun.value = null;
    selectedDraftIds.value = [];
    researchStartedAt.value = new Date().toISOString();
    generationStartedAt.value = "";
    await persistRecoveryRoute("researching");
    researchRun.value = await api.geoAnalysis.runQueryResearch(projectId.value, researchPayload());
    if (!researchRun.value.result?.researchContext) {
      await persistRecoveryRoute("research-failed");
      throw new Error(researchRun.value.errorMessage || "Query Research 未產生可用結果。");
    }
    await persistRecoveryRoute("research-complete");
    await generateQueries(researchRun.value.result.researchContext);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Query Search 執行失敗。";
  } finally {
    stopOperationLoading();
  }
}

async function regenerate(): Promise<void> {
  const context = researchRun.value?.result?.researchContext;
  if (!context || !validate()) return;
  startOperationLoading("正在重新生成 Query…");
  errorMessage.value = "";
  try {
    await generateQueries(context);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重新生成失敗。";
  } finally {
    stopOperationLoading();
  }
}

async function generateQueries(researchContext: string): Promise<void> {
  generationRun.value = null;
  selectedDraftIds.value = [];
  generationStartedAt.value = new Date().toISOString();
  await persistRecoveryRoute("generating");
  generationRun.value = await api.geoAnalysis.runQueryGeneration(
    projectId.value,
    generationPayload(researchContext),
  );
  await persistRecoveryRoute(
    generationRun.value.status === "failed" ? "generation-failed" : "drafts",
  );
  if (generationRun.value.status === "failed") {
    throw new Error(generationRun.value.errorMessage || "Query Generation 失敗。");
  }
  restoreDraftSelection();
  step.value = 2;
}

async function restorePersistedRuns(): Promise<void> {
  const persistedResearchRun = await loadPersistedResearchRun();
  researchRun.value = persistedResearchRun;
  const persistedGenerationRun = await loadPersistedGenerationRun(
    persistedResearchRun?.result?.researchContext ?? "",
  );
  generationRun.value = persistedGenerationRun;

  if (generationRun.value) {
    await persistRecoveryRoute(
      generationRun.value.status === "failed" ? "generation-failed" : "drafts",
    );
    if (generationRun.value.status === "failed") {
      errorMessage.value = generationRun.value.errorMessage || "Query Generation 失敗，可重新執行。";
      return;
    }
    restoreDraftSelection();
    step.value = 2;
    return;
  }

  const researchContext = researchRun.value?.result?.researchContext;
  if (researchRun.value?.status === "failed") {
    errorMessage.value = researchRun.value.errorMessage || "Query Research 失敗，可重新執行。";
    return;
  }
  if (!researchContext) {
    errorMessage.value = "尚未找到可恢復的 Query Research 結果，請稍後重新整理。";
    return;
  }
  if (route.query.phase === "generating") {
    errorMessage.value = "Query Generation 可能仍在執行，請稍後重新整理，避免重複生成。";
    return;
  }

  startOperationLoading("正在從已保存的 Research 結果繼續生成 Query…");
  try {
    await generateQueries(researchContext);
  } finally {
    stopOperationLoading();
  }
}

async function loadPersistedResearchRun(): Promise<GeoQueryResearchRunResource | null> {
  const [explicitRun, runs] = await Promise.all([
    props.researchRunId
      ? api.geoAnalysis.queryResearchRun(props.researchRunId).catch(() => null)
      : Promise.resolve(null),
    api.geoAnalysis.queryResearchRuns(projectId.value),
  ]);
  return latestGeoQueryRun(runsStartedAtOrAfter([
    ...(explicitRun ? [explicitRun] : []),
    ...runs.items,
  ], researchStartedAt.value));
}

async function loadPersistedGenerationRun(
  researchContext: string,
): Promise<GeoQueryGenerationRunResource | null> {
  const [explicitRun, runs] = await Promise.all([
    props.generationRunId
      ? api.geoAnalysis.queryGenerationRun(props.generationRunId).catch(() => null)
      : Promise.resolve(null),
    api.geoAnalysis.queryGenerationRuns(projectId.value),
  ]);
  const candidates = generationRunsForResearch(
    runsStartedAtOrAfter([
      ...(explicitRun ? [explicitRun] : []),
      ...runs.items,
    ], generationStartedAt.value),
    researchContext,
  );
  const latest = latestGeoQueryRun(candidates);
  if (!latest) return null;
  return explicitRun?.id === latest.id
    ? explicitRun
    : api.geoAnalysis.queryGenerationRun(latest.id);
}

function restoreDraftSelection(): void {
  selectedDraftIds.value = generationRun.value
    ? restoredDraftIds(generationRun.value)
    : [];
}

async function persistRecoveryRoute(phase: string): Promise<void> {
  if (!props.recoverable) return;
  try {
    await router.replace({
      name: projectRoutes.value.projectEdit,
      params: { projectId: projectId.value },
      query: {
        mode: "query-research",
        phase,
        ...(researchRun.value ? { researchRunId: researchRun.value.id } : {}),
        ...(generationRun.value ? { generationRunId: generationRun.value.id } : {}),
        ...(researchStartedAt.value ? { researchStartedAt: researchStartedAt.value } : {}),
        ...(generationStartedAt.value ? { generationStartedAt: generationStartedAt.value } : {}),
      },
    });
  } catch {
    emit("notify", "執行結果已保存，但瀏覽器恢復狀態更新失敗。", "warning");
  }
}

async function confirmDrafts(): Promise<void> {
  if (!selectedDraftIds.value.length) {
    showEmptyAlert.value = true;
    return;
  }
  startOperationLoading("正在建立 Query 並派送首次數據…");
  errorMessage.value = "";
  const attemptedDraftIds = [...selectedDraftIds.value];
  const failuresByDraftId = new Map<string, string>();
  const resolvedDraftIds = new Set<string>();
  const acceptedQueriesById = new Map<string, GeoQueryResource>();
  for (const draftId of attemptedDraftIds) {
    try {
      const query = await api.geoAnalysis.acceptQueryDraft(draftId, {
        createTopicIfMissing: true,
        status: "active",
      });
      acceptedQueriesById.set(query.id, query);
      resolvedDraftIds.add(draftId);
    } catch (error) {
      failuresByDraftId.set(draftId, error instanceof Error ? error.message : draftId);
    }
  }
  try {
    if (generationRun.value) {
      generationRun.value = await api.geoAnalysis.queryGenerationRun(generationRun.value.id);
      const reconciliation = await reconcileAcceptedQueries(
        projectId.value,
        attemptedDraftIds,
        generationRun.value.drafts,
        [...acceptedQueriesById.values()],
      );
      for (const query of reconciliation.queries) acceptedQueriesById.set(query.id, query);
      for (const draftId of reconciliation.reconciledDraftIds) {
        resolvedDraftIds.add(draftId);
        failuresByDraftId.delete(draftId);
      }
    }
  } catch {
    // Direct accept responses remain authoritative when reconciliation is unavailable.
  }
  selectedDraftIds.value = selectedDraftIds.value.filter((id) => !resolvedDraftIds.has(id));
  const acceptedQueries = [...acceptedQueriesById.values()];
  let firstRunSummary: GeoQueryFirstRunSummary | null = null;
  let firstRunError = "";
  if (!canRunJobs.value) {
    firstRunError = "目前帳號沒有首次數據執行權限";
  } else if (acceptedQueries.length) {
    try {
      firstRunSummary = await runAcceptedQueriesOnce(acceptedQueries);
    } catch (error) {
      firstRunError = error instanceof Error ? error.message : "首次數據派送失敗";
    }
  }
  stopOperationLoading();

  const resultParts = [`${acceptedQueries.length} 筆 Query 已建立`];
  if (firstRunSummary) {
    resultParts.push(`${firstRunSummary.combinations} 個首次執行組合`);
    resultParts.push(`${firstRunSummary.dispatched} 筆已派送`);
    if (firstRunSummary.alreadyReserved) resultParts.push(`${firstRunSummary.alreadyReserved} 筆今日已執行或已排程`);
    if (firstRunSummary.retryScheduled) resultParts.push(`${firstRunSummary.retryScheduled} 筆等待後端重試`);
    if (firstRunSummary.failures.length) resultParts.push(`${firstRunSummary.failures.length} 筆派送失敗`);
  }
  if (firstRunError) resultParts.push(firstRunError);
  const failures = [...failuresByDraftId.values()];
  if (failures.length) {
    errorMessage.value = `部分 Query 已建立，${failures.length} 筆建立失敗：${failures.join("；")}`;
    emit("notify", `${resultParts.join("；")}；${errorMessage.value}`, "error");
    return;
  }
  const runFailures = firstRunSummary?.failures ?? [];
  emit(
    "notify",
    `${resultParts.join("；")}${runFailures.length ? `：${runFailures.join("；")}` : "。"}`,
    firstRunError || firstRunSummary?.retryScheduled || runFailures.length ? "warning" : "success",
  );
  setStoredGeoProjectId(projectId.value);
  await router.push({ name: projectRoutes.value.overview });
}

function startOperationLoading(message: string): void {
  operationLoadingMessage.value = message;
  loading.value = true;
}

function stopOperationLoading(): void {
  loading.value = false;
  operationLoadingMessage.value = "";
}

function researchPayload() {
  return {
    provider: form.researchProvider,
    brandName: brandName.value,
    competitorBrands: competitorNames.value,
    keywords: keywords.value,
    region: profile.value!.project.defaultRegion as "TW" | "US",
    language: profile.value!.project.defaultLanguage || null,
    marketType: form.marketType,
    intents: [{ category: form.intentCategory, description: form.intentDescription.trim() }],
    audience: { name: form.audienceName.trim(), description: form.audienceDescription.trim() },
    brandMentionRules: {
      shouldMentionOwnBrand: form.shouldMentionOwnBrand,
      shouldMentionCompetitor: form.shouldMentionCompetitor,
    },
  };
}

function generationPayload(researchContext: string) {
  const activeTopics = topics.value.map((topic) => ({ name: topic.name.trim(), description: topic.description.trim() })).filter((topic) => topic.name);
  return {
    provider: form.runProvider,
    brandName: brandName.value,
    competitorBrands: competitorNames.value,
    keywords: keywords.value,
    region: profile.value!.project.defaultRegion as "TW" | "US",
    language: profile.value!.project.defaultLanguage || null,
    marketType: form.marketType,
    topics: activeTopics,
    topicNames: activeTopics.map((topic) => topic.name),
    intents: [{ category: form.intentCategory, description: form.intentDescription.trim() }],
    audience: { name: form.audienceName.trim(), description: form.audienceDescription.trim() },
    brandMentionRules: {
      shouldMentionOwnBrand: form.shouldMentionOwnBrand,
      shouldMentionCompetitor: form.shouldMentionCompetitor,
    },
    researchContext,
    maxQueries: Number(form.maxQueries),
  };
}

async function toggleDraft(draft: GeoQueryDraftResource): Promise<void> {
  if (draft.acceptedQueryId || selectionUpdatingIds.value.has(draft.id)) return;
  const wasSelected = selectedDraftIds.value.includes(draft.id);
  selectedDraftIds.value = wasSelected
    ? selectedDraftIds.value.filter((id) => id !== draft.id)
    : [...selectedDraftIds.value, draft.id];
  selectionUpdatingIds.value = new Set(selectionUpdatingIds.value).add(draft.id);
  try {
    const updated = await api.geoAnalysis.updateQueryDraftSelection(draft.id, {
      selectionStatus: wasSelected ? "rejected" : "shortlisted",
    });
    if (generationRun.value) {
      generationRun.value = {
        ...generationRun.value,
        drafts: generationRun.value.drafts.map((item) =>
          item.id === updated.id ? updated : item,
        ),
      };
    }
  } catch (error) {
    selectedDraftIds.value = wasSelected
      ? [...selectedDraftIds.value, draft.id]
      : selectedDraftIds.value.filter((id) => id !== draft.id);
    emit(
      "notify",
      error instanceof Error ? error.message : "Draft 選取狀態保存失敗。",
      "error",
    );
  } finally {
    const pending = new Set(selectionUpdatingIds.value);
    pending.delete(draft.id);
    selectionUpdatingIds.value = pending;
  }
}

function toggleAll(): void {
  const shouldClear = allChecked.value;
  for (const draft of selectableDrafts.value) {
    if (selectedDraftIds.value.includes(draft.id) === shouldClear) {
      void toggleDraft(draft);
    }
  }
}
</script>

<template>
  <main class="geo-form-page geo-query-research-page">
    <div
      class="geo-form-shell"
      :inert="operationLoadingMessage ? true : undefined"
      :aria-busy="Boolean(operationLoadingMessage)"
    >
      <header class="geo-form-page-header">
        <button class="geo-back-button" type="button" title="返回" @click="step === 2 ? step = 1 : router.push({ name: projectRoutes.projects })"><AppIcon name="chevron-left" :size="16" /></button>
        <div><h1>Query Search</h1><p>設定並生成 Query</p></div>
        <span class="geo-header-spacer"></span>
        <template v-if="step === 1"><button class="button button-secondary" type="button" @click="router.push({ name: projectRoutes.projects })">返回</button><button class="button button-primary" type="button" :disabled="loading" @click="executeSearch">執行 Query Search</button></template>
        <template v-else><button class="button button-secondary" type="button" @click="step = 1">返回</button><button class="button button-primary" type="button" :disabled="loading || selectionUpdating" @click="confirmDrafts">確認生成 Query</button></template>
      </header>
      <div v-if="errorMessage" class="geo-error-message">{{ errorMessage }}</div>
      <div v-if="loading && !profile" class="geo-form-loading">正在載入 Project…</div>
      <div v-else-if="profile" class="geo-form-stack">
        <template v-if="step === 1">
          <section class="geo-form-card"><header><strong>品牌基本資料</strong></header><div class="geo-read-grid"><div><span>Project 名稱</span><strong>{{ profile.project.name }}</strong></div><div><span>網址/網域</span><strong>{{ profile.ownBrand.websiteUrl || "—" }}</strong></div><div><span>客戶</span><strong>{{ profile.customerName }}</strong></div><div><span>地區</span><strong>{{ profile.project.defaultRegion }}</strong></div><div><span>語系</span><strong>{{ profile.project.defaultLanguage }}</strong></div><div><span>別名</span><strong>{{ profile.ownBrand.aliases.map((alias) => alias.alias).join("、") || "—" }}</strong></div><div class="geo-read-full"><span>競品</span><div><span v-for="competitor in profile.competitors" :key="competitor.clientId" class="geo-read-tag">{{ competitor.name }}</span><strong v-if="!profile.competitors.length">—</strong></div></div></div></section>
          <section class="geo-form-card"><header><strong>Provider</strong></header><div class="geo-form-grid"><GeoFormField label="Research / Generation Provider"><select v-model="form.researchProvider"><option value="gemini">Gemini</option></select></GeoFormField><GeoFormField label="Run Provider"><select v-model="form.runProvider"><option value="gemini">Gemini</option></select></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Keywords</strong><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button></header><div class="geo-card-body"><GeoTagInput v-model="keywordTags" :invalid="Boolean(formErrors.keywords)" placeholder="請輸入 Keyword" /><small v-if="formErrors.keywords" class="form-error">{{ formErrors.keywords }}</small><small>輸入後按 Enter 或逗號新增，最多 10 筆；也可貼上多行內容。</small></div></section>
          <section class="geo-form-card"><header><strong>Topics</strong><div><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button><button class="button button-secondary button-small" type="button" @click="addTopic">新增 Topic</button></div></header><div class="geo-card-body geo-topic-list"><div v-for="(topic, index) in topics" :key="index"><label><span>Topic 名稱</span><input v-model="topic.name" type="text" :class="{ invalid: formErrors.topics && !topic.name.trim() }" :aria-invalid="Boolean(formErrors.topics && !topic.name.trim())" placeholder="例如 產品、採購評估、供應商" @input="clearTopicError" /><small v-if="formErrors.topics && !topic.name.trim()" class="form-error">{{ formErrors.topics }}</small></label><label><span>Topic 描述</span><input v-model="topic.description" type="text" placeholder="描述此 Topic" /></label><button class="button button-secondary button-small" type="button" @click="topics.splice(index, 1)">移除</button></div><p v-if="!topics.length">尚未新增 Topic，點右上「新增 Topic」開始</p><small v-if="formErrors.topics && !topics.length" class="form-error">{{ formErrors.topics }}</small></div></section>
          <section class="geo-form-card"><header><strong>市場與受眾</strong></header><div class="geo-form-grid"><GeoFormField label="Market Type"><select v-model="form.marketType"><option value="b2b_procurement">B2B 採購</option><option value="b2c">B2C 消費</option></select></GeoFormField><GeoFormField label="Max Queries" required :error="formErrors.maxQueries"><input v-model.number="form.maxQueries" type="number" min="1" max="40" :class="{ invalid: formErrors.maxQueries }" :aria-invalid="Boolean(formErrors.maxQueries)" @input="clearFieldError('maxQueries')" /></GeoFormField><GeoFormField label="Audience" required :error="formErrors.audienceName"><input v-model="form.audienceName" type="text" :class="{ invalid: formErrors.audienceName }" :aria-invalid="Boolean(formErrors.audienceName)" @input="clearFieldError('audienceName')" /></GeoFormField><GeoFormField label="Audience Description" required :error="formErrors.audienceDescription"><input v-model="form.audienceDescription" type="text" :class="{ invalid: formErrors.audienceDescription }" :aria-invalid="Boolean(formErrors.audienceDescription)" @input="clearFieldError('audienceDescription')" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Intent 與提及規則</strong></header><div class="geo-form-grid"><GeoFormField label="Intent 分類" required :error="formErrors.intentCategory"><select v-model="form.intentCategory" :class="{ invalid: formErrors.intentCategory }" :aria-invalid="Boolean(formErrors.intentCategory)" @change="clearFieldError('intentCategory')"><option v-if="!standardIntentCategories.includes(form.intentCategory)" :value="form.intentCategory">{{ form.intentCategory }}</option><option v-for="category in standardIntentCategories" :key="category" :value="category">{{ category }}</option></select></GeoFormField><GeoFormField label="Intent 描述" required :error="formErrors.intentDescription"><input v-model="form.intentDescription" type="text" :class="{ invalid: formErrors.intentDescription }" :aria-invalid="Boolean(formErrors.intentDescription)" @input="clearFieldError('intentDescription')" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>提示詞風格</strong></header><div class="geo-toggle-list"><label><span class="geo-toggle-copy"><strong>提及自身品牌</strong><small>生成的 query 需包含自家品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionOwnBrand" type="checkbox" /><span aria-hidden="true"></span></span></label><label><span class="geo-toggle-copy"><strong>提及競品</strong><small>生成的 query 需包含競爭品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionCompetitor" type="checkbox" /><span aria-hidden="true"></span></span></label></div></section>
        </template>
        <section v-else class="geo-form-card geo-generation-results"><header><strong>生成結果</strong><div><span>已選 {{ selectedDraftIds.length }} / {{ selectableDrafts.length }}</span><button class="button button-secondary button-small" type="button" :disabled="loading || selectionUpdating" @click="regenerate">重新生成</button></div></header><div class="geo-result-head"><input type="checkbox" :checked="allChecked" :indeterminate.prop="someChecked" :disabled="selectionUpdating" @change="toggleAll" /><span>Query list</span></div><button v-for="draft in drafts" :key="draft.id" class="geo-result-row" :class="{ selected: selectedDraftIds.includes(draft.id), accepted: draft.acceptedQueryId }" type="button" :disabled="Boolean(draft.acceptedQueryId) || selectionUpdatingIds.has(draft.id)" @click="toggleDraft(draft)"><input type="checkbox" :checked="selectedDraftIds.includes(draft.id)" :disabled="Boolean(draft.acceptedQueryId) || selectionUpdatingIds.has(draft.id)" tabindex="-1" /><span><strong>{{ draft.queryText }}</strong><small>{{ draft.region }}/{{ draft.language }}<template v-if="draft.acceptedQueryId"> · 已建立</template></small></span></button><div v-if="!drafts.length" class="geo-table-empty">沒有生成結果</div></section>
      </div>
    </div>
    <GeoConfirmDialog :open="showEmptyAlert" single title="尚未選擇 Query" message="請至少勾選一筆 Query，再進行生成。" confirm-label="我知道了" @cancel="showEmptyAlert = false" @confirm="showEmptyAlert = false" />
    <Teleport to="body">
      <div
        v-if="operationLoadingMessage"
        class="geo-operation-loading-overlay"
        role="status"
        aria-live="polite"
        :aria-label="operationLoadingMessage"
      >
        <div class="geo-operation-loading-card">
          <span class="session-loading-spinner" aria-hidden="true"></span>
          <strong>{{ operationLoadingMessage }}</strong>
        </div>
      </div>
    </Teleport>
  </main>
</template>
