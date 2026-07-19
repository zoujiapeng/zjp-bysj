<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import ModalPanel from '../components/ModalPanel.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import type { Organization, Page, User } from '../types'
import { formatDateTime } from '../utils'

const pageData = ref<Page<User>>({ items: [], total: 0, page: 1, page_size: 20 })
const organizations = ref<Organization[]>([])
const filters = reactive({ keyword: '', role: '' })
const loading = ref(false)
const error = ref('')
const notice = ref('')
const createOpen = ref(false)
const editOpen = ref(false)
const selected = ref<User | null>(null)
const createForm = reactive({ username: '', password: '', full_name: '', role: 'COUNSELOR', organization_id: null as number | null })
const editForm = reactive({ full_name: '', password: '', role: 'COUNSELOR', organization_id: null as number | null, is_active: true })

async function load(page = 1) {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page, page_size: 20 }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.role) params.role = filters.role
    pageData.value = (await api.get<Page<User>>('/users', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

async function createUser() {
  try {
    await api.post('/users', { ...createForm, organization_id: createForm.organization_id || null })
    createOpen.value = false
    Object.assign(createForm, { username: '', password: '', full_name: '', role: 'COUNSELOR', organization_id: null })
    notice.value = '用户已创建'
    await load(1)
  } catch (err) { error.value = errorMessage(err) }
}

function openEdit(user: User) {
  selected.value = user
  Object.assign(editForm, { full_name: user.full_name, password: '', role: user.role, organization_id: user.organization_id, is_active: user.is_active })
  editOpen.value = true
}

async function updateUser() {
  if (!selected.value) return
  const payload: Record<string, unknown> = { full_name: editForm.full_name, role: editForm.role, organization_id: editForm.organization_id || null, is_active: editForm.is_active }
  if (editForm.password) payload.password = editForm.password
  try {
    await api.patch(`/users/${selected.value.id}`, payload)
    editOpen.value = false
    notice.value = '用户已更新'
    await load(pageData.value.page)
  } catch (err) { error.value = errorMessage(err) }
}

onMounted(async () => {
  try { organizations.value = (await api.get('/organizations')).data } catch (err) { error.value = errorMessage(err) }
  await load()
})
</script>

<template>
  <div class="page-header"><div><h1>用户管理</h1><p>维护管理员、辅导员和心理老师账号。</p></div><button class="primary" type="button" @click="createOpen = true">新建用户</button></div>
  <div v-if="error" class="error-box">{{ error }}</div><div v-if="notice" class="success-box">{{ notice }}</div>
  <section class="card">
    <form class="toolbar" @submit.prevent="load(1)"><div class="field grow"><label>关键词</label><input v-model="filters.keyword" placeholder="姓名或用户名" /></div><div class="field"><label>角色</label><select v-model="filters.role"><option value="">全部</option><option value="ADMIN">系统管理员</option><option value="COUNSELOR">辅导员</option><option value="PSYCHOLOGIST">心理老师</option></select></div><button class="primary" type="submit">查询</button></form>
    <div class="table-wrap"><table><thead><tr><th>用户</th><th>角色</th><th>所属机构</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead><tbody><tr v-for="user in pageData.items" :key="user.id"><td>{{ user.full_name }}<br /><span class="muted">{{ user.username }}</span></td><td><StatusBadge :value="user.role" /></td><td>{{ user.organization_name || '—' }}</td><td>{{ user.is_active ? '启用' : '停用' }}</td><td>{{ formatDateTime(user.last_login_at) }}</td><td><button class="small" type="button" @click="openEdit(user)">编辑</button></td></tr></tbody></table><div v-if="!loading && !pageData.items.length" class="empty-state">暂无用户。</div></div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>

  <ModalPanel title="新建用户" :open="createOpen" @close="createOpen = false"><form @submit.prevent="createUser"><div class="form-grid"><div class="field"><label>用户名 *</label><input v-model="createForm.username" required pattern="[A-Za-z0-9_.-]+" /></div><div class="field"><label>姓名 *</label><input v-model="createForm.full_name" required /></div><div class="field"><label>密码 *</label><input v-model="createForm.password" type="password" minlength="8" required /></div><div class="field"><label>角色 *</label><select v-model="createForm.role"><option value="COUNSELOR">辅导员</option><option value="PSYCHOLOGIST">心理老师</option><option value="ADMIN">系统管理员</option></select></div><div class="field full"><label>所属机构</label><select v-model.number="createForm.organization_id"><option :value="null">不指定</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div></div><div class="form-actions"><button type="button" @click="createOpen = false">取消</button><button class="primary" type="submit">创建</button></div></form></ModalPanel>

  <ModalPanel title="编辑用户" :open="editOpen" @close="editOpen = false"><form @submit.prevent="updateUser"><div class="form-grid"><div class="field"><label>姓名 *</label><input v-model="editForm.full_name" required /></div><div class="field"><label>角色 *</label><select v-model="editForm.role"><option value="COUNSELOR">辅导员</option><option value="PSYCHOLOGIST">心理老师</option><option value="ADMIN">系统管理员</option></select></div><div class="field"><label>新密码</label><input v-model="editForm.password" type="password" minlength="8" placeholder="不修改则留空" /></div><div class="field"><label>所属机构</label><select v-model.number="editForm.organization_id"><option :value="null">不指定</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div><div class="field full"><label><input v-model="editForm.is_active" type="checkbox" style="width:auto" /> 启用账号</label></div></div><div class="form-actions"><button type="button" @click="editOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form></ModalPanel>
</template>
