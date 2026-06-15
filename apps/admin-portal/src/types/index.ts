export type PageId = "dashboard" | "permissions";

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
