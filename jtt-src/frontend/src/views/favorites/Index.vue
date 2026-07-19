<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFavoritesStore } from '@/stores/favorites'

const router = useRouter()
const favoritesStore = useFavoritesStore()
const activeTab = ref('position')

onMounted(() => favoritesStore.fetchAll())

const handleRemove = async (favId: number, title: string) => {
  try {
    await ElMessageBox.confirm(`确定移除收藏「${title}」吗？`, '提示', { type: 'warning' })
    await favoritesStore.remove(favId)
    ElMessage.success('已移除收藏')
  } catch { /* 取消 */ }
}

const goPosition = (id: string) => router.push(`/positions/${id}`)
const goLearning = () => router.push('/learning')

const resourceTypeLabels: Record<string, string> = {
  course: '课程', book: '书籍', article: '文章', project: '项目', video: '视频',
}
</script>

<template>
  <div class="favorites-page">
    <div class="page-header">
      <div>
        <h2>我的收藏</h2>
        <p class="sub">共 {{ favoritesStore.totalCount }} 项收藏</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="fav-tabs">
      <!-- Tab 1: 岗位 -->
      <el-tab-pane name="position">
        <template #label>
          <span>岗位 <el-badge :value="favoritesStore.positionCount" :hidden="favoritesStore.positionCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.positionFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.positionFavs"
            :key="fav.id"
            class="fav-card"
            @click="goPosition(fav.item_id)"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
                <el-tag
                  v-if="fav.metadata?.category"
                  size="small"
                  :type="fav.metadata.category === 'new' ? 'success' : ''"
                >
                  {{ fav.metadata.category === 'new' ? '新兴' : '既有' }}
                </el-tag>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div v-if="fav.metadata?.salary_range" class="fav-salary">{{ fav.metadata.salary_range }}</div>
              <div v-if="fav.metadata?.skills?.length" class="fav-skills">
                <el-tag v-for="sk in fav.metadata.skills.slice(0, 5)" :key="sk" size="small" round>{{ sk }}</el-tag>
                <span v-if="fav.metadata.skills.length > 5" class="more">+{{ fav.metadata.skills.length - 5 }}</span>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏岗位">
            <el-button type="primary" @click="router.push('/positions')">去探索岗位</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 学习资料 -->
      <el-tab-pane name="learning_resource">
        <template #label>
          <span>学习资料 <el-badge :value="favoritesStore.resourceCount" :hidden="favoritesStore.resourceCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.resourceFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.resourceFavs"
            :key="fav.id"
            class="fav-card"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
                <el-tag size="small" type="success">
                  {{ resourceTypeLabels[fav.metadata?.type] || fav.metadata?.type || '资料' }}
                </el-tag>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div class="fav-meta">
                <span v-if="fav.metadata?.platform">平台: {{ fav.metadata.platform }}</span>
              </div>
              <div v-if="fav.metadata?.url" class="fav-link">
                <a :href="fav.metadata.url" target="_blank" @click.stop>查看资源</a>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏的学习资料">
            <el-button type="primary" @click="goLearning">去学习路径发现资料</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 错题 -->
      <el-tab-pane name="quiz_error">
        <template #label>
          <span>错题 <el-badge :value="favoritesStore.errorCount" :hidden="favoritesStore.errorCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.errorFavs.length > 0" class="error-list">
          <div
            v-for="fav in favoritesStore.errorFavs"
            :key="fav.id"
            class="error-card"
          >
            <div class="error-header">
              <h4>{{ fav.metadata?.question || fav.title }}</h4>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">移除</el-button>
            </div>
            <div class="error-body">
              <div class="error-answer wrong">
                <span class="error-label">你的答案</span>
                <span>{{ fav.metadata?.user_answer || '未作答' }}</span>
              </div>
              <div class="error-answer correct">
                <span class="error-label">正确答案</span>
                <span>{{ fav.metadata?.correct_answer || '无' }}</span>
              </div>
              <p v-if="fav.metadata?.explanation" class="error-explain">
                💡 {{ fav.metadata.explanation }}
              </p>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无错题" />
        </div>
      </el-tab-pane>

      <!-- Tab 4: AI知识点 -->
      <el-tab-pane name="knowledge_point">
        <template #label>
          <span>AI知识点 <el-badge :value="favoritesStore.knowledgeCount" :hidden="favoritesStore.knowledgeCount === 0" /></span>
        </template>
        <div v-if="favoritesStore.knowledgeFavs.length > 0" class="fav-grid">
          <div
            v-for="fav in favoritesStore.knowledgeFavs"
            :key="fav.id"
            class="fav-card"
          >
            <div class="fav-card-body">
              <div class="fav-card-header">
                <h4>{{ fav.title }}</h4>
              </div>
              <p v-if="fav.summary" class="fav-summary">{{ fav.summary }}</p>
              <div v-if="fav.metadata?.related_skills?.length" class="fav-skills">
                <el-tag v-for="sk in fav.metadata.related_skills" :key="sk" size="small" round>{{ sk }}</el-tag>
              </div>
            </div>
            <div class="fav-card-actions" @click.stop>
              <el-button text size="small" type="danger" @click="handleRemove(fav.id, fav.title)">取消收藏</el-button>
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="AI生成知识点即将上线">
            <p class="coming-soon-hint">AI 智能体功能即将上线，届时可自动生成并收藏知识点</p>
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.favorites-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.page-header h2 { font-size: 20px; font-weight: 700; }
.sub { font-size: 13px; color: var(--muted); margin-top: 4px; }

.fav-tabs {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 0 20px 20px;
}

.fav-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.fav-card {
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow 0.15s;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.fav-card:hover { box-shadow: var(--shadow-hover); }

.fav-card-body { padding: 16px 20px; flex: 1; }

.fav-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.fav-card-header h4 { font-size: 15px; font-weight: 600; }

.fav-summary {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.fav-salary { font-size: 13px; font-weight: 600; color: var(--danger); margin-bottom: 4px; }

.fav-skills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 4px; }
.more { font-size: 12px; color: var(--muted); }

.fav-meta { font-size: 12px; color: var(--weak); margin-bottom: 4px; }

.fav-link a {
  font-size: 12px;
  color: var(--brand);
  text-decoration: none;
}
.fav-link a:hover { text-decoration: underline; }

.fav-card-actions {
  padding: 10px 20px;
  border-top: 1px solid var(--hairline);
  display: flex;
  justify-content: flex-end;
}

/* Error cards */
.error-list { display: flex; flex-direction: column; gap: 12px; }

.error-card {
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  padding: 16px;
}
.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.error-header h4 { font-size: 14px; font-weight: 600; }

.error-body { display: flex; flex-direction: column; gap: 6px; }
.error-answer { font-size: 13px; display: flex; gap: 8px; }
.error-label { color: var(--weak); min-width: 70px; }
.error-answer.wrong span:last-child { color: var(--danger); }
.error-answer.correct span:last-child { color: var(--success); }
.error-explain { font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; }

<<<<<<< HEAD
.empty-tab { padding: 40px 0; text-align: center; }
.coming-soon-hint { font-size: 13px; color: var(--muted); margin-top: 4px; }
=======
.error-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.error-explanation {
  font-size: 12px;
  color: #a16207;
  background: #fefce8;
  padding: 8px 12px;
  border-radius: 8px;
  line-height: 1.5;
}

/* Empty states */
.empty-tab { padding: 60px 0; }

.coming-soon-hint {
  font-size: 13px;
  color: var(--muted);
  margin-top: 8px;
}
.path-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  cursor: pointer;
}
.path-head-left, .path-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.path-name { font-size: 14px; font-weight: 600; }
.path-dur { font-size: 12px; color: var(--muted); }
.expand-icon { transition: transform 0.2s; color: var(--muted); }
.expand-icon.rotated { transform: rotate(180deg); }

.path-body { padding: 0 20px 16px; border-top: 1px solid var(--hairline); }
.path-steps { padding: 12px 0; }
.path-step { display: flex; align-items: center; gap: 12px; padding: 6px 0; }
.step-dot {
  width: 22px; height: 22px;
  border-radius: 50%;
  border: 2px solid var(--hairline);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.step-dot.done { background: var(--brand); border-color: var(--brand); color: #fff; }
.step-info { display: flex; align-items: center; gap: 10px; }
.step-title { font-size: 13px; }
.step-dur { font-size: 12px; color: var(--muted); }

/* Notes */
.note-toolbar { margin: 16px 0 12px; }
.note-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.note-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  transition: box-shadow 0.2s;
}
.note-card:hover { box-shadow: var(--shadow-hover); }
.note-card-head { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.note-type-label { font-size: 12px; color: var(--muted); }
.note-card-actions { margin-left: auto; display: flex; gap: 2px; }
.note-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.note-preview { font-size: 13px; color: var(--muted); line-height: 1.5; margin-bottom: 8px; }
.note-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.note-date { font-size: 12px; color: var(--weak); }
>>>>>>> 144cd35 (fix(jtt): fit Error: Process completed with exit code 1.)
</style>
