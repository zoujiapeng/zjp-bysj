export type UserRole = 'ADMIN' | 'COUNSELOR' | 'PSYCHOLOGIST'
export type RiskLevel = 'GREEN' | 'YELLOW' | 'RED'
export type CaseStatus = 'OPEN' | 'MONITORING' | 'REFERRED' | 'CLOSED'
export type Confidentiality = 'NORMAL' | 'RESTRICTED'
export type FollowUpStatus = 'PLANNED' | 'COMPLETED' | 'UNREACHABLE' | 'CANCELLED'
export type FollowUpMethod = 'IN_PERSON' | 'PHONE' | 'MESSAGE' | 'HOME_VISIT' | 'OTHER'
export type StudentCondition = 'IMPROVED' | 'STABLE' | 'WORSE' | 'UNKNOWN'
export type ReferralStatus = 'PENDING' | 'ACCEPTED' | 'COMPLETED' | 'REJECTED'

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Organization {
  id: number
  code: string
  name: string
  is_active: boolean
  created_at: string
}

export interface User {
  id: number
  username: string
  full_name: string
  role: UserRole
  organization_id: number | null
  organization_name: string | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

export interface UserOption {
  id: number
  full_name: string
  username: string
  role: UserRole
  organization_id: number | null
}

export interface CaseListItem {
  id: number
  case_no: string
  student_id: number
  student_no: string
  student_name: string
  organization_name: string
  owner_id: number
  owner_name: string
  risk_level: RiskLevel
  status: CaseStatus
  source: string
  issue_tags: string[]
  confidentiality: Confidentiality
  next_follow_up_at: string | null
  opened_at: string
  is_overdue: boolean
}

export interface Student {
  id: number
  student_no: string
  name: string
  gender: string | null
  organization_id: number
  organization_name: string
  major: string | null
  grade: string | null
  class_name: string | null
  phone: string | null
  emergency_contact_name: string | null
  emergency_contact_phone: string | null
  counselor_id: number | null
  counselor_name: string | null
  is_active: boolean
  active_case: CaseListItem | null
  created_at: string
}

export interface FollowUp {
  id: number
  case_id: number
  case_no: string
  student_id: number
  student_no: string
  student_name: string
  created_by_id: number
  created_by_name: string
  scheduled_at: string
  completed_at: string | null
  status: FollowUpStatus
  method: FollowUpMethod | null
  condition: StudentCondition
  issue_tags: string[]
  summary: string | null
  actions: string | null
  contact_result: string | null
  next_follow_up_at: string | null
  is_overdue: boolean
  created_at: string
}

export interface RiskChange {
  id: number
  from_level: RiskLevel | null
  to_level: RiskLevel
  reason: string
  changed_by_id: number
  changed_by_name: string
  created_at: string
}

export interface Referral {
  id: number
  case_id: number
  case_no: string
  student_id: number
  student_no: string
  student_name: string
  requested_by_id: number
  requested_by_name: string
  assigned_to_id: number | null
  assigned_to_name: string | null
  status: ReferralStatus
  reason: string
  professional_note: string | null
  created_at: string
  processed_at: string | null
}

export interface CaseDetail extends CaseListItem {
  summary: string
  student: Student
  followups: FollowUp[]
  risk_history: RiskChange[]
  referrals: Referral[]
  closed_at: string | null
  close_reason: string | null
}

export interface DashboardTask {
  followup_id: number
  case_id: number
  student_id: number
  student_name: string
  student_no: string
  risk_level: RiskLevel
  scheduled_at: string
  is_overdue: boolean
}

export interface DashboardData {
  active_cases: number
  red_cases: number
  due_today: number
  overdue_tasks: number
  completed_this_month: number
  pending_referrals: number
  tasks: DashboardTask[]
}

export interface DistributionItem {
  key: string
  label: string
  count: number
}

export interface ReportSummary {
  date_from: string
  date_to: string
  active_case_count: number
  new_case_count: number
  closed_case_count: number
  completed_followup_count: number
  overdue_task_count: number
  on_time_rate: number
  risk_distribution: DistributionItem[]
  status_distribution: DistributionItem[]
  issue_distribution: DistributionItem[]
  organization_distribution: DistributionItem[]
  monthly_followups: { month: string; count: number }[]
}

export interface AuditLog {
  id: number
  actor_id: number | null
  actor_name: string | null
  action: string
  resource_type: string
  resource_id: string | null
  summary: string
  ip_address: string | null
  extra_data: Record<string, unknown>
  created_at: string
}
