<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api, downloadFile, errorMessage } from '../api/http'
import type { DistributionItem, Organization, ReportSummary } from '../types'
import { monthStartInput, todayInput } from '../utils'

const report = ref<ReportSummary | null>(null)
const organizations = ref<Organization[]>([])
const filters = reactive({ date_from: monthStartInput(), date_to: todayInput(), organization_id: '' })
const loading = ref(false)
const error = ref('')

const maxCount = (items: DistributionItem[]) => Math.max(1, ...items.map((item) => item.count))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string | number> = { date_from: filters.date_from, date_to: filters.date_to }
    if (filters.organization_id) params.organization_id = filters.organization_id
    report.value = (await api.get<ReportSummary>('/reports/summary', { params })).data
  } catch (err) { error.value = errorMessage(err) } finally { loading.value = false }
}

async function exportCsv() {
  const params = new URLSearchParams({ date_from: filters.date_from, date_to: filters.date_to })
  if (filters.organization_id) params.set('organization_id', filters.organization_id)
  try { await downloadFile(`/reports/export.csv?${params}`, `care-report-${filters.date_from}-${filters.date_to}.csv`) } catch (err) { error.value = errorMessage(err) }
}

onMounted(async () => {
  try { organizations.value = (await api.get('/organizations')).data } catch (err) { error.value = errorMessage(err) }
  await load()
})
</script>

<template>
  <div class="page-header"><div><h1>统计报表</h1><p>按时间和机构汇总关怀个案、随访完成情况与问题分布。</p></div><button type="button" @click="exportCsv">导出 CSV</button></div>
  <div v-if="error" class="error-box">{{ error }}</div>
  <section class="card"><form class="toolbar" @submit.prevent="load"><div class="field"><label>开始日期</label><input v-model="filters.date_from" type="date" required /></div><div class="field"><label>结束日期</label><input v-model="filters.date_to" type="date" required /></div><div class="field"><label>机构</label><select v-model="filters.organization_id"><option value="">全部</option><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div><button class="primary" type="submit">生成报表</button></form></section>

  <template v-if="report">
    <section class="stats-grid" style="margin-top:16px">
      <div class="stat-card"><span>当前在管</span><strong>{{ report.active_case_count }}</strong></div>
      <div class="stat-card"><span>期间新增</span><strong>{{ report.new_case_count }}</strong></div>
      <div class="stat-card"><span>期间结案</span><strong>{{ report.closed_case_count }}</strong></div>
      <div class="stat-card"><span>处理随访</span><strong>{{ report.completed_followup_count }}</strong></div>
      <div class="stat-card warning"><span>当前超期</span><strong>{{ report.overdue_task_count }}</strong></div>
      <div class="stat-card"><span>按时处理率</span><strong>{{ report.on_time_rate }}%</strong></div>
    </section>
    <div class="two-column">
      <section class="card"><h2>风险等级分布</h2><div class="bar-list"><div class="bar-row" v-for="item in report.risk_distribution" :key="item.key"><span>{{ item.label }}</span><div class="bar-track"><div class="bar-fill" :style="{ width: `${item.count / maxCount(report.risk_distribution) * 100}%` }"></div></div><strong>{{ item.count }}</strong></div><div v-if="!report.risk_distribution.length" class="empty-state">暂无数据</div></div></section>
      <section class="card"><h2>个案状态分布</h2><div class="bar-list"><div class="bar-row" v-for="item in report.status_distribution" :key="item.key"><span>{{ item.label }}</span><div class="bar-track"><div class="bar-fill" :style="{ width: `${item.count / maxCount(report.status_distribution) * 100}%` }"></div></div><strong>{{ item.count }}</strong></div><div v-if="!report.status_distribution.length" class="empty-state">暂无数据</div></div></section>
      <section class="card"><h2>主要问题分布</h2><div class="bar-list"><div class="bar-row" v-for="item in report.issue_distribution" :key="item.key"><span>{{ item.label }}</span><div class="bar-track"><div class="bar-fill" :style="{ width: `${item.count / maxCount(report.issue_distribution) * 100}%` }"></div></div><strong>{{ item.count }}</strong></div><div v-if="!report.issue_distribution.length" class="empty-state">暂无数据</div></div></section>
      <section class="card"><h2>机构在管个案</h2><div class="bar-list"><div class="bar-row" v-for="item in report.organization_distribution" :key="item.key"><span>{{ item.label }}</span><div class="bar-track"><div class="bar-fill" :style="{ width: `${item.count / maxCount(report.organization_distribution) * 100}%` }"></div></div><strong>{{ item.count }}</strong></div><div v-if="!report.organization_distribution.length" class="empty-state">暂无数据</div></div></section>
    </div>
    <section class="card"><h2>月度随访处理量</h2><div class="table-wrap"><table><thead><tr><th>月份</th><th>处理次数</th></tr></thead><tbody><tr v-for="item in report.monthly_followups" :key="item.month"><td>{{ item.month }}</td><td>{{ item.count }}</td></tr></tbody></table><div v-if="!report.monthly_followups.length" class="empty-state">该时间范围暂无随访记录。</div></div></section>
  </template>
  <div v-else-if="loading" class="card">正在生成报表…</div>
</template>
