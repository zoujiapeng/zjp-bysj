<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api, downloadFile, errorMessage } from '../api/http'
import { useAuthStore } from '../stores/auth'
import ModalPanel from '../components/ModalPanel.vue'
import PaginationBar from '../components/PaginationBar.vue'
import StatusBadge from '../components/StatusBadge.vue'
import type { Organization, Page, Student, UserOption } from '../types'

const auth = useAuthStore()
const pageData = ref<Page<Student>>({ items: [], total: 0, page: 1, page_size: 20 })
const organizations = ref<Organization[]>([])
const counselors = ref<UserOption[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const createOpen = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

const filters = reactive({ keyword: '', organization_id: '', grade: '', class_name: '' })
const form = reactive({
  student_no: '',
  name: '',
  gender: '',
  organization_id: null as number | null,
  major: '',
  grade: '',
  class_name: '',
  phone: '',
  emergency_contact_name: '',
  emergency_contact_phone: '',
  counselor_id: null as number | null,
})

const canManage = computed(() => auth.hasRole('ADMIN', 'COUNSELOR'))

async function load(page = 1) {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { page, page_size: 20 }
    for (const [key, value] of Object.entries(filters)) if (value) params[key] = value
    pageData.value = (await api.get<Page<Student>>('/students', { params })).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [orgResponse, counselorResponse] = await Promise.all([
    api.get<Organization[]>('/organizations'),
    api.get<UserOption[]>('/users/options', { params: { role: 'COUNSELOR' } }),
  ])
  organizations.value = orgResponse.data
  counselors.value = counselorResponse.data
  if (auth.user?.role === 'COUNSELOR') {
    form.organization_id = auth.user.organization_id
    form.counselor_id = auth.user.id
  }
}

function resetForm() {
  Object.assign(form, {
    student_no: '', name: '', gender: '',
    organization_id: auth.user?.role === 'COUNSELOR' ? auth.user.organization_id : null,
    major: '', grade: '', class_name: '', phone: '',
    emergency_contact_name: '', emergency_contact_phone: '',
    counselor_id: auth.user?.role === 'COUNSELOR' ? auth.user.id : null,
  })
}

async function createStudent() {
  error.value = ''
  if (!form.organization_id) {
    error.value = '请选择所属机构'
    return
  }
  try {
    await api.post('/students', {
      ...form,
      gender: form.gender || null,
      major: form.major || null,
      grade: form.grade || null,
      class_name: form.class_name || null,
      phone: form.phone || null,
      emergency_contact_name: form.emergency_contact_name || null,
      emergency_contact_phone: form.emergency_contact_phone || null,
    })
    createOpen.value = false
    resetForm()
    notice.value = '学生已创建'
    await load(1)
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function exportStudents() {
  try {
    await downloadFile('/students/export.csv', 'students.csv')
  } catch (err) {
    error.value = errorMessage(err)
  }
}

async function importCsv(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const body = new FormData()
  body.append('file', file)
  try {
    const response = await api.post('/students/import', body)
    const result = response.data
    notice.value = `导入完成：新增 ${result.created}，更新 ${result.updated}，跳过 ${result.skipped}`
    if (result.errors?.length) error.value = result.errors.slice(0, 5).map((item: any) => `第${item.row}行：${item.message}`).join('；')
    await load(1)
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    target.value = ''
  }
}

function downloadTemplate() {
  const content = '\ufeff学号,姓名,性别,机构编码,专业,年级,班级,手机号,紧急联系人,紧急联系电话,辅导员账号\n20260001,张三,男,CS,软件工程,2026,软件2601,13800000000,家长,13900000000,counselor1\n'
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'students-import-template.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try { await loadOptions() } catch (err) { error.value = errorMessage(err) }
  await load()
})
</script>

<template>
  <div class="page-header">
    <div><h1>学生档案</h1><p>维护基础信息，并进入学生页面处理关怀个案。</p></div>
    <div class="page-actions">
      <button type="button" @click="exportStudents">导出 CSV</button>
      <template v-if="canManage">
        <button type="button" @click="downloadTemplate">下载导入模板</button>
        <button type="button" @click="fileInput?.click()">导入 CSV</button>
        <input ref="fileInput" type="file" accept=".csv,text/csv" hidden @change="importCsv" />
        <button class="primary" type="button" @click="createOpen = true">新建学生</button>
      </template>
    </div>
  </div>

  <div v-if="error" class="error-box">{{ error }}</div>
  <div v-if="notice" class="success-box">{{ notice }}</div>

  <section class="card">
    <form class="toolbar" @submit.prevent="load(1)">
      <div class="field grow"><label>姓名或学号</label><input v-model="filters.keyword" placeholder="输入关键词" /></div>
      <div class="field"><label>机构</label><select v-model="filters.organization_id"><option value="">全部</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div>
      <div class="field"><label>年级</label><input v-model="filters.grade" /></div>
      <div class="field"><label>班级</label><input v-model="filters.class_name" /></div>
      <button class="primary" type="submit" :disabled="loading">查询</button>
    </form>

    <div class="table-wrap">
      <table>
        <thead><tr><th>学号</th><th>姓名</th><th>机构/班级</th><th>辅导员</th><th>当前关怀</th><th>下次随访</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="student in pageData.items" :key="student.id">
            <td>{{ student.student_no }}</td>
            <td>{{ student.name }}</td>
            <td>{{ student.organization_name }}<br /><span class="muted">{{ student.grade || '—' }} / {{ student.class_name || '—' }}</span></td>
            <td>{{ student.counselor_name || '未分配' }}</td>
            <td><template v-if="student.active_case"><StatusBadge :value="student.active_case.risk_level" /> <StatusBadge :value="student.active_case.status" /></template><span v-else class="muted">无在管个案</span></td>
            <td :class="{ 'danger-text': student.active_case?.is_overdue }">{{ student.active_case?.next_follow_up_at ? new Date(student.active_case.next_follow_up_at).toLocaleString('zh-CN') : '—' }}</td>
            <td><RouterLink class="button small" :to="`/students/${student.id}`">查看</RouterLink></td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && !pageData.items.length" class="empty-state">没有符合条件的学生。</div>
    </div>
    <PaginationBar :page="pageData.page" :page-size="pageData.page_size" :total="pageData.total" @change="load" />
  </section>

  <ModalPanel title="新建学生" :open="createOpen" @close="createOpen = false">
    <form @submit.prevent="createStudent">
      <div class="form-grid">
        <div class="field"><label>学号 *</label><input v-model="form.student_no" required /></div>
        <div class="field"><label>姓名 *</label><input v-model="form.name" required /></div>
        <div class="field"><label>性别</label><input v-model="form.gender" /></div>
        <div class="field"><label>所属机构 *</label><select v-model.number="form.organization_id" required :disabled="auth.user?.role === 'COUNSELOR'"><option :value="null">请选择</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div>
        <div class="field"><label>专业</label><input v-model="form.major" /></div>
        <div class="field"><label>年级</label><input v-model="form.grade" /></div>
        <div class="field"><label>班级</label><input v-model="form.class_name" /></div>
        <div class="field"><label>手机号</label><input v-model="form.phone" /></div>
        <div class="field"><label>紧急联系人</label><input v-model="form.emergency_contact_name" /></div>
        <div class="field"><label>紧急联系电话</label><input v-model="form.emergency_contact_phone" /></div>
        <div class="field full"><label>辅导员</label><select v-model.number="form.counselor_id" :disabled="auth.user?.role === 'COUNSELOR'"><option :value="null">未分配</option><option v-for="person in counselors.filter((item) => !form.organization_id || item.organization_id === form.organization_id)" :key="person.id" :value="person.id">{{ person.full_name }}（{{ person.username }}）</option></select></div>
      </div>
      <div class="form-actions"><button type="button" @click="createOpen = false">取消</button><button class="primary" type="submit">保存</button></div>
    </form>
  </ModalPanel>
</template>
