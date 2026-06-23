export type PageId = "dashboard" | "permissions" | "geo-tracking";

export interface NavigationItem {
  id: string;
  label: string;
  icon: IconName;
  group?: string;
  page?: PageId;
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

export type GeoRegion = "TW" | "US";
export type GeoMarketType = "b2c" | "b2b_procurement";
export type GeoProvider = "dummy" | "gemini";

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
