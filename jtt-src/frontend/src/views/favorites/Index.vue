<script setup lang="ts">
<<<<<<< HEAD
import { onMounted, ref } from 'vue'
=======
import { ref } from 'vue'
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useFavoritesStore } from '@/stores/favorites'
<<<<<<< HEAD

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
=======
import { useLearningStore } from '@/stores/learning'
import { mockNotes } from '@/mock/data/notes'
import type { Note } from '@/types'
import { ElMessage, ElMessageBox } from 'element-plus'
import PositionCard from '@/components/positions/PositionCard.vue'

const router = useRouter()
const favoritesStore = useFavoritesStore()
const learningStore = useLearningStore()

const activeTab = ref<'position' | 'learning_path' | 'note'>('position')

// Note editor dialog
const noteEditorVisible = ref(false)
const editingNote = ref<Partial<Note> | null>(null)
const noteForm = ref({ title: '', content: '', type: 'note' as Note['type'], url: '', tags: '' })

const openNoteEditor = (note?: Note) => {
  if (note) {
    editingNote.value = note
    noteForm.value = { title: note.title, content: note.content, type: note.type, url: note.url || '', tags: note.tags.join(', ') }
  } else {
    editingNote.value = null
    noteForm.value = { title: '', content: '', type: 'note', url: '', tags: '' }
  }
  noteEditorVisible.value = true
}

const saveNote = () => {
  if (!noteForm.value.title.trim()) {
    ElMessage.warning('请输入笔记标题')
    return
  }
  const tags = noteForm.value.tags.split(/[,，]/).map((t: string) => t.trim()).filter(Boolean)
  if (editingNote.value) {
    // Update existing
    const idx = mockNotes.findIndex((n) => n.id === editingNote.value!.id)
    if (idx >= 0) {
      mockNotes[idx] = {
        ...mockNotes[idx],
        title: noteForm.value.title,
        content: noteForm.value.content,
        type: noteForm.value.type,
        url: noteForm.value.url || undefined,
        tags,
        updatedAt: new Date().toISOString(),
      }
    }
    ElMessage.success('笔记已更新')
  } else {
    const newNote: Note = {
      id: `n-${Date.now()}`,
      title: noteForm.value.title,
      content: noteForm.value.content,
      type: noteForm.value.type,
      url: noteForm.value.url || undefined,
      tags,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
    mockNotes.unshift(newNote)
    favoritesStore.toggleFavorite('note', newNote.id)
    ElMessage.success('笔记已创建并加入收藏')
  }
  noteEditorVisible.value = false
}

const deleteNote = async (noteId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这条笔记吗？', '提示', { type: 'warning' })
    const idx = mockNotes.findIndex((n) => n.id === noteId)
    if (idx >= 0) mockNotes.splice(idx, 1)
    if (favoritesStore.isFavorited('note', noteId)) favoritesStore.toggleFavorite('note', noteId)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

// Learning path expanded state
const expandedPathId = ref<string | null>(null)
const togglePathExpand = (id: string) => {
  expandedPathId.value = expandedPathId.value === id ? null : id
}

const goPosition = (id: string) => router.push(`/positions/${id}`)

const getNoteIcon = (type: Note['type']) => {
  if (type === 'link') return 'Link'
  if (type === 'resource') return 'FolderOpened'
  return 'Document'
}
const getNoteTypeLabel = (type: Note['type']) => {
  if (type === 'link') return '链接'
  if (type === 'resource') return '资源'
  return '笔记'
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
}
</script>

<template>
  <div class="favorites-page">
    <div class="page-header">
      <div>
        <h2>我的收藏</h2>
<<<<<<< HEAD
        <p class="sub">共 {{ favoritesStore.totalCount }} 项收藏</p>
=======
        <p class="header-sub">共收藏 {{ favoritesStore.totalCount }} 项</p>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
      </div>
    </div>

    <el-tabs v-model="activeTab" class="fav-tabs">
      <!-- Tab 1: 岗位 -->
<<<<<<< HEAD
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
=======
      <el-tab-pane label="岗位" name="position">
        <template #label>
          <span>岗位 <el-badge :value="favoritesStore.positionCount" :max="99" class="tab-badge" /></span>
        </template>
        <div v-if="favoritesStore.positionFavorites.length > 0" class="position-grid">
          <PositionCard
            v-for="pos in favoritesStore.positionFavorites"
            :key="pos.id"
            :position="pos"
            @click="goPosition(pos.id)"
          />
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏岗位">
            <el-button type="primary" @click="router.push('/positions')">去探索岗位</el-button>
          </el-empty>
        </div>
      </el-tab-pane>

<<<<<<< HEAD
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
=======
      <!-- Tab 2: 学习路径 -->
      <el-tab-pane name="learning_path">
        <template #label>
          <span>学习路径 <el-badge :value="favoritesStore.learningPathCount" :max="99" class="tab-badge" /></span>
        </template>
        <div v-if="favoritesStore.learningPathFavorites.length > 0" class="path-list">
          <div
            v-for="path in favoritesStore.learningPathFavorites"
            :key="path.id"
            class="path-card"
          >
            <div class="path-header" @click="togglePathExpand(path.id)">
              <div class="path-head-left">
                <el-icon :size="20" color="var(--brand)"><Guide /></el-icon>
                <span class="path-name">{{ path.name }}</span>
                <el-tag size="small" type="success">{{ learningStore.getCompletionPercent(path.id) || 0 }}%</el-tag>
              </div>
              <div class="path-head-right">
                <span class="path-dur">{{ path.totalDuration }}</span>
                <el-button
                  :icon="favoritesStore.isFavorited('learning_path', path.id) ? 'StarFilled' : 'Star'"
                  text
                  size="small"
                  :type="favoritesStore.isFavorited('learning_path', path.id) ? 'warning' : ''"
                  @click.stop="favoritesStore.toggleFavorite('learning_path', path.id)"
                />
                <el-icon :size="16" class="expand-icon" :class="{ rotated: expandedPathId === path.id }"><ArrowDown /></el-icon>
              </div>
            </div>
            <div v-if="expandedPathId === path.id" class="path-body">
              <div class="path-steps">
                <div v-for="(step, idx) in path.steps" :key="step.id" class="path-step">
                  <div class="step-dot" :class="{ done: step.completed }">
                    <el-icon v-if="step.completed" :size="12"><Check /></el-icon>
                  </div>
                  <div class="step-info">
                    <span class="step-title">{{ step.title }}</span>
                    <span class="step-dur">{{ step.duration }}</span>
                  </div>
                </div>
              </div>
              <el-button type="primary" size="small" @click="router.push('/learning')">去学习</el-button>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
<<<<<<< HEAD
          <el-empty description="暂无收藏的学习资料">
            <el-button type="primary" @click="goLearning">去学习路径发现资料</el-button>
=======
          <el-empty description="暂无收藏学习路径">
            <el-button type="primary" @click="router.push('/learning')">去学习路径</el-button>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
          </el-empty>
        </div>
      </el-tab-pane>

<<<<<<< HEAD
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
                <span>{{ fav.metadata?.correct_answer || '-' }}</span>
              </div>
            </div>
            <div v-if="fav.metadata?.explanation" class="error-explanation">
              {{ fav.metadata.explanation }}
            </div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无错题记录">
            <el-button type="primary" @click="goLearning">去学习测试</el-button>
          </el-empty>
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
                <el-tag size="small" type="warning">AI生成</el-tag>
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
=======
      <!-- Tab 3: 笔记资料 -->
      <el-tab-pane name="note">
        <template #label>
          <span>笔记资料 <el-badge :value="favoritesStore.noteCount" :max="99" class="tab-badge" /></span>
        </template>
        <div class="note-toolbar">
          <el-button type="primary" @click="openNoteEditor()">
            <el-icon><Plus /></el-icon>新建笔记
          </el-button>
        </div>
        <div v-if="favoritesStore.noteFavorites.length > 0" class="note-grid">
          <div v-for="note in favoritesStore.noteFavorites" :key="note.id" class="note-card">
            <div class="note-card-head">
              <el-icon :size="20" :color="note.type === 'link' ? 'var(--brand)' : note.type === 'resource' ? 'var(--success)' : 'var(--warning)'">
                <component :is="getNoteIcon(note.type)" />
              </el-icon>
              <span class="note-type-label">{{ getNoteTypeLabel(note.type) }}</span>
              <div class="note-card-actions">
                <el-button :icon="'Edit'" text size="small" @click.stop="openNoteEditor(note)" />
                <el-button
                  :icon="favoritesStore.isFavorited('note', note.id) ? 'StarFilled' : 'Star'"
                  text
                  size="small"
                  :type="favoritesStore.isFavorited('note', note.id) ? 'warning' : ''"
                  @click.stop="favoritesStore.toggleFavorite('note', note.id)"
                />
                <el-button :icon="'Delete'" text size="small" type="danger" @click.stop="deleteNote(note.id)" />
              </div>
            </div>
            <h4 class="note-title">{{ note.title }}</h4>
            <p class="note-preview">{{ note.content.slice(0, 100) }}{{ note.content.length > 100 ? '...' : '' }}</p>
            <div class="note-tags">
              <el-tag v-for="t in note.tags.slice(0, 4)" :key="t" size="small">{{ t }}</el-tag>
            </div>
            <div class="note-date">{{ note.updatedAt }}</div>
          </div>
        </div>
        <div v-else class="empty-tab">
          <el-empty description="暂无收藏笔记">
            <el-button type="primary" @click="openNoteEditor()">新建笔记</el-button>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
          </el-empty>
        </div>
      </el-tab-pane>
    </el-tabs>
<<<<<<< HEAD
=======

    <!-- Note Editor Dialog -->
    <el-dialog v-model="noteEditorVisible" :title="editingNote ? '编辑笔记' : '新建笔记'" width="520px">
      <el-form label-position="top">
        <el-form-item label="笔记标题">
          <el-input v-model="noteForm.title" placeholder="输入标题" maxlength="100" />
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="noteForm.type">
            <el-radio-button value="note">笔记</el-radio-button>
            <el-radio-button value="link">链接</el-radio-button>
            <el-radio-button value="resource">资源</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="noteForm.type === 'link' || noteForm.type === 'resource'" label="链接地址">
          <el-input v-model="noteForm.url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="noteForm.content" type="textarea" :rows="4" placeholder="输入笔记内容..." />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="noteForm.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="noteEditorVisible = false">取消</el-button>
        <el-button type="primary" @click="saveNote">保存</el-button>
      </template>
    </el-dialog>
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
  </div>
</template>

<style scoped>
.favorites-page { max-width: 1200px; margin: 0 auto; }

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
<<<<<<< HEAD
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
=======
}
.header-text h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.header-sub { font-size: 13px; color: var(--muted); }

.fav-tabs { margin-top: 4px; }
.tab-badge { margin-left: 4px; }

.position-grid {
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}

<<<<<<< HEAD
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
  gap: 8px;
  margin-bottom: 8px;
}
.fav-card-header h4 { font-size: 15px; font-weight: 600; }

.fav-summary {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fav-salary {
  font-size: 13px;
  font-weight: 600;
  color: var(--danger);
  margin-bottom: 6px;
}

.fav-skills { display: flex; gap: 4px; flex-wrap: wrap; }
.fav-skills .more { font-size: 12px; color: var(--muted); line-height: 24px; }

.fav-meta { font-size: 12px; color: var(--weak); margin-top: 8px; }

.fav-link { margin-top: 8px; }
.fav-link a { font-size: 13px; color: var(--brand); text-decoration: none; }
.fav-link a:hover { text-decoration: underline; }

.fav-card-actions {
  border-top: 1px solid var(--hairline);
  padding: 8px 12px;
  display: flex;
  justify-content: flex-end;
}

/* Error cards */
.error-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.error-card {
  border: 1px solid var(--hairline);
  border-radius: var(--radius);
  padding: 20px;
}

.error-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}
.error-header h4 { font-size: 14px; font-weight: 600; flex: 1; line-height: 1.5; }

.error-body {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
}

.error-answer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}
.error-answer.wrong { color: #ef4444; }
.error-answer.correct { color: #22c55e; }

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
=======
.empty-tab { padding: 60px 0; }

/* Learning Paths */
.path-list { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }
.path-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
>>>>>>> aa08688 (feat(fyz-backend): add job filtering)
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
</style>
