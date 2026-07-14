<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import {
  applyProjectDiscoveryDraft,
  createProjectIdentityDraft,
  createProjectSuggestionsDraft,
  isProjectIdentityDraftConfirmable,
  type ProjectIdentityDraft,
  type ProjectSuggestionsDraft,
  type QueryResearchProjectReplacement,
} from "../../composables/project-discovery-draft";
import { ApiError, api } from "../../services/api";
import type {
  GeoMarketType,
  GeoQueryAudienceRequest,
  GeoRegion,
} from "../../types";
import AppIcon from "../ui/AppIcon.vue";

const props = defineProps<{
  region: GeoRegion;
  language: string;
  marketType: GeoMarketType;
  audience: GeoQueryAudienceRequest | null;
}>();

const emit = defineEmits<{
  apply: [replacement: QueryResearchProjectReplacement];
}>();

const input = reactive({
  projectUrl: "",
  competitorCount: 5,
  topicCount: 5,
  keywordCount: 5,
});
const identityDraft = ref<ProjectIdentityDraft | null>(null);
const suggestionsDraft = ref<ProjectSuggestionsDraft | null>(null);
const inspecting = ref(false);
const suggesting = ref(false);
const error = ref("");
const message = ref("");
const applyPending = ref(false);

const canSuggest = computed(
  () =>
    identityDraft.value !== null &&
    isProjectIdentityDraftConfirmable(identityDraft.value),
);

watch(
  () => props.language,
  () => invalidateIdentity(),
);
watch(
  () => [
    props.region,
    props.marketType,
    props.audience?.name ?? "",
    props.audience?.description ?? "",
  ],
  () => invalidateSuggestions(),
);
watch(
  () => [input.competitorCount, input.topicCount, input.keywordCount],
  () => invalidateSuggestions(),
);

async function inspectProject(): Promise<void> {
  const projectUrl = input.projectUrl.trim();
  if (!projectUrl) {
    error.value = "請輸入公開的 Project URL。";
    return;
  }
  inspecting.value = true;
  error.value = "";
  message.value = "";
  applyPending.value = false;
  suggestionsDraft.value = null;
  try {
    const result = await api.inspectGeoProject({
      projectUrl,
      language: props.language,
    });
    identityDraft.value = createProjectIdentityDraft(result);
    message.value = "品牌資料已載入。";
  } catch (caught) {
    identityDraft.value = null;
    error.value = errorMessage(caught);
  } finally {
    inspecting.value = false;
  }
}

async function generateSuggestions(): Promise<void> {
  if (!identityDraft.value || !canSuggest.value) {
    error.value = "請確認品牌名稱、業務描述與至少一項核心產品或服務。";
    return;
  }
  suggesting.value = true;
  error.value = "";
  message.value = "";
  applyPending.value = false;
  try {
    const confirmedProject = normalizedIdentity(identityDraft.value);
    const result = await api.suggestGeoProject({
      confirmedProject,
      region: props.region,
      language: props.language,
      marketType: props.marketType,
      audience: props.audience,
      competitorCount: input.competitorCount,
      topicCount: input.topicCount,
      keywordCount: input.keywordCount,
    });
    identityDraft.value = confirmedProject;
    suggestionsDraft.value = createProjectSuggestionsDraft(result);
    message.value = "建議已產生。";
  } catch (caught) {
    suggestionsDraft.value = null;
    error.value = errorMessage(caught);
  } finally {
    suggesting.value = false;
  }
}

function requestApply(): void {
  if (!identityDraft.value || !suggestionsDraft.value) return;
  applyPending.value = true;
  message.value = "";
}

function confirmApply(): void {
  if (!identityDraft.value || !suggestionsDraft.value) return;
  if (!isProjectIdentityDraftConfirmable(identityDraft.value)) {
    error.value = "請確認品牌資料後再套用。";
    applyPending.value = false;
    return;
  }
  emit(
    "apply",
    applyProjectDiscoveryDraft(identityDraft.value, suggestionsDraft.value),
  );
  error.value = "";
  message.value = "建議已套用至 Query Research 設定。";
  applyPending.value = false;
}

function addCoreOffering(): void {
  identityDraft.value?.coreOfferings.push("");
  invalidateSuggestions(true);
}

function removeCoreOffering(index: number): void {
  identityDraft.value?.coreOfferings.splice(index, 1);
  invalidateSuggestions(true);
}

function addCompetitor(): void {
  suggestionsDraft.value?.competitors.push("");
}

function addTopic(): void {
  suggestionsDraft.value?.topics.push({ name: "", description: "" });
}

function addKeyword(): void {
  suggestionsDraft.value?.keywords.push("");
}

function removeCompetitor(index: number): void {
  suggestionsDraft.value?.competitors.splice(index, 1);
}

function removeTopic(index: number): void {
  suggestionsDraft.value?.topics.splice(index, 1);
}

function removeKeyword(index: number): void {
  suggestionsDraft.value?.keywords.splice(index, 1);
}

function invalidateIdentity(): void {
  identityDraft.value = null;
  suggestionsDraft.value = null;
  applyPending.value = false;
  error.value = "";
  message.value = "";
}

function invalidateSuggestions(showMessage = false): void {
  const hadSuggestions = suggestionsDraft.value !== null;
  suggestionsDraft.value = null;
  applyPending.value = false;
  if (showMessage && hadSuggestions) {
    message.value = "品牌資料已更新。";
  }
}

function normalizedIdentity(
  identity: ProjectIdentityDraft,
): ProjectIdentityDraft {
  return {
    ...identity,
    projectName: identity.projectName.trim(),
    projectDescription: identity.projectDescription.trim(),
    coreOfferings: cleanedLines(identity.coreOfferings),
    targetAudiences: cleanedLines(identity.targetAudiences),
  };
}

function cleanedLines(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean);
}

function errorMessage(caught: unknown): string {
  if (!(caught instanceof ApiError)) return "Project Discovery 目前無法回應。";
  const messages: Record<string, string> = {
    insufficient_project_context:
      "此網址的公開內容不足，請更換內容較完整的 URL 或手動輸入設定。",
    invalid_confirmed_project: "品牌資料不完整，請確認後再試一次。",
    project_url_retrieval_failed: "無法讀取此公開網址，請確認網址後再試一次。",
    project_url_inspection_failed: "Project 身分辨識失敗，請稍後再試。",
    project_market_research_not_grounded:
      "本次搜尋沒有取得可驗證的市場資料，請稍後再試。",
    project_market_research_failed: "市場搜尋失敗，請稍後再試。",
  };
  return messages[caught.message] ?? caught.message;
}

function referenceLabel(title: string | null | undefined, url: string): string {
  if (title?.trim()) return title.trim();
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
</script>

<template>
  <fieldset class="geo-fieldset geo-discovery-fieldset">
    <legend>Project URL 建議</legend>
    <div class="geo-discovery-url-row">
      <label>
        <span>Project URL</span>
        <input
          v-model="input.projectUrl"
          type="url"
          placeholder="https://example.com/"
          autocomplete="url"
          @input="invalidateIdentity"
        />
      </label>
      <button
        class="button button-secondary"
        type="button"
        :disabled="inspecting || suggesting"
        @click="inspectProject"
      >
        <AppIcon name="search" :size="16" />
        {{ inspecting ? "分析中" : "分析 Project" }}
      </button>
    </div>

    <p v-if="error" class="geo-discovery-feedback error" role="alert">
      <AppIcon name="alert-circle" :size="16" />
      {{ error }}
    </p>
    <p v-if="message" class="geo-discovery-feedback success" role="status">
      <AppIcon name="check-circle" :size="16" />
      {{ message }}
    </p>

    <section v-if="identityDraft" class="geo-discovery-stage">
      <header class="geo-discovery-stage-header">
        <strong><span>1</span>品牌確認</strong>
      </header>

      <label>
        <span>品牌名稱</span>
        <input
          v-model="identityDraft.projectName"
          type="text"
          @input="invalidateSuggestions(true)"
        />
      </label>
      <label>
        <span>業務描述</span>
        <textarea
          v-model="identityDraft.projectDescription"
          rows="3"
          @input="invalidateSuggestions(true)"
        ></textarea>
      </label>

      <div class="geo-discovery-list-section identity-list">
        <header class="geo-discovery-list-header">
          <strong>核心產品 / 服務</strong>
          <button
            class="button button-secondary button-small"
            type="button"
            @click="addCoreOffering"
          >
            <AppIcon name="plus" :size="14" />新增
          </button>
        </header>
        <div
          v-for="(_, index) in identityDraft.coreOfferings"
          :key="`discovery-offering-${index}`"
          class="geo-discovery-input-row"
        >
          <input
            v-model="identityDraft.coreOfferings[index]"
            type="text"
            :aria-label="`核心產品或服務 ${index + 1}`"
            @input="invalidateSuggestions(true)"
          />
          <button
            class="geo-icon-button"
            type="button"
            title="移除核心產品或服務"
            :aria-label="`移除核心產品或服務 ${index + 1}`"
            @click="removeCoreOffering(index)"
          >
            <AppIcon name="trash" :size="15" />
          </button>
        </div>
      </div>

      <div class="geo-three-col geo-discovery-counts">
        <label>
          <span>競品數量</span>
          <input
            v-model.number="input.competitorCount"
            type="number"
            min="1"
            max="8"
          />
        </label>
        <label>
          <span>Topic 數量</span>
          <input
            v-model.number="input.topicCount"
            type="number"
            min="1"
            max="8"
          />
        </label>
        <label>
          <span>Keyword 數量</span>
          <input
            v-model.number="input.keywordCount"
            type="number"
            min="1"
            max="10"
          />
        </label>
      </div>

      <div class="geo-discovery-actions">
        <button
          class="button button-primary"
          type="button"
          :disabled="!canSuggest || suggesting || inspecting"
          @click="generateSuggestions"
        >
          <AppIcon name="search" :size="16" />
          {{ suggesting ? "生成中" : "確認並產生建議" }}
        </button>
      </div>
    </section>

    <section v-if="suggestionsDraft" class="geo-discovery-stage">
      <header class="geo-discovery-stage-header">
        <strong><span>2</span>建議結果</strong>
      </header>

      <div class="geo-discovery-list-section first">
        <header class="geo-discovery-list-header">
          <strong>競品</strong>
          <button
            class="button button-secondary button-small"
            type="button"
            @click="addCompetitor"
          >
            <AppIcon name="plus" :size="14" />新增競品
          </button>
        </header>
        <div
          v-for="(_, index) in suggestionsDraft.competitors"
          :key="`discovery-competitor-${index}`"
          class="geo-discovery-input-row"
        >
          <input
            v-model="suggestionsDraft.competitors[index]"
            type="text"
            :aria-label="`競品 ${index + 1}`"
          />
          <button
            class="geo-icon-button"
            type="button"
            title="移除競品"
            :aria-label="`移除競品 ${index + 1}`"
            @click="removeCompetitor(index)"
          >
            <AppIcon name="trash" :size="15" />
          </button>
        </div>
      </div>

      <div class="geo-discovery-list-section">
        <header class="geo-discovery-list-header">
          <strong>Topics</strong>
          <button
            class="button button-secondary button-small"
            type="button"
            @click="addTopic"
          >
            <AppIcon name="plus" :size="14" />新增 Topic
          </button>
        </header>
        <div
          v-for="(topic, index) in suggestionsDraft.topics"
          :key="`discovery-topic-${index}`"
          class="geo-discovery-topic-row"
        >
          <div class="geo-discovery-list-header compact">
            <strong>Topic {{ index + 1 }}</strong>
            <button
              class="geo-icon-button"
              type="button"
              title="移除 Topic"
              :aria-label="`移除 Topic ${index + 1}`"
              @click="removeTopic(index)"
            >
              <AppIcon name="trash" :size="15" />
            </button>
          </div>
          <label>
            <span>名稱</span>
            <input v-model="topic.name" type="text" />
          </label>
          <label>
            <span>描述</span>
            <textarea v-model="topic.description" rows="2"></textarea>
          </label>
        </div>
      </div>

      <div class="geo-discovery-list-section">
        <header class="geo-discovery-list-header">
          <strong>Keywords</strong>
          <button
            class="button button-secondary button-small"
            type="button"
            @click="addKeyword"
          >
            <AppIcon name="plus" :size="14" />新增 Keyword
          </button>
        </header>
        <div
          v-for="(_, index) in suggestionsDraft.keywords"
          :key="`discovery-keyword-${index}`"
          class="geo-discovery-input-row"
        >
          <input
            v-model="suggestionsDraft.keywords[index]"
            type="text"
            :aria-label="`Keyword ${index + 1}`"
          />
          <button
            class="geo-icon-button"
            type="button"
            title="移除 Keyword"
            :aria-label="`移除 Keyword ${index + 1}`"
            @click="removeKeyword(index)"
          >
            <AppIcon name="trash" :size="15" />
          </button>
        </div>
      </div>

      <details
        v-if="suggestionsDraft.references.length"
        class="geo-discovery-references"
      >
        <summary>搜尋依據（{{ suggestionsDraft.references.length }}）</summary>
        <ul>
          <li
            v-for="reference in suggestionsDraft.references"
            :key="reference.url"
          >
            <a :href="reference.url" target="_blank" rel="noreferrer">
              {{ referenceLabel(reference.title, reference.url) }}
            </a>
          </li>
        </ul>
      </details>

      <div class="geo-discovery-actions">
        <button
          class="button button-primary"
          type="button"
          @click="requestApply"
        >
          <AppIcon name="check" :size="16" />套用至表單
        </button>
      </div>

      <div v-if="applyPending" class="geo-discovery-confirm">
        <p>這會取代目前的自身品牌、競品、Topics 與 Keywords。</p>
        <div>
          <button
            class="button button-secondary"
            type="button"
            @click="applyPending = false"
          >
            取消
          </button>
          <button
            class="button button-primary"
            type="button"
            @click="confirmApply"
          >
            確認取代
          </button>
        </div>
      </div>
    </section>
  </fieldset>
</template>
