<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { roleLabels } from '../utils'
import { api, errorMessage } from '../api/http'
import ModalPanel from './ModalPanel.vue'
import type { UserRole } from '../types'

interface NavItem {
  to: string
  label: string
  roles?: UserRole[]
}

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)
const passwordOpen = ref(false)
const passwordError = ref('')
const passwordNotice = ref('')
const passwordForm = ref({ current_password: '', new_password: '', confirm_password: '' })

const allItems: NavItem[] = [
  { to: '/dashboard', label: '工作台' },
  { to: '/students', label: '学生档案' },
  { to: '/cases', label: '关怀个案' },
  { to: '/followups', label: '随访任务' },
  { to: '/referrals', label: '转介管理' },
  { to: '/reports', label: '统计报表' },
  { to: '/users', label: '用户管理', roles: ['ADMIN'] },
  { to: '/organizations', label: '组织机构', roles: ['ADMIN'] },
  { to: '/audit-logs', label: '审计日志', roles: ['ADMIN'] },
]

const items = computed(() =>
  allItems.filter((item) => !item.roles || (auth.user && item.roles.includes(auth.user.role))),
)

async function changePassword() {
  passwordError.value = ''
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  try {
    await api.post('/auth/change-password', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password,
    })
    passwordNotice.value = '密码已修改'
    passwordOpen.value = false
    passwordForm.value = { current_password: '', new_password: '', confirm_password: '' }
  } catch (err) {
    passwordError.value = errorMessage(err)
  }
}

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="app-layout">
    <header class="topbar">
      <button class="menu-button" type="button" aria-label="打开菜单" @click="menuOpen = !menuOpen">☰</button>
      <div>
        <strong>学生心理关怀随访系统</strong>
        <span class="topbar-subtitle">工作协同与过程留痕</span>
      </div>
      <div class="topbar-user" v-if="auth.user">
        <span>{{ auth.user.full_name }}</span>
        <span class="muted">{{ roleLabels[auth.user.role] }}</span>
        <button class="link-button" type="button" @click="passwordOpen = true">修改密码</button>
        <button class="link-button" type="button" @click="logout">退出</button>
      </div>
    </header>

    <aside class="sidebar" :class="{ open: menuOpen }">
      <nav>
        <RouterLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          @click="menuOpen = false"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <p class="sidebar-note">本系统不提供自动心理诊断。紧急风险应按学校应急制度线下处置。</p>
    </aside>

    <main class="main-content" @click="menuOpen = false">
      <div v-if="passwordNotice" class="success-box">{{ passwordNotice }}</div>
      <RouterView />
    </main>

    <ModalPanel title="修改密码" :open="passwordOpen" @close="passwordOpen = false">
      <form @submit.prevent="changePassword">
        <div class="form-grid">
          <div class="field full"><label>当前密码 *</label><input v-model="passwordForm.current_password" type="password" required /></div>
          <div class="field full"><label>新密码 *</label><input v-model="passwordForm.new_password" type="password" minlength="8" required /></div>
          <div class="field full"><label>确认新密码 *</label><input v-model="passwordForm.confirm_password" type="password" minlength="8" required /></div>
        </div>
        <div v-if="passwordError" class="error-box">{{ passwordError }}</div>
        <div class="form-actions"><button type="button" @click="passwordOpen = false">取消</button><button class="primary" type="submit">保存</button></div>
      </form>
    </ModalPanel>
  </div>
</template>
