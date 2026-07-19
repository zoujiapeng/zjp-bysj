<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import ModalPanel from '../components/ModalPanel.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import type { FollowUp, Page } from '../types'
import { conditionLabels, defaultLocalDateTime, formatDateTime, methodLabels, toIso } from '../utils'

const pageData = ref<Page<FollowUp>>({ items: [], total: 0, page: 1, page_size: 20 })
const filters = reactive({ status: 'PLANNED', overdue: '' })
const loading = ref(false)
const error = ref('')
const notice = ref('')
const modalOpen = ref(false)
const selected = ref<FollowUp | null>(null)
const form = reactive({
  method: 'IN_PERSON', condition: 'STABLE', status: 'COMPLETED', issue_tags: '', summary: '',
  actions: '', contact_result: '', completed_at: defaultLocalDateTime(0),
  next_follow_up_at: defaultLocalDateTime(7), next_method: 'PHONE',
})

function parseTags(value: string) {
  return value.split(/[，,、]/).map((item) => item.trim()).filter(Boolean)
}

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number | boolean> = { page, page_size: 20 }
    if (filters.status) params.status = filters.status
    if (filters.overdue) params.overdue = filters.overdue === 'true'
    pageData.value = (await api.get<Page<FollowUp>>('/followups', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

function openComplete(item: FollowUp) {
  selected.value = item
  Object.assign(form, {
    method: item.method ?? 'IN_PERSON', condition: 'STABLE', status: 'COMPLETED',
    issue_tags: item.issue_tags.join('、'), summary: '', actions: '', contact_result: '',
    completed_at: defaultLocalDateTime(0), next_follow_up_at: defaultLocalDateTime(7), next_method: 'PHONE',
  })
  modalOpen.value = true
}

async function save() {
  if (!selected.value) return
  try {
    await api.post(`/followups/${selected.value.id}/complete`, {
      method: form.method,
      condition: form.condition,
      status: form.status,
      issue_tags: parseTags(form.issue_tags),
      summary: form.summary,
      actions: form.actions,
      contact_result: form.contact_result || null,
      completed_at: toIso(form.completed_at),
      next_follow_up_at: toIso(form.next_follow_up_at),
      next_method: form.next_follow_up_at ? form.next_method : null,
    })
    modalOpen.value = false
    notice.value = '随访结果已保存'
    await load(pageData.value.page)
  } catch (err) { error.value = errorMessage(err) }
}

async function cancel(item: FollowUp) {
  if (!confirm(`确认取消 ${item.student_name} 的随访计划？`)) return
  try {
    await api.post(`/followups/${item.id}/cancel`)
    notice.value = '随访计划已取消'
    await load(pageData.value.page)
  } catch (err) { error.value = errorMessage(err) }
}

onMounted(() => load())
</script>

<template>
  <div class="page-header"><div><h1>随访任务</h1><p>集中处理待随访和超期任务，完成后可直接生成下一次计划。</p></div></div>
  <div v-if="error" class="error-box">{{ error }}</div><div v-if="notice" class="success-box">{{ notice }}</div>
  <section class="card">
    <form class="toolbar" @submit.prevent="load(1)">
      <div class="field"><label>状态</label><select v-model="filters.status"><option value="">全部</option><option value="PLANNED">待随访</option><option value="COMPLETED">已完成</option><option value="UNREACHABLE">未联系成功</option><option value="CANCELLED">已取消</option></select></div>
      <div class="field"><label>是否超期</label><select v-model="filters.overdue"><option value="">全部</option><option value="true">仅超期</option><option value="false">未超期</option></select></div>
      <button class="primary" type="submit">查询</button>
    </form>
    <div class="table-wrap"><table>
      <thead><tr><th>计划时间</th><th>学生</th><th>状态</th><th>方式</th><th>简要内容</th><th>记录人</th><th>操作</th></tr></thead>
      <tbody><tr v-for="item in pageData.items" :key="item.id">
        <td :class="{ 'danger-text': item.is_overdue }">{{ formatDateTime(item.scheduled_at) }}</td>
        <td>{{ item.student_name }}<br /><span class="muted">{{ item.student_no }}</span></td>
        <td><StatusBadge :value="item.status" /><br /><StatusBadge v-if="item.status !== 'PLANNED'" :value="item.condition" /></td>
        <td>{{ item.method ? methodLabels[item.method] : '待确定' }}</td>
        <td>{{ item.summary || '—' }}</td><td>{{ item.created_by_name }}</td>
        <td><div class="row-actions"><RouterLink class="button small" :to="`/students/${item.student_id}`">学生档案</RouterLink><button v-if="item.status === 'PLANNED'" class="small primary" type="button" @click="openComplete(item)">填写结果</button><button v-if="item.status === 'PLANNED'" class="small" type="button" @click="cancel(item)">取消</button></div></td>
      </tr></tbody>
    </table><div v-if="!loading && !pageData.items.length" class="empty-state">没有符合条件的随访任务。</div></div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>

  <ModalPanel :title="`填写随访结果：${selected?.student_name || ''}`" :open="modalOpen" wide @close="modalOpen = false">
    <form @submit.prevent="save"><div class="form-grid">
      <div class="field"><label>完成时间 *</label><input v-model="form.completed_at" type="datetime-local" required /></div>
      <div class="field"><label>方式 *</label><select v-model="form.method"><option v-for="(label, key) in methodLabels" :key="key" :value="key">{{ label }}</option></select></div>
      <div class="field"><label>处理结果 *</label><select v-model="form.status"><option value="COMPLETED">已完成</option><option value="UNREACHABLE">未联系成功</option></select></div>
      <div class="field"><label>学生状态 *</label><select v-model="form.condition"><option v-for="(label, key) in conditionLabels" :key="key" :value="key">{{ label }}</option></select></div>
      <div class="field full"><label>问题标签</label><input v-model="form.issue_tags" /></div>
      <div class="field full"><label>情况记录 *</label><textarea v-model="form.summary" required></textarea></div>
      <div class="field full"><label>处理措施 *</label><textarea v-model="form.actions" required></textarea></div>
      <div class="field full"><label>联系结果补充</label><input v-model="form.contact_result" /></div>
      <div class="field"><label>下次随访时间</label><input v-model="form.next_follow_up_at" type="datetime-local" /></div>
      <div class="field"><label>下次方式</label><select v-model="form.next_method"><option v-for="(label, key) in methodLabels" :key="key" :value="key">{{ label }}</option></select></div>
    </div><div class="form-actions"><button type="button" @click="modalOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form>
  </ModalPanel>
</template>
