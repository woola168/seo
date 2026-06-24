<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import AppIcon from "../components/ui/AppIcon.vue";
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
  seoTaskId: "11111111-1111-4111-8111-111111111111",
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
    form.seoTaskId = example.seoTaskId;
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
  });
}

async function generateQueries(): Promise<void> {
  if (!canSubmit()) return;
  await run(async () => {
    const result = await api.generateGeoQueries({
      seoTaskId: form.seoTaskId,
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
  });
}

async function runSelectedQueries(): Promise<void> {
  if (!selectedQueries.value.length) {
    error.value = "請先將至少一筆 Prompt 加入 Shortlist。";
    return;
  }
  await run(async () => {
    const result = await api.runGeoQueries(
      form.seoTaskId,
      provider.value,
      selectedQueries.value,
    );
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
  <section class="geo-page geo-tracking-page">
    <header class="geo-header">
      <div class="geo-heading">
        <span class="geo-page-badge">Admin Portal 測試頁</span>
        <h1>GEO 跑題實驗室</h1>
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
        <header class="card-header">
          <div>
            <h2>Input & Settings</h2>
            <p>輸入品牌、競品、keywords、地區、語言、intent 與 audience。</p>
          </div>
        </header>
        <div class="geo-form-body">
          <fieldset class="geo-fieldset">
            <legend>專案與品牌</legend>
            <label>
              <span>SEO 任務 ID</span>
              <input v-model="form.seoTaskId" type="text" />
            </label>
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
            <legend>市場與 Topic</legend>
            <label>
              <span>關鍵字清單</span>
              <textarea v-model="form.keywords" rows="3"></textarea>
            </label>
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
            <div class="geo-topic-editor">
              <div class="geo-topic-editor-header">
                <span>Topic 約束</span>
                <button class="button button-secondary" type="button" @click="addTopic">
                  新增 Topic
                </button>
              </div>
              <div
                v-for="(topic, index) in form.topics"
                :key="index"
                class="geo-topic-row"
              >
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
                <button
                  class="button button-secondary"
                  type="button"
                  :disabled="form.topics.length <= 1"
                  @click="removeTopic(index)"
                >
                  移除
                </button>
              </div>
            </div>
          </fieldset>

          <fieldset class="geo-fieldset">
            <legend>生成約束</legend>
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
                <span>query 需提及競品</span>
              </label>
            </div>
            <label>
              <span>最大 Query 數</span>
              <input v-model.number="form.maxQueries" min="1" max="40" type="number" />
            </label>
          </fieldset>
        </div>
      </form>

      <div class="geo-main-column">
        <section class="card geo-research geo-step-card">
          <header class="card-header geo-step-header">
            <div>
              <h2><span class="geo-step-number">1</span>Query Research 工具</h2>
              <p>拿左側的關鍵字、品牌、競品、地區、語言、Topic、Intent 與 Audience 生成 query draft。</p>
            </div>
            <div class="geo-run-actions">
              <label class="geo-provider-control">
                <span>Generation Provider</span>
                <select
                  v-model="queryGenerationProvider"
                  aria-label="Generation Provider"
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
          </header>
          <div class="geo-process-note">
            <AppIcon name="sparkles" :size="17" />
            <div>
              <strong>Query Research 不是已保存紀錄。</strong>
              <p>這一步只負責生成候選 query；生成後才會進入下方 Query / Topic 管理預覽。</p>
            </div>
          </div>
        </section>

        <section class="card geo-queries geo-step-card">
          <header class="card-header geo-step-header">
            <div>
              <h2><span class="geo-step-number">2</span>Query / Topic 管理預覽</h2>
              <p>呈現已生成的 topic 與 query 暫存紀錄，正式保存待 DB/CRUD。</p>
            </div>
            <span class="geo-record-count">
              {{ queries.length }} 筆紀錄，Shortlist {{ selectedQueries.length }} 筆
            </span>
          </header>
          <div v-if="!queries.length" class="empty-state">
            <AppIcon name="list" />
            <strong>尚未有 Query / Topic 管理紀錄</strong>
            <p>使用 Query Research 工具生成 query 後，這裡只負責預覽與選取紀錄。</p>
          </div>
          <div v-else class="table-scroll">
            <table class="data-table geo-query-table">
              <thead>
                <tr>
                  <th>Prompt</th>
                  <th>Keywords</th>
                  <th>Intent</th>
                  <th>動作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="query in queries" :key="query.id">
                  <td class="geo-prompt-cell">
                    <strong>{{ query.text }}</strong>
                    <small>
                      {{ query.topicName }} · {{ query.attributes.audience.name }}
                      · {{ query.region }} · {{ query.language }}
                    </small>
                  </td>
                  <td class="geo-keyword-tags">
                    <span
                      v-for="keyword in queryKeywords(query)"
                      :key="`${query.id}-${keyword}`"
                      class="badge badge-muted"
                    >
                      {{ keyword }}
                    </span>
                  </td>
                  <td>
                    <span
                      class="geo-intent-pill"
                      :class="intentCodeTone(query.attributes.intent.category)"
                      :title="`${intentCategoryLabel(query.attributes.intent.category)}：${query.attributes.intent.description}`"
                    >
                      {{ intentCategoryCode(query.attributes.intent.category) }}
                    </span>
                  </td>
                  <td class="geo-actions-cell">
                    <button
                      class="button button-secondary geo-shortlist-button"
                      type="button"
                      :class="{ active: shortlistedQueryIds.has(query.id) }"
                      @click="toggleShortlist(query.id)"
                    >
                      {{ shortlistedQueryIds.has(query.id) ? "Shortlisted" : "+ Shortlist" }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="card geo-results geo-step-card">
          <header class="card-header geo-step-header">
            <div>
              <h2><span class="geo-step-number">3</span>Runner 跑題引擎</h2>
              <p>把 Query / Topic 管理預覽中已加入 Shortlist 的 prompt 送到指定 AI adapter，取得 response 與 references。</p>
            </div>
            <div class="geo-run-actions">
              <label class="geo-provider-control">
                <span>Run Provider</span>
                <select v-model="provider" aria-label="Run Provider">
                  <option value="dummy">Dummy</option>
                  <option value="gemini">Gemini Vertex AI</option>
                  <option value="google_aio">Google AIO (SerpApi)</option>
                </select>
              </label>
              <button
                class="button button-primary"
                type="button"
                :disabled="loading || !selectedQueries.length"
                @click="runSelectedQueries"
              >
                <AppIcon name="activity" :size="16" />跑 Shortlist
              </button>
            </div>
          </header>
          <div v-if="!runResults.length" class="empty-state">
            <AppIcon name="activity" />
            <strong>尚未執行 Runner</strong>
            <p>先把 prompt 加入 Shortlist，再使用 provider 建立 run request。</p>
          </div>
          <div v-else class="geo-result-list">
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
