import { createApp } from "vue";
import { createWebHistory } from "vue-router";
import App from "./App.vue";
import { createPortalContext, providePortalContext } from "./composables/portal-context";
import { createPortalRouter } from "./router/routes";
import { api } from "./services/api";
import "./styles.css";

const portal = createPortalContext(api);
const router = createPortalRouter(
  createWebHistory(),
  portal.session.hasSession,
  portal.session.loadPermissionNames,
);
const app = createApp(App);
app.use(router);
providePortalContext(app, portal);

router.isReady().then(() => app.mount("#app"));
