<template>
  <div>
    <div class="page-header">
      <h1>首页仪表盘</h1>
      <p>IT 岗位人才洞察平台 · 数据驱动决策</p>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card anim-fade-up anim-delay-1">
        <div class="stat-icon-box blue"><el-icon><Briefcase /></el-icon></div>
        <div class="stat-body">
          <div class="stat-value">1,286</div>
          <div class="stat-label">岗位总数</div>
          <div class="stat-change up">+12.5% ↑</div>
        </div>
      </div>
      <div class="stat-card anim-fade-up anim-delay-2">
        <div class="stat-icon-box green"><el-icon><Collection /></el-icon></div>
        <div class="stat-body">
          <div class="stat-value">347</div>
          <div class="stat-label">技能标签</div>
          <div class="stat-change up">+8.3% ↑</div>
        </div>
      </div>
      <div class="stat-card anim-fade-up anim-delay-3">
        <div class="stat-icon-box amber"><el-icon><TrendCharts /></el-icon></div>
        <div class="stat-body">
          <div class="stat-value">126</div>
          <div class="stat-label">本周新增岗位</div>
          <div class="stat-change up">+5.7% ↑</div>
        </div>
      </div>
      <div class="stat-card anim-fade-up anim-delay-4">
        <div class="stat-icon-box indigo"><el-icon><Connection /></el-icon></div>
        <div class="stat-body">
          <div class="stat-value">53</div>
          <div class="stat-label">待处理匹配</div>
          <div class="stat-change down">-2.1% ↓</div>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <!-- Core Flow -->
      <div class="dash-card anim-fade-up anim-delay-1">
        <div class="dash-card-header">
          <span class="dash-card-title">核心流程</span>
          <span class="dash-card-badge">4 个模块</span>
        </div>
        <div class="dash-card-body">
          <div class="flow-steps">
            <div class="flow-step">
              <div class="flow-step-num done">1</div>
              <div class="flow-step-body">
                <h4>新岗位发现</h4>
                <p>多源数据识别新兴岗位，自动生成岗位定义</p>
              </div>
            </div>
            <div class="flow-step">
              <div class="flow-step-num done">2</div>
              <div class="flow-step-body">
                <h4>能力动态更新</h4>
                <p>追踪岗位技能要求变化，标注新增/删除项</p>
              </div>
            </div>
            <div class="flow-step">
              <div class="flow-step-num">3</div>
              <div class="flow-step-body">
                <h4>全景图谱可视化</h4>
                <p>交互式岗位-技能关联网络，技能点级别粒度</p>
              </div>
            </div>
            <div class="flow-step">
              <div class="flow-step-num">4</div>
              <div class="flow-step-body">
                <h4>人岗匹配诊断</h4>
                <p>简历解析 + 多维度匹配 + 差距分析与学习建议</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Entry -->
      <div class="dash-card anim-fade-up anim-delay-2">
        <div class="dash-card-header">
          <span class="dash-card-title">快速入口</span>
          <span class="dash-card-badge">探索模块</span>
        </div>
        <div class="dash-card-body">
          <div class="quick-grid">
            <div class="quick-entry" @click="$router.push('/discover')">
              <div class="quick-icon" style="background:var(--color-brand-light);color:var(--color-brand);">
                <el-icon><Aim /></el-icon>
              </div>
              新岗位发现
            </div>
            <div class="quick-entry" @click="$router.push('/changes')">
              <div class="quick-icon" style="background:var(--color-success-light);color:var(--color-success);">
                <el-icon><Refresh /></el-icon>
              </div>
              能力更新
            </div>
            <div class="quick-entry" @click="$router.push('/graph')">
              <div class="quick-icon" style="background:var(--color-warning-light);color:var(--color-warning);">
                <el-icon><Share /></el-icon>
              </div>
              技能图谱
            </div>
            <div class="quick-entry" @click="$router.push('/matching')">
              <div class="quick-icon" style="background:#ede9fe;color:#7c6ff7;">
                <el-icon><Connection /></el-icon>
              </div>
              匹配诊断
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>
