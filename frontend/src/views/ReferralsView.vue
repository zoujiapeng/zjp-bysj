<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import ModalPanel from '../components/ModalPanel.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useAuthStore } from '../stores/auth'
import type { Page, Referral, UserOption } from '../types'
import { formatDateTime } from '../utils'

const auth = useAuthStore()
const pageData = ref<Page<Referral>>({ items: [], total: 0, page: 1, page_size: 20 })
const psychologists = ref<UserOption[]>([])
const statusFilter = ref('')
const loading = ref(false)
const error = ref('')
const notice = ref('')
const modalOpen = ref(false)
const selected = ref<Referral | null>(null)
const form = reactive({ status: 'ACCEPTED', assigned_to_id: null as number | null, professional_note: '' })
const canProcess = computed(() => auth.hasRole('ADMIN', 'PSYCHOLOGIST'))

async function load(page = 1) {
  loading.value = true
  try {
    const params: Record<string, string | number> = { page, page_size: 20 }
    if (statusFilter.value) params.status = statusFilter.value
    pageData.value = (await api.get<Page<Referral>>('/referrals', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

function openProcess(item: Referral) {
  selected.value = item
  form.status = item.status === 'PENDING' ? 'ACCEPTED' : 'COMPLETED'
  form.assigned_to_id = item.assigned_to_id ?? (auth.user?.role === 'PSYCHOLOGIST' ? auth.user.id : null)
  form.professional_note = item.professional_note ?? ''
  modalOpen.value = true
}

async function save() {
  if (!selected.value) return
  try {
    await api.patch(`/referrals/${selected.value.id}`, {
      status: form.status,
      assigned_to_id: form.assigned_to_id,
      professional_note: form.professional_note || null,
    })
    modalOpen.value = false
    notice.value = '转介状态已更新'
    await load(pageData.value.page)
  } catch (err) { error.value = errorMessage(err) }
}

onMounted(async () => {
  try { psychologists.value = (await api.get('/users/options', { params: { role: 'PSYCHOLOGIST' } })).data } catch (err) { error.value = errorMessage(err) }
  await load()
})
</script>

<template>
  <div class="page-header"><div><h1>转介管理</h1><p>辅导员发起转介，心理老师接收并记录专业处理意见。</p></div></div>
  <div v-if="error" class="error-box">{{ error }}</div><div v-if="notice" class="success-box">{{ notice }}</div>
  <section class="card">
    <form class="toolbar" @submit.prevent="load(1)"><div class="field"><label>状态</label><select v-model="statusFilter"><option value="">全部</option><option value="PENDING">待接收</option><option value="ACCEPTED">处理中</option><option value="COMPLETED">已完成</option><option value="REJECTED">已退回</option></select></div><button class="primary" type="submit">查询</button></form>
    <div class="table-wrap"><table>
      <thead><tr><th>发起时间</th><th>学生</th><th>状态</th><th>发起人/接收人</th><th>转介原因</th><th>专业意见</th><th>操作</th></tr></thead>
      <tbody><tr v-for="item in pageData.items" :key="item.id">
        <td>{{ formatDateTime(item.created_at) }}</td><td>{{ item.student_name }}<br /><span class="muted">{{ item.student_no }}</span></td>
        <td><StatusBadge :value="item.status" /></td><td>{{ item.requested_by_name }}<br /><span class="muted">{{ item.assigned_to_name || '待分配' }}</span></td>
        <td class="pre-line">{{ item.reason }}</td><td class="pre-line">{{ item.professional_note || '—' }}</td>
        <td><div class="row-actions"><RouterLink class="button small" :to="`/students/${item.student_id}`">学生档案</RouterLink><button v-if="canProcess && !['COMPLETED','REJECTED'].includes(item.status)" class="small primary" type="button" @click="openProcess(item)">处理</button></div></td>
      </tr></tbody>
    </table><div v-if="!loading && !pageData.items.length" class="empty-state">没有符合条件的转介记录。</div></div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>

  <ModalPanel :title="`处理转介：${selected?.student_name || ''}`" :open="modalOpen" @close="modalOpen = false">
    <form @submit.prevent="save"><div class="form-grid">
      <div class="field"><label>处理状态 *</label><select v-model="form.status"><option v-if="selected?.status === 'PENDING'" value="ACCEPTED">接收处理</option><option value="REJECTED">退回</option><option v-if="selected?.status === 'ACCEPTED'" value="COMPLETED">完成转介</option></select></div>
      <div class="field"><label>心理老师</label><select v-model.number="form.assigned_to_id" :disabled="auth.user?.role === 'PSYCHOLOGIST'"><option :value="null">请选择</option><option v-for="person in psychologists" :key="person.id" :value="person.id">{{ person.full_name }}</option></select></div>
      <div class="field full" v-if="auth.user?.role === 'PSYCHOLOGIST'"><label>专业处理意见</label><textarea v-model="form.professional_note" :required="form.status === 'COMPLETED'"></textarea><span class="help-text">完成转介时必须填写。请记录支持建议，不在系统中作自动诊断。</span></div>
    </div><div class="form-actions"><button type="button" @click="modalOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form>
  </ModalPanel>
</template>
