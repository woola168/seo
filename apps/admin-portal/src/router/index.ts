import { createWebHistory } from "vue-router";

import { api } from "../services/api";
import { createPortalRouter } from "./routes";

export const router = createPortalRouter(createWebHistory(), api.hasSession);
