import type {
  GeoAiAnswerSample,
  GeoAnalysisRunResult,
  GeoEntityAlias,
  GeoEntityResource,
  GeoJob,
  GeoPlatform,
  GeoProject,
  GeoQuery,
  GeoRecommendation,
  GeoReportMetric,
  GeoSchedule,
  GeoTopic,
  GeoTopicPerformance,
  GeoTrendPoint,
} from "../types";

export interface GeoMockState {
  projects: GeoProject[];
  entities: GeoEntityResource[];
  aliases: GeoEntityAlias[];
  topics: GeoTopic[];
  queries: GeoQuery[];
  platforms: GeoPlatform[];
  schedules: GeoSchedule[];
  jobs: GeoJob[];
  reportMetrics: GeoReportMetric[];
  trendPoints: GeoTrendPoint[];
  topicPerformance: GeoTopicPerformance[];
  aiAnswerSamples: GeoAiAnswerSample[];
  runResults: GeoAnalysisRunResult[];
  recommendations: GeoRecommendation[];
}

export const geoPlatformCatalog: GeoPlatform[] = [
  { id: "11111111-1111-4111-8111-111111111101", name: "ChatGPT", model: "gpt-4.1", status: "active" },
  { id: "11111111-1111-4111-8111-111111111102", name: "Gemini", model: "gemini-2.5-pro", status: "active" },
  { id: "11111111-1111-4111-8111-111111111103", name: "Claude", model: "claude-sonnet-4", status: "active" },
  { id: "11111111-1111-4111-8111-111111111104", name: "Perplexity", model: "sonar", status: "active" },
  { id: "11111111-1111-4111-8111-111111111105", name: "Google AIO", model: "ai-overview", status: "active" },
];

const projects: GeoProject[] = [
  {
    id: "geo-project-kinsan",
    customerId: "customer-kinsan",
    customerName: "金山旅宿",
    seoTaskId: "seo-task-kinsan-content",
    seoTaskName: "北海岸內容 SEO",
    name: "金山旅宿 GEO 追蹤",
    defaultRegion: "TW",
    defaultLanguage: "zh-TW",
    status: "active",
    dailyRunBudget: 320,
    createdAt: "2026-06-01T01:00:00.000Z",
    updatedAt: "2026-06-20T03:20:00.000Z",
  },
];

const topics: GeoTopic[] = [
  {
    id: "geo-topic-onsen",
    projectId: "geo-project-kinsan",
    name: "溫泉住宿推薦",
    description: "評估 AI 是否會在北海岸溫泉住宿推薦中提及品牌。",
    status: "active",
  },
  {
    id: "geo-topic-family",
    projectId: "geo-project-kinsan",
    name: "親子旅遊",
    description: "觀察親子行程與住宿需求中的品牌能見度。",
    status: "active",
  },
];

const entities: GeoEntityResource[] = [
  {
    id: "geo-entity-kinsan",
    projectId: "geo-project-kinsan",
    entityType: "own_brand",
    name: "金山旅宿",
    websiteUrl: "https://example.com",
    description: "北海岸溫泉住宿品牌，主打週末放鬆、親子旅遊與交通便利。",
    status: "active",
    createdAt: "2026-06-01T00:00:00.000Z",
    updatedAt: "2026-06-01T00:00:00.000Z",
  },
  {
    id: "geo-entity-competitor",
    projectId: "geo-project-kinsan",
    entityType: "competitor",
    name: "北海岸溫泉會館",
    websiteUrl: "https://competitor.example.com",
    description: "主要競品，用於比較 SOV 與 mentions。",
    status: "active",
    createdAt: "2026-06-01T00:00:00.000Z",
    updatedAt: "2026-06-01T00:00:00.000Z",
  },
];

const aliases: GeoEntityAlias[] = [
  {
    id: "geo-alias-kinsan",
    entityId: "geo-entity-kinsan",
    alias: "金山旅宿",
    matchType: "contains",
  },
  {
    id: "geo-alias-domain",
    entityId: "geo-entity-kinsan",
    alias: "example.com",
    matchType: "domain",
  },
];

const queries: GeoQuery[] = [
  {
    id: "geo-query-onsen-1",
    projectId: "geo-project-kinsan",
    topicId: "geo-topic-onsen",
    queryText: "北海岸適合週末放鬆的溫泉住宿推薦",
    region: "TW",
    language: "zh-TW",
    marketType: "b2c",
    intent: "recommendation",
    buyerStage: "consideration",
    isBranded: false,
    priority: "high",
    status: "active",
  },
  {
    id: "geo-query-onsen-2",
    projectId: "geo-project-kinsan",
    topicId: "geo-topic-onsen",
    queryText: "金山旅宿評價和交通方便嗎",
    region: "TW",
    language: "zh-TW",
    marketType: "b2c",
    intent: "comparison",
    buyerStage: "decision",
    isBranded: true,
    priority: "normal",
    status: "active",
  },
];

const schedules: GeoSchedule[] = [
  {
    id: "geo-schedule-daily-chatgpt",
    queryId: "geo-query-onsen-1",
    platformId: "11111111-1111-4111-8111-111111111101",
    frequency: "daily",
    priority: "high",
    timezone: "Asia/Taipei",
    nextRunAt: "2026-06-24T01:00:00.000Z",
    status: "active",
  },
];

const jobs: GeoJob[] = [
  {
    id: "geo-job-20260623-chatgpt",
    projectId: "geo-project-kinsan",
    queryId: "geo-query-onsen-1",
    platformId: "11111111-1111-4111-8111-111111111101",
    scheduleId: "geo-schedule-daily-chatgpt",
    jobType: "scheduled_run",
    priority: "high",
    scheduledFor: "2026-06-23T01:00:00.000Z",
    status: "succeeded",
    attemptCount: 1,
    maxAttempts: 3,
    dedupeKey: "geo-project-kinsan:geo-query-onsen-1:11111111-1111-4111-8111-111111111101:2026-06-23T01:00:00Z",
    externalRunId: "mock-run-001",
    lastErrorMessage: null,
    createdAt: "2026-06-23T00:58:00.000Z",
    updatedAt: "2026-06-23T01:05:00.000Z",
  },
];

const reportMetrics: GeoReportMetric[] = [
  {
    id: "visibility",
    label: "Visibility",
    value: "64%",
    delta: "+8%",
    tone: "success",
    description: "品牌在 AI 回答中被看見的比例。",
  },
  {
    id: "sov",
    label: "SOV",
    value: "31%",
    delta: "+4%",
    tone: "blue",
    description: "相對競品的 AI 答案聲量占比。",
  },
  {
    id: "mentions",
    label: "Mentions",
    value: "142",
    delta: "+19",
    tone: "info",
    description: "品牌或 alias 被提及的次數。",
  },
  {
    id: "citations",
    label: "Citations",
    value: "38",
    delta: "+6",
    tone: "purple",
    description: "AI 回答引用或提到官網 URL 的次數。",
  },
];

const trendPoints: GeoTrendPoint[] = [
  { label: "6/17", visibility: 44, sov: 23, mentions: 61 },
  { label: "6/18", visibility: 48, sov: 25, mentions: 70 },
  { label: "6/19", visibility: 53, sov: 28, mentions: 88 },
  { label: "6/20", visibility: 55, sov: 29, mentions: 96 },
  { label: "6/21", visibility: 59, sov: 30, mentions: 113 },
  { label: "6/22", visibility: 61, sov: 30, mentions: 128 },
  { label: "6/23", visibility: 64, sov: 31, mentions: 142 },
];

const topicPerformance: GeoTopicPerformance[] = [
  {
    topicId: "geo-topic-onsen",
    topicName: "溫泉住宿推薦",
    visibility: 69,
    sov: 34,
    queryCount: 2,
    betterPerformer: "ChatGPT",
  },
  {
    topicId: "geo-topic-family",
    topicName: "親子旅遊",
    visibility: 55,
    sov: 24,
    queryCount: 1,
    betterPerformer: "Perplexity",
  },
];

const aiAnswerSamples: GeoAiAnswerSample[] = [
  {
    id: "geo-answer-sample-1",
    platform: "ChatGPT",
    queryText: "北海岸適合週末放鬆的溫泉住宿推薦",
    answerSummary:
      "AI 回答提及品牌的地點、泡湯體驗與交通便利性，引用官網與地圖頁面。",
    mentionedEntities: ["金山旅宿", "北海岸溫泉會館"],
    citations: ["https://example.com/onsen", "https://example.com/location"],
    sentiment: "positive",
  },
  {
    id: "geo-answer-sample-2",
    platform: "Gemini",
    queryText: "金山旅宿評價和交通方便嗎",
    answerSummary:
      "AI 回答以評價摘要與交通資訊回應，品牌被提及但缺少價格與房型資訊。",
    mentionedEntities: ["金山旅宿"],
    citations: ["https://example.com/reviews"],
    sentiment: "neutral",
  },
];

const runResults: GeoAnalysisRunResult[] = [
  {
    id: "geo-run-result-1",
    jobId: "geo-job-20260623-chatgpt",
    queryId: "geo-query-onsen-1",
    provider: "gemini",
    surface: "Gemini",
    model: "gemini-3.1-flash-lite",
    region: "TW",
    language: "zh-TW",
    status: "completed",
    rawResponse:
      "北海岸週末放鬆可考慮金山旅宿，適合想安排溫泉、老街與海岸線行程的旅客。",
    references: [
      {
        url: "https://example.com/onsen",
        title: "金山旅宿溫泉住宿",
        domain: "example.com",
        position: 1,
      },
    ],
    error: null,
    runAt: "2026-06-25T02:10:00.000Z",
    analysisStatus: "completed",
    analysisErrorCode: null,
    analysisErrorMessage: null,
  },
];

const recommendations: GeoRecommendation[] = [
  {
    id: "geo-recommendation-1",
    title: "補強交通與停車 FAQ",
    description: "多數 AI 回答提到交通方便，但缺少停車與大眾運輸細節，可新增 FAQ 提升引用機率。",
    priority: "high",
  },
  {
    id: "geo-recommendation-2",
    title: "建立親子兩天一夜行程頁",
    description: "親子旅遊 query 已出現需求，可用行程頁承接住宿、景點與餐飲推薦。",
    priority: "normal",
  },
];

function cloneItems<T>(items: T[]): T[] {
  return items.map((item) => ({ ...item }));
}

export function createGeoMockState(): GeoMockState {
  return {
    projects: cloneItems(projects),
    entities: cloneItems(entities),
    aliases: cloneItems(aliases),
    topics: cloneItems(topics),
    queries: cloneItems(queries),
    platforms: cloneItems(geoPlatformCatalog),
    schedules: cloneItems(schedules),
    jobs: cloneItems(jobs),
    reportMetrics: cloneItems(reportMetrics),
    trendPoints: cloneItems(trendPoints),
    topicPerformance: cloneItems(topicPerformance),
    aiAnswerSamples: aiAnswerSamples.map((item) => ({
      ...item,
      mentionedEntities: [...item.mentionedEntities],
      citations: [...item.citations],
    })),
    runResults: runResults.map((item) => ({
      ...item,
      references: item.references.map((reference) => ({ ...reference })),
    })),
    recommendations: cloneItems(recommendations),
  };
}
