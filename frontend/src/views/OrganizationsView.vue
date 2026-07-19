<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { api, errorMessage } from '../api/http'
import ModalPanel from '../components/ModalPanel.vue'
import type { Organization } from '../types'
import { formatDateTime } from '../utils'

const items = ref<Organization[]>([])
const error = ref('')
const notice = ref('')
const modalOpen = ref(false)
const selected = ref<Organization | null>(null)
const form = reactive({ code: '', name: '', is_active: true })

async function load() {
  try { items.value = (await api.get('/organizations', { params: { include_inactive: true } })).data } catch (err) { error.value = errorMessage(err) }
}

function openCreate() { selected.value = null; Object.assign(form, { code: '', name: '', is_active: true }); modalOpen.value = true }
function openEdit(item: Organization) { selected.value = item; Object.assign(form, { code: item.code, name: item.name, is_active: item.is_active }); modalOpen.value = true }

async function save() {
  try {
    if (selected.value) await api.patch(`/organizations/${selected.value.id}`, form)
    else await api.post('/organizations', { code: form.code, name: form.name })
    modalOpen.value = false
    notice.value = selected.value ? '机构已更新' : '机构已创建'
    await load()
  } catch (err) { error.value = errorMessage(err) }
}

onMounted(load)
</script>

<template>
  <div class="page-header"><div><h1>组织机构</h1><p>维护学院或其他学生管理单位，编码用于 CSV 导入。</p></div><button class="primary" type="button" @click="openCreate">新建机构</button></div>
  <div v-if="error" class="error-box">{{ error }}</div><div v-if="notice" class="success-box">{{ notice }}</div>
  <section class="card"><div class="table-wrap"><table><thead><tr><th>编码</th><th>名称</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody><tr v-for="item in items" :key="item.id"><td>{{ item.code }}</td><td>{{ item.name }}</td><td>{{ item.is_active ? '启用' : '停用' }}</td><td>{{ formatDateTime(item.created_at) }}</td><td><button class="small" type="button" @click="openEdit(item)">编辑</button></td></tr></tbody></table><div v-if="!items.length" class="empty-state">请先创建一个学院或管理机构。</div></div></section>
  <ModalPanel :title="selected ? '编辑机构' : '新建机构'" :open="modalOpen" @close="modalOpen = false"><form @submit.prevent="save"><div class="form-grid"><div class="field"><label>编码 *</label><input v-model="form.code" required /></div><div class="field"><label>名称 *</label><input v-model="form.name" required /></div><div class="field full" v-if="selected"><label><input v-model="form.is_active" type="checkbox" style="width:auto" /> 启用机构</label></div></div><div class="form-actions"><button type="button" @click="modalOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form></ModalPanel>
</template>
