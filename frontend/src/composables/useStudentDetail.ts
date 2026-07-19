import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, errorMessage } from '../api/http'
import { useAuthStore } from '../stores/auth'
import type { CaseDetail, FollowUp, Organization, Student, UserOption } from '../types'
import {
  conditionLabels,
  defaultLocalDateTime,
  formatDateTime,
  methodLabels,
  toIso,
} from '../utils'

export function useStudentDetail() {
  const route = useRoute()
  const router = useRouter()
  const auth = useAuthStore()
  const studentId = Number(route.params.id)

  const student = ref<Student | null>(null)
  const caseData = ref<CaseDetail | null>(null)
  const caseRestricted = ref(false)
  const organizations = ref<Organization[]>([])
  const counselors = ref<UserOption[]>([])
  const psychologists = ref<UserOption[]>([])
  const loading = ref(false)
  const error = ref('')
  const notice = ref('')

  const editOpen = ref(false)
  const createCaseOpen = ref(false)
  const editCaseOpen = ref(false)
  const planOpen = ref(false)
  const followupOpen = ref(false)
  const riskOpen = ref(false)
  const referralOpen = ref(false)
  const closeOpen = ref(false)
  const selectedFollowupId = ref<number | null>(null)

  const editStudentForm = reactive({
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
    is_active: true,
  })
  const createCaseForm = reactive({
    owner_id: null as number | null,
    risk_level: 'GREEN',
    source: '辅导员日常观察',
    issue_tags: '',
    summary: '',
    confidentiality: 'NORMAL',
    next_follow_up_at: defaultLocalDateTime(3),
  })
  const editCaseForm = reactive({
    owner_id: null as number | null,
    source: '',
    issue_tags: '',
    summary: '',
    confidentiality: 'NORMAL',
    status: 'OPEN',
  })
  const planForm = reactive({
    scheduled_at: defaultLocalDateTime(3),
    method: 'IN_PERSON',
    purpose: '',
  })
  const followupForm = reactive({
    method: 'IN_PERSON',
    condition: 'STABLE',
    status: 'COMPLETED',
    issue_tags: '',
    summary: '',
    actions: '',
    contact_result: '',
    completed_at: defaultLocalDateTime(0),
    next_follow_up_at: defaultLocalDateTime(7),
    next_method: 'PHONE',
    risk_level: 'GREEN',
    risk_reason: '',
  })
  const riskForm = reactive({ risk_level: 'YELLOW', reason: '' })
  const referralForm = reactive({ reason: '', assigned_to_id: null as number | null })
  const closeForm = reactive({ reason: '' })

  const canEditStudent = computed(() => auth.hasRole('ADMIN', 'COUNSELOR'))
  const canModifyCase = computed(() => {
    if (!auth.user || !caseData.value) return false
    return (
      auth.user.role === 'ADMIN' ||
      auth.user.role === 'PSYCHOLOGIST' ||
      caseData.value.owner_id === auth.user.id
    )
  })

  function tags(value: string): string[] {
    return value
      .split(/[，,、]/)
      .map((item) => item.trim())
      .filter((item, index, array) => item && array.indexOf(item) === index)
  }

  function setNotice(message: string) {
    notice.value = message
    window.setTimeout(() => {
      if (notice.value === message) notice.value = ''
    }, 4000)
  }

  async function loadStudent() {
    student.value = (await api.get<Student>(`/students/${studentId}`)).data
  }

  async function loadCase() {
    caseData.value = null
    caseRestricted.value = false
    if (!student.value?.active_case) return
    try {
      caseData.value = (
        await api.get<CaseDetail>(`/cases/${student.value.active_case.id}`)
      ).data
    } catch (err: any) {
      if (err.response?.status === 403) caseRestricted.value = true
      else throw err
    }
  }

  async function loadAll() {
    loading.value = true
    error.value = ''
    try {
      await loadStudent()
      await loadCase()
    } catch (err) {
      error.value = errorMessage(err)
    } finally {
      loading.value = false
    }
  }

  function openEditStudent() {
    if (!student.value) return
    Object.assign(editStudentForm, {
      name: student.value.name,
      gender: student.value.gender ?? '',
      organization_id: student.value.organization_id,
      major: student.value.major ?? '',
      grade: student.value.grade ?? '',
      class_name: student.value.class_name ?? '',
      phone: student.value.phone ?? '',
      emergency_contact_name: student.value.emergency_contact_name ?? '',
      emergency_contact_phone: student.value.emergency_contact_phone ?? '',
      counselor_id: student.value.counselor_id,
      is_active: student.value.is_active,
    })
    editOpen.value = true
  }

  async function saveStudent() {
    try {
      await api.patch(`/students/${studentId}`, {
        ...editStudentForm,
        gender: editStudentForm.gender || null,
        major: editStudentForm.major || null,
        grade: editStudentForm.grade || null,
        class_name: editStudentForm.class_name || null,
        phone: editStudentForm.phone || null,
        emergency_contact_name: editStudentForm.emergency_contact_name || null,
        emergency_contact_phone: editStudentForm.emergency_contact_phone || null,
      })
      editOpen.value = false
      setNotice('学生信息已更新')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  async function createCase() {
    try {
      await api.post('/cases', {
        student_id: studentId,
        owner_id: createCaseForm.owner_id,
        risk_level: createCaseForm.risk_level,
        source: createCaseForm.source,
        issue_tags: tags(createCaseForm.issue_tags),
        summary: createCaseForm.summary,
        confidentiality: createCaseForm.confidentiality,
        next_follow_up_at: toIso(createCaseForm.next_follow_up_at),
      })
      createCaseOpen.value = false
      setNotice('关怀个案已建立')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  function openEditCase() {
    if (!caseData.value) return
    Object.assign(editCaseForm, {
      owner_id: caseData.value.owner_id,
      source: caseData.value.source,
      issue_tags: caseData.value.issue_tags.join('、'),
      summary: caseData.value.summary,
      confidentiality: caseData.value.confidentiality,
      status: caseData.value.status,
    })
    editCaseOpen.value = true
  }

  async function saveCase() {
    if (!caseData.value) return
    try {
      const payload: Record<string, unknown> = {
        owner_id: editCaseForm.owner_id,
        source: editCaseForm.source,
        issue_tags: tags(editCaseForm.issue_tags),
        summary: editCaseForm.summary,
        confidentiality: editCaseForm.confidentiality,
      }
      if (caseData.value.status !== 'REFERRED') payload.status = editCaseForm.status
      await api.patch(`/cases/${caseData.value.id}`, payload)
      editCaseOpen.value = false
      setNotice('个案信息已更新')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  async function createPlan() {
    if (!caseData.value) return
    try {
      await api.post(`/cases/${caseData.value.id}/followups/plans`, {
        scheduled_at: toIso(planForm.scheduled_at),
        method: planForm.method || null,
        purpose: planForm.purpose || null,
      })
      planOpen.value = false
      setNotice('随访计划已创建')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  function openFollowup(item?: FollowUp) {
    selectedFollowupId.value = item?.id ?? null
    Object.assign(followupForm, {
      method: item?.method ?? 'IN_PERSON',
      condition: 'STABLE',
      status: 'COMPLETED',
      issue_tags: caseData.value?.issue_tags.join('、') ?? '',
      summary: '',
      actions: '',
      contact_result: '',
      completed_at: defaultLocalDateTime(0),
      next_follow_up_at: defaultLocalDateTime(7),
      next_method: 'PHONE',
      risk_level: caseData.value?.risk_level ?? 'GREEN',
      risk_reason: '',
    })
    followupOpen.value = true
  }

  async function saveFollowup() {
    if (!caseData.value) return
    const payload = {
      method: followupForm.method,
      condition: followupForm.condition,
      status: followupForm.status,
      issue_tags: tags(followupForm.issue_tags),
      summary: followupForm.summary,
      actions: followupForm.actions,
      contact_result: followupForm.contact_result || null,
      completed_at: toIso(followupForm.completed_at),
      next_follow_up_at: toIso(followupForm.next_follow_up_at),
      next_method: followupForm.next_follow_up_at ? followupForm.next_method : null,
      risk_level: followupForm.risk_level,
      risk_reason: followupForm.risk_reason || null,
    }
    try {
      if (selectedFollowupId.value) {
        await api.post(`/followups/${selectedFollowupId.value}/complete`, payload)
      } else {
        await api.post(`/cases/${caseData.value.id}/followups/complete`, payload)
      }
      followupOpen.value = false
      setNotice('随访结果已保存')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  function openRisk() {
    if (!caseData.value) return
    riskForm.risk_level =
      caseData.value.risk_level === 'GREEN' ? 'YELLOW' : caseData.value.risk_level
    riskForm.reason = ''
    riskOpen.value = true
  }

  async function saveRisk() {
    if (!caseData.value) return
    try {
      await api.post(`/cases/${caseData.value.id}/risk`, riskForm)
      riskOpen.value = false
      setNotice('风险等级已更新')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  async function createReferral() {
    if (!caseData.value) return
    try {
      await api.post(`/cases/${caseData.value.id}/referrals`, referralForm)
      referralOpen.value = false
      setNotice('转介申请已提交')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  async function closeCase() {
    if (!caseData.value) return
    try {
      await api.post(`/cases/${caseData.value.id}/close`, closeForm)
      closeOpen.value = false
      setNotice('个案已结案')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  async function cancelFollowup(id: number) {
    if (!confirm('确认取消该随访计划？')) return
    try {
      await api.post(`/followups/${id}/cancel`)
      setNotice('随访计划已取消')
      await loadAll()
    } catch (err) {
      error.value = errorMessage(err)
    }
  }

  onMounted(async () => {
    if (!Number.isFinite(studentId)) {
      await router.replace('/students')
      return
    }
    try {
      const [orgResponse, counselorResponse, psychologistResponse] = await Promise.all([
        api.get<Organization[]>('/organizations'),
        api.get<UserOption[]>('/users/options', { params: { role: 'COUNSELOR' } }),
        api.get<UserOption[]>('/users/options', { params: { role: 'PSYCHOLOGIST' } }),
      ])
      organizations.value = orgResponse.data
      counselors.value = counselorResponse.data
      psychologists.value = psychologistResponse.data
    } catch (err) {
      error.value = errorMessage(err)
    }
    await loadAll()
  })

  return {
    auth,
    student,
    caseData,
    caseRestricted,
    organizations,
    counselors,
    psychologists,
    loading,
    error,
    notice,
    editOpen,
    createCaseOpen,
    editCaseOpen,
    planOpen,
    followupOpen,
    riskOpen,
    referralOpen,
    closeOpen,
    selectedFollowupId,
    editStudentForm,
    createCaseForm,
    editCaseForm,
    planForm,
    followupForm,
    riskForm,
    referralForm,
    closeForm,
    canEditStudent,
    canModifyCase,
    openEditStudent,
    saveStudent,
    createCase,
    openEditCase,
    saveCase,
    createPlan,
    openFollowup,
    saveFollowup,
    openRisk,
    saveRisk,
    createReferral,
    closeCase,
    cancelFollowup,
    formatDateTime,
    methodLabels,
    conditionLabels,
  }
}
