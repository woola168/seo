import type { GeoProject, GeoProjectStatusResource } from "../types";

export interface GeoProjectStatusUpdateState {
  updatingId: string;
}

export type GeoProjectStatusUpdateResult =
  | { status: "ignored" }
  | { status: "succeeded"; response: GeoProjectStatusResource }
  | { status: "failed"; error: unknown };

export function nextGeoProjectStatus(
  status: GeoProject["status"],
): "active" | "paused" {
  return status === "active" ? "paused" : "active";
}

export function geoProjectStatusAction(
  status: GeoProject["status"],
): "上架" | "下架" {
  return status === "active" ? "下架" : "上架";
}

export async function updateGeoProjectStatus(
  state: GeoProjectStatusUpdateState,
  project: GeoProject,
  canUpdate: boolean,
  request: (
    projectId: string,
    status: "active" | "paused",
  ) => Promise<GeoProjectStatusResource>,
): Promise<GeoProjectStatusUpdateResult> {
  if (!canUpdate || state.updatingId) return { status: "ignored" };
  state.updatingId = project.id;
  try {
    return {
      status: "succeeded",
      response: await request(project.id, nextGeoProjectStatus(project.status)),
    };
  } catch (error) {
    return { status: "failed", error };
  } finally {
    state.updatingId = "";
  }
}

export function applyGeoProjectStatusResponse(
  projects: GeoProject[],
  response: GeoProjectStatusResource,
): GeoProject[] {
  return projects.map((project) =>
    project.id === response.projectId
      ? { ...project, status: response.status, updatedAt: response.updatedAt }
      : project,
  );
}
