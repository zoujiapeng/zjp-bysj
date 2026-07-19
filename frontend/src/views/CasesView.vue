<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import type { CaseListItem, Organization, Page, UserOption } from '../types'
import { formatDateTime } from '../utils'

const pageData = ref<Page<CaseListItem>>({ items: [], total: 0, page: 1, page_size: 20 })
const organizations = ref<Organization[]>([])
const owners = ref<UserOption[]>([])
const loading = ref(false)
const error = ref('')
const filters = reactive({ keyword: '', risk_level: '', status: '', organization_id: '', owner_id: '', overdue: '' })

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number | boolean> = { page, page_size: 20 }
    for (const [key, value] of Object.entries(filters)) {
      if (value === '') continue
      params[key] = key === 'overdue' ? value === 'true' : value
    }
    pageData.value = (await api.get<Page<CaseListItem>>('/cases', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

onMounted(async () => {
  try {
    const [orgs, users] = await Promise.all([api.get('/organizations'), api.get('/users/options')])
    organizations.value = orgs.data
    owners.value = users.data.filter((item: UserOption) => item.role !== 'ADMIN')
  } catch (err) { error.value = errorMessage(err) }
  await load()
})
</script>

<template>
  <div class="page-header"><div><h1>关怀个案</h1><p>按风险、状态和超期情况集中查看在管对象。</p></div></div>
  <div v-if="error" class="error-box">{{ error }}</div>
  <section class="card">
    <form class="toolbar" @submit.prevent="load(1)">
      <div class="field grow"><label>关键词</label><input v-model="filters.keyword" placeholder="个案号、姓名或学号" /></div>
      <div class="field"><label>风险等级</label><select v-model="filters.risk_level"><option value="">全部</option><option value="GREEN">一般关注</option><option value="YELLOW">重点关注</option><option value="RED">紧急关注</option></select></div>
      <div class="field"><label>个案状态</label><select v-model="filters.status"><option value="">全部</option><option value="OPEN">跟进中</option><option value="MONITORING">稳定观察</option><option value="REFERRED">已转介</option><option value="CLOSED">已结案</option></select></div>
      <div class="field"><label>机构</label><select v-model="filters.organization_id"><option value="">全部</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div>
      <div class="field"><label>负责人</label><select v-model="filters.owner_id"><option value="">全部</option><option v-for="owner in owners" :key="owner.id" :value="owner.id">{{ owner.full_name }}</option></select></div>
      <div class="field"><label>随访状态</label><select v-model="filters.overdue"><option value="">全部</option><option value="true">仅超期</option><option value="false">未超期</option></select></div>
      <button class="primary" type="submit">查询</button>
    </form>
    <div class="table-wrap">
      <table>
        <thead><tr><th>学生</th><th>机构</th><th>风险/状态</th><th>问题标签</th><th>负责人</th><th>下次随访</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="item in pageData.items" :key="item.id">
            <td>{{ item.student_name }}<br /><span class="muted">{{ item.student_no }} / {{ item.case_no }}</span></td>
            <td>{{ item.organization_name }}</td>
            <td><StatusBadge :value="item.risk_level" /> <StatusBadge :value="item.status" /><br /><StatusBadge v-if="item.confidentiality === 'RESTRICTED'" value="RESTRICTED" /></td>
            <td><div class="tags"><span class="tag" v-for="tag in item.issue_tags" :key="tag">{{ tag }}</span></div></td>
            <td>{{ item.owner_name }}</td>
            <td :class="{ 'danger-text': item.is_overdue }">{{ formatDateTime(item.next_follow_up_at) }}</td>
            <td><RouterLink class="button small" :to="`/students/${item.student_id}`">进入档案</RouterLink></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !pageData.items.length" class="empty-state">没有符合条件的个案。</div>
    </div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>
</template>
