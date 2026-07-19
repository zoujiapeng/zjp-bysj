<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { errorMessage } from '../api/http'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(username.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch (err) {
    error.value = errorMessage(err)
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-card">
      <h1>学生心理关怀随访系统</h1>
      <p class="muted">面向辅导员和心理老师的关怀工作台</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label for="username">用户名</label>
          <input id="username" v-model="username" autocomplete="username" required autofocus />
        </div>
        <div class="field">
          <label for="password">密码</label>
          <input id="password" v-model="password" type="password" autocomplete="current-password" required />
        </div>
        <div v-if="error" class="error-box">{{ error }}</div>
        <button class="primary" type="submit" :disabled="auth.loading">
          {{ auth.loading ? '登录中…' : '登录' }}
        </button>
      </form>
      <p class="help-text">心理数据属于敏感信息，请勿共享账号。系统不替代专业诊断和紧急处置流程。</p>
    </section>
  </main>
</template>
