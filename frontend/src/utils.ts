import type {
  CaseStatus,
  FollowUpMethod,
  FollowUpStatus,
  ReferralStatus,
  RiskLevel,
  StudentCondition,
  UserRole,
} from './types'

export const roleLabels: Record<UserRole, string> = {
  ADMIN: '系统管理员',
  COUNSELOR: '辅导员',
  PSYCHOLOGIST: '心理老师',
}

export const riskLabels: Record<RiskLevel, string> = {
  GREEN: '一般关注',
  YELLOW: '重点关注',
  RED: '紧急关注',
}

export const caseStatusLabels: Record<CaseStatus, string> = {
  OPEN: '跟进中',
  MONITORING: '稳定观察',
  REFERRED: '已转介',
  CLOSED: '已结案',
}

export const followupStatusLabels: Record<FollowUpStatus, string> = {
  PLANNED: '待随访',
  COMPLETED: '已完成',
  UNREACHABLE: '未联系成功',
  CANCELLED: '已取消',
}

export const methodLabels: Record<FollowUpMethod, string> = {
  IN_PERSON: '面谈',
  PHONE: '电话',
  MESSAGE: '消息/微信',
  HOME_VISIT: '家访',
  OTHER: '其他',
}

export const conditionLabels: Record<StudentCondition, string> = {
  IMPROVED: '改善',
  STABLE: '稳定',
  WORSE: '恶化',
  UNKNOWN: '未知',
}

export const referralStatusLabels: Record<ReferralStatus, string> = {
  PENDING: '待接收',
  ACCEPTED: '处理中',
  COMPLETED: '已完成',
  REJECTED: '已退回',
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

export function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}

export function toIso(localValue: string): string | null {
  if (!localValue) return null
  const date = new Date(localValue)
  return Number.isNaN(date.getTime()) ? null : date.toISOString()
}

export function defaultLocalDateTime(daysFromNow = 0): string {
  const date = new Date(Date.now() + daysFromNow * 24 * 60 * 60 * 1000)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 16)
}

export function todayInput(): string {
  const date = new Date()
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 10)
}

export function monthStartInput(): string {
  const date = new Date()
  date.setDate(1)
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset())
  return date.toISOString().slice(0, 10)
}
