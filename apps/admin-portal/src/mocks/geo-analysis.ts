import type {
  GeoAiAnswerSample,
  GeoEntity,
  GeoEntityAlias,
  GeoJob,
  GeoMarket,
  GeoPlatform,
  GeoProject,
  GeoQuery,
  GeoQueryPlatform,
  GeoRecommendation,
  GeoReportMetric,
  GeoSchedule,
  GeoTopic,
  GeoTopicPerformance,
  GeoTrendPoint,
} from "../types";

export interface GeoMockState {
  projects: GeoProject[];
  markets: GeoMarket[];
  entities: GeoEntity[];
  aliases: GeoEntityAlias[];
  topics: GeoTopic[];
  queries: GeoQuery[];
  platforms: GeoPlatform[];
  queryPlatforms: GeoQueryPlatform[];
  schedules: GeoSchedule[];
  jobs: GeoJob[];
  reportMetrics: GeoReportMetric[];
  trendPoints: GeoTrendPoint[];
  topicPerformance: GeoTopicPerformance[];
  aiAnswerSamples: GeoAiAnswerSample[];
  recommendations: GeoRecommendation[];
}

const projects: GeoProject[] = [
  {
    id: "geo-project-kinsan",
    customerId: "customer-kinsan",
    customerName: "金山旅宿",
    seoTaskId: "seo-task-kinsan-content",
    seoTaskName: "旅宿內容 SEO",
    name: "金山旅宿 GEO 追蹤",
    defaultRegion: "TW",
    defaultLanguage: "zh-TW",
    status: "active",
    dailyRunBudget: 320,
    createdAt: "2026-06-01T01:00:00.000Z",
    updatedAt: "2026-06-20T03:20:00.000Z",
  },
  {
    id: "geo-project-b2b",
    customerId: "customer-b2b",
    customerName: "B2B SaaS 客戶",
    seoTaskId: "seo-task-b2b-awareness",
    seoTaskName: "品牌聲量監測",
    name: "AI 搜尋品牌能見度",
    defaultRegion: "US",
    defaultLanguage: "en-US",
    status: "paused",
    dailyRunBudget: 180,
    createdAt: "2026-06-05T06:15:00.000Z",
    updatedAt: "2026-06-18T07:30:00.000Z",
  },
];

const markets: GeoMarket[] = [
  {
    id: "geo-market-tw",
    projectId: "geo-project-kinsan",
    region: "TW",
    language: "zh-TW",
    marketName: "台灣繁中市場",
    promptLocaleHint: "以台灣使用者的繁體中文語境回答",
    serpGl: "tw",
    serpHl: "zh-TW",
    serpLocation: "Taiwan",
    status: "active",
  },
  {
    id: "geo-market-us",
    projectId: "geo-project-b2b",
    region: "US",
    language: "en-US",
    marketName: "美國英文市場",
    promptLocaleHint: "Answer as a US B2B buyer",
    serpGl: "us",
    serpHl: "en",
    serpLocation: "United States",
    status: "paused",
  },
];

const entities: GeoEntity[] = [
  {
    id: "geo-entity-kinsan",
    projectId: "geo-project-kinsan",
    entityType: "brand",
    name: "金山旅宿",
    websiteUrl: "https://example.com",
    description: "主要品牌與官網露出追蹤。",
    status: "active",
  },
  {
    id: "geo-entity-hot-spring",
    projectId: "geo-project-kinsan",
    entityType: "competitor",
    name: "北海岸溫泉會館",
    websiteUrl: "https://competitor.example.com",
    description: "主要競品，觀察 AI 回答中的推薦順位。",
    status: "active",
  },
  {
    id: "geo-entity-b2b-brand",
    projectId: "geo-project-b2b",
    entityType: "brand",
    name: "YouniFlow",
    websiteUrl: "https://saas.example.com",
    description: "B2B SaaS 品牌與產品名稱。",
    status: "paused",
  },
];

const aliases: GeoEntityAlias[] = [
  {
    id: "geo-alias-kinsan-1",
    entityId: "geo-entity-kinsan",
    alias: "金山溫泉旅宿",
    matchType: "contains",
  },
  {
    id: "geo-alias-kinsan-2",
    entityId: "geo-entity-kinsan",
    alias: "example.com",
    matchType: "domain",
  },
  {
    id: "geo-alias-competitor-1",
    entityId: "geo-entity-hot-spring",
    alias: "北海岸溫泉",
    matchType: "contains",
  },
];

const topics: GeoTopic[] = [
  {
    id: "geo-topic-onsen",
    projectId: "geo-project-kinsan",
    name: "溫泉住宿推薦",
    description: "追蹤旅遊規劃與住宿推薦型 query。",
    status: "active",
  },
  {
    id: "geo-topic-family",
    projectId: "geo-project-kinsan",
    name: "親子旅遊",
    description: "觀察親子客群對地點、設施與交通的問答。",
    status: "active",
  },
  {
    id: "geo-topic-b2b",
    projectId: "geo-project-b2b",
    name: "Workflow automation",
    description: "B2B buyer 在 AI 平台上的工具比較。",
    status: "paused",
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
    intent: "comparison",
    buyerStage: "decision",
    isBranded: true,
    priority: "normal",
    status: "active",
  },
  {
    id: "geo-query-family-1",
    projectId: "geo-project-kinsan",
    topicId: "geo-topic-family",
    queryText: "帶小孩去金山玩兩天一夜怎麼安排",
    region: "TW",
    language: "zh-TW",
    intent: "planning",
    buyerStage: "awareness",
    isBranded: false,
    priority: "normal",
    status: "active",
  },
  {
    id: "geo-query-b2b-1",
    projectId: "geo-project-b2b",
    topicId: "geo-topic-b2b",
    queryText: "best workflow automation tools for marketing teams",
    region: "US",
    language: "en-US",
    intent: "comparison",
    buyerStage: "consideration",
    isBranded: false,
    priority: "normal",
    status: "paused",
  },
];

const platforms: GeoPlatform[] = [
  { id: "geo-platform-chatgpt", name: "ChatGPT", model: "GPT-4.1", status: "active" },
  { id: "geo-platform-gemini", name: "Gemini", model: "Gemini 2.5 Pro", status: "active" },
  { id: "geo-platform-claude", name: "Claude", model: "Claude Sonnet 4", status: "active" },
  { id: "geo-platform-perplexity", name: "Perplexity", model: "Sonar", status: "active" },
  { id: "geo-platform-aio", name: "Google AIO", model: "AI Overview", status: "paused" },
];

const queryPlatforms: GeoQueryPlatform[] = [
  {
    id: "geo-query-platform-1",
    queryId: "geo-query-onsen-1",
    platformId: "geo-platform-chatgpt",
    model: "GPT-4.1",
    status: "active",
  },
  {
    id: "geo-query-platform-2",
    queryId: "geo-query-onsen-1",
    platformId: "geo-platform-gemini",
    model: "Gemini 2.5 Pro",
    status: "active",
  },
  {
    id: "geo-query-platform-3",
    queryId: "geo-query-onsen-2",
    platformId: "geo-platform-claude",
    model: "Claude Sonnet 4",
    status: "active",
  },
  {
    id: "geo-query-platform-4",
    queryId: "geo-query-family-1",
    platformId: "geo-platform-perplexity",
    model: "Sonar",
    status: "active",
  },
];

const schedules: GeoSchedule[] = [
  {
    id: "geo-schedule-daily-chatgpt",
    queryId: "geo-query-onsen-1",
    platformId: "geo-platform-chatgpt",
    frequency: "daily",
    priority: "high",
    timezone: "Asia/Taipei",
    nextRunAt: "2026-06-24T01:00:00.000Z",
    status: "active",
  },
  {
    id: "geo-schedule-weekly-gemini",
    queryId: "geo-query-onsen-2",
    platformId: "geo-platform-gemini",
    frequency: "weekly",
    priority: "normal",
    timezone: "Asia/Taipei",
    nextRunAt: "2026-06-29T01:00:00.000Z",
    status: "active",
  },
  {
    id: "geo-schedule-manual-claude",
    queryId: "geo-query-family-1",
    platformId: "geo-platform-claude",
    frequency: "manual",
    priority: "normal",
    timezone: "Asia/Taipei",
    nextRunAt: null,
    status: "paused",
  },
];

const jobs: GeoJob[] = [
  {
    id: "geo-job-20260623-chatgpt",
    projectId: "geo-project-kinsan",
    queryId: "geo-query-onsen-1",
    platformId: "geo-platform-chatgpt",
    scheduleId: "geo-schedule-daily-chatgpt",
    jobType: "scheduled_run",
    priority: "high",
    scheduledFor: "2026-06-23T01:00:00.000Z",
    status: "succeeded",
    attemptCount: 1,
    maxAttempts: 3,
    dedupeKey: "geo-project-kinsan:geo-query-onsen-1:geo-platform-chatgpt:2026-06-23T01:00:00Z",
    externalRunId: "mock-run-001",
    lastErrorMessage: null,
    createdAt: "2026-06-23T00:58:00.000Z",
    updatedAt: "2026-06-23T01:05:00.000Z",
  },
  {
    id: "geo-job-20260623-gemini",
    projectId: "geo-project-kinsan",
    queryId: "geo-query-onsen-2",
    platformId: "geo-platform-gemini",
    scheduleId: "geo-schedule-weekly-gemini",
    jobType: "scheduled_run",
    priority: "normal",
    scheduledFor: "2026-06-23T02:00:00.000Z",
    status: "running_external",
    attemptCount: 1,
    maxAttempts: 3,
    dedupeKey: "geo-project-kinsan:geo-query-onsen-2:geo-platform-gemini:2026-06-23T02:00:00Z",
    externalRunId: "mock-run-002",
    lastErrorMessage: null,
    createdAt: "2026-06-23T01:58:00.000Z",
    updatedAt: "2026-06-23T02:01:00.000Z",
  },
  {
    id: "geo-job-20260622-claude",
    projectId: "geo-project-kinsan",
    queryId: "geo-query-family-1",
    platformId: "geo-platform-claude",
    scheduleId: null,
    jobType: "manual_run",
    priority: "normal",
    scheduledFor: "2026-06-22T06:30:00.000Z",
    status: "failed",
    attemptCount: 3,
    maxAttempts: 3,
    dedupeKey: "geo-project-kinsan:geo-query-family-1:geo-platform-claude:2026-06-22T06:30:00Z",
    externalRunId: "mock-run-003",
    lastErrorMessage: "Mock：外部執行逾時",
    createdAt: "2026-06-22T06:30:00.000Z",
    updatedAt: "2026-06-22T06:45:00.000Z",
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
  {
    id: "used-url",
    label: "Used URL",
    value: "17",
    delta: "+3",
    tone: "warning",
    description: "被模型採用為資料來源的頁面數。",
  },
  {
    id: "share",
    label: "Share",
    value: "22%",
    delta: "+5%",
    tone: "success",
    description: "目標 topic 內的相對曝光份額。",
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
  {
    topicId: "geo-topic-b2b",
    topicName: "Workflow automation",
    visibility: 41,
    sov: 18,
    queryCount: 1,
    betterPerformer: "Gemini",
  },
];

const aiAnswerSamples: GeoAiAnswerSample[] = [
  {
    id: "geo-answer-sample-1",
    platform: "ChatGPT",
    queryText: "北海岸適合週末放鬆的溫泉住宿推薦",
    answerSummary:
      "Mock 摘要：回答提到金山旅宿適合週末放鬆，強調交通、湯屋與附近景點，但競品在餐飲內容較完整。",
    mentionedEntities: ["金山旅宿", "北海岸溫泉會館"],
    citations: ["https://example.com/onsen", "https://example.com/location"],
    sentiment: "positive",
  },
  {
    id: "geo-answer-sample-2",
    platform: "Gemini",
    queryText: "金山旅宿評價和交通方便嗎",
    answerSummary:
      "Mock 摘要：回答採中性語氣，提及大眾運輸與自駕資訊，但未引用官方交通頁。",
    mentionedEntities: ["金山旅宿"],
    citations: ["https://example.com/reviews"],
    sentiment: "neutral",
  },
];

const recommendations: GeoRecommendation[] = [
  {
    id: "geo-recommendation-1",
    title: "補強交通與停車 FAQ",
    description:
      "多數 AI 回答會提到交通方便性，但引用來源分散，建議新增可被引用的官方 FAQ。",
    priority: "high",
  },
  {
    id: "geo-recommendation-2",
    title: "建立親子旅遊兩天一夜範本",
    description:
      "親子旅遊 query 的品牌提及率較低，可新增行程內容並加入周邊景點結構化資訊。",
    priority: "normal",
  },
  {
    id: "geo-recommendation-3",
    title: "競品比較頁先維持規劃",
    description:
      "目前競品內容多由第三方來源補足，正式指標穩定後再評估是否建立比較型 landing page。",
    priority: "low",
  },
];

function cloneItems<T>(items: T[]): T[] {
  return items.map((item) => ({ ...item }));
}

export function createGeoMockState(): GeoMockState {
  return {
    projects: cloneItems(projects),
    markets: cloneItems(markets),
    entities: cloneItems(entities),
    aliases: cloneItems(aliases),
    topics: cloneItems(topics),
    queries: cloneItems(queries),
    platforms: cloneItems(platforms),
    queryPlatforms: cloneItems(queryPlatforms),
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
    recommendations: cloneItems(recommendations),
  };
}
