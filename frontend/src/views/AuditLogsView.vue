<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import PaginationBar from '../components/PaginationBar.vue'
import type { AuditLog, Page } from '../types'
import { formatDateTime } from '../utils'

const pageData = ref<Page<AuditLog>>({ items: [], total: 0, page: 1, page_size: 30 })
const filters = reactive({ action: '', actor_id: '' })
const error = ref('')
const loading = ref(false)

async function load(page = 1) {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page, page_size: 30 }
    if (filters.action) params.action = filters.action
    if (filters.actor_id) params.actor_id = filters.actor_id
    pageData.value = (await api.get<Page<AuditLog>>('/audit-logs', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

onMounted(() => load())
</script>

<template>
  <div class="page-header"><div><h1>审计日志</h1><p>追踪登录、敏感个案查看、风险调整、数据导出等关键操作。</p></div></div>
  <div v-if="error" class="error-box">{{ error }}</div>
  <section class="card"><form class="toolbar" @submit.prevent="load(1)"><div class="field grow"><label>操作代码</label><input v-model="filters.action" placeholder="例如 CHANGE_RISK" /></div><div class="field"><label>用户 ID</label><input v-model="filters.actor_id" type="number" /></div><button class="primary" type="submit">查询</button></form>
    <div class="table-wrap"><table><thead><tr><th>时间</th><th>操作人</th><th>操作</th><th>对象</th><th>摘要</th><th>IP</th></tr></thead><tbody><tr v-for="item in pageData.items" :key="item.id"><td>{{ formatDateTime(item.created_at) }}</td><td>{{ item.actor_name || '系统' }}<br /><span class="muted">ID {{ item.actor_id ?? '—' }}</span></td><td>{{ item.action }}</td><td>{{ item.resource_type }} / {{ item.resource_id || '—' }}</td><td>{{ item.summary }}</td><td>{{ item.ip_address || '—' }}</td></tr></tbody></table><div v-if="!loading && !pageData.items.length" class="empty-state">暂无审计日志。</div></div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>
</template>
