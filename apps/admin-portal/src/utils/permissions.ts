interface PermissionPresentation {
  key: string;
  label: string;
  description: string;
}

const permissionPresentations: Record<
  string,
  Omit<PermissionPresentation, "key">
> = {
  "users.read": {
    label: "檢視使用者",
    description: "查看員工帳號與基本資料。",
  },
  "users.manage": {
    label: "管理使用者",
    description: "邀請、編輯、啟用或停用員工帳號。",
  },
  "roles.read": {
    label: "檢視角色",
    description: "查看角色及其包含的權限。",
  },
  "roles.manage": {
    label: "管理角色",
    description: "建立角色並調整角色權限。",
  },
  "permissions.read": {
    label: "檢視權限項目",
    description: "查看系統可設定的權限清單。",
  },
  "access-grants.read": {
    label: "檢視資源存取範圍",
    description: "查看使用者可存取的客戶與任務。",
  },
  "access-grants.manage": {
    label: "管理資源存取範圍",
    description: "調整使用者可存取的客戶與任務。",
  },
  "departments.read": {
    label: "檢視部門",
    description: "查看部門資料與成員數量。",
  },
  "departments.manage": {
    label: "管理部門",
    description: "建立、編輯或刪除部門。",
  },
  "customers.read": {
    label: "檢視客戶",
    description: "查看客戶清單與客戶資料。",
  },
  "customers.create": {
    label: "新增客戶",
    description: "建立新的客戶資料。",
  },
  "customers.update": {
    label: "編輯客戶",
    description: "修改既有客戶資料。",
  },
  "customers.delete": {
    label: "刪除客戶",
    description: "將客戶資料標記為刪除。",
  },
  "tasks.read": {
    label: "檢視任務",
    description: "查看 SEO 任務清單與任務資料。",
  },
  "tasks.create": {
    label: "新增任務",
    description: "建立新的 SEO 任務。",
  },
  "tasks.update": {
    label: "編輯任務",
    description: "修改既有 SEO 任務資料。",
  },
  "tasks.delete": {
    label: "刪除任務",
    description: "將 SEO 任務標記為刪除。",
  },
  "authorization.evaluate": {
    label: "執行授權判斷",
    description: "檢查其他使用者是否可執行指定操作。",
  },
  "audit-events.read": {
    label: "檢視稽核紀錄",
    description: "查看帳號、角色與權限異動紀錄。",
  },
};

export function hasPermission(
  permissions: readonly string[],
  permission: string,
): boolean {
  return permissions.includes(permission);
}

export function describePermission(permission: string): PermissionPresentation {
  const presentation = permissionPresentations[permission];
  return {
    key: permission,
    label: presentation?.label ?? permission,
    description: presentation?.description ?? "尚未提供此權限的中文說明。",
  };
}

export function permissionLabel(permission: string): string {
  return describePermission(permission).label;
}
