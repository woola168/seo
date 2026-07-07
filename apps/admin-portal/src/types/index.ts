export type PageId =
  | "dashboard"
  | "permissions-members"
  | "permissions-roles"
  | "permissions-departments"
  | "permissions-authorization"
  | "geo-analysis-overview"
  | "geo-analysis-projects"
  | "geo-analysis-entities"
  | "geo-analysis-queries"
  | "geo-analysis-schedules"
  | "geo-analysis-jobs"
  | "geo-analysis-reports"
  | "geo-analysis-report-design"
  | "geo-analysis-flow-check"
  | "geo-analysis-query-research"
  | "geo-tracking";

export interface NavigationItem {
  id: string;
  label: string;
  icon: IconName;
  group?: string;
  page?: PageId;
  children?: NavigationItem[];
  badge?: string;
  disabled?: boolean;
}

export type IconName =
  | "activity"
  | "alert-circle"
  | "bell"
  | "briefcase"
  | "calendar"
  | "check"
  | "check-circle"
  | "chevron-left"
  | "chevron-right"
  | "clock"
  | "download"
  | "edit"
  | "eye"
  | "grid"
  | "info"
  | "layers"
  | "list"
  | "lock"
  | "logout"
  | "mail"
  | "menu"
  | "more"
  | "plus"
  | "refresh"
  | "search"
  | "settings"
  | "shield"
  | "sparkles"
  | "trash"
  | "user"
  | "users"
  | "x";

export type SemanticTone =
  | "info"
  | "warning"
  | "error"
  | "success"
  | "muted"
  | "purple"
  | "blue";

export interface StatMetric {
  label: string;
  value: string | number;
  tone?: SemanticTone;
}

export interface SessionUser {
  id: string;
  email: string;
  displayName: string;
  status: string;
  roleIds: string[];
  departmentId?: string | null;
  authProvider?: string;
  lastLoginAt?: string | null;
  invitedAt?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
}

export interface UserAccess extends SessionUser {
  customerIds: string[];
  taskIds: string[];
}

export interface Capabilities {
  permissions: string[];
  hasGlobalResourceAccess: boolean;
  customerIds: string[];
  taskIds: string[];
}

export interface Role {
  id: string;
  name: string;
  permissions: string[];
  isSystem: boolean;
  hasGlobalResourceAccess: boolean;
}

export interface AuthorizationDecision {
  allowed: boolean;
  reasonCode: string;
}

export type ToastTone = "info" | "success" | "warning" | "error";

export interface ToastMessage {
  id: number;
  message: string;
  tone: ToastTone;
}

export interface DashboardTask {
  id: number;
  name: string;
  client: string;
  initials: string;
  color: string;
  status: "progress" | "waiting" | "review" | "pending";
  words: number;
  dueDate: string;
}

export interface DashboardNotification {
  id: number;
  initials: string;
  color: string;
  message: string;
  time: string;
  unread: boolean;
}

export interface MemberMetadata {
  department: string | null;
  lastLogin: string | null;
  source: "workspace" | "external" | null;
  color: string;
}

export interface MemberView extends UserAccess, MemberMetadata {
  roleNames: string[];
}

export type MemberSortField =
  | "displayName"
  | "email"
  | "role"
  | "department"
  | "status"
  | "lastLogin";

export interface MemberQuery {
  search: string;
  role: string;
  department: string;
  status: string;
  sortField: MemberSortField;
  sortDirection: "asc" | "desc";
  page: number;
  pageSize: number;
}

export interface PaginatedMembers {
  items: MemberView[];
  total: number;
  totalPages: number;
  page: number;
}

export interface Department {
  id: string;
  name: string;
  description: string;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface CreateInvitationInput {
  email: string;
  displayName: string;
  departmentId: string | null;
  roleIds: string[];
  customerIds: string[];
  taskIds: string[];
  sendInvitation: boolean;
}

export interface UserInvitation {
  id: string;
  userId: string;
  email: string;
  expiresAt: string;
  createdAt: string;
}

export interface CustomerSummary {
  id: string;
  name: string;
  status: "active" | "archived";
}

export interface TaskSummary {
  id: string;
  customerId: string;
  customerName: string;
  name: string;
  status: "active" | "archived";
}

export interface PageResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface CollectionResponse<T> {
  items: T[];
  total: number;
}

export type GeoRegion = "TW" | "US";
export type GeoMarketType = "b2c" | "b2b_procurement";
export type GeoQueryProvider = "dummy" | "gemini";
export type GeoProvider = GeoQueryProvider | "google_aio";

export interface GeoDummyProject {
  seoTaskId: string;
  brandName: string;
  competitorBrands: string[];
  keywords: string[];
  region: GeoRegion;
  marketType: GeoMarketType;
  topics?: GeoTopicInput[];
  topicNames: string[];
}

export interface GeoTopicInput {
  name: string;
  description: string;
}

export interface GeoGeneratedQuery {
  id: string;
  seoTaskId: string;
  text: string;
  keywords: string[];
  topicId: string | null;
  topicName: string;
  region: GeoRegion;
  language: string;
  marketType: GeoMarketType;
  isBranded: boolean;
  attributes: {
    intent: {
      category: string;
      description: string;
    };
    keyword: string;
    topicName: string;
    topicDescription: string;
    audience: {
      name: string;
      description: string;
    };
    brandMentionRules: {
      shouldMentionOwnBrand: boolean;
      shouldMentionCompetitor: boolean;
    };
  };
  metadata: Record<string, string>;
  source: string;
  status: string;
}

export interface GeoTopicSummary {
  id: string;
  name: string;
  description: string;
}

export interface GeoQueryResearchResult {
  researchContext: string;
  searchedKeywords: string[];
  sourceUrls: string[];
}

export interface GeoQueryGenerationResult {
  topics: GeoTopicSummary[];
  queries: GeoGeneratedQuery[];
}

export interface GeoRunResult {
  id: string;
  runRequestId: string;
  queryId: string;
  provider: GeoProvider;
  surface: string;
  model: string;
  region: GeoRegion;
  language: string;
  status: "completed" | "failed";
  rawResponse: string;
  referenceUrls: string[];
  references: Array<{
    url: string;
    title: string | null;
  }>;
  error: string | null;
  runAt: string;
}

export interface GeoRunRequestResult {
  id: string;
  seoTaskId: string;
  timing: "run_now" | "next_cycle";
  results: GeoRunResult[];
}

export interface GeoProject {
  id: string;
  customerId: string | null;
  customerName: string;
  seoTaskId: string | null;
  seoTaskName: string | null;
  name: string;
  defaultRegion: string;
  defaultLanguage: string;
  status: "active" | "paused" | "archived";
  dailyRunBudget: number;
  createdAt: string;
  updatedAt: string;
}

export interface GeoMarket {
  id: string;
  projectId: string;
  region: string;
  language: string;
  marketName: string;
  promptLocaleHint: string;
  serpGl: string | null;
  serpHl: string | null;
  serpLocation: string | null;
  status: "active" | "paused";
}

export interface GeoEntity {
  id: string;
  projectId: string;
  entityType: "own_brand" | "brand" | "competitor" | "website" | "partner";
  name: string;
  websiteUrl: string | null;
  description: string;
  status: "active" | "paused" | "archived";
}

export interface GeoEntityAlias {
  id: string;
  entityId: string;
  alias: string;
  matchType: "exact" | "contains" | "domain";
}

export interface GeoTopic {
  id: string;
  projectId: string;
  name: string;
  description: string;
  status: "active" | "paused" | "archived";
}

export interface GeoQuery {
  id: string;
  projectId: string;
  topicId: string | null;
  queryText: string;
  region: string;
  language: string;
  marketType: GeoMarketType;
  intent: string;
  buyerStage: string;
  isBranded: boolean;
  priority: "low" | "normal" | "high";
  status: "active" | "paused" | "archived";
}

export interface GeoPlatform {
  id: string;
  name: string;
  model: string;
  status: "active" | "paused";
}

export interface GeoQueryPlatform {
  id: string;
  queryId: string;
  platformId: string;
  model: string;
  status: "active" | "paused";
}

export interface GeoSchedule {
  id: string;
  queryId: string;
  platformId: string;
  frequency: "daily" | "weekly" | "manual";
  priority: "low" | "normal" | "high";
  timezone: string;
  nextRunAt: string | null;
  status: "active" | "paused";
}

export interface GeoJob {
  id: string;
  projectId: string;
  queryId: string;
  platformId: string;
  scheduleId: string | null;
  jobType: "manual_run" | "scheduled_run";
  priority: "low" | "normal" | "high";
  scheduledFor: string;
  status:
    | "pending"
    | "published"
    | "running_external"
    | "succeeded"
    | "failed"
    | "cancelled";
  attemptCount: number;
  maxAttempts: number;
  dedupeKey: string;
  externalRunId: string | null;
  lastErrorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GeoReportMetric {
  id: string;
  label: string;
  value: string;
  delta: string;
  tone: SemanticTone;
  description: string;
}

export interface GeoTrendPoint {
  label: string;
  visibility: number;
  sov: number;
  mentions: number;
}

export interface GeoTopicPerformance {
  topicId: string;
  topicName: string;
  visibility: number;
  sov: number;
  queryCount: number;
  betterPerformer: string;
}

export interface GeoAiAnswerSample {
  id: string;
  platform: string;
  queryText: string;
  answerSummary: string;
  mentionedEntities: string[];
  citations: string[];
  sentiment: "positive" | "neutral" | "negative";
}

export interface GeoAnalysisRunResult {
  id: string;
  jobId: string;
  queryId: string;
  provider: GeoProvider;
  surface: string;
  model: string;
  region: string;
  language: string;
  status: "completed" | "failed";
  rawResponse: string;
  references: Array<{
    url: string;
    title: string | null;
    domain: string | null;
    position: number;
  }>;
  error: string | null;
  runAt: string;
  analysisStatus: string | null;
  analysisErrorCode: string | null;
  analysisErrorMessage: string | null;
}

export interface GeoKMindHubWorkspaceMapping {
  id: string;
  tenantId: string;
  workspaceId: string;
  displayName: string;
  provisioningMode: string;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface GeoRecommendation {
  id: string;
  title: string;
  description: string;
  priority: "low" | "normal" | "high";
}

export interface GeoDashboardMetricValue {
  value: number;
  unit: "percent" | "count" | "position";
  numerator: number | null;
  denominator: number | null;
  comparisonValue: number | null;
  delta: number | null;
  deltaUnit: "pp" | "count" | "position" | null;
}

export interface GeoDashboardOverviewCard {
  metricName: "visibility" | "mentions" | "sov" | "average_position";
  label: string;
  metric: GeoDashboardMetricValue;
}

export interface GeoDashboardEntityRow {
  entityId: string;
  entityRole: "own_brand" | "competitor";
  entityName: string;
  visibility: GeoDashboardMetricValue;
  mentions: GeoDashboardMetricValue;
  averagePosition: GeoDashboardMetricValue;
}

export interface GeoDashboardCitationRow {
  scopeType: "url" | "domain";
  value: string;
  label: string;
  ownership: string | null;
  sourceType: string | null;
  citationCount: GeoDashboardMetricValue;
  usedPercent: GeoDashboardMetricValue;
  sharePercent: GeoDashboardMetricValue;
}

export interface GeoDashboardSentimentRow {
  sentiment: "positive" | "negative";
  statementCount: GeoDashboardMetricValue;
}

export interface GeoDashboardReport {
  periodStart: string;
  periodEnd: string;
  comparisonStart: string;
  comparisonEnd: string;
  overview: GeoDashboardOverviewCard[];
  entities: GeoDashboardEntityRow[];
  citationUrls: GeoDashboardCitationRow[];
  citationDomains: GeoDashboardCitationRow[];
  sentiments: GeoDashboardSentimentRow[];
}

export interface GeoDashboardReportQuery {
  periodStart: string;
  periodEnd: string;
  comparisonStart: string;
  comparisonEnd: string;
  queryId?: string;
  topicId?: string;
  provider?: string;
  region?: string;
  language?: string;
}

export interface GeoProjectResource {
  id: string;
  customerId: string | null;
  seoTaskId: string | null;
  name: string;
  defaultRegion: string;
  defaultLanguage: string;
  status: GeoProject["status"];
  dailyRunBudget: number;
  createdAt: string;
  updatedAt: string;
}

export interface GeoProjectRequest {
  customerId: string | null;
  seoTaskId: string | null;
  name: string;
  defaultRegion: string;
  defaultLanguage: string;
  status: GeoProject["status"];
  dailyRunBudget: number;
}

export interface GeoEntityResource extends GeoEntity {
  createdAt: string;
  updatedAt: string;
}

export interface GeoEntityRequest {
  entityType: GeoEntity["entityType"];
  name: string;
  websiteUrl: string | null;
  description: string;
  status: GeoEntity["status"];
}

export interface GeoEntityAliasResource extends GeoEntityAlias {
  createdAt: string;
}

export interface GeoEntityAliasRequest {
  alias: string;
  matchType: GeoEntityAlias["matchType"];
}

export interface GeoTopicResource extends GeoTopic {
  createdAt: string;
  updatedAt: string;
}

export interface GeoTopicRequest {
  name: string;
  description: string;
  status: GeoTopic["status"];
}

export interface GeoQueryResource {
  id: string;
  projectId: string;
  topicId: string | null;
  queryText: string;
  region: string;
  language: string;
  marketType: GeoMarketType;
  intent: string | null;
  buyerStage: string | null;
  isBranded: boolean;
  priority: GeoQuery["priority"];
  status: GeoQuery["status"];
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface GeoAnalysisQueryRequest {
  topicId: string | null;
  queryText: string;
  region: string;
  language: string;
  marketType: GeoMarketType;
  intent: string | null;
  buyerStage: string | null;
  isBranded: boolean;
  priority: GeoQuery["priority"];
  status: GeoQuery["status"];
  metadata: Record<string, unknown>;
}

export interface GeoQueryPlatformResource extends GeoQueryPlatform {
  createdAt: string;
  updatedAt: string;
}

export interface GeoQueryPlatformRequest {
  platformId: string;
  model: string | null;
  status: GeoQueryPlatform["status"];
}

export interface GeoScheduleResource extends GeoSchedule {
  lastScheduledAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface GeoScheduleRequest {
  platformId: string;
  frequency: GeoSchedule["frequency"];
  priority: GeoSchedule["priority"];
  timezone: string;
  nextRunAt: string | null;
  status: GeoSchedule["status"];
}

export interface GeoJobResource extends GeoJob {
  dispatchBackend: string | null;
  dispatchMessageId: string | null;
  lastErrorCode: string | null;
}

export interface GeoJobRequest {
  platformId: string;
  scheduledFor: string | null;
  priority: GeoJob["priority"];
  jobType: GeoJob["jobType"];
}

export interface GeoQueryAudienceRequest {
  name: string;
  description: string;
}

export interface GeoQueryIntentRequest {
  category: string;
  description: string;
}

export interface GeoBrandMentionRulesRequest {
  shouldMentionOwnBrand: boolean;
  shouldMentionCompetitor: boolean;
}

export interface GeoQueryResearchRunRequest {
  provider: GeoQueryProvider;
  brandName: string;
  competitorBrands: string[];
  keywords: string[];
  region: GeoRegion;
  language: string | null;
  marketType: GeoMarketType;
  intents: GeoQueryIntentRequest[];
  audience: GeoQueryAudienceRequest | null;
  brandMentionRules: GeoBrandMentionRulesRequest;
}

export interface GeoQueryResearchResultResource {
  researchContext: string;
  searchedKeywords: string[];
  sourceUrls: string[];
}

export interface GeoQueryResearchRunResource {
  id: string;
  projectId: string;
  provider: GeoQueryProvider;
  status: "completed" | "failed";
  requestPayload: Record<string, unknown>;
  result: GeoQueryResearchResultResource | null;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
}

export interface GeoQueryGenerationRunRequest {
  seoTaskId: string;
  provider: GeoQueryProvider;
  brandName: string;
  competitorBrands: string[];
  keywords: string[];
  region: GeoRegion;
  language: string | null;
  marketType: GeoMarketType;
  topics: GeoTopicInput[];
  topicNames: string[];
  intents: GeoQueryIntentRequest[];
  audience: GeoQueryAudienceRequest;
  brandMentionRules: GeoBrandMentionRulesRequest;
  researchContext: string | null;
  maxQueries: number;
}

export interface GeoQueryDraftResource {
  id: string;
  generationRunId: string;
  projectId: string;
  topicId: string | null;
  topicName: string;
  queryText: string;
  keywords: string[];
  region: GeoRegion;
  language: string;
  marketType: GeoMarketType;
  intent: string | null;
  isBranded: boolean;
  status: "draft";
  selectionStatus: "shortlisted" | "rejected" | "accepted" | null;
  acceptedQueryId: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface GeoQueryGenerationRunResource {
  id: string;
  projectId: string;
  provider: GeoQueryProvider;
  status: "completed" | "failed";
  requestPayload: Record<string, unknown>;
  errorCode: string | null;
  errorMessage: string | null;
  createdAt: string;
  completedAt: string | null;
  drafts: GeoQueryDraftResource[];
}

export interface GeoQueryDraftSelectionRequest {
  selectionStatus: "shortlisted" | "rejected";
}

export interface GeoAcceptQueryDraftRequest {
  createTopicIfMissing: boolean;
  status: GeoQuery["status"];
}
