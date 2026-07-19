<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import StatusBadge from '../components/StatusBadge.vue'
import type { DashboardData } from '../types'
import { formatDateTime } from '../utils'

const data = ref<DashboardData | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get<DashboardData>('/dashboard')).data
  } catch (err) {
    error.value = errorMessage(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-header">
    <div>
      <h1>今日工作台</h1>
      <p>优先处理超期任务、紧急关注和待接收转介。</p>
    </div>
    <button type="button" @click="load" :disabled="loading">刷新</button>
  </div>

  <div v-if="error" class="error-box">{{ error }}</div>
  <div v-if="loading && !data" class="card">正在加载…</div>

  <template v-if="data">
    <section class="stats-grid">
      <div class="stat-card"><span>当前在管个案</span><strong>{{ data.active_cases }}</strong></div>
      <div class="stat-card danger"><span>紧急关注</span><strong>{{ data.red_cases }}</strong></div>
      <div class="stat-card"><span>今日待随访</span><strong>{{ data.due_today }}</strong></div>
      <div class="stat-card warning"><span>超期任务</span><strong>{{ data.overdue_tasks }}</strong></div>
      <div class="stat-card"><span>本月已处理随访</span><strong>{{ data.completed_this_month }}</strong></div>
      <div class="stat-card"><span>处理中转介</span><strong>{{ data.pending_referrals }}</strong></div>
    </section>

    <section class="card">
      <h2>近期随访任务</h2>
      <div class="table-wrap" v-if="data.tasks.length">
        <table>
          <thead>
            <tr><th>计划时间</th><th>学生</th><th>风险</th><th>状态</th><th>操作</th></tr>
          </thead>
          <tbody>
            <tr v-for="task in data.tasks" :key="task.followup_id">
              <td :class="{ 'danger-text': task.is_overdue }">{{ formatDateTime(task.scheduled_at) }}</td>
              <td>{{ task.student_name }} <span class="muted">{{ task.student_no }}</span></td>
              <td><StatusBadge :value="task.risk_level" /></td>
              <td><span v-if="task.is_overdue" class="danger-text">已超期</span><span v-else>待处理</span></td>
              <td><RouterLink class="button small" :to="`/students/${task.student_id}`">处理任务</RouterLink></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">当前没有待随访任务。</div>
    </section>
  </template>
</template>
