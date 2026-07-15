<template>
  <div class="transfer-page">
    <DataState :loading="loading" :error="error" @retry="loadAll" />

    <section class="metric-grid anim-fade-up">
      <button class="metric-card" type="button" @click="openDataView('talents')"><span class="metric-label">企业人才池</span><strong>{{ talents.length }}</strong><small>{{ activeTalentCount }} 人可参与分析</small><em>查看人才 <el-icon><ArrowRight /></el-icon></em></button>
      <button class="metric-card amber" type="button" @click="openDataView('positions')"><span class="metric-label">内部开放岗位</span><strong>{{ openPositions.length }}</strong><small>{{ openHeadcount }} 个待配置名额</small><em>查看岗位 <el-icon><ArrowRight /></el-icon></em></button>
      <button class="metric-card" type="button" @click="openDataView('demands')"><span class="metric-label">技能缺口</span><strong>{{ criticalDemandCount }}</strong><small>供给缺口大于 0</small><em>查看供需 <el-icon><ArrowRight /></el-icon></em></button>
      <button class="metric-card green" type="button" @click="openDataView('decisions')"><span class="metric-label">已确认转岗</span><strong>{{ decisions.length }}</strong><small>管理层确认记录</small><em>查看决策 <el-icon><ArrowRight /></el-icon></em></button>
    </section>

    <section class="dash-card transfer-workbench anim-fade-up anim-delay-2">
      <el-tabs v-model="activeTab" class="transfer-tabs">
        <el-tab-pane label="人岗适配分析" name="analysis">
          <div class="analysis-layout">
            <aside class="analysis-control">
              <div class="section-heading"><span>01</span><div><h3>确定分析对象</h3><p>可从员工出发推荐岗位，也可从岗位出发筛选人才。</p></div></div>
              <el-radio-group v-model="analysisMode" class="mode-switch">
                <el-radio-button value="talent">按人才找岗位</el-radio-button>
                <el-radio-button value="position">按岗位找人才</el-radio-button>
              </el-radio-group>
              <el-form label-position="top" class="analysis-form">
                <el-form-item v-if="analysisMode === 'talent'" label="选择企业人才">
                  <el-select v-model="selectedTalentId" filterable placeholder="姓名 / 工号 / 当前岗位" style="width:100%">
                    <el-option v-for="talent in activeTalents" :key="talent.id" :value="talent.id" :label="`${talent.name} · ${talent.employee_no} · ${talent.current_position}`" />
                  </el-select>
                </el-form-item>
                <el-form-item v-else label="选择内部开放岗位">
                  <el-select v-model="selectedPositionId" filterable placeholder="岗位 / 接收部门" style="width:100%">
                    <el-option v-for="position in openPositions" :key="position.id" :value="position.id" :label="`${position.title} · ${position.department}`" />
                  </el-select>
                </el-form-item>
                <el-form-item label="采用转岗规则">
                  <el-select v-model="selectedRuleId" clearable placeholder="系统默认 / 当前生效规则" style="width:100%">
                    <el-option v-for="rule in activeRules" :key="rule.id" :value="rule.id" :label="`${rule.name} v${rule.version}（生效）`" />
                  </el-select>
                </el-form-item>
              </el-form>
              <button class="analyze-button" :disabled="matching" @click="runMatch"><el-icon :class="{ 'is-loading': matching }"><Refresh /></el-icon>{{ matching ? "正在计算" : "执行人岗适配" }}</button>
              <div class="policy-note"><el-icon><InfoFilled /></el-icon><span>硬性规则不通过时不可确认；匹配分达到阈值后，仍需管理层人工确认。</span></div>
            </aside>

            <main class="analysis-results">
              <div class="results-head"><div><span class="results-kicker">DECISION QUEUE</span><h3>适配结果</h3></div><span v-if="matchResults.length" class="result-count">{{ matchResults.length }} 组</span></div>
              <div v-if="!matchResults.length" class="empty-result">
                <div class="empty-orbit"><el-icon><Connection /></el-icon></div>
                <h3>等待管理层发起分析</h3>
                <p>系统只在内部开放岗位与企业人才池之间进行匹配，不读取公开招聘岗位。</p>
              </div>
              <div v-else class="match-table-wrap">
                <el-table :data="matchResults" style="width:100%" height="510">
                  <el-table-column label="人才 → 内部岗位" min-width="210">
                    <template #default="{ row }"><div class="pair-cell"><strong>{{ row.talent_name }}</strong><small>{{ row.current_department }} · {{ row.current_position }}</small><span><el-icon><ArrowRight /></el-icon>{{ row.position_title }} · {{ row.target_department }}</span></div></template>
                  </el-table-column>
                  <el-table-column label="规则结果" width="126">
                    <template #default="{ row }"><el-tag :type="row.eligible ? 'success' : 'danger'" effect="plain">{{ row.eligible ? "通过硬规则" : "不符合" }}</el-tag><small v-if="!row.eligible" class="reject-reason">{{ row.disqualifications.join("；") }}</small></template>
                  </el-table-column>
                  <el-table-column label="匹配分" width="132">
                    <template #default="{ row }"><div class="score-cell"><strong>{{ row.score }}</strong><el-progress :percentage="row.score" :show-text="false" :stroke-width="6" :color="scoreColor(row.score)" /></div></template>
                  </el-table-column>
                  <el-table-column label="能力差距" min-width="200">
                    <template #default="{ row }"><div class="gap-cell"><span v-for="skill in row.missing_skills" :key="skill">{{ skill }}</span><small v-if="!row.missing_skills.length">核心技能已覆盖</small><em>{{ row.estimated_development_weeks }} 周培养预估</em></div></template>
                  </el-table-column>
                  <el-table-column label="管理动作" width="110" fixed="right">
                    <template #default="{ row }"><el-button type="primary" link :disabled="!row.eligible || row.score < matchThreshold(row)" @click="confirmTransfer(row)">确认转岗</el-button></template>
                  </el-table-column>
                </el-table>
              </div>
            </main>
          </div>
        </el-tab-pane>

        <el-tab-pane label="内部开放岗位" name="positions">
          <div class="tab-toolbar"><div><h3>内部开放岗位</h3><p>这里只展示已通过审批、当前可参与转岗分析的岗位。</p></div><el-button @click="router.push({ path: '/jobs', query: { scope: 'internal' } })">进入岗位管理</el-button></div>
          <el-table :data="openPositions" style="width:100%">
            <el-table-column prop="title" label="岗位" min-width="170" />
            <el-table-column prop="department" label="接收部门" min-width="130" />
            <el-table-column prop="receiving_manager" label="接收负责人" min-width="130"><template #default="{ row }">{{ row.receiving_manager || "待确认" }}</template></el-table-column>
            <el-table-column prop="level" label="职级" width="90" />
            <el-table-column prop="headcount" label="名额" width="80" align="center" />
            <el-table-column label="必备技能" min-width="230"><template #default="{ row }"><div class="tag-list"><el-tag v-for="skill in row.required_skills" :key="skill" size="small" effect="plain">{{ skill }}</el-tag></div></template></el-table-column>
            <el-table-column label="操作" width="120"><template #default="{ row }"><el-button type="primary" link @click="analyzePosition(row.id)">适配人才</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="企业人才池" name="talents">
          <div class="tab-toolbar"><div><h3>企业人才池</h3><p>从企业员工主数据目录按工号检索并加入，无需重复录入员工档案。</p></div><el-button type="primary" @click="openTalentDialog"><el-icon><Plus /></el-icon>按工号加入人才</el-button></div>
          <el-table :data="talents" style="width:100%">
            <el-table-column prop="employee_no" label="工号" width="110" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="department" label="当前部门" min-width="130" />
            <el-table-column prop="current_position" label="当前岗位" min-width="150" />
            <el-table-column label="司龄 / 岗位任职" width="145"><template #default="{ row }">{{ row.tenure_months }} / {{ row.position_tenure_months }} 个月</template></el-table-column>
            <el-table-column label="技能" min-width="240"><template #default="{ row }"><div class="tag-list"><el-tag v-for="skill in row.skills.slice(0, 5)" :key="skill" size="small" effect="plain">{{ skill }}</el-tag></div></template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">{{ row.status === "active" ? "可参与" : "受限" }}</el-tag></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="企业技能需求库" name="demands">
          <div class="tab-toolbar"><div><h3>企业数据技能需求库</h3><p>从内部开放岗位聚合需求，与企业人才池技能供给实时对比。</p></div><el-button @click="loadAll"><el-icon><Refresh /></el-icon>刷新供需</el-button></div>
          <el-table :data="skillDemands" style="width:100%" :default-sort="{ prop: 'gap', order: 'descending' }">
            <el-table-column prop="skill" label="技能" min-width="160"><template #default="{ row }"><strong>{{ row.skill }}</strong></template></el-table-column>
            <el-table-column label="类型" width="110"><template #default="{ row }"><el-tag :type="row.requirement_type === 'required' ? 'danger' : 'warning'" effect="plain" size="small">{{ row.requirement_type === "required" ? "岗位必需" : "可培养" }}</el-tag></template></el-table-column>
            <el-table-column prop="departments" label="需求部门" min-width="180"><template #default="{ row }">{{ row.departments.join("、") }}</template></el-table-column>
            <el-table-column prop="position_count" label="涉及岗位" width="100" align="center" />
            <el-table-column prop="demand_headcount" label="需求人数" width="100" align="center" />
            <el-table-column prop="talent_supply" label="内部供给" width="100" align="center" />
            <el-table-column prop="gap" label="供给缺口" width="110" sortable align="center"><template #default="{ row }"><strong :class="['gap-number', { critical: row.gap > 0 }]">{{ row.gap }}</strong></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="转岗规则" name="rules">
          <div class="tab-toolbar"><div><h3>转岗规则</h3><p>版本化管理司龄、岗位任职时间与匹配阈值；激活新规则会停用旧规则。</p></div><el-button type="primary" @click="ruleDialog = true"><el-icon><Plus /></el-icon>新建规则版本</el-button></div>
          <el-table :data="rules" style="width:100%">
            <el-table-column prop="name" label="规则名称" min-width="180" />
            <el-table-column label="版本" width="80"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
            <el-table-column prop="min_tenure_months" label="最低司龄（月）" width="130" />
            <el-table-column prop="min_position_tenure_months" label="岗位任职（月）" width="130" />
            <el-table-column prop="min_match_score" label="确认阈值" width="100" />
            <el-table-column label="评分权重" min-width="160"><template #default="{ row }">技能 {{ row.skill_weight }}% · 司龄 {{ row.tenure_weight }}%</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "当前生效" : row.status === "draft" ? "草稿" : "历史版本" }}</el-tag></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="已确认决策" name="decisions">
          <div class="tab-toolbar"><div><h3>已确认转岗决策</h3><p>记录由管理层确定的“人—岗位”组合，作为后续沟通与学习计划的依据。</p></div></div>
          <el-table :data="decisions" style="width:100%">
            <el-table-column prop="talent_name" label="员工" min-width="120" />
            <el-table-column prop="position_title" label="确定转入岗位" min-width="180" />
            <el-table-column prop="match_score" label="确认时匹配分" width="130" />
            <el-table-column label="待补技能" min-width="220"><template #default="{ row }"><div class="tag-list"><el-tag v-for="skill in row.missing_skills" :key="skill" size="small" type="warning" effect="plain">{{ skill }}</el-tag><span v-if="!row.missing_skills.length">无核心缺口</span></div></template></el-table-column>
            <el-table-column prop="note" label="决策备注" min-width="200" show-overflow-tooltip />
            <el-table-column prop="created_at" label="确认时间" width="180"><template #default="{ row }">{{ formatDate(row.created_at) }}</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default><el-tag type="success">已确认</el-tag></template></el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </section>

    <el-dialog v-model="talentDialog" title="从企业员工目录加入人才" width="600px" destroy-on-close>
      <div class="directory-search-note">输入工号中的任意数字，系统会在下方即时联想企业员工主数据。</div>
      <el-form label-position="top">
        <el-form-item label="搜索员工工号">
          <el-select v-model="selectedEmployeeId" filterable remote reserve-keyword clearable placeholder="输入工号，如 1008" :remote-method="searchDirectory" :loading="directoryLoading" style="width:100%" @change="selectDirectoryEmployee">
            <el-option v-for="employee in directoryOptions" :key="employee.id" :value="employee.id" :disabled="employee.in_talent_pool" :label="`${employee.employee_no} · ${employee.name} · ${employee.department}`">
              <div class="employee-option"><strong>{{ employee.employee_no }}</strong><span>{{ employee.name }} · {{ employee.department }} · {{ employee.current_position }}</span><em v-if="employee.in_talent_pool">已在人才池</em></div>
            </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="selectedEmployee" class="employee-preview">
        <div class="employee-preview-head"><span>{{ selectedEmployee.name }}</span><strong>{{ selectedEmployee.employee_no }}</strong></div>
        <dl><div><dt>当前部门</dt><dd>{{ selectedEmployee.department }}</dd></div><div><dt>当前岗位</dt><dd>{{ selectedEmployee.current_position }}</dd></div><div><dt>职级</dt><dd>{{ selectedEmployee.level }}</dd></div><div><dt>司龄 / 任职</dt><dd>{{ selectedEmployee.tenure_months }} / {{ selectedEmployee.position_tenure_months }} 个月</dd></div></dl>
        <div class="tag-list"><el-tag v-for="skill in selectedEmployee.skills" :key="skill" size="small" effect="plain">{{ skill }}</el-tag></div>
      </div>
      <el-empty v-else-if="directorySearched && !directoryLoading && directoryOptions.length === 0" description="企业员工目录暂无匹配，请先通过 HR 同步接口导入主数据" :image-size="70" />
      <template #footer><el-button @click="talentDialog = false">取消</el-button><el-button type="primary" :disabled="!selectedEmployee || selectedEmployee.in_talent_pool" :loading="addingTalent" @click="createTalentFromDirectory">加入人才池</el-button></template>
    </el-dialog>

    <el-dialog v-model="ruleDialog" title="新建转岗规则版本" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="规则名称"><el-input v-model="ruleForm.name" /></el-form-item>
        <div class="form-grid"><el-form-item label="最低司龄（月）"><el-input-number v-model="ruleForm.min_tenure_months" :min="0" style="width:100%" /></el-form-item><el-form-item label="最低岗位任职（月）"><el-input-number v-model="ruleForm.min_position_tenure_months" :min="0" style="width:100%" /></el-form-item></div>
        <div class="form-grid"><el-form-item label="最低匹配分"><el-input-number v-model="ruleForm.min_match_score" :min="0" :max="100" style="width:100%" /></el-form-item><el-form-item label="状态"><el-select v-model="ruleForm.status" style="width:100%"><el-option label="立即生效" value="active" /><el-option label="保存草稿" value="draft" /></el-select></el-form-item></div>
        <el-form-item label="技能权重"><el-slider v-model="ruleForm.skill_weight" :min="0" :max="100" show-input /></el-form-item>
        <el-alert :title="`司龄权重自动设为 ${100 - ruleForm.skill_weight}%`" type="info" :closable="false" />
      </el-form>
      <template #footer><el-button @click="ruleDialog = false">取消</el-button><el-button type="primary" @click="createRule">创建版本</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowRight, Connection, InfoFilled, Plus, Refresh } from "@element-plus/icons-vue";
import DataState from "@/components/common/DataState.vue";
import { dataProvider } from "@/data";
import type { EnterpriseEmployeeDirectory, EnterpriseTalent, InternalMatchResult, InternalPosition, SkillDemandSummary, TransferDecision, TransferRuleSet } from "@/domain/types";

const route = useRoute();
const router = useRouter();
const availableTabs = new Set(["analysis", "positions", "talents", "demands", "rules", "decisions"]);
const requestedTab = typeof route.query.tab === "string" ? route.query.tab : "analysis";
const activeTab = ref(availableTabs.has(requestedTab) ? requestedTab : "analysis");
const loading = ref(false);
const matching = ref(false);
const error = ref("");
const talents = ref<EnterpriseTalent[]>([]);
const positions = ref<InternalPosition[]>([]);
const skillDemands = ref<SkillDemandSummary[]>([]);
const rules = ref<TransferRuleSet[]>([]);
const decisions = ref<TransferDecision[]>([]);
const matchResults = ref<InternalMatchResult[]>([]);
const analysisMode = ref<"talent" | "position">("position");
const selectedTalentId = ref<number>();
const selectedPositionId = ref<number>();
const selectedRuleId = ref<number>();
const talentDialog = ref(false);
const ruleDialog = ref(false);
const directoryOptions = ref<EnterpriseEmployeeDirectory[]>([]);
const selectedEmployeeId = ref<number>();
const selectedEmployee = ref<EnterpriseEmployeeDirectory | null>(null);
const directoryLoading = ref(false);
const directorySearched = ref(false);
const addingTalent = ref(false);

const activeTalents = computed(() => talents.value.filter((item) => item.status === "active"));
const activeRules = computed(() => rules.value.filter((item) => item.status === "active"));
const activeTalentCount = computed(() => activeTalents.value.length);
const openPositions = computed(() => positions.value.filter((item) => item.status === "open"));
const openHeadcount = computed(() => openPositions.value.reduce((sum, item) => sum + item.headcount, 0));
const criticalDemandCount = computed(() => skillDemands.value.filter((item) => item.gap > 0).length);

const ruleForm = reactive({ name: "企业内部转岗规则", min_tenure_months: 12, min_position_tenure_months: 6, min_match_score: 70, skill_weight: 85, status: "active" as "active" | "draft" | "inactive" });

onMounted(async () => {
  const positionId = Number(route.query.positionId);
  if (Number.isFinite(positionId) && positionId > 0) selectedPositionId.value = positionId;
  await loadAll();
});

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    [talents.value, positions.value, skillDemands.value, rules.value, decisions.value] = await Promise.all([
      dataProvider.internalTransfer.listTalents(), dataProvider.internalTransfer.listPositions(), dataProvider.internalTransfer.listSkillDemands(), dataProvider.internalTransfer.listRuleSets(), dataProvider.internalTransfer.listDecisions(),
    ]);
    if (!selectedRuleId.value) selectedRuleId.value = rules.value.find((item) => item.status === "active")?.id;
  } catch (exception) {
    error.value = exception instanceof Error ? exception.message : "内部转岗数据加载失败";
  } finally {
    loading.value = false;
  }
}

function openDataView(tab: string) {
  activeTab.value = tab;
  router.replace({ query: { ...route.query, tab } });
}

function analyzePosition(positionId: number) {
  selectedPositionId.value = positionId;
  analysisMode.value = "position";
  openDataView("analysis");
}

async function openTalentDialog() {
  talentDialog.value = true;
  selectedEmployeeId.value = undefined;
  selectedEmployee.value = null;
  await searchDirectory("");
}

async function searchDirectory(keyword: string) {
  directoryLoading.value = true;
  directorySearched.value = true;
  try {
    directoryOptions.value = await dataProvider.internalTransfer.searchEmployeeDirectory(keyword);
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "企业员工目录检索失败");
  } finally {
    directoryLoading.value = false;
  }
}

function selectDirectoryEmployee(employeeId?: number) {
  selectedEmployee.value = directoryOptions.value.find((item) => item.id === employeeId) || null;
}

async function runMatch() {
  if (analysisMode.value === "talent" && !selectedTalentId.value) return ElMessage.warning("请先选择企业人才");
  if (analysisMode.value === "position" && !selectedPositionId.value) return ElMessage.warning("请先选择内部开放岗位");
  matching.value = true;
  try {
    matchResults.value = analysisMode.value === "talent"
      ? await dataProvider.internalTransfer.matchByTalent({ talent_id: selectedTalentId.value!, rule_set_id: selectedRuleId.value })
      : await dataProvider.internalTransfer.matchByPosition({ position_id: selectedPositionId.value!, rule_set_id: selectedRuleId.value });
    if (!matchResults.value.length) ElMessage.info("当前范围内暂无可分析的人岗组合");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "人岗适配失败");
  } finally {
    matching.value = false;
  }
}

function matchThreshold(row: InternalMatchResult) {
  return rules.value.find((item) => item.id === row.rule_set_id)?.min_match_score ?? 60;
}

async function confirmTransfer(row: InternalMatchResult) {
  try {
    const { value } = await ElMessageBox.prompt(`确认将“${row.talent_name}”转入“${row.position_title}”？`, "管理层确认转岗", { confirmButtonText: "确认决定", cancelButtonText: "取消", inputPlaceholder: "填写决策备注（可选）", inputType: "textarea" });
    await dataProvider.internalTransfer.createDecision({ talent_id: Number(row.talent_id), position_id: Number(row.position_id), rule_set_id: row.rule_set_id || undefined, note: value });
    decisions.value = await dataProvider.internalTransfer.listDecisions();
    ElMessage.success("转岗决定已确认并记录");
  } catch (exception) {
    if (exception === "cancel" || exception === "close") return;
    ElMessage.error(exception instanceof Error ? exception.message : "转岗决定确认失败");
  }
}

async function createTalentFromDirectory() {
  if (!selectedEmployee.value || selectedEmployee.value.in_talent_pool) return;
  addingTalent.value = true;
  try {
    await dataProvider.internalTransfer.createTalentFromDirectory(Number(selectedEmployee.value.id));
    talentDialog.value = false;
    await loadAll();
    ElMessage.success("员工主数据已自动写入企业人才池");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "加入人才池失败");
  } finally {
    addingTalent.value = false;
  }
}

async function createRule() {
  if (!ruleForm.name.trim()) return ElMessage.warning("请填写规则名称");
  try {
    await dataProvider.internalTransfer.createRuleSet({ ...ruleForm, tenure_weight: 100 - ruleForm.skill_weight });
    ruleDialog.value = false;
    await loadAll();
    ElMessage.success(ruleForm.status === "active" ? "新规则版本已生效" : "规则草稿已保存");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "规则创建失败");
  }
}

function scoreColor(score: number) { return score >= 80 ? "#34b37e" : score >= 60 ? "#4f6ef6" : "#e85d5d"; }
function formatDate(value: string) { return new Date(value).toLocaleString("zh-CN", { hour12: false }); }
</script>

<style scoped>
.transfer-page{display:flex;flex-direction:column;gap:16px}.transfer-hero{display:flex;align-items:center;justify-content:space-between;gap:28px;padding:26px 30px;border-radius:16px;background:linear-gradient(118deg,#172033 0%,#243457 64%,#34314d 100%);color:#fff;box-shadow:0 14px 34px rgba(23,32,51,.16)}.hero-eyebrow{color:#9fb2ff;font-family:"JetBrains Mono",monospace;font-size:10px;font-weight:700;letter-spacing:.11em}.transfer-hero h1{margin:7px 0 5px;font-size:27px;letter-spacing:-.03em}.transfer-hero p{max-width:730px;margin:0;color:#cbd3e4;font-size:13px;line-height:1.7}.hero-security{display:flex;align-items:center;gap:11px;min-width:210px;padding:12px 15px;border:1px solid rgba(255,255,255,.13);border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;color:#cbd3e4}.hero-security .el-icon{font-size:22px;color:#f1b963}.hero-security strong{color:#fff}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric-grid article{position:relative;overflow:hidden;padding:18px 20px;border:1px solid var(--border-color);border-radius:14px;background:var(--bg-card)}.metric-grid article:after{position:absolute;right:-15px;bottom:-25px;width:70px;height:70px;border-radius:50%;background:#edf1ff;content:""}.metric-grid article.amber:after{background:#fff0d5}.metric-grid article.green:after{background:#e8f7f0}.metric-label{display:block;color:var(--text-muted);font-size:12px}.metric-grid strong{position:relative;z-index:1;display:block;margin:5px 0 1px;font-size:27px}.metric-grid small{color:var(--text-secondary);font-size:11px}.transfer-workbench{overflow:hidden}.transfer-tabs :deep(.el-tabs__header){margin:0;padding:0 22px;border-bottom:1px solid var(--border-color)}.transfer-tabs :deep(.el-tabs__nav-wrap:after){display:none}.transfer-tabs :deep(.el-tab-pane){padding:0 22px 22px}.analysis-layout{display:grid;grid-template-columns:310px minmax(0,1fr);gap:0;min-height:560px}.analysis-control{padding:25px 22px 22px 0;border-right:1px solid var(--border-color)}.section-heading{display:flex;gap:12px;margin-bottom:20px}.section-heading>span{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;background:var(--color-brand);color:#fff;font-family:"JetBrains Mono",monospace;font-size:11px}.section-heading h3,.results-head h3,.tab-toolbar h3{margin:0;color:var(--text-primary);font-size:16px}.section-heading p,.tab-toolbar p{margin:4px 0 0;color:var(--text-muted);font-size:12px;line-height:1.55}.mode-switch{display:flex;width:100%;margin-bottom:20px}.mode-switch :deep(.el-radio-button){flex:1}.mode-switch :deep(.el-radio-button__inner){width:100%}.analysis-form{padding:15px;border-radius:12px;background:var(--bg-page)}.analyze-button{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;height:42px;margin-top:14px;border:0;border-radius:10px;background:var(--color-brand);color:#fff;font-weight:600;cursor:pointer}.analyze-button:disabled{opacity:.65;cursor:not-allowed}.policy-note{display:flex;align-items:flex-start;gap:7px;margin-top:13px;color:var(--text-muted);font-size:11px;line-height:1.55}.policy-note .el-icon{margin-top:2px;color:var(--color-brand);flex:0 0 auto}.analysis-results{min-width:0;padding:25px 0 0 22px}.results-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.results-kicker{display:block;margin-bottom:3px;color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-size:9px;font-weight:700;letter-spacing:.1em}.result-count{padding:5px 9px;border-radius:8px;background:var(--color-brand-light);color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-size:11px}.empty-result{display:flex;align-items:center;flex-direction:column;justify-content:center;height:430px;border:1px dashed var(--border-color);border-radius:14px;background:linear-gradient(180deg,var(--bg-page),transparent);text-align:center}.empty-orbit{display:grid;place-items:center;width:70px;height:70px;border:1px solid #dce3ff;border-radius:50%;background:#f3f5ff;color:var(--color-brand);font-size:28px;box-shadow:0 0 0 12px rgba(79,110,246,.04)}.empty-result h3{margin:20px 0 6px;font-size:15px}.empty-result p{max-width:410px;margin:0;color:var(--text-muted);font-size:12px;line-height:1.7}.pair-cell{display:flex;flex-direction:column}.pair-cell strong{font-size:13px}.pair-cell small{margin-top:2px;color:var(--text-muted)}.pair-cell span{display:flex;align-items:center;gap:4px;margin-top:7px;color:var(--color-brand);font-size:12px}.reject-reason{display:block;margin-top:6px;color:var(--color-danger);font-size:10px;line-height:1.35}.score-cell strong{display:block;margin-bottom:5px;font-family:"JetBrains Mono",monospace;font-size:18px}.gap-cell{display:flex;gap:4px;flex-wrap:wrap}.gap-cell span{padding:2px 6px;border-radius:5px;background:#fff0ef;color:#c34848;font-size:10px}.gap-cell small{color:var(--color-success)}.gap-cell em{display:block;width:100%;margin-top:4px;color:var(--text-muted);font-size:10px;font-style:normal}.tab-toolbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px 0 16px}.tag-list{display:flex;gap:5px;flex-wrap:wrap}.gap-number{font-family:"JetBrains Mono",monospace}.gap-number.critical{color:var(--color-danger)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:1100px){.metric-grid{grid-template-columns:repeat(2,1fr)}.analysis-layout{grid-template-columns:1fr}.analysis-control{padding-right:0;border-right:0;border-bottom:1px solid var(--border-color)}.analysis-results{padding-left:0}}@media(max-width:720px){.transfer-hero{align-items:flex-start;flex-direction:column}.hero-security{width:100%}.metric-grid{grid-template-columns:1fr 1fr}.form-grid{grid-template-columns:1fr}.transfer-tabs :deep(.el-tab-pane){padding:0 12px 16px}.transfer-tabs :deep(.el-tabs__header){padding:0 12px}}
.metric-card{position:relative;overflow:hidden;padding:17px 19px;border:1px solid var(--border-color);border-radius:13px;background:var(--bg-card);color:var(--text-primary);font:inherit;text-align:left;cursor:pointer;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}.metric-card:after{position:absolute;right:-15px;bottom:-25px;width:70px;height:70px;border-radius:50%;background:#edf1ff;content:""}.metric-card.amber:after{background:#fff0d5}.metric-card.green:after{background:#e8f7f0}.metric-card:hover{z-index:1;border-color:var(--color-brand);box-shadow:0 9px 25px rgba(40,59,112,.1);transform:translateY(-2px)}.metric-card strong{position:relative;z-index:1;display:block;margin:4px 0 1px;font-family:"JetBrains Mono",monospace;font-size:27px}.metric-card small{display:block;color:var(--text-secondary);font-size:11px}.metric-card em{position:relative;z-index:1;display:flex;align-items:center;gap:3px;margin-top:11px;color:var(--color-brand);font-size:11px;font-style:normal;font-weight:600}.directory-search-note{margin-bottom:16px;padding:10px 12px;border-left:3px solid var(--color-brand);background:var(--color-brand-light);color:var(--text-secondary);font-size:12px;line-height:1.6}.employee-option{display:flex;align-items:center;gap:10px;width:100%}.employee-option strong{min-width:72px;color:var(--text-primary);font-family:"JetBrains Mono",monospace}.employee-option span{overflow:hidden;color:var(--text-secondary);text-overflow:ellipsis;white-space:nowrap}.employee-option em{margin-left:auto;color:var(--text-muted);font-size:11px;font-style:normal}.employee-preview{padding:16px;border:1px solid #dce3ff;border-radius:12px;background:linear-gradient(145deg,#fafbff,#f3f6ff)}.employee-preview-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.employee-preview-head span{font-size:17px;font-weight:700}.employee-preview-head strong{color:var(--color-brand);font-family:"JetBrains Mono",monospace}.employee-preview dl{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 13px}.employee-preview dl div{padding:9px 10px;border-radius:8px;background:rgba(255,255,255,.72)}.employee-preview dt{color:var(--text-muted);font-size:10px}.employee-preview dd{margin:3px 0 0;color:var(--text-primary);font-size:12px;font-weight:600}
</style>
