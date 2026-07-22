<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePositionsStore } from '@/stores/positions'
import { useFavoritesStore } from '@/stores/favorites'
import { useResumeStore } from '@/stores/resume'

const route = useRoute()
const router = useRouter()
const positionsStore = usePositionsStore()
const favoritesStore = useFavoritesStore()
const resumeStore = useResumeStore()
const position = ref<any>(null)
const resumeDialogVisible = ref(false)

const openMatchDialog = () => {
  resumeDialogVisible.value = true
}

const selectResumeAndDiagnose = (resumeId: string) => {
  resumeDialogVisible.value = false
  const posId = route.params.id as string
  router.push(`/diagnosis/${resumeId}?positionId=${posId}&focusPos=true`)
}

onMounted(async () => {
  const id = route.params.id as string
  await Promise.all([
    positionsStore.fetchDetail(id),
    resumeStore.fetchList(),
  ])
  position.value = positionsStore.currentPosition
})

const toggleFav = async () => {
  if (!position.value) return
  const posId = String(position.value.id)
  const faved = favoritesStore.isFavorited('position', posId)
  if (faved) {
    const fav = favoritesStore.allFavorites.find((f: any) => f.item_type === 'position' && f.item_id === posId)
    if (fav) await favoritesStore.remove(fav.id)
  } else {
    await favoritesStore.add({
      item_type: 'position',
      item_id: posId,
      title: position.value.name,
      summary: position.value.summary?.slice(0, 100) || '',
      metadata: {
        position_id: position.value.id,
        name: position.value.name,
        category: position.value.category,
        career_level: position.value.careerLevel,
        salary_range: position.value.salaryRange,
        skills: (position.value.requiredSkills || []).map((s: any) => s.name),
      },
      tags: position.value.techStack || [],
    })
  }
}

const stackLabel = (stack?: string) => {
  const map: Record<string, string> = { ai: 'AI/人工智能', backend: '后端开发', data: '数据', devops: '运维/DevOps' }
  return stack ? map[stack] || stack : ''
}

// 解析数字分条的文本，返回 {label, items}[] 结构
const parseNumberedText = (text: string): { label?: string; items: string[] }[] => {
  if (!text) return []
  // 先按【xxx】分段标题拆分
  const sectionParts = text.split(/(【[^】]+】)/)
  const sections: { label?: string; items: string[] }[] = []

  for (let i = 0; i < sectionParts.length; i++) {
    const part = sectionParts[i]!.trim()
    if (!part) continue
    // 是分段标题
    if (/^【[^】]+】$/.test(part)) {
      continue
    }
    // 获取上一部分是否为标题
    const label = i > 0 && /^【[^】]+】$/.test(sectionParts[i - 1]!.trim())
      ? sectionParts[i - 1]!.trim()
      : undefined

    // 按数字编号拆分：1、 2. 3） 等，去掉原始编号前缀
    const rawItems = part
      .split(/(?=\d+[、.）)．]\s*)/)
      .map(s => s.trim().replace(/^\d+[、.）)．]\s*/, '').trim())
      .filter(s => s.length > 0)

    if (rawItems.length > 1) {
      sections.push({ label, items: rawItems })
    } else if (rawItems.length === 1 && rawItems[0]) {
      // 单条无编号的，尝试按句号拆分短句
      const sentences = rawItems[0].split(/[。；;]/).map(s => s.trim()).filter(s => s.length > 5)
      if (sentences.length >= 2) {
        sections.push({ label, items: sentences.map(s => s + '。') })
      } else {
        sections.push({ label, items: [rawItems[0]] })
      }
    }
  }
  return sections
}

</script>

<template>
  <div class="detail-page" v-if="position">
    <div class="detail-header">
      <div class="header-left">
        <h1>{{ position.name }}</h1>
        <div class="header-meta">
          <el-tag :type="position.category === 'new' ? 'success' : ''" effect="plain">
            {{ position.category === 'new' ? '新兴岗位' : '既有岗位' }}
          </el-tag>
          <span v-if="position.stack" class="meta-text">{{ stackLabel(position.stack) }}</span>
          <span v-if="position.company" class="meta-text">{{ position.company }}</span>
          <span v-if="position.city" class="meta-text">{{ position.city }}</span>
          <span v-if="position.salaryRange" class="meta-text salary">{{ position.salaryRange }}</span>
          <span v-if="position.postedAt" class="meta-text">发布于 {{ position.postedAt }}</span>
        </div>
        <div v-if="position.experience || position.education" class="header-tags">
          <el-tag v-if="position.experience" size="small" effect="plain">{{ position.experience }}</el-tag>
          <el-tag v-if="position.education" size="small" effect="plain">{{ position.education }}</el-tag>
        </div>
      </div>
      <div class="header-actions">
        <el-button
          :type="favoritesStore.isFavorited('position', String(position.id)) ? 'warning' : 'default'"
          :icon="favoritesStore.isFavorited('position', String(position.id)) ? 'StarFilled' : 'Star'"
          @click="toggleFav"
        >
          {{ favoritesStore.isFavorited('position', String(position.id)) ? '已收藏' : '收藏岗位' }}
        </el-button>
        <el-button type="primary" @click="openMatchDialog">
          开始匹配诊断
        </el-button>
      </div>
    </div>

    <div class="detail-body">
      <div class="detail-main">
        <!-- JD 全文 -->
        <el-card v-if="position.jdText" class="section-card">
          <template #header><span class="card-header">岗位详情（JD）</span></template>
          <div v-for="(section, si) in parseNumberedText(position.jdText)" :key="'jd-s'+si" class="item-section">
            <div v-if="section.label" class="item-section-label">{{ section.label }}</div>
            <div class="item-tags">
              <div v-for="(item, ii) in section.items" :key="ii" class="item-tag">
                <span v-if="section.items.length > 1" class="item-num">{{ ii + 1 }}</span>
                <span class="item-text">{{ item }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 职责要求 -->
        <el-card v-if="position.responsibilitiesText" class="section-card">
          <template #header><span class="card-header">岗位职责</span></template>
          <div v-for="(section, si) in parseNumberedText(position.responsibilitiesText)" :key="'resp-s'+si" class="item-section">
            <div v-if="section.label" class="item-section-label">{{ section.label }}</div>
            <div class="item-tags">
              <div v-for="(item, ii) in section.items" :key="ii" class="item-tag">
                <span v-if="section.items.length > 1" class="item-num">{{ ii + 1 }}</span>
                <span class="item-text">{{ item }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 任职要求 -->
        <el-card v-if="position.requirementsText" class="section-card">
          <template #header><span class="card-header">任职要求</span></template>
          <div v-for="(section, si) in parseNumberedText(position.requirementsText)" :key="'req-s'+si" class="item-section">
            <div v-if="section.label" class="item-section-label">{{ section.label }}</div>
            <div class="item-tags">
              <div v-for="(item, ii) in section.items" :key="ii" class="item-tag">
                <span v-if="section.items.length > 1" class="item-num">{{ ii + 1 }}</span>
                <span class="item-text">{{ item }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 技能标签 -->
        <el-card v-if="position.requiredSkills && position.requiredSkills.length > 0" class="section-card">
          <template #header><span class="card-header">相关技能</span></template>
          <div class="skill-group">
            <div v-for="sk in position.requiredSkills" :key="sk.id" class="skill-chip">
              {{ sk.name }}
            </div>
          </div>
        </el-card>
      </div>

      <div class="detail-side">
        <!-- 基本信息 -->
        <el-card class="section-card">
          <template #header><span class="card-header">基本信息</span></template>
          <div class="info-list">
            <div v-if="position.company" class="info-row">
              <span class="info-label">公司</span>
              <span class="info-value">{{ position.company }}</span>
            </div>
            <div v-if="position.city" class="info-row">
              <span class="info-label">城市</span>
              <span class="info-value">{{ position.city }}</span>
            </div>
            <div v-if="position.salaryRange" class="info-row">
              <span class="info-label">薪资</span>
              <span class="info-value salary">{{ position.salaryRange }}</span>
            </div>
            <div v-if="position.experience" class="info-row">
              <span class="info-label">经验要求</span>
              <span class="info-value">{{ position.experience }}</span>
            </div>
            <div v-if="position.education" class="info-row">
              <span class="info-label">学历要求</span>
              <span class="info-value">{{ position.education }}</span>
            </div>
            <div v-if="position.stack" class="info-row">
              <span class="info-label">技术栈</span>
              <span class="info-value">{{ stackLabel(position.stack) }}</span>
            </div>
            <div v-if="position.postedAt" class="info-row">
              <span class="info-label">发布日期</span>
              <span class="info-value">{{ position.postedAt }}</span>
            </div>
          </div>
        </el-card>

        <!-- 学习建议 -->
        <el-card v-if="position.category === 'new'" class="section-card">
          <template #header><span class="card-header">学习建议</span></template>
          <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">该岗位为新兴岗位，可根据必备技能自动推导学习路径</p>
          <el-button type="primary" plain size="default" @click="router.push('/career')">一键生成学习路径</el-button>
        </el-card>
      </div>
    </div>

    <!-- 简历选择对话框 -->
    <el-dialog v-model="resumeDialogVisible" title="选择简历开始匹配诊断" width="480px" top="12vh">
      <div v-if="resumeStore.resumes.length === 0" style="text-align:center;padding:20px;">
        <p style="color:var(--muted);margin-bottom:12px;">暂无简历，请先创建</p>
        <el-button type="primary" @click="router.push('/diagnosis')">去创建简历</el-button>
      </div>
      <div v-else class="resume-picker-list">
        <div
          v-for="r in resumeStore.resumes"
          :key="r.id"
          class="resume-picker-item"
          @click="selectResumeAndDiagnose(r.id)"
        >
          <div class="picker-left">
            <el-icon :size="20"><Document /></el-icon>
            <span class="picker-name">{{ r.name }}</span>
          </div>
          <el-icon :size="16" color="var(--brand)"><ArrowRight /></el-icon>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.detail-page { max-width: 1200px; margin: 0 auto; }

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
  background: #fff;
  padding: 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.header-left h1 { font-size: 22px; font-weight: 700; margin-bottom: 10px; }

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.header-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.meta-text { font-size: 13px; color: var(--muted); }
.meta-text.salary { color: var(--danger); font-weight: 600; }

.detail-body {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 20px;
}

.section-card { margin-bottom: 16px; }
.card-header { font-size: 15px; font-weight: 600; }

.summary { font-size: 14px; color: var(--ink); line-height: 1.6; }

/* 分条标签 */
.item-section { margin-bottom: 14px; }
.item-section:last-child { margin-bottom: 0; }

.item-section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 8px;
  padding-left: 2px;
}

.item-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-tag {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  background: var(--canvas);
  border-radius: 6px;
  border-left: 3px solid var(--brand);
  transition: background 0.15s;
}
.item-tag:hover {
  background: var(--brand-light);
}

.item-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 1px;
}

.item-text {
  font-size: 13px;
  color: var(--ink);
  line-height: 1.65;
  flex: 1;
}

.skill-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.skill-chip {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  background: var(--brand-light);
  color: var(--brand);
}

/* Side info */
.info-list { display: flex; flex-direction: column; gap: 10px; }

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.info-label { font-size: 13px; color: var(--muted); }
.info-value { font-size: 13px; color: var(--ink); font-weight: 500; }
.info-value.salary { color: var(--danger); font-weight: 600; }

/* Resume picker dialog */
.resume-picker-list { display: flex; flex-direction: column; gap: 8px; }
.resume-picker-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-radius: var(--radius);
  border: 1px solid var(--hairline); cursor: pointer;
  transition: all 0.15s;
}
.resume-picker-item:hover { background: var(--canvas); border-color: var(--brand); }
.picker-left { display: flex; align-items: center; gap: 10px; }
.picker-name { font-size: 14px; font-weight: 500; }
</style>
