<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppIcon from "../components/ui/AppIcon.vue";
import GeoConfirmDialog from "../components/geo/GeoConfirmDialog.vue";
import GeoFormField from "../components/geo/GeoFormField.vue";
import { api } from "../services/api";
import {
  createDefaultQuerySettingsForm,
  loadProjectQuerySettings,
  normalizeQuerySettingsKeywords,
} from "../services/geo-project-query-settings";
import { loadGeoProjectProfile, type GeoProjectProfile } from "../services/geo-project-profile";
import type {
  GeoQueryDraftResource,
  GeoQueryGenerationRunResource,
  GeoQueryResearchRunResource,
  ToastTone,
} from "../types";

const emit = defineEmits<{ notify: [message: string, tone?: ToastTone] }>();
defineProps<{ permissions: readonly string[] }>();
const route = useRoute();
const router = useRouter();
const projectId = computed(() => typeof route.params.projectId === "string" ? route.params.projectId : "");
const profile = ref<GeoProjectProfile | null>(null);
const loading = ref(false);
const errorMessage = ref("");
const step = ref<1 | 2>(1);
const researchRun = ref<GeoQueryResearchRunResource | null>(null);
const generationRun = ref<GeoQueryGenerationRunResource | null>(null);
const selectedDraftIds = ref<string[]>([]);
const showEmptyAlert = ref(false);
const topics = ref<Array<{ name: string; description: string }>>([]);
const form = reactive({
  ...createDefaultQuerySettingsForm(),
});

const drafts = computed(() => generationRun.value?.drafts ?? []);
const selectableDrafts = computed(() => drafts.value.filter((draft) => !draft.acceptedQueryId));
const allChecked = computed(() => selectableDrafts.value.length > 0 && selectableDrafts.value.every((draft) => selectedDraftIds.value.includes(draft.id)));
const someChecked = computed(() => selectedDraftIds.value.length > 0 && !allChecked.value);
const brandName = computed(() => profile.value?.ownBrand.name || profile.value?.project.name || "");
const competitorNames = computed(() => profile.value?.competitors.map((competitor) => competitor.name) ?? []);
const keywords = computed(() => normalizeQuerySettingsKeywords(form.keywords));
const standardIntentCategories = ["導航型", "資訊型", "商業評估"];

onMounted(() => void load());

async function load(): Promise<void> {
  if (!projectId.value) {
    await router.replace({ name: "geo-projects" });
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
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "無法載入 Project。";
  } finally {
    loading.value = false;
  }
}

function validate(): boolean {
  if (!brandName.value) {
    errorMessage.value = "Project 尚未設定主要品牌。";
    return false;
  }
  if (!keywords.value.length) {
    errorMessage.value = "請至少輸入一個 Keyword。";
    return false;
  }
  if (!topics.value.some((topic) => topic.name.trim())) {
    errorMessage.value = "請至少輸入一個 Topic。";
    return false;
  }
  if (!form.audienceName.trim() || !form.audienceDescription.trim() || !form.intentDescription.trim()) {
    errorMessage.value = "請完整填寫受眾與 Intent。";
    return false;
  }
  if (!Number.isInteger(Number(form.maxQueries)) || form.maxQueries < 1 || form.maxQueries > 40) {
    errorMessage.value = "Max Queries 必須是 1–40 的整數。";
    return false;
  }
  errorMessage.value = "";
  return true;
}

async function executeSearch(): Promise<void> {
  if (!validate() || !profile.value) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    researchRun.value = await api.geoAnalysis.runQueryResearch(projectId.value, researchPayload());
    if (!researchRun.value.result?.researchContext) {
      throw new Error(researchRun.value.errorMessage || "Query Research 未產生可用結果。");
    }
    generationRun.value = await api.geoAnalysis.runQueryGeneration(
      projectId.value,
      generationPayload(researchRun.value.result.researchContext),
    );
    if (generationRun.value.status === "failed") {
      throw new Error(generationRun.value.errorMessage || "Query Generation 失敗。");
    }
    selectedDraftIds.value = [];
    step.value = 2;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Query Search 執行失敗。";
  } finally {
    loading.value = false;
  }
}

async function regenerate(): Promise<void> {
  const context = researchRun.value?.result?.researchContext;
  if (!context || !validate()) return;
  loading.value = true;
  errorMessage.value = "";
  try {
    generationRun.value = await api.geoAnalysis.runQueryGeneration(projectId.value, generationPayload(context));
    selectedDraftIds.value = [];
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "重新生成失敗。";
  } finally {
    loading.value = false;
  }
}

async function confirmDrafts(): Promise<void> {
  if (!selectedDraftIds.value.length) {
    showEmptyAlert.value = true;
    return;
  }
  loading.value = true;
  errorMessage.value = "";
  const failures: string[] = [];
  for (const draftId of selectedDraftIds.value) {
    try {
      await api.geoAnalysis.acceptQueryDraft(draftId, { createTopicIfMissing: true, status: "active" });
    } catch (error) {
      failures.push(error instanceof Error ? error.message : draftId);
    }
  }
  try {
    if (generationRun.value) {
      generationRun.value = await api.geoAnalysis.queryGenerationRun(generationRun.value.id);
    }
  } catch {
    // The accepted Query resources are authoritative even if reconciliation fails.
  }
  selectedDraftIds.value = selectedDraftIds.value.filter((id) =>
    generationRun.value?.drafts.some((draft) => draft.id === id && !draft.acceptedQueryId),
  );
  loading.value = false;
  if (failures.length) {
    errorMessage.value = `部分 Query 已建立，${failures.length} 筆失敗：${failures.join("；")}`;
    emit("notify", errorMessage.value, "error");
    return;
  }
  emit("notify", "已將選取結果建立為正式 Query。", "success");
  await router.push({ name: "geo-project-edit", params: { projectId: projectId.value } });
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

function toggleDraft(draft: GeoQueryDraftResource): void {
  if (draft.acceptedQueryId) return;
  selectedDraftIds.value = selectedDraftIds.value.includes(draft.id)
    ? selectedDraftIds.value.filter((id) => id !== draft.id)
    : [...selectedDraftIds.value, draft.id];
}

function toggleAll(): void {
  selectedDraftIds.value = allChecked.value ? [] : selectableDrafts.value.map((draft) => draft.id);
}
</script>

<template>
  <main class="geo-form-page geo-query-research-page">
    <div class="geo-form-shell">
      <header class="geo-form-page-header">
        <button class="geo-back-button" type="button" title="返回" @click="step === 2 ? step = 1 : router.push({ name: 'geo-projects' })"><AppIcon name="chevron-left" :size="16" /></button>
        <div><h1>Query Search</h1><p>設定並生成 Query</p></div>
        <span class="geo-header-spacer"></span>
        <template v-if="step === 1"><button class="button button-secondary" type="button" @click="router.push({ name: 'geo-projects' })">返回</button><button class="button button-primary" type="button" :disabled="loading" @click="executeSearch">執行 Query Search</button></template>
        <template v-else><button class="button button-secondary" type="button" @click="step = 1">返回</button><button class="button button-primary" type="button" :disabled="loading" @click="confirmDrafts">確認生成 Query</button></template>
      </header>
      <div v-if="errorMessage" class="geo-error-message">{{ errorMessage }}</div>
      <div v-if="loading && !profile" class="geo-form-loading">正在載入 Project…</div>
      <div v-else-if="profile" class="geo-form-stack">
        <template v-if="step === 1">
          <section class="geo-form-card"><header><strong>品牌基本資料</strong></header><div class="geo-read-grid"><div><span>Project 名稱</span><strong>{{ profile.project.name }}</strong></div><div><span>網址/網域</span><strong>{{ profile.ownBrand.websiteUrl || "—" }}</strong></div><div><span>客戶</span><strong>{{ profile.customerName }}</strong></div><div><span>地區</span><strong>{{ profile.project.defaultRegion }}</strong></div><div><span>語系</span><strong>{{ profile.project.defaultLanguage }}</strong></div><div><span>別名</span><strong>{{ profile.ownBrand.aliases.map((alias) => alias.alias).join("、") || "—" }}</strong></div><div class="geo-read-full"><span>競品</span><div><span v-for="competitor in profile.competitors" :key="competitor.clientId" class="geo-read-tag">{{ competitor.name }}</span><strong v-if="!profile.competitors.length">—</strong></div></div></div></section>
          <section class="geo-form-card"><header><strong>Provider</strong></header><div class="geo-form-grid"><GeoFormField label="Research / Generation Provider"><select v-model="form.researchProvider"><option value="gemini">Gemini</option></select></GeoFormField><GeoFormField label="Run Provider"><select v-model="form.runProvider"><option value="gemini">Gemini</option></select></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Keywords</strong><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button></header><div class="geo-card-body"><textarea v-model="form.keywords" rows="5" placeholder="一行一個 keyword"></textarea><small>一行一個 keyword，或用 AI 依專案資料自動生成。</small></div></section>
          <section class="geo-form-card"><header><strong>Topics</strong><div><button class="button button-secondary button-small" type="button" disabled><AppIcon name="sparkles" :size="14" />AI生成</button><button class="button button-secondary button-small" type="button" @click="topics.push({ name: '', description: '' })">新增 Topic</button></div></header><div class="geo-card-body geo-topic-list"><div v-for="(topic, index) in topics" :key="index"><label><span>Topic 名稱</span><input v-model="topic.name" type="text" placeholder="例如 產品、採購評估、供應商" /></label><label><span>Topic 描述</span><input v-model="topic.description" type="text" placeholder="描述此 Topic" /></label><button class="button button-secondary button-small" type="button" @click="topics.splice(index, 1)">移除</button></div><p v-if="!topics.length">尚未新增 Topic，點右上「新增 Topic」開始</p></div></section>
          <section class="geo-form-card"><header><strong>市場與受眾</strong></header><div class="geo-form-grid"><GeoFormField label="Market Type"><select v-model="form.marketType"><option value="b2b_procurement">B2B 採購</option><option value="b2c">B2C 消費</option></select></GeoFormField><GeoFormField label="Max Queries"><input v-model.number="form.maxQueries" type="number" min="1" max="40" /></GeoFormField><GeoFormField label="Audience"><input v-model="form.audienceName" type="text" /></GeoFormField><GeoFormField label="Audience Description"><input v-model="form.audienceDescription" type="text" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>Intent 與提及規則</strong></header><div class="geo-form-grid"><GeoFormField label="Intent 分類"><select v-model="form.intentCategory"><option v-if="!standardIntentCategories.includes(form.intentCategory)" :value="form.intentCategory">{{ form.intentCategory }}</option><option v-for="category in standardIntentCategories" :key="category" :value="category">{{ category }}</option></select></GeoFormField><GeoFormField label="Intent 描述"><input v-model="form.intentDescription" type="text" /></GeoFormField></div></section>
          <section class="geo-form-card"><header><strong>提示詞風格</strong></header><div class="geo-toggle-list"><label><span class="geo-toggle-copy"><strong>提及自身品牌</strong><small>生成的 query 需包含自家品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionOwnBrand" type="checkbox" /><span aria-hidden="true"></span></span></label><label><span class="geo-toggle-copy"><strong>提及競品</strong><small>生成的 query 需包含競爭品牌名稱</small></span><span class="geo-toggle-switch"><input v-model="form.shouldMentionCompetitor" type="checkbox" /><span aria-hidden="true"></span></span></label></div></section>
        </template>
        <section v-else class="geo-form-card geo-generation-results"><header><strong>生成結果</strong><div><span>已選 {{ selectedDraftIds.length }} / {{ selectableDrafts.length }}</span><button class="button button-secondary button-small" type="button" :disabled="loading" @click="regenerate">重新生成</button></div></header><div class="geo-result-head"><input type="checkbox" :checked="allChecked" :indeterminate.prop="someChecked" @change="toggleAll" /><span>Query list</span></div><button v-for="draft in drafts" :key="draft.id" class="geo-result-row" :class="{ selected: selectedDraftIds.includes(draft.id), accepted: draft.acceptedQueryId }" type="button" :disabled="Boolean(draft.acceptedQueryId)" @click="toggleDraft(draft)"><input type="checkbox" :checked="selectedDraftIds.includes(draft.id)" :disabled="Boolean(draft.acceptedQueryId)" tabindex="-1" /><span><strong>{{ draft.queryText }}</strong><small>{{ draft.region }}/{{ draft.language }}<template v-if="draft.acceptedQueryId"> · 已建立</template></small></span></button><div v-if="!drafts.length" class="geo-table-empty">沒有生成結果</div></section>
      </div>
    </div>
    <GeoConfirmDialog :open="showEmptyAlert" single title="尚未選擇 Query" message="請至少勾選一筆 Query，再進行生成。" confirm-label="我知道了" @cancel="showEmptyAlert = false" @confirm="showEmptyAlert = false" />
  </main>
</template>
