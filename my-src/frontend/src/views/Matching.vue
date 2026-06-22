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
            <el-button type="primary" size="default" @click="$router.push('/matching')">
              <el-icon><Upload /></el-icon> 上传简历
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats row -->
    <div class="match-stats-row anim-fade-up anim-delay-1">
      <div class="match-stat"><span class="ms-num">{{ filteredList.length }}</span><span class="ms-label">匹配人才</span></div>
      <div class="match-stat"><span class="ms-num green">{{ urgentCount }}</span><span class="ms-label">急缺岗位</span></div>
      <div class="match-stat"><span class="ms-num blue">{{ highMatchCount }}</span><span class="ms-label">高匹配 (≥90%)</span></div>
    </div>

    <!-- Talent cards -->
    <div class="match-grid anim-fade-up anim-delay-2">
      <div
        class="match-card"
        v-for="item in filteredList"
        :key="item.id"
        @click="$router.push(`/matching/${item.id}`)"
      >
        <div class="mc-top">
          <div class="mc-avatar">{{ item.name.charAt(0) }}</div>
          <div class="mc-info">
            <div class="mc-name">
              {{ item.name }}
              <el-tag v-if="item.isNew" size="small" type="danger" style="margin-left:6px;">NEW</el-tag>
              <el-tag v-if="item.urgent" size="small" type="warning" style="margin-left:4px;">急缺</el-tag>
            </div>
            <div class="mc-pos">{{ item.position }} · {{ item.department }}</div>
          </div>
          <FavoriteButton type="resume" :target-id="item.id" :title="item.name" compact />
          <div class="mc-score-cell">
            <div class="score-ring" :style="{ '--pct': `${item.score}%` }"><span>{{ item.score }}%</span></div>
          </div>
        </div>
        <div class="mc-tags">
          <el-tag v-for="s in item.matched.slice(0, 4)" :key="s" size="small" type="success" effect="plain">{{ s }}</el-tag>
          <el-tag v-for="s in item.missing.slice(0, 2)" :key="'m_'+s" size="small" type="danger" effect="plain">{{ s }}</el-tag>
          <span v-if="item.matched.length > 4 || item.missing.length > 2" class="mc-more">+{{ item.matched.length + item.missing.length - 6 }} 项</span>
        </div>
        <div class="mc-footer">
          <span>{{ item.experience }} · {{ item.education }}</span>
          <el-button text type="primary" size="small">查看详情 →</el-button>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="filteredList.length === 0" class="jm-empty" style="padding:60px 20px;">
      <el-icon style="font-size:40px;color:var(--color-border);"><Search /></el-icon>
      <p style="margin-top:12px;">没有匹配的人才信息</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Search, Upload } from "@element-plus/icons-vue";
import FavoriteButton from "@/components/common/FavoriteButton.vue";
import DataState from "@/components/common/DataState.vue";
import { useTalentStore } from "@/stores/talents";
import type { TalentSummary } from "@/domain/types";

const filterName = ref("");
const filterPosition = ref("");
const filterDept = ref("");
const filterScore = ref("");
const sortBy = ref("score");
const store = useTalentStore();
const { talents, loading, error } = storeToRefs(store);
onMounted(() => store.load());

function sortList(list: TalentSummary[]): TalentSummary[] {
  if (sortBy.value === "urgent") {
    return [...list].sort((a, b) => (b.urgent ? 1 : 0) - (a.urgent ? 1 : 0) || b.score - a.score);
  }
  if (sortBy.value === "newest") {
    return [...list].sort((a, b) => b.id - a.id);
  }
  return [...list].sort((a, b) => b.score - a.score);
}

const filteredList = computed(() => {
  let list = talents.value;
  if (filterName.value) list = list.filter(t => t.name.includes(filterName.value));
  if (filterPosition.value) list = list.filter(t => t.position.includes(filterPosition.value));
  if (filterDept.value) list = list.filter(t => t.department.includes(filterDept.value));
  if (filterScore.value) list = list.filter(t => t.score >= Number(filterScore.value));
  return sortList(list);
});

const urgentCount = computed(() => talents.value.filter(t => t.urgent).length);
const highMatchCount = computed(() => talents.value.filter(t => t.score >= 90).length);

function applyFilter() {}
</script>
