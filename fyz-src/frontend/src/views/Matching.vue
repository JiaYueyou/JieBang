<template>
  <div>
    <DataState :loading="loading" :error="error" @retry="store.refresh()" />
    <!-- Filter bar -->
    <div class="dash-card anim-fade-up" style="margin-bottom:16px;">
      <div class="dash-card-body" style="padding:14px 20px;">
        <div class="match-filter-row">
          <div class="match-filter-inputs">
            <el-input v-model="filterName" placeholder="姓名" clearable style="width:140px;" size="default" @input="applyFilter" />
            <el-input v-model="filterPosition" placeholder="岗位" clearable style="width:160px;" size="default" @input="applyFilter" />
            <el-input v-model="filterDept" placeholder="部门" clearable style="width:140px;" size="default" @input="applyFilter" />
            <el-select v-model="filterJobId" placeholder="匹配岗位" clearable style="width:190px;" size="default" @change="applyFilter">
              <el-option v-for="job in jobOptions" :key="job.id" :label="job.title" :value="job.id" />
            </el-select>
            <el-select v-model="filterScore" placeholder="匹配度" clearable style="width:130px;" size="default" @change="applyFilter">
              <el-option label="90% 以上" value="90" /><el-option label="80% 以上" value="80" />
              <el-option label="70% 以上" value="70" /><el-option label="全部" value="" />
            </el-select>
          </div>
          <div class="match-filter-actions">
            <el-select v-model="sortBy" style="width:140px;" size="default" @change="applyFilter">
              <el-option label="匹配度优先" value="score" /><el-option label="急缺岗位优先" value="urgent" />
              <el-option label="最新优先" value="newest" />
            </el-select>
            <el-button type="primary" size="default" @click="uploadVisible = true">
              <el-icon><Upload /></el-icon> 上传简历
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="match-stats-row anim-fade-up anim-delay-1">
      <div class="match-stat"><span class="ms-num">{{ filteredList.length }}</span><span class="ms-label">{{ filterJobId ? '该岗位候选人' : '匹配人才' }}</span></div>
      <div class="match-stat"><span class="ms-num green">{{ urgentCount }}</span><span class="ms-label">{{ filterJobId ? '急缺岗位候选人' : '急缺岗位' }}</span></div>
      <div class="match-stat"><span class="ms-num blue">{{ highMatchCount }}</span><span class="ms-label">高匹配 (≥90%)</span></div>
    </div>

    <!-- Talent cards -->
    <div class="match-grid anim-fade-up anim-delay-2">
      <div
        class="match-card"
        v-for="item in pagedList"
        :key="item.id"
        @click="openTalent(item)"
      >
        <div class="mc-top">
          <div class="mc-avatar">{{ item.name.charAt(0) }}</div>
          <div class="mc-info">
            <div class="mc-name">
              {{ item.name }}
              <el-tag v-if="item.isNew" size="small" type="danger" style="margin-left:6px;">NEW</el-tag>
              <el-tag v-if="cardMatch(item).urgent" size="small" type="warning" style="margin-left:4px;">急缺</el-tag>
            </div>
            <div class="mc-pos">{{ item.position }} · {{ item.department }}</div>
            <div class="mc-match-job">匹配岗位：{{ cardMatch(item).job_title }}</div>
          </div>
          <FavoriteButton type="resume" :target-id="item.id" :title="item.name" compact />
          <div class="mc-score-cell">
            <div class="score-ring" :style="{ '--pct': `${cardMatch(item).score}%` }"><span>{{ cardMatch(item).score }}%</span></div>
          </div>
        </div>
        <div class="mc-tags">
          <el-tag v-for="s in cardMatch(item).matched.slice(0, 4)" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
          <el-tag v-for="s in cardMatch(item).missing.slice(0, 2)" :key="'m_'+s" size="small" type="danger" effect="plain">{{ s }}</el-tag>
          <span v-if="cardMatch(item).matched.length > 4 || cardMatch(item).missing.length > 2" class="mc-more">+{{ cardMatch(item).matched.length + cardMatch(item).missing.length - 6 }} 项</span>
        </div>
        <div class="mc-footer">
          <span>{{ item.experience }} · {{ item.education }}</span>
          <el-button text type="primary" size="small">查看详情 →</el-button>
        </div>
      </div>
    </div>
    <div v-if="filteredList.length > pageSize" class="matching-pagination">
      <span>共 {{ filteredList.length }} 位人才</span>
      <el-pagination
        v-model:current-page="currentPage"
        size="small"
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="filteredList.length"
      />
    </div>

    <!-- Empty state -->
    <div v-if="filteredList.length === 0" class="jm-empty" style="padding:60px 20px;">
      <el-icon style="font-size:40px;color:var(--color-border);"><Search /></el-icon>
      <p style="margin-top:12px;">没有匹配的人才信息</p>
    </div>

    <el-dialog v-model="uploadVisible" title="上传简历并生成岗位匹配" width="520px">
      <el-form label-width="92px">
        <el-form-item label="简历文件">
          <el-upload :auto-upload="false" :limit="1" accept=".txt,.md,.pdf,.docx" :on-change="onFileChange" :on-remove="onFileRemove">
            <el-button><el-icon><Upload /></el-icon> 选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="uploadForm.name" placeholder="未填写时使用文件名" /></el-form-item>
        <el-form-item label="当前岗位"><el-input v-model="uploadForm.currentPosition" /></el-form-item>
        <el-form-item label="工作年限"><el-input v-model="uploadForm.experience" placeholder="例如：3 年" /></el-form-item>
        <el-form-item label="学历"><el-input v-model="uploadForm.education" /></el-form-item>
        <el-form-item label="部门"><el-input v-model="uploadForm.department" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadFile" @click="submitUpload">上传并匹配</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, type UploadFile } from "element-plus";
import { storeToRefs } from "pinia";
import { Search, Upload } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useTalentStore } from "@/stores/talents";
import { useHistoryStore } from "@/stores/history";
import { useRouter } from "vue-router";
import type { TalentMatch, TalentSummary } from "@/domain/types";
import { dataProvider } from "@/data";

const filterName = ref("");
const filterPosition = ref("");
const filterDept = ref("");
const filterJobId = ref<number | undefined>();
const filterScore = ref("");
const sortBy = ref("score");
const currentPage = ref(1);
const pageSize = 12;
const uploadVisible = ref(false);
const uploading = ref(false);
const uploadFile = ref<File | null>(null);
const uploadForm = reactive({ name: "", currentPosition: "", experience: "", education: "", department: "" });
const store = useTalentStore();
const historyStore = useHistoryStore();
const router = useRouter();
const { talents, loading, error } = storeToRefs(store);
onMounted(() => store.load());

const jobOptions = computed(() => {
  const jobs = new Map<number, { id: number; title: string }>();
  talents.value.forEach((talent) => talentMatches(talent).forEach((match) => {
    jobs.set(match.job_id, { id: match.job_id, title: match.job_title });
  }));
  return [...jobs.values()].sort((a, b) => a.title.localeCompare(b.title, "zh-CN"));
});

function fallbackMatch(talent: TalentSummary): TalentMatch {
  return {
    id: talent.match_id, resume_id: talent.resume_id, job_id: talent.targetJobIds?.[0] ?? 0,
    job_title: talent.targetJobs?.[0] ?? "未指定岗位", algorithm_version: "legacy", urgent: Boolean(talent.urgent),
    score: talent.score, matched: talent.matched, missing: talent.missing,
  };
}

function talentMatches(talent: TalentSummary): TalentMatch[] {
  return talent.matches?.length ? talent.matches : [fallbackMatch(talent)];
}

function cardMatch(talent: TalentSummary): TalentMatch {
  if (filterJobId.value) return talentMatches(talent).find((match) => match.job_id === filterJobId.value) ?? fallbackMatch(talent);
  return talentMatches(talent)[0] ?? fallbackMatch(talent);
}

function sortList(list: TalentSummary[]): TalentSummary[] {
  if (sortBy.value === "urgent") {
    return [...list].sort((a, b) => Number(cardMatch(b).urgent) - Number(cardMatch(a).urgent) || cardMatch(b).score - cardMatch(a).score);
  }
  if (sortBy.value === "newest") {
    return [...list].sort((a, b) => b.id - a.id);
  }
  return [...list].sort((a, b) => cardMatch(b).score - cardMatch(a).score);
}

const filteredList = computed(() => {
  let list = talents.value;
  if (filterName.value) list = list.filter(t => t.name.includes(filterName.value));
  if (filterPosition.value) list = list.filter(t => t.position.includes(filterPosition.value) || talentMatches(t).some(match => match.job_title.includes(filterPosition.value)));
  if (filterDept.value) list = list.filter(t => t.department.includes(filterDept.value));
  if (filterJobId.value) list = list.filter(t => talentMatches(t).some(match => match.job_id === filterJobId.value));
  if (filterScore.value) list = list.filter(t => cardMatch(t).score >= Number(filterScore.value));
  return sortList(list);
});
const pagedList = computed(() => {
  const start = (currentPage.value - 1) * pageSize;
  return filteredList.value.slice(start, start + pageSize);
});

const urgentCount = computed(() => filteredList.value.filter(t => cardMatch(t).urgent).length);
const highMatchCount = computed(() => filteredList.value.filter(t => cardMatch(t).score >= 90).length);

function applyFilter() {
  currentPage.value = 1;
}

async function openTalent(item: TalentSummary) {
  try {
    await historyStore.record({
      type: "resume",
      targetId: item.resume_id,
      title: item.name,
      description: `${item.position} · ${item.department}`,
      source: "人才匹配",
      tags: [...item.matched, ...item.missing].slice(0, 5),
      url: `/matching/${item.resume_id}`,
    });
  } catch {
    ElMessage.warning("人才详情已打开，但浏览足迹记录失败");
  }
  await router.push(`/matching/${item.resume_id}`);
}

function onFileChange(file: UploadFile) { uploadFile.value = file.raw || null; }
function onFileRemove() { uploadFile.value = null; }
async function submitUpload() {
  if (!uploadFile.value) return;
  uploading.value = true;
  try {
    await dataProvider.talents.upload({ file: uploadFile.value, ...uploadForm });
    await store.refresh();
    uploadVisible.value = false;
    ElMessage.success("简历已保存并完成岗位匹配");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "简历上传失败");
  } finally { uploading.value = false; }
}
</script>

<style scoped>
.mc-match-job {
  margin-top: 3px;
  color: var(--color-brand);
  font-size: 12px;
  font-weight: 700;
}
</style>
