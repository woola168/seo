<script setup lang="ts">
import { RouterView } from "vue-router";

import AppToast from "../components/ui/AppToast.vue";
import { usePortalNotifications } from "../composables/portal-context";

const notifications = usePortalNotifications();
</script>

<template>
  <RouterView />
  <AppToast
    v-if="notifications.toast.value"
    :toast="notifications.toast.value"
    @close="notifications.dismiss"
  />
</template>
