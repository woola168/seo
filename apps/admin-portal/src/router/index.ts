import { createWebHistory } from "vue-router";

import { api } from "../services/api";
import { getSessionCapabilities } from "../services/session-capabilities";
import { createPortalRouter } from "./routes";

export const router = createPortalRouter(
  createWebHistory(),
  api.hasSession,
  () => getSessionCapabilities().then((value) => value.permissions),
);
