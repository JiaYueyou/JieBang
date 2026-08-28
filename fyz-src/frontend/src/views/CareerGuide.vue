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

        <el-tab-pane label="AI 职业规划" name="agent">
          <div class="career-agent-layout">
            <aside class="career-agent-form">
              <div class="section-heading"><span>AI</span><div><h3>生成可解释的培养建议</h3><p>Agent 建议与规则匹配、管理层决定相互独立，不会自动确认转岗。</p></div></div>
              <el-form label-position="top">
                <el-form-item label="选择企业人才">
                  <el-select v-model="careerTalentId" filterable placeholder="选择人才" style="width:100%">
                    <el-option v-for="talent in activeTalents" :key="talent.id" :value="Number(talent.id)" :label="`${talent.name} · ${talent.current_position}`" />
                  </el-select>
                </el-form-item>
                <el-form-item label="目标内部岗位">
                  <el-select v-model="careerTargetIds" multiple filterable placeholder="可选择多个目标岗位" style="width:100%">
                    <el-option v-for="position in openPositions" :key="position.id" :value="Number(position.id)" :label="`${position.title} · ${position.department}`" />
                  </el-select>
                </el-form-item>
                <el-form-item label="补充技能">
                  <el-input v-model="careerExtraSkills" type="textarea" :rows="3" placeholder="例如：Python、数据分析、项目管理" />
                </el-form-item>
                <el-form-item label="企业技术栈背景">
                  <el-input v-model="careerEnterpriseTech" type="textarea" :rows="3" placeholder="用于约束学习路径，不作为自动决策依据" />
                </el-form-item>
              </el-form>
              <button class="analyze-button" :disabled="careerLoading" @click="runCareerAgent">
                <el-icon :class="{ 'is-loading': careerLoading }"><Refresh /></el-icon>
                {{ careerLoading ? "Agent 正在分析" : "生成职业规划建议" }}
              </button>
              <p class="career-run-id" v-if="careerAgentRunId">审计 ID：{{ careerAgentRunId }}</p>
            </aside>
            <main class="career-agent-results">
              <el-alert
                v-if="careerAgentStatus === 'degraded'"
                title="当前为规则模板降级结果，请人工复核"
                type="warning"
                :closable="false"
                show-icon
              />
              <el-alert v-if="careerError" :title="careerError" type="error" :closable="false" show-icon />
              <div v-if="careerLoading" class="career-streaming-state">
                <div class="career-streaming-head"><span class="streaming-pulse"></span><div><strong>{{ careerStage }}</strong><small>正在分阶段生成可审计的职业规划建议</small></div><b>{{ careerProgress }}%</b></div>
                <el-progress :percentage="careerProgress" :show-text="false" :stroke-width="8" />
                <div class="career-stage-list"><span v-for="(stage, index) in careerStages" :key="stage" :class="{ active: index <= careerStageIndex }">{{ index < careerStageIndex ? "✓" : index === careerStageIndex ? "●" : "○" }} {{ stage }}</span></div>
                <div class="career-streaming-preview"><i></i><i></i><i></i><i></i></div>
              </div>
              <div v-else-if="careerRecommendations.length" class="career-recommendations">
                <article v-for="item in careerRecommendations" :key="item.job_id" class="career-recommendation">
                  <header><div><span>#{{ item.rank }} · Agent 建议</span><h3>{{ item.job }}</h3></div><strong>{{ item.recommendScore }}%</strong></header>
                  <div class="career-score-row"><span>当前匹配 {{ item.currentMatch }}%</span><span>培养后参考 {{ item.afterMatch }}%</span></div>
                  <div class="career-gap"><small>待补能力</small><el-tag v-for="skill in item.gaps || []" :key="skill" type="warning" effect="plain">{{ skill }}</el-tag><span v-if="!item.gaps?.length">暂无核心缺口</span></div>
                  <ol><li v-for="step in item.learningPlan" :key="step.skill"><strong>{{ step.skill }}</strong><span>{{ step.time }} · {{ difficultyLabel(step.difficulty) }}</span></li></ol>
                  <p>{{ item.explanation }}</p>
                  <footer>建议项目：{{ item.suggestedProject }}；预计 {{ item.totalTime }}</footer>
                </article>
              </div>
              <div v-else class="empty-result"><div class="empty-orbit"><el-icon><Connection /></el-icon></div><h3>尚未生成 Agent 建议</h3><p>选择人才和目标岗位后运行。刷新页面时，未完成任务和已完成结果都会从当前会话恢复。</p></div>
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

        <el-tab-pane label="企业部门" name="departments">
          <div class="tab-toolbar"><div><h3>企业部门管理</h3><p>统一维护录用、员工目录和内部岗位使用的标准部门。</p></div><el-button type="primary" @click="openCreateDepartment"><el-icon><Plus /></el-icon>新建部门</el-button></div>
          <el-table :data="departments" style="width:100%">
            <el-table-column prop="code" label="部门编号" width="120" />
            <el-table-column prop="name" label="部门名称" min-width="170" />
            <el-table-column prop="manager" label="部门负责人" min-width="140"><template #default="{ row }">{{ row.manager || "待配置" }}</template></el-table-column>
            <el-table-column prop="location" label="办公地点" min-width="130"><template #default="{ row }">{{ row.location || "待配置" }}</template></el-table-column>
            <el-table-column prop="employee_count" label="员工人数" width="100" align="center" />
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "启用" : "停用" }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button type="primary" link @click="openEditDepartment(row)">编辑</el-button><el-button type="danger" link @click="removeDepartment(row)">删除</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="员工目录" name="employees">
          <div class="tab-toolbar"><div><h3>企业员工目录</h3><p>维护企业工号、所属部门、岗位、职级和技能；在人才池中的员工修改后会同步更新。</p></div><el-button type="primary" @click="openCreateEmployee"><el-icon><Plus /></el-icon>新增员工</el-button></div>
          <el-table :data="employees" style="width:100%">
            <el-table-column prop="employee_no" label="工号" width="115" />
            <el-table-column prop="name" label="姓名" width="110" />
            <el-table-column prop="department" label="所属部门" min-width="140" />
            <el-table-column prop="current_position" label="当前岗位" min-width="160" />
            <el-table-column label="职级" width="90"><template #default="{ row }">{{ levelLabel(row.level) }}</template></el-table-column>
            <el-table-column label="技能" min-width="220"><template #default="{ row }"><div class="tag-list"><el-tag v-for="skill in row.skills.slice(0, 4)" :key="skill" size="small" effect="plain">{{ skill }}</el-tag></div></template></el-table-column>
            <el-table-column label="人才池" width="100"><template #default="{ row }"><el-tag :type="row.in_talent_pool ? 'success' : 'info'">{{ row.in_talent_pool ? "已加入" : "未加入" }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="150" fixed="right"><template #default="{ row }"><el-button type="primary" link @click="openEditEmployee(row)">编辑</el-button><el-button type="danger" link :disabled="row.in_talent_pool" @click="removeEmployee(row)">删除</el-button></template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="企业人才池" name="talents">
          <div class="tab-toolbar"><div><h3>企业人才池</h3><p>在职员工可按工号加入；外部候选人须先在人才匹配页确认录用，系统将自动分配工号。</p></div><div class="toolbar-actions"><el-button @click="router.push('/matching')">录用外部候选人</el-button><el-button type="primary" @click="openTalentDialog"><el-icon><Plus /></el-icon>按工号加入在职员工</el-button></div></div>
          <div class="pool-flow"><span>外部候选人</span><i>确认录用</i><span>自动分配工号</span><i>同步员工目录</i><strong>进入企业人才池</strong><em>可参与内部匹配</em></div>
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
          <div class="tab-toolbar"><div><h3>转岗规则</h3><p>支持查看、新建、编辑和删除；启用一条规则时，系统会自动停用原生效规则。</p></div><el-button type="primary" @click="openCreateRule"><el-icon><Plus /></el-icon>新建规则</el-button></div>
          <el-table :data="rules" style="width:100%">
            <el-table-column prop="name" label="规则名称" min-width="180" />
            <el-table-column label="版本" width="80"><template #default="{ row }">v{{ row.version }}</template></el-table-column>
            <el-table-column prop="min_tenure_months" label="最低司龄（月）" width="130" />
            <el-table-column prop="min_position_tenure_months" label="岗位任职（月）" width="130" />
            <el-table-column prop="min_match_score" label="确认阈值" width="100" />
            <el-table-column label="评分权重" min-width="160"><template #default="{ row }">技能 {{ row.skill_weight }}% · 司龄 {{ row.tenure_weight }}%</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === "active" ? "当前生效" : row.status === "draft" ? "草稿" : "历史版本" }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="190" fixed="right"><template #default="{ row }"><el-button type="primary" link @click="viewRule(row.id)">查看</el-button><el-button type="primary" link @click="openEditRule(row)">编辑</el-button><el-button type="danger" link :disabled="row.status === 'active'" @click="removeRule(row)">删除</el-button></template></el-table-column>
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

    <el-dialog v-model="departmentDialog" :title="departmentEditingId ? '编辑企业部门' : '新建企业部门'" width="540px" destroy-on-close>
      <el-form label-position="top"><div class="form-grid"><el-form-item label="部门编号" required><el-input v-model="departmentForm.code" placeholder="例如：D001" /></el-form-item><el-form-item label="部门名称" required><el-input v-model="departmentForm.name" placeholder="例如：平台研发部" @input="handleDepartmentNameChange" /></el-form-item></div><div class="form-grid"><el-form-item label="部门负责人"><el-select v-model="departmentManagerId" filterable remote reserve-keyword clearable :remote-method="searchDepartmentManagers" :loading="departmentManagerLoading" :disabled="!departmentForm.name.trim()" placeholder="输入姓名或工号检索本部门人员" style="width:100%" @change="selectDepartmentManager"><el-option v-for="employee in departmentManagerOptions" :key="employee.id" :label="`${employee.name} · ${employee.employee_no}`" :value="Number(employee.id)"><span>{{ employee.name }}</span><small class="manager-option-meta">{{ employee.employee_no }} · {{ employee.department }}</small></el-option></el-select></el-form-item><el-form-item label="办公地点"><el-input v-model="departmentForm.location" /></el-form-item></div><div class="manager-selection-note">负责人候选仅显示“{{ departmentForm.name.trim() || '当前部门' }}”的在职员工，可输入姓名或工号快速匹配。</div><el-form-item label="状态"><el-select v-model="departmentForm.status" style="width:100%"><el-option label="启用" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item></el-form>
      <template #footer><el-button @click="departmentDialog = false">取消</el-button><el-button type="primary" :loading="masterDataSaving" @click="saveDepartment">保存部门</el-button></template>
    </el-dialog>

    <el-dialog v-model="employeeDialog" :title="employeeEditingId ? '编辑员工资料' : '新增企业员工'" width="680px" destroy-on-close>
      <el-form label-position="top"><div class="form-grid"><el-form-item label="工号" required><el-input v-model="employeeForm.employee_no" /></el-form-item><el-form-item label="姓名" required><el-input v-model="employeeForm.name" /></el-form-item></div><div class="form-grid"><el-form-item label="所属部门" required><el-select v-model="employeeForm.department" filterable style="width:100%"><el-option v-for="department in activeDepartments" :key="department.id" :label="department.name" :value="department.name" /></el-select></el-form-item><el-form-item label="当前岗位" required><el-input v-model="employeeForm.current_position" /></el-form-item></div><div class="form-grid"><el-form-item label="职级"><el-select v-model="employeeForm.level" style="width:100%"><el-option label="实习生" value="intern" /><el-option label="初级" value="junior" /><el-option label="中级" value="mid" /><el-option label="高级" value="senior" /><el-option label="专家" value="expert" /></el-select></el-form-item><el-form-item label="工作城市"><el-input v-model="employeeForm.location" /></el-form-item></div><div class="form-grid"><el-form-item label="司龄（月）"><el-input-number v-model="employeeForm.tenure_months" :min="0" style="width:100%" /></el-form-item><el-form-item label="当前岗位任职（月）"><el-input-number v-model="employeeForm.position_tenure_months" :min="0" style="width:100%" /></el-form-item></div><el-form-item label="技能（使用逗号或顿号分隔）"><el-input v-model="employeeSkillsText" type="textarea" :rows="3" placeholder="Java、Spring Boot、MySQL" /></el-form-item><el-form-item label="状态"><el-select v-model="employeeForm.status" style="width:100%"><el-option label="在职" value="active" /><el-option label="停用" value="inactive" /></el-select></el-form-item></el-form>
      <template #footer><el-button @click="employeeDialog = false">取消</el-button><el-button type="primary" :loading="masterDataSaving" @click="saveEmployee">保存员工资料</el-button></template>
    </el-dialog>

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
        <dl><div><dt>当前部门</dt><dd>{{ selectedEmployee.department }}</dd></div><div><dt>当前岗位</dt><dd>{{ selectedEmployee.current_position }}</dd></div><div><dt>职级</dt><dd>{{ levelLabel(selectedEmployee.level) }}</dd></div><div><dt>司龄 / 任职</dt><dd>{{ selectedEmployee.tenure_months }} / {{ selectedEmployee.position_tenure_months }} 个月</dd></div></dl>
        <div class="tag-list"><el-tag v-for="skill in selectedEmployee.skills" :key="skill" size="small" effect="plain">{{ skill }}</el-tag></div>
      </div>
      <el-empty v-else-if="directorySearched && !directoryLoading && directoryOptions.length === 0" description="企业员工目录暂无匹配，请先通过 HR 同步接口导入主数据" :image-size="70" />
      <template #footer><el-button @click="talentDialog = false">取消</el-button><el-button type="primary" :disabled="!selectedEmployee || selectedEmployee.in_talent_pool" :loading="addingTalent" @click="createTalentFromDirectory">加入人才池</el-button></template>
    </el-dialog>

    <el-dialog v-model="ruleDialog" :title="ruleEditingId ? '编辑转岗规则' : '新建转岗规则'" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="规则名称"><el-input v-model="ruleForm.name" /></el-form-item>
        <div class="form-grid"><el-form-item label="最低司龄（月）"><el-input-number v-model="ruleForm.min_tenure_months" :min="0" style="width:100%" /></el-form-item><el-form-item label="最低岗位任职（月）"><el-input-number v-model="ruleForm.min_position_tenure_months" :min="0" style="width:100%" /></el-form-item></div>
        <div class="form-grid"><el-form-item label="最低匹配分"><el-input-number v-model="ruleForm.min_match_score" :min="0" :max="100" style="width:100%" /></el-form-item><el-form-item label="状态"><el-select v-model="ruleForm.status" style="width:100%"><el-option label="立即生效" value="active" /><el-option label="保存草稿" value="draft" /></el-select></el-form-item></div>
        <el-form-item label="技能权重"><el-slider v-model="ruleForm.skill_weight" :min="0" :max="100" show-input /></el-form-item>
        <el-alert :title="`司龄权重自动设为 ${100 - ruleForm.skill_weight}%`" type="info" :closable="false" />
      </el-form>
      <template #footer><el-button @click="ruleDialog = false">取消</el-button><el-button type="primary" :loading="savingRule" @click="saveRule">{{ ruleEditingId ? '保存修改' : '创建规则' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="ruleDetailDialog" title="转岗规则详情" width="560px">
      <el-descriptions v-if="ruleDetail" :column="2" border><el-descriptions-item label="规则名称" :span="2">{{ ruleDetail.name }}</el-descriptions-item><el-descriptions-item label="版本">v{{ ruleDetail.version }}</el-descriptions-item><el-descriptions-item label="状态">{{ ruleStatusLabel(ruleDetail.status) }}</el-descriptions-item><el-descriptions-item label="最低司龄">{{ ruleDetail.min_tenure_months }} 个月</el-descriptions-item><el-descriptions-item label="岗位任职">{{ ruleDetail.min_position_tenure_months }} 个月</el-descriptions-item><el-descriptions-item label="确认阈值">{{ ruleDetail.min_match_score }} 分</el-descriptions-item><el-descriptions-item label="评分权重">技能 {{ ruleDetail.skill_weight }}% · 司龄 {{ ruleDetail.tenure_weight }}%</el-descriptions-item><el-descriptions-item label="最后更新" :span="2">{{ formatDate(ruleDetail.updated_at) }}</el-descriptions-item></el-descriptions>
      <template #footer><el-button type="primary" @click="ruleDetailDialog = false">关闭</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowRight, Connection, InfoFilled, Plus, Refresh } from "@element-plus/icons-vue";
import DataState from "@/components/common/DataState.vue";
import { dataProvider } from "@/data";
import { levelLabel } from "@/utils/displayLabels";
import { useCareerStore } from "@/stores/career";
import type { EnterpriseDepartment, EnterpriseEmployeeDirectory, EnterpriseTalent, InternalMatchResult, InternalPosition, SkillDemandSummary, TransferDecision, TransferRuleSet } from "@/domain/types";

const route = useRoute();
const router = useRouter();
const availableTabs = new Set(["analysis", "agent", "positions", "departments", "employees", "talents", "demands", "rules", "decisions"]);
const requestedTab = typeof route.query.tab === "string" ? route.query.tab : "analysis";
const activeTab = ref(availableTabs.has(requestedTab) ? requestedTab : "analysis");
const loading = ref(false);
const matching = ref(false);
const error = ref("");
const talents = ref<EnterpriseTalent[]>([]);
const departments = ref<EnterpriseDepartment[]>([]);
const employees = ref<EnterpriseEmployeeDirectory[]>([]);
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
const ruleDetailDialog = ref(false);
const ruleDetail = ref<TransferRuleSet | null>(null);
const ruleEditingId = ref<number>();
const savingRule = ref(false);
const directoryOptions = ref<EnterpriseEmployeeDirectory[]>([]);
const selectedEmployeeId = ref<number>();
const selectedEmployee = ref<EnterpriseEmployeeDirectory | null>(null);
const directoryLoading = ref(false);
const directorySearched = ref(false);
const addingTalent = ref(false);
const departmentDialog = ref(false);
const departmentEditingId = ref<number>();
const departmentManagerId = ref<number>();
const departmentManagerOptions = ref<EnterpriseEmployeeDirectory[]>([]);
const selectedDepartmentManager = ref<EnterpriseEmployeeDirectory | null>(null);
const departmentManagerLoading = ref(false);
const employeeDialog = ref(false);
const employeeEditingId = ref<number>();
const employeeSkillsText = ref("");
const masterDataSaving = ref(false);
const careerStore = useCareerStore();
const {
  data: careerRecommendations,
  loading: careerLoading,
  error: careerError,
  agentStatus: careerAgentStatus,
  agentRunId: careerAgentRunId,
} = storeToRefs(careerStore);
const careerTalentId = ref<number>();
const careerTargetIds = ref<number[]>([]);
const careerExtraSkills = ref("");
const careerEnterpriseTech = ref("");
const careerStages = ["读取人才能力档案", "核对目标岗位要求", "计算能力差距", "生成培养路径", "整理解释与项目建议"];
const careerStageIndex = ref(0);
const careerProgress = ref(0);
const careerStage = computed(() => careerStages[careerStageIndex.value]);
let careerProgressTimer: ReturnType<typeof setInterval> | undefined;

const activeTalents = computed(() => talents.value.filter((item) => item.status === "active"));
const activeRules = computed(() => rules.value.filter((item) => item.status === "active"));
const activeTalentCount = computed(() => activeTalents.value.length);
const openPositions = computed(() => positions.value.filter((item) => item.status === "open"));
const openHeadcount = computed(() => openPositions.value.reduce((sum, item) => sum + item.headcount, 0));
const criticalDemandCount = computed(() => skillDemands.value.filter((item) => item.gap > 0).length);
const activeDepartments = computed(() => departments.value.filter((item) => item.status === "active"));

const ruleForm = reactive({ name: "企业内部转岗规则", min_tenure_months: 12, min_position_tenure_months: 6, min_match_score: 70, skill_weight: 85, status: "active" as "active" | "draft" | "inactive" });
const departmentForm = reactive({ code: "", name: "", location: "", status: "active" as "active" | "inactive" });
const employeeForm = reactive({ employee_no: "", name: "", department: "", current_position: "", level: "mid", location: "", tenure_months: 0, position_tenure_months: 0, status: "active" as "active" | "inactive", source: "manual", skills: [] as string[], project_highlights: [] as string[] });

onMounted(async () => {
  const positionId = Number(route.query.positionId);
  if (Number.isFinite(positionId) && positionId > 0) selectedPositionId.value = positionId;
  await loadAll();
  await careerStore.restore();
});

async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    [talents.value, positions.value, departments.value, employees.value, skillDemands.value, rules.value, decisions.value] = await Promise.all([
      dataProvider.internalTransfer.listTalents(), dataProvider.internalTransfer.listPositions(), dataProvider.internalTransfer.listDepartments(), dataProvider.internalTransfer.searchEmployeeDirectory(""), dataProvider.internalTransfer.listSkillDemands(), dataProvider.internalTransfer.listRuleSets(), dataProvider.internalTransfer.listDecisions(),
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

function currentDepartmentEmployeeOptions(items: EnterpriseEmployeeDirectory[]) {
  const departmentName = departmentForm.name.trim();
  if (!departmentName) return [];
  return items.filter((item) => item.status === "active" && item.department.trim() === departmentName);
}

function mergeManagerOptions(items: EnterpriseEmployeeDirectory[]) {
  const merged = selectedDepartmentManager.value ? [selectedDepartmentManager.value, ...items] : items;
  departmentManagerOptions.value = Array.from(new Map(merged.map((item) => [Number(item.id), item])).values());
}

async function searchDepartmentManagers(keyword: string) {
  const departmentName = departmentForm.name.trim();
  if (!departmentName) {
    departmentManagerOptions.value = [];
    return;
  }
  departmentManagerLoading.value = true;
  try {
    mergeManagerOptions(currentDepartmentEmployeeOptions(
      await dataProvider.internalTransfer.searchEmployeeDirectory(keyword.trim(), departmentName),
    ));
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "企业员工检索失败");
  } finally {
    departmentManagerLoading.value = false;
  }
}

function selectDepartmentManager(employeeId?: number) {
  if (!employeeId) {
    selectedDepartmentManager.value = null;
    return;
  }
  selectedDepartmentManager.value = departmentManagerOptions.value.find((item) => Number(item.id) === employeeId)
    || currentDepartmentEmployeeOptions(employees.value).find((item) => Number(item.id) === employeeId)
    || null;
}

function handleDepartmentNameChange() {
  const departmentName = departmentForm.name.trim();
  if (selectedDepartmentManager.value?.department.trim() !== departmentName) {
    selectedDepartmentManager.value = null;
    departmentManagerId.value = undefined;
  }
  mergeManagerOptions(currentDepartmentEmployeeOptions(employees.value));
}

function openCreateDepartment() {
  departmentEditingId.value = undefined;
  const nextCode = `D${String(departments.value.length + 1).padStart(3, "0")}`;
  Object.assign(departmentForm, { code: nextCode, name: "", location: "", status: "active" });
  departmentManagerId.value = undefined;
  selectedDepartmentManager.value = null;
  mergeManagerOptions(currentDepartmentEmployeeOptions(employees.value));
  departmentDialog.value = true;
}

async function openEditDepartment(department: EnterpriseDepartment) {
  departmentEditingId.value = Number(department.id);
  Object.assign(departmentForm, { code: department.code, name: department.name, location: department.location || "", status: department.status });
  let manager = department.manager
    ? currentDepartmentEmployeeOptions(employees.value).find((item) => item.name === department.manager) || null
    : null;
  selectedDepartmentManager.value = manager;
  departmentManagerId.value = manager ? Number(manager.id) : undefined;
  mergeManagerOptions(currentDepartmentEmployeeOptions(employees.value));
  departmentDialog.value = true;
  if (department.manager && !manager) {
    await searchDepartmentManagers(department.manager);
    manager = departmentManagerOptions.value.find((item) => item.name === department.manager) || null;
    selectedDepartmentManager.value = manager;
    departmentManagerId.value = manager ? Number(manager.id) : undefined;
    mergeManagerOptions(departmentManagerOptions.value);
  }
}

async function saveDepartment() {
  if (!departmentForm.code.trim() || !departmentForm.name.trim()) return ElMessage.warning("请填写部门编号和名称");
  masterDataSaving.value = true;
  try {
    const payload = { ...departmentForm, code: departmentForm.code.trim(), name: departmentForm.name.trim(), manager: selectedDepartmentManager.value?.name || null, location: departmentForm.location.trim() || null };
    if (departmentEditingId.value) await dataProvider.internalTransfer.updateDepartment(departmentEditingId.value, payload);
    else await dataProvider.internalTransfer.createDepartment(payload);
    departmentDialog.value = false;
    await loadAll();
    ElMessage.success(departmentEditingId.value ? "部门资料已更新" : "企业部门已创建");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "部门资料保存失败");
  } finally { masterDataSaving.value = false; }
}

async function removeDepartment(department: EnterpriseDepartment) {
  try {
    await ElMessageBox.confirm(`确认删除部门“${department.name}”吗？有关联数据时系统会阻止删除。`, "删除企业部门", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" });
    await dataProvider.internalTransfer.removeDepartment(Number(department.id));
    await loadAll();
    ElMessage.success("部门已删除");
  } catch (exception) {
    if (exception === "cancel" || exception === "close") return;
    ElMessage.error(exception instanceof Error ? exception.message : "部门删除失败");
  }
}

function resetEmployeeForm() {
  Object.assign(employeeForm, { employee_no: "", name: "", department: activeDepartments.value[0]?.name || "", current_position: "", level: "mid", location: "", tenure_months: 0, position_tenure_months: 0, status: "active", source: "manual", skills: [], project_highlights: [] });
  employeeSkillsText.value = "";
}

function openCreateEmployee() {
  employeeEditingId.value = undefined;
  resetEmployeeForm();
  employeeDialog.value = true;
}

function openEditEmployee(employee: EnterpriseEmployeeDirectory) {
  employeeEditingId.value = Number(employee.id);
  Object.assign(employeeForm, { employee_no: employee.employee_no, name: employee.name, department: employee.department, current_position: employee.current_position, level: employee.level, location: employee.location || "", tenure_months: employee.tenure_months, position_tenure_months: employee.position_tenure_months, status: employee.status, source: employee.source, skills: employee.skills, project_highlights: employee.project_highlights });
  employeeSkillsText.value = employee.skills.join("、");
  employeeDialog.value = true;
}

async function saveEmployee() {
  if (!employeeForm.employee_no.trim() || !employeeForm.name.trim() || !employeeForm.department || !employeeForm.current_position.trim()) return ElMessage.warning("请完整填写工号、姓名、部门和岗位");
  masterDataSaving.value = true;
  try {
    const payload = { ...employeeForm, employee_no: employeeForm.employee_no.trim(), name: employeeForm.name.trim(), current_position: employeeForm.current_position.trim(), location: employeeForm.location.trim() || null, skills: employeeSkillsText.value.split(/[、,，;；]/).map((item) => item.trim()).filter(Boolean) };
    if (employeeEditingId.value) await dataProvider.internalTransfer.updateEmployee(employeeEditingId.value, payload);
    else await dataProvider.internalTransfer.createEmployee(payload);
    employeeDialog.value = false;
    await loadAll();
    ElMessage.success(employeeEditingId.value ? "员工资料已更新" : "企业员工已新增");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "员工资料保存失败");
  } finally { masterDataSaving.value = false; }
}

async function removeEmployee(employee: EnterpriseEmployeeDirectory) {
  try {
    await ElMessageBox.confirm(`确认从员工目录删除“${employee.name}（${employee.employee_no}）”吗？`, "删除员工", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" });
    await dataProvider.internalTransfer.removeEmployee(Number(employee.id));
    await loadAll();
    ElMessage.success("员工目录记录已删除");
  } catch (exception) {
    if (exception === "cancel" || exception === "close") return;
    ElMessage.error(exception instanceof Error ? exception.message : "员工删除失败");
  }
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

async function runCareerAgent() {
  const talent = talents.value.find((item) => Number(item.id) === careerTalentId.value);
  if (!talent) return ElMessage.warning("请先选择企业人才");
  const targetIds = careerTargetIds.value.length
    ? careerTargetIds.value
    : openPositions.value.map((item) => Number(item.id));
  const targetJobs = openPositions.value
    .filter((item) => targetIds.includes(Number(item.id)))
    .map((item) => item.title);
  careerStageIndex.value = 0;
  careerProgress.value = 8;
  if (careerProgressTimer) clearInterval(careerProgressTimer);
  careerProgressTimer = setInterval(() => {
    careerProgress.value = Math.min(92, careerProgress.value + (careerProgress.value < 60 ? 5 : 2));
    careerStageIndex.value = Math.min(careerStages.length - 1, Math.floor(careerProgress.value / 20));
  }, 550);
  try {
    await careerStore.analyze({
      skillText: [...talent.skills, careerExtraSkills.value].filter(Boolean).join("、"),
      enterpriseTech: careerEnterpriseTech.value,
      enterpriseJobs: targetJobs,
      targetJobIds: targetIds,
    });
    careerProgress.value = 100;
    careerStageIndex.value = careerStages.length - 1;
    if (careerStore.error) ElMessage.error(careerStore.error);
  } finally {
    if (careerProgressTimer) clearInterval(careerProgressTimer);
    careerProgressTimer = undefined;
  }
}

function difficultyLabel(value: string) {
  const labels: Record<string, string> = { easy: "简单", medium: "中等", hard: "较难" };
  return labels[value.trim().toLowerCase()] || value;
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

function resetRuleForm() {
  Object.assign(ruleForm, { name: "企业内部转岗规则", min_tenure_months: 12, min_position_tenure_months: 6, min_match_score: 70, skill_weight: 85, status: "active" });
}

function openCreateRule() {
  ruleEditingId.value = undefined;
  resetRuleForm();
  ruleDialog.value = true;
}

function openEditRule(rule: TransferRuleSet) {
  ruleEditingId.value = Number(rule.id);
  Object.assign(ruleForm, {
    name: rule.name,
    min_tenure_months: rule.min_tenure_months,
    min_position_tenure_months: rule.min_position_tenure_months,
    min_match_score: rule.min_match_score,
    skill_weight: rule.skill_weight,
    status: rule.status,
  });
  ruleDialog.value = true;
}

async function viewRule(id: number | string) {
  try {
    ruleDetail.value = await dataProvider.internalTransfer.getRuleSet(Number(id));
    ruleDetailDialog.value = true;
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "规则详情加载失败");
  }
}

function ruleStatusLabel(status: TransferRuleSet["status"]) {
  return status === "active" ? "当前生效" : status === "draft" ? "草稿" : "历史版本";
}

async function saveRule() {
  if (!ruleForm.name.trim()) return ElMessage.warning("请填写规则名称");
  savingRule.value = true;
  try {
    const payload = { ...ruleForm, tenure_weight: 100 - ruleForm.skill_weight };
    if (ruleEditingId.value) await dataProvider.internalTransfer.updateRuleSet(ruleEditingId.value, payload);
    else await dataProvider.internalTransfer.createRuleSet(payload);
    ruleDialog.value = false;
    await loadAll();
    ElMessage.success(ruleEditingId.value ? "转岗规则已更新" : ruleForm.status === "active" ? "新规则已生效" : "规则草稿已保存");
  } catch (exception) {
    ElMessage.error(exception instanceof Error ? exception.message : "规则保存失败");
  } finally {
    savingRule.value = false;
  }
}

async function removeRule(rule: TransferRuleSet) {
  try {
    await ElMessageBox.confirm(`确认删除“${rule.name} v${rule.version}”吗？`, "删除转岗规则", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" });
    await dataProvider.internalTransfer.removeRuleSet(Number(rule.id));
    await loadAll();
    ElMessage.success("转岗规则已删除");
  } catch (exception) {
    if (exception === "cancel" || exception === "close") return;
    ElMessage.error(exception instanceof Error ? exception.message : "规则删除失败");
  }
}

function scoreColor(score: number) { return score >= 80 ? "#34b37e" : score >= 60 ? "#4f6ef6" : "#e85d5d"; }
function formatDate(value: string) { return new Date(value).toLocaleString("zh-CN", { hour12: false }); }
onBeforeUnmount(() => { if (careerProgressTimer) clearInterval(careerProgressTimer); });
</script>

<style scoped>
.transfer-page{display:flex;flex-direction:column;gap:16px}.transfer-hero{display:flex;align-items:center;justify-content:space-between;gap:28px;padding:26px 30px;border-radius:16px;background:linear-gradient(118deg,#172033 0%,#243457 64%,#34314d 100%);color:#fff;box-shadow:0 14px 34px rgba(23,32,51,.16)}.hero-eyebrow{color:#9fb2ff;font-family:"JetBrains Mono",monospace;font-size:10px;font-weight:700;letter-spacing:.11em}.transfer-hero h1{margin:7px 0 5px;font-size:27px;letter-spacing:-.03em}.transfer-hero p{max-width:730px;margin:0;color:#cbd3e4;font-size:13px;line-height:1.7}.hero-security{display:flex;align-items:center;gap:11px;min-width:210px;padding:12px 15px;border:1px solid rgba(255,255,255,.13);border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;color:#cbd3e4}.hero-security .el-icon{font-size:22px;color:#f1b963}.hero-security strong{color:#fff}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric-grid article{position:relative;overflow:hidden;padding:18px 20px;border:1px solid var(--border-color);border-radius:14px;background:var(--bg-card)}.metric-grid article:after{position:absolute;right:-15px;bottom:-25px;width:70px;height:70px;border-radius:50%;background:#edf1ff;content:""}.metric-grid article.amber:after{background:#fff0d5}.metric-grid article.green:after{background:#e8f7f0}.metric-label{display:block;color:var(--text-muted);font-size:12px}.metric-grid strong{position:relative;z-index:1;display:block;margin:5px 0 1px;font-size:27px}.metric-grid small{color:var(--text-secondary);font-size:11px}.transfer-workbench{overflow:hidden}.transfer-tabs :deep(.el-tabs__header){margin:0;padding:0 22px;border-bottom:1px solid var(--border-color)}.transfer-tabs :deep(.el-tabs__nav-wrap:after){display:none}.transfer-tabs :deep(.el-tab-pane){padding:0 22px 22px}.analysis-layout{display:grid;grid-template-columns:310px minmax(0,1fr);gap:0;min-height:560px}.analysis-control{padding:25px 22px 22px 0;border-right:1px solid var(--border-color)}.section-heading{display:flex;gap:12px;margin-bottom:20px}.section-heading>span{display:grid;place-items:center;width:31px;height:31px;border-radius:9px;background:var(--color-brand);color:#fff;font-family:"JetBrains Mono",monospace;font-size:11px}.section-heading h3,.results-head h3,.tab-toolbar h3{margin:0;color:var(--text-primary);font-size:16px}.section-heading p,.tab-toolbar p{margin:4px 0 0;color:var(--text-muted);font-size:12px;line-height:1.55}.mode-switch{display:flex;width:100%;margin-bottom:20px}.mode-switch :deep(.el-radio-button){flex:1}.mode-switch :deep(.el-radio-button__inner){width:100%}.analysis-form{padding:15px;border-radius:12px;background:var(--bg-page)}.analyze-button{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;height:42px;margin-top:14px;border:0;border-radius:10px;background:var(--color-brand);color:#fff;font-weight:600;cursor:pointer}.analyze-button:disabled{opacity:.65;cursor:not-allowed}.policy-note{display:flex;align-items:flex-start;gap:7px;margin-top:13px;color:var(--text-muted);font-size:11px;line-height:1.55}.policy-note .el-icon{margin-top:2px;color:var(--color-brand);flex:0 0 auto}.analysis-results{min-width:0;padding:25px 0 0 22px}.results-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.results-kicker{display:block;margin-bottom:3px;color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-size:9px;font-weight:700;letter-spacing:.1em}.result-count{padding:5px 9px;border-radius:8px;background:var(--color-brand-light);color:var(--color-brand);font-family:"JetBrains Mono",monospace;font-size:11px}.empty-result{display:flex;align-items:center;flex-direction:column;justify-content:center;height:430px;border:1px dashed var(--border-color);border-radius:14px;background:linear-gradient(180deg,var(--bg-page),transparent);text-align:center}.empty-orbit{display:grid;place-items:center;width:70px;height:70px;border:1px solid #dce3ff;border-radius:50%;background:#f3f5ff;color:var(--color-brand);font-size:28px;box-shadow:0 0 0 12px rgba(79,110,246,.04)}.empty-result h3{margin:20px 0 6px;font-size:15px}.empty-result p{max-width:410px;margin:0;color:var(--text-muted);font-size:12px;line-height:1.7}.pair-cell{display:flex;flex-direction:column}.pair-cell strong{font-size:13px}.pair-cell small{margin-top:2px;color:var(--text-muted)}.pair-cell span{display:flex;align-items:center;gap:4px;margin-top:7px;color:var(--color-brand);font-size:12px}.reject-reason{display:block;margin-top:6px;color:var(--color-danger);font-size:10px;line-height:1.35}.score-cell strong{display:block;margin-bottom:5px;font-family:"JetBrains Mono",monospace;font-size:18px}.gap-cell{display:flex;gap:4px;flex-wrap:wrap}.gap-cell span{padding:2px 6px;border-radius:5px;background:#fff0ef;color:#c34848;font-size:10px}.gap-cell small{color:var(--color-success)}.gap-cell em{display:block;width:100%;margin-top:4px;color:var(--text-muted);font-size:10px;font-style:normal}.tab-toolbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:20px 0 16px}.tag-list{display:flex;gap:5px;flex-wrap:wrap}.gap-number{font-family:"JetBrains Mono",monospace}.gap-number.critical{color:var(--color-danger)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:1100px){.metric-grid{grid-template-columns:repeat(2,1fr)}.analysis-layout{grid-template-columns:1fr}.analysis-control{padding-right:0;border-right:0;border-bottom:1px solid var(--border-color)}.analysis-results{padding-left:0}}@media(max-width:720px){.transfer-hero{align-items:flex-start;flex-direction:column}.hero-security{width:100%}.metric-grid{grid-template-columns:1fr 1fr}.form-grid{grid-template-columns:1fr}.transfer-tabs :deep(.el-tab-pane){padding:0 12px 16px}.transfer-tabs :deep(.el-tabs__header){padding:0 12px}}
.metric-card{position:relative;overflow:hidden;padding:17px 19px;border:1px solid var(--border-color);border-radius:13px;background:var(--bg-card);color:var(--text-primary);font:inherit;text-align:left;cursor:pointer;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease}.metric-card:after{position:absolute;right:-15px;bottom:-25px;width:70px;height:70px;border-radius:50%;background:#edf1ff;content:""}.metric-card.amber:after{background:#fff0d5}.metric-card.green:after{background:#e8f7f0}.metric-card:hover{z-index:1;border-color:var(--color-brand);box-shadow:0 9px 25px rgba(40,59,112,.1);transform:translateY(-2px)}.metric-card strong{position:relative;z-index:1;display:block;margin:4px 0 1px;font-family:"JetBrains Mono",monospace;font-size:27px}.metric-card small{display:block;color:var(--text-secondary);font-size:11px}.metric-card em{position:relative;z-index:1;display:flex;align-items:center;gap:3px;margin-top:11px;color:var(--color-brand);font-size:11px;font-style:normal;font-weight:600}.manager-option-meta{float:right;margin-left:14px;color:var(--text-muted);font-size:11px}.manager-selection-note{margin:-9px 0 15px;color:var(--text-muted);font-size:11px;line-height:1.5}.directory-search-note{margin-bottom:16px;padding:10px 12px;border-left:3px solid var(--color-brand);background:var(--color-brand-light);color:var(--text-secondary);font-size:12px;line-height:1.6}.employee-option{display:flex;align-items:center;gap:10px;width:100%}.employee-option strong{min-width:72px;color:var(--text-primary);font-family:"JetBrains Mono",monospace}.employee-option span{overflow:hidden;color:var(--text-secondary);text-overflow:ellipsis;white-space:nowrap}.employee-option em{margin-left:auto;color:var(--text-muted);font-size:11px;font-style:normal}.employee-preview{padding:16px;border:1px solid #dce3ff;border-radius:12px;background:linear-gradient(145deg,#fafbff,#f3f6ff)}.employee-preview-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.employee-preview-head span{font-size:17px;font-weight:700}.employee-preview-head strong{color:var(--color-brand);font-family:"JetBrains Mono",monospace}.employee-preview dl{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 13px}.employee-preview dl div{padding:9px 10px;border-radius:8px;background:rgba(255,255,255,.72)}.employee-preview dt{color:var(--text-muted);font-size:10px}.employee-preview dd{margin:3px 0 0;color:var(--text-primary);font-size:12px;font-weight:600}
.career-agent-layout{display:grid;grid-template-columns:330px minmax(0,1fr);min-height:560px}.career-agent-form{padding:25px 22px 22px 0;border-right:1px solid var(--border-color)}.career-agent-results{padding:25px 0 0 22px}.career-run-id{margin-top:10px;color:var(--text-muted);font:10px var(--font-mono);word-break:break-all}.career-recommendations{display:grid;gap:12px;margin-top:12px}.career-recommendation{padding:17px;border:1px solid var(--border-color);border-radius:13px;background:var(--bg-card)}.career-recommendation header{display:flex;align-items:flex-start;justify-content:space-between}.career-recommendation header span{color:var(--color-brand);font-size:10px;font-weight:700}.career-recommendation header h3{margin:3px 0 0}.career-recommendation header>strong{font:700 22px var(--font-mono);color:var(--color-brand)}.career-score-row{display:flex;gap:8px;margin:12px 0}.career-score-row span{padding:5px 8px;border-radius:7px;background:var(--color-brand-light);font-size:11px}.career-gap{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.career-gap small{margin-right:4px;color:var(--text-muted)}.career-recommendation ol{display:grid;gap:5px;margin:12px 0;padding-left:22px}.career-recommendation li span{margin-left:8px;color:var(--text-muted);font-size:11px}.career-recommendation p,.career-recommendation footer{color:var(--text-secondary);font-size:12px;line-height:1.6}.career-recommendation footer{margin-top:8px;padding-top:8px;border-top:1px solid var(--border-color)}@media(max-width:1100px){.career-agent-layout{grid-template-columns:1fr}.career-agent-form{padding-right:0;border-right:0;border-bottom:1px solid var(--border-color)}.career-agent-results{padding-left:0}}
.career-agent-results{height:620px;min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-gutter:stable;padding-right:10px;padding-bottom:20px}.career-recommendation{padding:20px}.career-recommendation header span{font-size:12px}.career-recommendation header h3{font-size:20px}.career-recommendation header>strong{font-size:25px}.career-score-row span,.career-gap,.career-recommendation ol{font-size:14px}.career-recommendation ol{gap:9px}.career-recommendation li span{font-size:13px}.career-recommendation p,.career-recommendation footer{font-size:14px;line-height:1.8}.career-streaming-state{margin-top:10px;padding:22px;border:1px solid #d9e1ff;border-radius:14px;background:linear-gradient(145deg,#f6f8ff,#fff)}.career-streaming-head{display:flex;align-items:center;gap:11px;margin-bottom:16px}.career-streaming-head>div{display:flex;min-width:0;flex:1;flex-direction:column}.career-streaming-head strong{font-size:16px}.career-streaming-head small{margin-top:3px;color:var(--text-muted);font-size:12px}.career-streaming-head b{color:var(--color-brand);font:700 20px var(--font-mono)}.streaming-pulse{width:9px;height:9px;border-radius:50%;background:var(--color-brand);box-shadow:0 0 0 0 rgba(79,110,246,.4);animation:streaming-pulse 1.4s infinite}.career-stage-list{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin-top:17px}.career-stage-list span{color:var(--text-muted);font-size:11px}.career-stage-list span.active{color:var(--color-brand);font-weight:700}.career-streaming-preview{display:grid;gap:9px;margin-top:24px;padding:18px;border-radius:12px;background:var(--color-bg-muted)}.career-streaming-preview i{display:block;width:90%;height:10px;border-radius:999px;background:linear-gradient(90deg,#e5e9f5 20%,#f6f8ff 45%,#e5e9f5 70%);background-size:200% 100%;animation:streaming-shimmer 1.4s linear infinite}.career-streaming-preview i:nth-child(2){width:72%}.career-streaming-preview i:nth-child(3){width:84%}.career-streaming-preview i:nth-child(4){width:55%}@keyframes streaming-pulse{70%{box-shadow:0 0 0 8px rgba(79,110,246,0)}}@keyframes streaming-shimmer{to{background-position:-200% 0}}@media(max-width:1100px){.career-agent-results{height:600px;padding-left:0}.career-stage-list{grid-template-columns:1fr 1fr}}
.toolbar-actions{display:flex;align-items:center;gap:9px;flex-wrap:wrap;justify-content:flex-end}.pool-flow{display:flex;align-items:center;gap:8px;margin-bottom:16px;padding:12px 14px;border:1px solid #dce4ff;border-radius:10px;background:linear-gradient(90deg,#f7f9ff,#fff);color:var(--text-secondary);font-size:12px}.pool-flow span,.pool-flow strong{padding:4px 8px;border-radius:6px;background:#fff;box-shadow:0 1px 4px rgba(40,59,112,.08)}.pool-flow strong{color:var(--color-brand)}.pool-flow i{color:var(--text-muted);font-size:10px;font-style:normal}.pool-flow i:after{margin-left:8px;content:'→';color:#8ea3f7}.pool-flow em{margin-left:auto;color:var(--color-success);font-size:11px;font-style:normal;font-weight:700}@media(max-width:850px){.pool-flow{align-items:flex-start;flex-direction:column}.pool-flow i:after{content:'↓'}.pool-flow em{margin-left:0}.tab-toolbar{align-items:flex-start;flex-direction:column}.toolbar-actions{justify-content:flex-start}}
</style>
