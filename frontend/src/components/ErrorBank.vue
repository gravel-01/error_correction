<script setup>
import { ref, reactive, computed, watch } from 'vue'
import * as api from '../api.js'
import QuestionDetailModal from './QuestionDetailModal.vue'

const props = defineProps({
  theme: { type: String, default: 'light' },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['go-workspace', 'push-toast', 'open-image'])

// ---- 筛选条件 ----
const filters = reactive({
  subject: '',
  knowledge_tag: '',
  question_type: '',
  keyword: '',
  start_date: '',
  end_date: '',
  review_status: '',
})
const page = ref(1)
const pageSize = ref(20)

// ---- 数据 ----
const items = ref([])
const total = ref(0)
const totalPages = ref(0)
const loading = ref(false)
const subjects = ref([])
const questionTypes = ref([])
const tagNames = ref([])
const selectedIds = reactive(new Set())

const detailOpen = ref(false)
const detailQuestion = ref(null)

const totalText = computed(() => `共收录 ${total.value} 道题目`)

// ---- 查询 ----
let debounceTimer = null
const doQuery = async () => {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (filters.subject) params.subject = filters.subject
    if (filters.knowledge_tag) params.knowledge_tag = filters.knowledge_tag
    if (filters.question_type) params.question_type = filters.question_type
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.start_date) params.start_date = filters.start_date
    if (filters.end_date) params.end_date = filters.end_date
    if (filters.review_status) params.review_status = filters.review_status

    const data = await api.fetchErrorBank(params)
    items.value = data.items || []
    total.value = data.total || 0
    totalPages.value = data.total_pages || 0
  } catch (e) {
    emit('push-toast', 'error', e instanceof Error ? e.message : String(e))
  } finally {
    loading.value = false
  }
}

const debouncedQuery = () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; doQuery() }, 300)
}

watch(() => [filters.subject, filters.knowledge_tag, filters.question_type, filters.start_date, filters.end_date, filters.review_status], debouncedQuery)
watch(() => filters.keyword, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => { page.value = 1; doQuery() }, 500)
})

const resetFilters = () => {
  Object.keys(filters).forEach(k => filters[k] = '')
  page.value = 1
  doQuery()
}

const goPage = (p) => {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  doQuery()
}

const toggleSelect = (id) => { selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id) }
const clearSelection = () => { selectedIds.clear() }

const doExport = async () => {
  if (!selectedIds.size) return
  try {
    const data = await api.exportFromDb(Array.from(selectedIds))
    emit('push-toast', 'success', '错题本导出成功')
    let filename = 'wrongbook.md'
    if (data.output_path) {
      const parts = String(data.output_path).split(/[/\\]/)
      const last = parts[parts.length - 1]; if (last) filename = last
    }
    const a = document.createElement('a')
    a.href = `/download/${encodeURIComponent(filename)}?t=${Date.now()}`
    a.download = filename
    document.body.appendChild(a); a.click(); a.remove()
  } catch (e) {
    emit('push-toast', 'error', '导出失败: ' + (e instanceof Error ? e.message : String(e)))
  }
}

const openDetail = (q) => { detailQuestion.value = q; detailOpen.value = true }
const closeDetail = () => { detailOpen.value = false; detailQuestion.value = null }

const onDeleted = (id) => {
  items.value = items.value.filter(q => q.id !== id)
  total.value = Math.max(0, total.value - 1)
  selectedIds.delete(id)
  closeDetail()
}

const onAnswerSaved = (id, answer, updatedAt) => {
  const q = items.value.find(x => x.id === id)
  if (q) { q.user_answer = answer; q.updated_at = updatedAt }
}

const onReviewStatusChanged = (id, status, updatedAt) => {
  const q = items.value.find(x => x.id === id)
  if (q) { q.review_status = status; q.updated_at = updatedAt }
}

const getSummary = (q) => {
  const blocks = q.content_json || []
  const texts = blocks.filter(b => b.block_type === 'text').map(b => b.content || '')
  const joined = texts.join(' ').replace(/<[^>]+>/g, '')
  return joined.length > 120 ? joined.slice(0, 120) + '...' : joined
}

const pageButtons = computed(() => {
  const tp = totalPages.value; const cp = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const pages = [1]
  let start = Math.max(2, cp - 1); let end = Math.min(tp - 1, cp + 1)
  if (start > 2) pages.push('...')
  for (let i = start; i <= end; i++) pages.push(i)
  if (end < tp - 1) pages.push('...')
  pages.push(tp)
  return pages
})

const loadFilters = async () => {
  try {
    subjects.value = await api.fetchSubjects()
    questionTypes.value = await api.fetchQuestionTypes()
    tagNames.value = await api.fetchTagNames()
  } catch (_) {}
}

watch(() => props.visible, (v) => { if (v) { loadFilters(); doQuery() } }, { immediate: true })
</script>

<template>
  <div class="relative min-h-full">
    <!-- 专属动态光晕 -->
    <div class="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <div class="absolute -top-[5%] right-[-5%] h-[45vw] w-[45vw] rounded-full bg-blue-500/10 mix-blend-multiply blur-[120px] dark:bg-indigo-600/15 dark:mix-blend-screen"></div>
      <div class="absolute -bottom-[10%] left-[-10%] h-[35vw] w-[35vw] rounded-full bg-emerald-400/10 mix-blend-multiply blur-[100px] dark:bg-cyan-600/10 dark:mix-blend-screen"></div>
    </div>

    <div class="container relative z-10 mx-auto max-w-6xl px-4 py-8 sm:px-8">
      <!-- 页面标题：强化科技质感 -->
      <div class="mb-10 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div class="mb-2 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold text-blue-600 dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
            <i class="fa-solid fa-vault animate-pulse"></i> 智能存档中心
          </div>
          <h2 class="text-3xl font-black tracking-tight text-slate-900 sm:text-4xl dark:text-white">
            错题知识图谱
          </h2>
          <p class="mt-2 flex items-center gap-2 text-sm font-medium text-slate-500 dark:text-slate-400">
            <i class="fa-solid fa-chart-line text-blue-500"></i> {{ totalText }} · 记录每一次认知的突破
          </p>
        </div>
        <button @click="emit('go-workspace')" class="btn-primary group h-12 px-8 shadow-xl shadow-blue-500/20">
          <i class="fa-solid fa-plus-circle transition-transform group-hover:rotate-90"></i>
          录入新题目
        </button>
      </div>

      <!-- 搜索控制台：玻璃态工具栏 -->
      <div class="mb-8 space-y-5 rounded-3xl border border-slate-200/60 bg-white/40 p-5 shadow-sm backdrop-blur-2xl dark:border-white/10 dark:bg-[#0A0A0F]/60 sm:p-6">
        <!-- 第一行：关键词 + 三个下拉 -->
        <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <!-- 关键词 -->
          <div>
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">内容检索 / Keyword</label>
            <div class="relative group">
              <i class="fa-solid fa-magnifying-glass absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors"></i>
              <input v-model="filters.keyword" type="text" placeholder="搜索题目关键词..." class="h-11 w-full rounded-xl border border-slate-200 bg-white/60 pl-11 pr-4 text-sm font-medium outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 dark:border-white/5 dark:bg-white/5 dark:text-white dark:focus:border-indigo-500/50" />
            </div>
          </div>

          <div>
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">学科 / Subject</label>
            <select v-model="filters.subject" class="h-11 w-full rounded-xl border border-slate-200 bg-white/60 px-3 text-sm font-bold text-slate-700 outline-none transition-all focus:border-blue-500 dark:border-white/5 dark:bg-white/5 dark:text-slate-300">
              <option value="">全部学科</option>
              <option v-for="s in subjects" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>

          <div>
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">标签 / Tags</label>
            <select v-model="filters.knowledge_tag" class="h-11 w-full rounded-xl border border-slate-200 bg-white/60 px-3 text-sm font-bold text-slate-700 outline-none transition-all focus:border-blue-500 dark:border-white/5 dark:bg-white/5 dark:text-slate-300">
              <option value="">全部知识点</option>
              <option v-for="t in tagNames" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>

          <div>
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">题型 / Type</label>
            <select v-model="filters.question_type" class="h-11 w-full rounded-xl border border-slate-200 bg-white/60 px-3 text-sm font-bold text-slate-700 outline-none transition-all focus:border-blue-500 dark:border-white/5 dark:bg-white/5 dark:text-slate-300">
              <option value="">全部题型</option>
              <option v-for="t in questionTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>
        </div>

        <!-- 第二行：复习状态 + 日期范围 + 重置 -->
        <div class="flex flex-wrap items-end gap-5">
          <div class="w-40 shrink-0">
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">状态 / Status</label>
            <select v-model="filters.review_status" class="h-11 w-full rounded-xl border border-slate-200 bg-white/60 px-3 text-sm font-bold text-slate-700 outline-none transition-all focus:border-blue-500 dark:border-white/5 dark:bg-white/5 dark:text-slate-300">
              <option value="">全部状态</option>
              <option value="待复习">待复习</option>
              <option value="复习中">复习中</option>
              <option value="已掌握">已掌握</option>
            </select>
          </div>
          <div class="min-w-0 flex-1">
            <label class="mb-2 block text-[11px] font-black uppercase tracking-widest text-slate-400 dark:text-slate-500">时间跨度 / Date Range</label>
            <div class="flex items-center gap-2">
              <input v-model="filters.start_date" type="date" class="h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white/60 px-3 text-xs font-bold dark:border-white/5 dark:bg-white/5 dark:text-white" />
              <span class="shrink-0 text-slate-400">-</span>
              <input v-model="filters.end_date" type="date" class="h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white/60 px-3 text-xs font-bold dark:border-white/5 dark:bg-white/5 dark:text-white" />
            </div>
          </div>
          <button @click="resetFilters" class="btn-secondary h-11 shrink-0 px-5 shadow-sm" title="重置筛选">
            <i class="fa-solid fa-arrow-rotate-right"></i>
          </button>
        </div>
      </div>

      <!-- 列表区：使用精美的卡片网格 -->
      <div v-if="loading" class="flex flex-col items-center justify-center py-40">
        <div class="relative h-16 w-16">
          <div class="absolute inset-0 animate-spin rounded-full border-4 border-blue-500/20 border-t-blue-500"></div>
          <i class="fa-solid fa-cube absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-xl text-blue-500"></i>
        </div>
        <p class="mt-6 font-mono text-xs font-black uppercase tracking-[0.3em] text-slate-400">Syncing Knowledge Vault...</p>
      </div>

      <div v-else-if="!items.length" class="flex flex-col items-center justify-center rounded-[2.5rem] border-2 border-dashed border-slate-200 bg-slate-50/50 py-32 dark:border-white/5 dark:bg-white/5">
        <div class="mb-8 flex h-24 w-24 items-center justify-center rounded-3xl bg-white shadow-xl dark:bg-slate-900">
          <i class="fa-solid fa-box-open text-4xl text-slate-300 dark:text-slate-700"></i>
        </div>
        <p class="text-xl font-black text-slate-900 dark:text-white">暂无匹配记录</p>
        <p class="mt-2 text-sm font-medium text-slate-500">调整筛选条件，或者开始新的录入</p>
      </div>

      <div v-else class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div
          v-for="q in items"
          :key="q.id"
          @click="openDetail(q)"
          class="group relative cursor-pointer overflow-hidden rounded-[2rem] border bg-white/80 p-6 shadow-sm backdrop-blur-md transition-all duration-500 hover:-translate-y-1.5 hover:shadow-2xl dark:bg-[#0A0A0F]/60"
          :class="selectedIds.has(q.id) ? 'border-blue-500 ring-1 ring-blue-500/50 shadow-blue-500/10' : 'border-slate-200/60 dark:border-white/10 hover:border-blue-400/40'"
        >
          <!-- 学科状态条 -->
          <div class="absolute left-0 top-0 h-full w-1.5 opacity-80"
            :class="q.subject === '数学' ? 'bg-blue-500' : q.subject === '物理' ? 'bg-indigo-600' : 'bg-emerald-500'">
          </div>

          <div class="flex items-start gap-5">
            <!-- 勾选框：科技感微动效 -->
            <button class="mt-1 shrink-0" @click.stop="toggleSelect(q.id)">
              <div class="flex h-6 w-6 items-center justify-center rounded-lg border-2 transition-all duration-300"
                :class="selectedIds.has(q.id) ? 'border-blue-500 bg-blue-500 text-white rotate-12 scale-110 shadow-lg shadow-blue-500/40' : 'border-slate-300 bg-white dark:border-slate-700 dark:bg-slate-900'">
                <i v-show="selectedIds.has(q.id)" class="fa-solid fa-check text-[11px] font-black"></i>
              </div>
            </button>

            <div class="min-w-0 flex-1">
              <!-- 顶部标签云 -->
              <div class="mb-4 flex flex-wrap items-center gap-2">
                <span class="rounded-lg bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-slate-500 dark:bg-white/5 dark:text-slate-400">
                  {{ q.question_type }}
                </span>
                <span v-for="tag in (q.knowledge_tags || [])" :key="tag" class="inline-flex items-center gap-1.5 rounded-lg border border-blue-500/20 bg-blue-500/5 px-2.5 py-1 text-[10px] font-black text-blue-600 dark:text-blue-300">
                  <span class="h-1 w-1 rounded-full bg-blue-500"></span> {{ tag }}
                </span>
                <span class="ml-auto flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-black uppercase tracking-wider"
                  :class="q.review_status === '已掌握' ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400' : q.review_status === '复习中' ? 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400' : 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400'">
                  <i class="fa-solid" :class="q.review_status === '已掌握' ? 'fa-circle-check' : q.review_status === '复习中' ? 'fa-spinner' : 'fa-clock'"></i>
                  {{ q.review_status || '待复习' }}
                </span>
              </div>
              
              <!-- 题目摘要 -->
              <p class="line-clamp-3 text-sm font-bold leading-relaxed text-slate-700 transition-colors group-hover:text-slate-900 dark:text-slate-300 dark:group-hover:text-white">
                {{ getSummary(q) }}
              </p>
              
              <!-- 底部元数据 -->
              <div class="mt-6 flex items-center justify-between border-t border-slate-50 pt-4 text-[10px] font-black uppercase tracking-widest text-slate-400 dark:border-white/5">
                <span class="font-mono">Ref: #{{ q.id }}</span>
                <span class="flex items-center gap-1.5"><i class="fa-regular fa-calendar-alt text-blue-500"></i> {{ q.created_at ? new Date(q.created_at).toLocaleDateString() : 'UNKNOWN' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 分页控制：浮动微拟物风格 -->
      <div v-if="totalPages > 1" class="mt-16 flex items-center justify-center gap-2">
        <button @click="goPage(page - 1)" :disabled="page <= 1" class="btn-secondary h-11 w-11 p-0 disabled:opacity-30">
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <div class="flex items-center gap-1.5 rounded-2xl bg-white/50 p-1.5 shadow-sm dark:bg-white/5">
          <template v-for="(p, i) in pageButtons" :key="i">
            <span v-if="p === '...'" class="flex w-8 justify-center font-bold text-slate-400">...</span>
            <button v-else @click="goPage(p)" 
              class="h-9 min-w-[36px] rounded-xl text-xs font-black transition-all"
              :class="p === page ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' : 'text-slate-500 hover:bg-white dark:hover:bg-white/10'">
              {{ p }}
            </button>
          </template>
        </div>
        <button @click="goPage(page + 1)" :disabled="page >= totalPages" class="btn-secondary h-11 w-11 p-0 disabled:opacity-30">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- 底部悬浮操作胶囊：导出专用 -->
    <Transition enter-active-class="transition duration-500 ease-out" enter-from-class="translate-y-20 opacity-0" enter-to-class="translate-y-0 opacity-100" leave-active-class="transition duration-300 ease-in" leave-from-class="translate-y-0 opacity-100" leave-to-class="translate-y-20 opacity-0">
      <div v-if="selectedIds.size" class="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 md:bottom-10">
        <div class="flex items-center gap-6 rounded-full border border-white/20 bg-slate-900/90 px-8 py-4 shadow-[0_20px_50px_rgba(0,0,0,0.3)] backdrop-blur-2xl dark:bg-slate-800/80">
          <div class="flex items-center gap-3 border-r border-white/10 pr-6">
            <div class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 font-mono text-xs font-black text-white outline outline-4 outline-blue-500/20">
              {{ selectedIds.size }}
            </div>
            <span class="text-sm font-black tracking-widest text-white uppercase">Items Locked</span>
          </div>
          <div class="flex items-center gap-4">
            <button @click="doExport" class="btn-primary h-10 px-6 text-xs font-black shadow-lg shadow-blue-500/40">
              <i class="fa-solid fa-file-export mr-2"></i> 生成复习卷
            </button>
            <button @click="clearSelection" class="text-xs font-black tracking-widest text-slate-400 hover:text-white transition-colors">
              RESET
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <QuestionDetailModal
      :open="detailOpen"
      :question="detailQuestion"
      @close="closeDetail"
      @open-image="(src) => emit('open-image', src)"
      @deleted="onDeleted"
      @answer-saved="onAnswerSaved"
      @review-status-changed="onReviewStatusChanged"
      @push-toast="(type, msg) => emit('push-toast', type, msg)"
    />
  </div>
</template>

<style scoped>
/* 列表入场动画 */
.container {
  animation: vaultEntry 0.8s cubic-bezier(0.2, 0, 0, 1) both;
}
@keyframes vaultEntry {
  from { opacity: 0; transform: scale(0.98) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>