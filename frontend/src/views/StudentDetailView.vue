<script setup lang="ts">
import ModalPanel from '../components/ModalPanel.vue'
import StatusBadge from '../components/StatusBadge.vue'
import { useStudentDetail } from '../composables/useStudentDetail'

const {
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
} = useStudentDetail()
</script>

<template>
  <div class="page-header">
    <div>
      <h1>{{ student?.name || '学生档案' }}</h1>
      <p v-if="student">{{ student.student_no }} · {{ student.organization_name }} · {{ student.class_name || '未填写班级' }}</p>
    </div>
    <div class="page-actions">
      <RouterLink class="button" to="/students">返回列表</RouterLink>
      <button v-if="student && canEditStudent" type="button" @click="openEditStudent">编辑学生</button>
      <button v-if="student && !student.active_case && canEditStudent" class="primary" type="button" @click="createCaseOpen = true">建立关怀个案</button>
    </div>
  </div>

  <div v-if="error" class="error-box">{{ error }}</div>
  <div v-if="notice" class="success-box">{{ notice }}</div>
  <div v-if="loading && !student" class="card">正在加载…</div>

  <template v-if="student">
    <section class="card">
      <h2>基本信息</h2>
      <div class="detail-grid">
        <div class="detail-item"><span>姓名 / 性别</span>{{ student.name }} / {{ student.gender || '—' }}</div>
        <div class="detail-item"><span>专业 / 年级 / 班级</span>{{ student.major || '—' }} / {{ student.grade || '—' }} / {{ student.class_name || '—' }}</div>
        <div class="detail-item"><span>负责辅导员</span>{{ student.counselor_name || '未分配' }}</div>
        <div class="detail-item"><span>手机号</span>{{ student.phone || '—' }}</div>
        <div class="detail-item"><span>紧急联系人</span>{{ student.emergency_contact_name || '—' }}</div>
        <div class="detail-item"><span>紧急联系电话</span>{{ student.emergency_contact_phone || '—' }}</div>
      </div>
    </section>

    <section v-if="caseRestricted" class="card">
      <h2>受限个案</h2>
      <p>该个案被设置为受限内容。系统管理员只能查看汇总信息，详细记录仅负责人和心理老师可见。</p>
      <StatusBadge v-if="student.active_case" :value="student.active_case.risk_level" />
      <StatusBadge v-if="student.active_case" :value="student.active_case.status" />
    </section>

    <template v-if="caseData">
      <section class="card">
        <div class="page-header">
          <div>
            <h2>关怀个案</h2>
            <p>{{ caseData.case_no }} · 建档于 {{ formatDateTime(caseData.opened_at) }}</p>
          </div>
          <div class="page-actions" v-if="canModifyCase && caseData.status !== 'CLOSED'">
            <button type="button" @click="openEditCase">编辑个案</button>
            <button type="button" @click="planOpen = true">计划随访</button>
            <button type="button" @click="openFollowup()">补录随访</button>
            <button type="button" @click="openRisk">调整风险</button>
            <button type="button" @click="referralOpen = true">发起转介</button>
            <button class="danger" type="button" @click="closeOpen = true">结案</button>
          </div>
        </div>
        <div class="detail-grid">
          <div class="detail-item"><span>风险等级</span><StatusBadge :value="caseData.risk_level" /></div>
          <div class="detail-item"><span>个案状态</span><StatusBadge :value="caseData.status" /></div>
          <div class="detail-item"><span>保密级别</span><StatusBadge :value="caseData.confidentiality" /></div>
          <div class="detail-item"><span>负责人</span>{{ caseData.owner_name }}</div>
          <div class="detail-item"><span>来源</span>{{ caseData.source }}</div>
          <div class="detail-item"><span>下次随访</span><strong :class="{ 'danger-text': caseData.is_overdue }">{{ formatDateTime(caseData.next_follow_up_at) }}</strong></div>
          <div class="detail-item full"><span>问题标签</span><div class="tags"><span class="tag" v-for="tag in caseData.issue_tags" :key="tag">{{ tag }}</span></div></div>
        </div>
        <h3 style="margin-top:18px">建档摘要</h3>
        <p class="pre-line">{{ caseData.summary }}</p>
        <template v-if="caseData.status === 'CLOSED'">
          <h3>结案说明</h3><p class="pre-line">{{ caseData.close_reason }}</p>
        </template>
      </section>

      <div class="two-column">
        <section class="card">
          <h2>随访时间线</h2>
          <div v-if="caseData.followups.length" class="timeline">
            <article v-for="item in caseData.followups" :key="item.id" class="timeline-item">
              <h4>{{ formatDateTime(item.scheduled_at) }} <StatusBadge :value="item.status" /> <StatusBadge v-if="item.status !== 'PLANNED'" :value="item.condition" /></h4>
              <p v-if="item.method" class="muted">方式：{{ methodLabels[item.method] }} · 记录人：{{ item.created_by_name }}</p>
              <p v-if="item.summary" class="pre-line">{{ item.summary }}</p>
              <p v-if="item.actions"><strong>处理措施：</strong>{{ item.actions }}</p>
              <p v-if="item.next_follow_up_at" class="muted">下次随访：{{ formatDateTime(item.next_follow_up_at) }}</p>
              <div class="row-actions" v-if="item.status === 'PLANNED' && canModifyCase">
                <button class="small primary" type="button" @click="openFollowup(item)">填写结果</button>
                <button class="small" type="button" @click="cancelFollowup(item.id)">取消计划</button>
              </div>
            </article>
          </div>
          <div v-else class="empty-state">暂无随访记录。</div>
        </section>

        <div>
          <section class="card">
            <h2>风险变化</h2>
            <div v-if="caseData.risk_history.length" class="timeline">
              <article v-for="item in caseData.risk_history" :key="item.id" class="timeline-item">
                <h4><StatusBadge :value="item.to_level" /> {{ formatDateTime(item.created_at) }}</h4>
                <p>{{ item.reason }}</p><p class="muted">操作人：{{ item.changed_by_name }}</p>
              </article>
            </div>
            <div v-else class="empty-state">暂无风险变化。</div>
          </section>
          <section class="card">
            <h2>转介记录</h2>
            <div v-if="caseData.referrals.length" class="timeline">
              <article v-for="item in caseData.referrals" :key="item.id" class="timeline-item">
                <h4><StatusBadge :value="item.status" /> {{ formatDateTime(item.created_at) }}</h4>
                <p>{{ item.reason }}</p>
                <p v-if="item.professional_note"><strong>专业意见：</strong>{{ item.professional_note }}</p>
                <p class="muted">接收人：{{ item.assigned_to_name || '待分配' }}</p>
              </article>
            </div>
            <div v-else class="empty-state">暂无转介记录。</div>
          </section>
        </div>
      </div>
    </template>
  </template>

  <ModalPanel title="编辑学生信息" :open="editOpen" @close="editOpen = false">
    <form @submit.prevent="saveStudent"><div class="form-grid">
      <div class="field"><label>姓名 *</label><input v-model="editStudentForm.name" required /></div>
      <div class="field"><label>性别</label><input v-model="editStudentForm.gender" /></div>
      <div class="field"><label>所属机构 *</label><select v-model.number="editStudentForm.organization_id" required :disabled="auth.user?.role === 'COUNSELOR'"><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select></div>
      <div class="field"><label>辅导员</label><select v-model.number="editStudentForm.counselor_id" :disabled="auth.user?.role === 'COUNSELOR'"><option :value="null">未分配</option><option v-for="person in counselors.filter((item) => !editStudentForm.organization_id || item.organization_id === editStudentForm.organization_id)" :key="person.id" :value="person.id">{{ person.full_name }}</option></select></div>
      <div class="field"><label>专业</label><input v-model="editStudentForm.major" /></div><div class="field"><label>年级</label><input v-model="editStudentForm.grade" /></div>
      <div class="field"><label>班级</label><input v-model="editStudentForm.class_name" /></div><div class="field"><label>手机号</label><input v-model="editStudentForm.phone" /></div>
      <div class="field"><label>紧急联系人</label><input v-model="editStudentForm.emergency_contact_name" /></div><div class="field"><label>紧急联系电话</label><input v-model="editStudentForm.emergency_contact_phone" /></div>
      <div class="field full"><label><input v-model="editStudentForm.is_active" type="checkbox" style="width:auto" /> 在校/有效</label></div>
    </div><div class="form-actions"><button type="button" @click="editOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form>
  </ModalPanel>

  <ModalPanel title="建立关怀个案" :open="createCaseOpen" @close="createCaseOpen = false">
    <form @submit.prevent="createCase"><div class="form-grid">
      <div class="field"><label>初始风险 *</label><select v-model="createCaseForm.risk_level"><option value="GREEN">一般关注</option><option value="YELLOW">重点关注</option><option value="RED">紧急关注</option></select></div>
      <div class="field"><label>保密级别</label><select v-model="createCaseForm.confidentiality"><option value="NORMAL">普通</option><option value="RESTRICTED">受限</option></select></div>
      <div class="field full"><label>负责人</label><select v-model.number="createCaseForm.owner_id" :disabled="auth.user?.role !== 'ADMIN'"><option :value="null">{{ auth.user?.role === 'ADMIN' ? '默认使用学生辅导员' : '当前用户' }}</option><option v-for="person in [...counselors, ...psychologists]" :key="person.id" :value="person.id">{{ person.full_name }}</option></select></div>
      <div class="field full"><label>发现来源 *</label><input v-model="createCaseForm.source" required /></div>
      <div class="field full"><label>问题标签</label><input v-model="createCaseForm.issue_tags" placeholder="学习压力、睡眠、人际关系" /></div>
      <div class="field full"><label>建档摘要 *</label><textarea v-model="createCaseForm.summary" required></textarea></div>
      <div class="field full"><label>首次随访时间</label><input v-model="createCaseForm.next_follow_up_at" type="datetime-local" /></div>
    </div><div class="form-actions"><button type="button" @click="createCaseOpen = false">取消</button><button class="primary" type="submit">建立个案</button></div></form>
  </ModalPanel>

  <ModalPanel title="编辑个案" :open="editCaseOpen" @close="editCaseOpen = false">
    <form @submit.prevent="saveCase"><div class="form-grid">
      <div class="field"><label>状态</label><select v-model="editCaseForm.status" :disabled="caseData?.status === 'REFERRED'"><option value="OPEN">跟进中</option><option value="MONITORING">稳定观察</option><option v-if="caseData?.status === 'REFERRED'" value="REFERRED">已转介（由转介流程维护）</option></select></div>
      <div class="field"><label>保密级别</label><select v-model="editCaseForm.confidentiality"><option value="NORMAL">普通</option><option value="RESTRICTED">受限</option></select></div>
      <div class="field full"><label>负责人</label><select v-model.number="editCaseForm.owner_id"><option v-for="person in [...counselors, ...psychologists]" :key="person.id" :value="person.id">{{ person.full_name }}</option></select></div>
      <div class="field full"><label>来源</label><input v-model="editCaseForm.source" required /></div>
      <div class="field full"><label>问题标签</label><input v-model="editCaseForm.issue_tags" /></div>
      <div class="field full"><label>摘要</label><textarea v-model="editCaseForm.summary" required></textarea></div>
    </div><div class="form-actions"><button type="button" @click="editCaseOpen = false">取消</button><button class="primary" type="submit">保存</button></div></form>
  </ModalPanel>

  <ModalPanel title="计划随访" :open="planOpen" @close="planOpen = false">
    <form @submit.prevent="createPlan"><div class="form-grid">
      <div class="field"><label>计划时间 *</label><input v-model="planForm.scheduled_at" type="datetime-local" required /></div>
      <div class="field"><label>建议方式</label><select v-model="planForm.method"><option value="IN_PERSON">面谈</option><option value="PHONE">电话</option><option value="MESSAGE">消息/微信</option><option value="HOME_VISIT">家访</option><option value="OTHER">其他</option></select></div>
      <div class="field full"><label>本次目的</label><textarea v-model="planForm.purpose"></textarea></div>
    </div><div class="form-actions"><button type="button" @click="planOpen = false">取消</button><button class="primary" type="submit">保存计划</button></div></form>
  </ModalPanel>

  <ModalPanel :title="selectedFollowupId ? '填写随访结果' : '补录随访记录'" :open="followupOpen" wide @close="followupOpen = false">
    <form @submit.prevent="saveFollowup"><div class="form-grid">
      <div class="field"><label>完成时间 *</label><input v-model="followupForm.completed_at" type="datetime-local" required /></div>
      <div class="field"><label>随访方式 *</label><select v-model="followupForm.method"><option v-for="(_, key) in methodLabels" :key="key" :value="key">{{ methodLabels[key] }}</option></select></div>
      <div class="field"><label>处理结果 *</label><select v-model="followupForm.status"><option value="COMPLETED">已完成</option><option value="UNREACHABLE">未联系成功</option></select></div>
      <div class="field"><label>学生状态 *</label><select v-model="followupForm.condition"><option v-for="(_, key) in conditionLabels" :key="key" :value="key">{{ conditionLabels[key] }}</option></select></div>
      <div class="field full"><label>主要问题标签</label><input v-model="followupForm.issue_tags" /></div>
      <div class="field full"><label>情况记录 *</label><textarea v-model="followupForm.summary" required></textarea></div>
      <div class="field full"><label>本次措施 *</label><textarea v-model="followupForm.actions" required></textarea></div>
      <div class="field full"><label>联系结果补充</label><input v-model="followupForm.contact_result" /></div>
      <div class="field"><label>风险等级</label><select v-model="followupForm.risk_level"><option value="GREEN">一般关注</option><option value="YELLOW">重点关注</option><option value="RED">紧急关注</option></select></div>
      <div class="field"><label>风险调整原因</label><input v-model="followupForm.risk_reason" placeholder="风险变化时必填" /></div>
      <div class="field"><label>下次随访时间</label><input v-model="followupForm.next_follow_up_at" type="datetime-local" /></div>
      <div class="field"><label>下次方式</label><select v-model="followupForm.next_method"><option v-for="(_, key) in methodLabels" :key="key" :value="key">{{ methodLabels[key] }}</option></select></div>
    </div><div class="form-actions"><button type="button" @click="followupOpen = false">取消</button><button class="primary" type="submit">保存记录</button></div></form>
  </ModalPanel>

  <ModalPanel title="调整风险等级" :open="riskOpen" @close="riskOpen = false">
    <form @submit.prevent="saveRisk"><div class="form-grid">
      <div class="field full"><label>新风险等级 *</label><select v-model="riskForm.risk_level"><option value="GREEN">一般关注</option><option value="YELLOW">重点关注</option><option value="RED">紧急关注</option></select></div>
      <div class="field full"><label>调整原因 *</label><textarea v-model="riskForm.reason" required></textarea></div>
    </div><div class="form-actions"><button type="button" @click="riskOpen = false">取消</button><button class="primary" type="submit">确认调整</button></div></form>
  </ModalPanel>

  <ModalPanel title="发起心理中心转介" :open="referralOpen" @close="referralOpen = false">
    <form @submit.prevent="createReferral"><div class="form-grid">
      <div class="field full"><label>指定心理老师</label><select v-model.number="referralForm.assigned_to_id"><option :value="null">暂不指定</option><option v-for="person in psychologists" :key="person.id" :value="person.id">{{ person.full_name }}</option></select></div>
      <div class="field full"><label>转介原因 *</label><textarea v-model="referralForm.reason" required></textarea></div>
    </div><div class="form-actions"><button type="button" @click="referralOpen = false">取消</button><button class="primary" type="submit">提交转介</button></div></form>
  </ModalPanel>

  <ModalPanel title="结案" :open="closeOpen" @close="closeOpen = false">
    <form @submit.prevent="closeCase"><p class="help-text">结案会取消尚未完成的随访任务。红色风险个案只能由心理老师结案。</p><div class="field"><label>结案说明 *</label><textarea v-model="closeForm.reason" required></textarea></div><div class="form-actions"><button type="button" @click="closeOpen = false">取消</button><button class="danger" type="submit">确认结案</button></div></form>
  </ModalPanel>
</template>
