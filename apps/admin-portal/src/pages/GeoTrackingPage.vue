<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import ProjectDiscoveryPanel from "../components/geo/ProjectDiscoveryPanel.vue";
import AppIcon from "../components/ui/AppIcon.vue";
import type { QueryResearchProjectReplacement } from "../composables/project-discovery-draft";
import { ApiError, api } from "../services/api";
import type {
  GeoGeneratedQuery,
  GeoMarketType,
  GeoProvider,
  GeoQueryProvider,
  GeoRegion,
  GeoRunResult,
  GeoTopicInput,
} from "../types";

const intentCategoryOptions = [
  {
    value: "navigational",
    label: "導航",
    description: "用尋找官方網站、品牌頁面、地址、登入或售後資訊的角度生成 query。",
  },
  {
    value: "informational",
    label: "資訊",
    description: "用查詢知識、教學、定義、常見問題的角度生成 query。",
  },
  {
    value: "commercial_investigation",
    label: "商業",
    description: "用比較選項、評估供應商、查看評價與採購風險的角度生成 query。",
  },
  {
    value: "transactional",
    label: "交易",
    description: "用準備購買、詢價、預約、取得優惠或採取行動的角度生成 query。",
  },
];

const form = reactive({
  brandName: "Shan Hua Plastic Industrial Co., Ltd. (SHPI)",
  competitorBrands: "CEJN Industrial Corporation",
  keywords: "pneumatic tubing\nair brake hose",
  region: "US" as GeoRegion,
  language: "en-US",
  marketType: "b2b_procurement" as GeoMarketType,
  topics: [
    {
      name: "品牌型",
      description: "聚焦自身品牌、競品品牌、品牌比較與品牌信任度。",
    },
    {
      name: "產品型",
      description: "聚焦產品用途、規格、適用情境、品質與替代方案。",
    },
    {
      name: "採購評估",
      description: "聚焦供應商條件、交期、認證、外銷能力與採購風險。",
    },
  ] as GeoTopicInput[],
  intentCategory: "commercial_investigation",
  intentDescription:
    "用比較選項、評估供應商、查看評價與採購風險的角度生成 query。",
  audienceName: "B2B 採購",
  audienceDescription: "正在評估供應商的採購人員",
  shouldMentionOwnBrand: true,
  shouldMentionCompetitor: true,
  maxQueries: 8,
});

const provider = ref<GeoProvider>("dummy");
const queryGenerationProvider = ref<GeoQueryProvider>("dummy");
const loading = ref(false);
const error = ref("");
const queries = ref<GeoGeneratedQuery[]>([]);
const shortlistedQueryIds = ref<Set<string>>(new Set());
const runResults = ref<GeoRunResult[]>([]);
const querySection = ref<HTMLElement | null>(null);
const projectDiscoveryResetKey = ref(0);

const selectedQueries = computed(() =>
  queries.value.filter((query) => shortlistedQueryIds.value.has(query.id)),
);

const keywordCount = computed(() => lines(form.keywords).length);
const marketTypeLabel = computed(() =>
  form.marketType === "b2b_procurement" ? "B2B 採購" : "B2C 消費",
);
onMounted(() => {
  void loadExample();
});

async function loadExample(): Promise<void> {
  await run(async () => {
    const example = await api.geoDummyProject();
    form.brandName = example.brandName;
    form.competitorBrands = example.competitorBrands.join("\n");
    form.keywords = example.keywords.join("\n");
    form.region = example.region;
    form.language = example.region === "US" ? "en-US" : "zh-TW";
    form.marketType = example.marketType;
    form.topics = example.topics?.length
      ? example.topics.map((topic) => ({ ...topic }))
      : example.topicNames.map((name) => ({ name, description: "" }));
    form.intentCategory = "commercial_investigation";
    applyIntentDefaultDescription();
    form.audienceName = "B2B 採購";
    form.audienceDescription = "正在評估供應商的採購人員";
    form.shouldMentionOwnBrand = true;
    form.shouldMentionCompetitor = true;
    queries.value = [];
    shortlistedQueryIds.value = new Set();
    runResults.value = [];
    provider.value = "dummy";
    queryGenerationProvider.value = "dummy";
    projectDiscoveryResetKey.value += 1;
  });
}

function applyProjectDiscovery(
  replacement: QueryResearchProjectReplacement,
): void {
  form.brandName = replacement.brandName;
  form.competitorBrands = replacement.competitorBrands;
  form.topics = replacement.topics;
  form.keywords = replacement.keywords;
  queries.value = [];
  shortlistedQueryIds.value = new Set();
  runResults.value = [];
}

async function generateQueries(): Promise<void> {
  if (!canSubmit()) return;
  await run(async () => {
    const result = await api.generateGeoQueries({
      provider: queryGenerationProvider.value,
      brandName: form.brandName,
      competitorBrands: lines(form.competitorBrands),
      keywords: lines(form.keywords),
      region: form.region,
      language: form.language || null,
      marketType: form.marketType,
      topics: normalizedTopics(),
      topicNames: normalizedTopics().map((topic) => topic.name),
      intents: [
        {
          category: form.intentCategory,
          description: form.intentDescription,
        },
      ],
      audience: {
        name: form.audienceName,
        description: form.audienceDescription,
      },
      brandMentionRules: {
        shouldMentionOwnBrand: form.shouldMentionOwnBrand,
        shouldMentionCompetitor: form.shouldMentionCompetitor,
      },
      researchContext: null,
      maxQueries: form.maxQueries,
    });
    queries.value = result.queries;
    shortlistedQueryIds.value = new Set();
    runResults.value = [];
    await nextTick();
    querySection.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

async function runSelectedQueries(): Promise<void> {
  if (!selectedQueries.value.length) {
    error.value = "請先將至少一筆 Prompt 加入 Shortlist。";
    return;
  }
  await run(async () => {
    const result = await api.runGeoQueries(provider.value, selectedQueries.value);
    runResults.value = result.results;
  });
}

function toggleShortlist(queryId: string): void {
  const next = new Set(shortlistedQueryIds.value);
  if (next.has(queryId)) next.delete(queryId);
  else next.add(queryId);
  shortlistedQueryIds.value = next;
}

function lines(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function addTopic(): void {
  form.topics.push({ name: "", description: "" });
}

function removeTopic(index: number): void {
  if (form.topics.length <= 1) return;
  form.topics.splice(index, 1);
}

function normalizedTopics(): GeoTopicInput[] {
  return form.topics
    .map((topic) => ({
      name: topic.name.trim(),
      description: topic.description.trim(),
    }))
    .filter((topic) => topic.name);
}

function canSubmit(): boolean {
  const keywords = lines(form.keywords);
  if (!form.brandName.trim()) {
    error.value = "請填寫品牌名稱。";
    return false;
  }
  if (!keywords.length) {
    error.value = "請至少輸入一個關鍵字。";
    return false;
  }
  if (keywords.length > 10) {
    error.value = "關鍵字最多 10 個。";
    return false;
  }
  if (!normalizedTopics().length) {
    error.value = "請至少輸入一個 Topic 名稱。";
    return false;
  }
  if (!form.intentDescription.trim()) {
    error.value = "請填寫 Intent 描述。";
    return false;
  }
  if (!form.audienceName.trim() || !form.audienceDescription.trim()) {
    error.value = "請填寫 Audience 名稱與描述。";
    return false;
  }
  if (!Number.isFinite(form.maxQueries) || form.maxQueries < 1) {
    error.value = "請輸入 Query 數量，且至少為 1。";
    return false;
  }
  return true;
}

function applyRegionDefaultLanguage(): void {
  form.language = form.region === "US" ? "en-US" : "zh-TW";
}

function applyIntentDefaultDescription(): void {
  const selected = intentCategoryOptions.find(
    (option) => option.value === form.intentCategory,
  );
  form.intentDescription = selected?.description ?? "";
}

function intentCategoryLabel(category: string): string {
  return (
    intentCategoryOptions.find((option) => option.value === category)?.label ??
    category
  );
}

function intentCategoryCode(category: string): string {
  const codeByCategory: Record<string, string> = {
    navigational: "N",
    informational: "I",
    commercial_investigation: "C",
    transactional: "T",
  };
  return codeByCategory[category] ?? "?";
}

function intentCodeTone(category: string): string {
  const toneByCategory: Record<string, string> = {
    navigational: "geo-intent-n",
    informational: "geo-intent-i",
    commercial_investigation: "geo-intent-c",
    transactional: "geo-intent-t",
  };
  return toneByCategory[category] ?? "geo-intent-unknown";
}

function queryKeywords(query: GeoGeneratedQuery): string[] {
  return query.keywords?.length ? query.keywords : [query.attributes.keyword];
}

function referenceDisplayLabel(
  reference: GeoRunResult["references"][number],
): string {
  if (reference.title?.trim()) return reference.title.trim();
  return domainLabel(reference.url);
}

function resultReferences(
  result: GeoRunResult,
): GeoRunResult["references"] {
  if (result.references?.length) return result.references;
  return result.referenceUrls.map((url) => ({ url, title: null }));
}

function domainLabel(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

async function run(action: () => Promise<void>): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    await action();
  } catch (caught) {
    error.value =
      caught instanceof ApiError ? caught.message : "GEO 跑題服務目前無法回應。";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <section class="page geo-tracking-page">
    <header class="page-header geo-query-header">
      <div class="geo-heading">
        <p class="page-kicker">Query Research</p>
        <h1>GEO Query Research</h1>
        <p>
          依據品牌、競品、關鍵字、Topic、Intent 與 Audience 產生候選 query，
          後續可挑選要納入 GEO tracking 的題目。
        </p>
      </div>
      <div class="geo-header-actions">
        <button class="button button-secondary" type="button" @click="loadExample">
          載入範例
        </button>
      </div>
    </header>

    <div class="geo-status-strip">
      <div>
        <span>Keywords</span>
        <strong>{{ keywordCount }}/10</strong>
      </div>
      <div>
        <span>地區 / 語言</span>
        <strong>{{ form.region }} · {{ form.language }}</strong>
      </div>
      <div>
        <span>市場語境</span>
        <strong>{{ marketTypeLabel }}</strong>
      </div>
      <div>
        <span>生成角度</span>
        <strong>{{ intentCategoryLabel(form.intentCategory) }}</strong>
      </div>
    </div>

    <div v-if="error" class="mock-notice subtle">
      <AppIcon name="alert-circle" :size="17" />{{ error }}
    </div>

    <div class="geo-workbench">
      <form class="card geo-form" @submit.prevent>
        <header class="card-header geo-step-header">
          <div>
            <h2><span class="geo-step-number">1</span>設定與生成</h2>
            <p>設定品牌、市場、Topic、Intent 與 Audience。</p>
          </div>
        </header>
        <div class="geo-form-body">
          <fieldset class="geo-fieldset">
            <legend>市場設定</legend>
            <div class="geo-three-col">
              <label>
                <span>地區</span>
                <select
                  v-model="form.region"
                  aria-label="地區"
                  @change="applyRegionDefaultLanguage"
                >
                  <option value="TW">台灣</option>
                  <option value="US">美國</option>
                </select>
              </label>
              <label>
                <span>語言</span>
                <select v-model="form.language" aria-label="語言">
                  <option value="zh-TW">繁體中文（台灣）</option>
                  <option value="en-US">English (US)</option>
                </select>
              </label>
              <label>
                <span>市場語境</span>
                <select v-model="form.marketType" aria-label="市場語境">
                  <option value="b2c">B2C 消費</option>
                  <option value="b2b_procurement">B2B 採購</option>
                </select>
              </label>
            </div>
          </fieldset>

          <ProjectDiscoveryPanel
            :key="projectDiscoveryResetKey"
            :region="form.region"
            :language="form.language"
            :market-type="form.marketType"
            @apply="applyProjectDiscovery"
          />

          <fieldset class="geo-fieldset">
            <legend>專案與品牌</legend>
            <label>
              <span>自身品牌</span>
              <input v-model="form.brandName" type="text" />
            </label>
            <label>
              <span>競品品牌</span>
              <textarea v-model="form.competitorBrands" rows="3"></textarea>
            </label>
          </fieldset>

          <fieldset class="geo-fieldset">
            <legend>Keywords 與 Topics</legend>
            <label>
              <span>關鍵字清單</span>
              <textarea v-model="form.keywords" rows="3"></textarea>
            </label>
            <div class="geo-topic-editor">
              <div class="geo-topic-editor-header">
                <div>
                  <span>Topic 約束</span>
                  <small>{{ form.topics.length }} 個 Topic</small>
                </div>
                <button class="button button-secondary" type="button" @click="addTopic">
                  <AppIcon name="plus" :size="15" />新增 Topic
                </button>
              </div>
              <div
                v-for="(topic, index) in form.topics"
                :key="index"
                class="geo-topic-row"
              >
                <div class="geo-topic-row-header">
                  <strong>Topic {{ index + 1 }}</strong>
                  <button
                    class="geo-icon-button geo-topic-remove"
                    type="button"
                    :disabled="form.topics.length <= 1"
                    :title="form.topics.length <= 1 ? '至少保留一個 Topic' : `移除 Topic ${index + 1}`"
                    :aria-label="`移除 Topic ${index + 1}`"
                    @click="removeTopic(index)"
                  >
                    <AppIcon name="trash" :size="16" />
                  </button>
                </div>
                <label>
                  <span>Topic 名稱</span>
                  <input v-model="topic.name" type="text" />
                </label>
                <label>
                  <span>Topic 描述</span>
                  <textarea
                    v-model="topic.description"
                    aria-label="Topic 描述"
                    rows="3"
                  ></textarea>
                </label>
              </div>
            </div>
          </fieldset>

          <fieldset class="geo-fieldset">
            <legend>Query 生成約束</legend>
            <label>
              <span>Intent 分類</span>
              <select
                v-model="form.intentCategory"
                aria-label="Intent 分類"
                @change="applyIntentDefaultDescription"
              >
                <option
                  v-for="option in intentCategoryOptions"
                  :key="option.value"
                  :value="option.value"
                >
                  {{ option.label }}
                </option>
              </select>
            </label>
            <label>
              <span>Intent 描述</span>
              <textarea
                v-model="form.intentDescription"
                aria-label="Intent 描述"
                rows="3"
              ></textarea>
            </label>
            <div class="geo-two-col">
              <label>
                <span>Audience 名稱</span>
                <input v-model="form.audienceName" type="text" />
              </label>
              <label>
                <span>Audience 描述</span>
                <input v-model="form.audienceDescription" type="text" />
              </label>
            </div>
            <div class="geo-toggle-grid">
              <label class="check-row">
                <input v-model="form.shouldMentionOwnBrand" type="checkbox" />
                <span>query 需提及自身品牌</span>
              </label>
              <label class="check-row">
                <input v-model="form.shouldMentionCompetitor" type="checkbox" />
                <span>query 可視情境提及競品</span>
              </label>
            </div>
            <label>
              <span>最大題數</span>
              <input v-model.number="form.maxQueries" min="1" max="40" type="number" />
            </label>
          </fieldset>
        </div>
        <div class="geo-form-footer">
          <label class="geo-provider-control">
            <span>Query 生成模型</span>
            <select
              v-model="queryGenerationProvider"
              aria-label="Query 生成模型"
            >
              <option value="dummy">Dummy</option>
              <option value="gemini">Gemini</option>
            </select>
          </label>
          <button
            class="button button-primary"
            type="button"
            :disabled="loading"
            @click="generateQueries"
          >
            <AppIcon name="sparkles" :size="16" />生成 Query
          </button>
        </div>
      </form>

      <div class="geo-main-column">
        <section ref="querySection" class="card geo-queries geo-step-card">
          <header class="card-header geo-step-header">
            <div>
              <h2><span class="geo-step-number">2</span>候選 Query</h2>
              <p>檢視生成結果並選取要執行的題目。</p>
            </div>
            <span class="geo-record-count">
              {{ queries.length }} 筆 · 已選 {{ selectedQueries.length }} 筆
            </span>
          </header>
          <div v-if="!queries.length" class="empty-state">
            <AppIcon name="list" />
            <strong>尚未生成候選 Query</strong>
            <p>完成左側設定後即可生成。</p>
          </div>
          <div v-else class="geo-query-list">
            <div class="geo-query-list-head" aria-hidden="true">
              <span>Prompt</span>
              <span>Keywords</span>
              <span>Intent</span>
              <span>動作</span>
            </div>
            <article
              v-for="query in queries"
              :key="query.id"
              class="geo-query-row"
              :class="{ selected: shortlistedQueryIds.has(query.id) }"
            >
              <div class="geo-prompt-cell">
                <strong>{{ query.text }}</strong>
                <small>
                  {{ query.topicName }} · {{ query.attributes.audience.name }}
                  · {{ query.region }} · {{ query.language }}
                </small>
              </div>
              <div class="geo-keyword-tags">
                <span class="geo-mobile-label">Keywords</span>
                <div>
                    <span
                      v-for="keyword in queryKeywords(query)"
                      :key="`${query.id}-${keyword}`"
                      class="badge badge-muted"
                    >
                      {{ keyword }}
                    </span>
                </div>
              </div>
              <div class="geo-intent-cell">
                <span class="geo-mobile-label">Intent</span>
                <span
                  class="geo-intent-label"
                  :title="query.attributes.intent.description"
                >
                    <span
                      class="geo-intent-pill"
                      :class="intentCodeTone(query.attributes.intent.category)"
                    >
                      {{ intentCategoryCode(query.attributes.intent.category) }}
                    </span>
                    {{ intentCategoryLabel(query.attributes.intent.category) }}
                </span>
              </div>
              <div class="geo-actions-cell">
                <button
                  class="button button-secondary geo-shortlist-button"
                  type="button"
                  :class="{ active: shortlistedQueryIds.has(query.id) }"
                  @click="toggleShortlist(query.id)"
                >
                  {{ shortlistedQueryIds.has(query.id) ? "已加入" : "加入 Shortlist" }}
                </button>
              </div>
            </article>
          </div>
        </section>

        <section
          class="card geo-results geo-step-card"
          :class="{ 'geo-results-inactive': !selectedQueries.length }"
        >
          <header class="card-header geo-step-header">
            <div>
              <h2><span class="geo-step-number">3</span>Runner 跑題引擎</h2>
              <p v-if="selectedQueries.length">
                已選 {{ selectedQueries.length }} 筆 Query，選擇模型後即可執行。
              </p>
              <p v-else>加入至少一筆 Shortlist 後即可執行。</p>
            </div>
            <div v-if="selectedQueries.length" class="geo-run-actions">
              <label class="geo-provider-control">
                <span>執行模型</span>
                <select v-model="provider" aria-label="執行模型">
                  <option value="dummy">Dummy</option>
                  <option value="gemini">Gemini Vertex AI</option>
                  <option value="google_aio">Google AIO (SerpApi)</option>
                </select>
              </label>
              <button
                class="button button-primary"
                type="button"
                :disabled="loading"
                @click="runSelectedQueries"
              >
                <AppIcon name="activity" :size="16" />執行 Shortlist
              </button>
            </div>
          </header>
          <div v-if="selectedQueries.length && !runResults.length" class="geo-run-ready">
            <AppIcon name="activity" :size="18" />
            <span>Runner 已準備完成</span>
          </div>
          <div v-else-if="runResults.length" class="geo-result-list">
            <article v-for="result in runResults" :key="result.id" class="geo-result-item">
              <header>
                <span class="badge badge-info">{{ result.provider }}</span>
                <span class="badge badge-blue">{{ result.surface }}</span>
                <span class="badge" :class="result.status === 'completed' ? 'badge-success' : 'badge-error'">
                  {{ result.status }}
                </span>
                <small>
                  {{ result.region }} · {{ result.language }} · {{ result.model || "no model" }}
                </small>
              </header>
              <p v-if="result.error" class="form-error">{{ result.error }}</p>
              <pre v-else>{{ result.rawResponse }}</pre>
              <div v-if="resultReferences(result).length" class="geo-source-list">
                <a
                  v-for="reference in resultReferences(result)"
                  :key="reference.url"
                  :href="reference.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ referenceDisplayLabel(reference) }}
                </a>
              </div>
            </article>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>
