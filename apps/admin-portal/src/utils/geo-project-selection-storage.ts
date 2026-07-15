const GEO_PROJECT_SELECTION_KEY = "geoAnalysis:selectedProjectId";

function getStorage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function getStoredGeoProjectId(): string {
  try {
    return getStorage()?.getItem(GEO_PROJECT_SELECTION_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setStoredGeoProjectId(projectId: string): void {
  try {
    const storage = getStorage();
    if (!storage) return;
    if (projectId) {
      storage.setItem(GEO_PROJECT_SELECTION_KEY, projectId);
    } else {
      storage.removeItem(GEO_PROJECT_SELECTION_KEY);
    }
  } catch {
    // 受限瀏覽器環境可能停用 storage，仍允許頁面以記憶體狀態運作。
  }
}

export function resolveStoredGeoProjectId(
  projects: ReadonlyArray<{ id: string }>,
): string {
  const storedProjectId = getStoredGeoProjectId();
  const resolvedProjectId = projects.some((project) => project.id === storedProjectId)
    ? storedProjectId
    : projects[0]?.id ?? "";
  setStoredGeoProjectId(resolvedProjectId);
  return resolvedProjectId;
}
