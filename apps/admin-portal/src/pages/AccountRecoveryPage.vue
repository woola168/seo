<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePortalSession } from "../composables/portal-context";
import type { RecoveryMode } from "../utils/session-bootstrap";

const route = useRoute();
const router = useRouter();
const session = usePortalSession();
const { loading, error } = session;
const mode = computed<Exclude<RecoveryMode, null>>(() => {
  if (route.meta.recoveryMode === "reset") return "reset";
  if (route.meta.recoveryMode === "accept") return "accept";
  return "request";
});
const token = computed(() => typeof route.query.token === "string" ? route.query.token : "");
const email = ref("");
const password = ref("");
const confirmation = ref("");
const localError = ref("");
const isPasswordMode = computed(() => mode.value !== "request");

async function submit(): Promise<void> {
  localError.value = "";
  if (isPasswordMode.value && password.value !== confirmation.value) {
    localError.value = "兩次輸入的密碼不一致。";
    return;
  }
  const value = isPasswordMode.value ? password.value : email.value.trim();
  if (await session.recover(mode.value, token.value, value)) {
    await router.replace({ name: "login" });
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-visual">
      <div class="login-visual-brand">
        <strong>Younilab SEO</strong>
        <span>安全地恢復您的後台帳號</span>
      </div>
    </section>
    <section class="login-panel">
      <div class="login-form-wrap">
        <div class="login-heading">
          <h1>
            {{
              mode === "request"
                ? "忘記密碼"
                : mode === "accept"
                  ? "設定帳號密碼"
                  : "重設密碼"
            }}
          </h1>
          <p v-if="mode === 'request'">
            輸入帳號 Email；若帳號存在，系統會建立一封待寄送通知。
          </p>
          <p v-else>新密碼需為 12 到 128 個字元。</p>
        </div>

        <form @submit.prevent="submit">
          <label v-if="mode === 'request'" class="form-field">
            <span>Email</span>
            <input v-model="email" type="email" autocomplete="email" required />
          </label>
          <template v-else>
            <label class="form-field">
              <span>新密碼</span>
              <input
                v-model="password"
                type="password"
                autocomplete="new-password"
                minlength="12"
                maxlength="128"
                required
              />
            </label>
            <label class="form-field">
              <span>確認新密碼</span>
              <input
                v-model="confirmation"
                type="password"
                autocomplete="new-password"
                minlength="12"
                maxlength="128"
                required
              />
            </label>
          </template>
          <p v-if="localError || error" class="form-error" role="alert">
            {{ localError || error }}
          </p>
          <button class="button button-primary login-submit" :disabled="loading">
            {{ loading ? "處理中..." : "送出" }}
          </button>
          <button class="text-button" type="button" @click="router.replace({ name: 'login' })">
            返回登入
          </button>
        </form>
      </div>
    </section>
  </main>
</template>
