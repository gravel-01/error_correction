<script setup>
import { ref, watch, nextTick } from 'vue'
import { isHtml, sanitizeHtml, formatOption } from '../utils.js'
import * as api from '../api.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  question: { type: Object, default: null },
})

const emit = defineEmits(['close', 'open-image', 'deleted', 'answer-saved', 'review-status-changed', 'push-toast'])

const activeTab = ref('content') // 'content' | 'analysis'
const userAnswer = ref('')
const isSaving = ref(false)

// AI 分析相关
const isAnalyzing = ref(false)
const aiReport = ref(null)
const typedText = ref('')

const typeset = async () => {
  await nextTick()
  if (window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
    window.MathJax.typesetPromise()
  }
}

watch(() => props.open, (newVal) => {
  if (newVal && props.question) {
    userAnswer.value = props.question.user_answer || ''
    activeTab.value = 'content'
    aiReport.value = null
    typedText.value = ''
    typeset()
  }
})

const saveAnswer = async () => {
  if (!props.question) return
  isSaving.value = true
  try {
    const data = await api.saveAnswer(props.question.id, userAnswer.value)
    emit('answer-saved', props.question.id, data.user_answer, data.updated_at)
    emit('push-toast', 'success', '答题记录已保存')
  } catch (e) {
    emit('push-toast', 'error', '保存失败')
  } finally {
    isSaving.value = false
  }
}

const triggerAiAnalysis = async () => {
  if (!props.question) return
  isAnalyzing.value = true
  activeTab.value = 'analysis'
  aiReport.value = null
  typedText.value = ''
  try {
    const data = await api.requestAiAnalysis([props.question.id])
    const a = data.analysis || {}
    const pq = (a.per_question || []).find(function (p) { return p.question_id === props.question.id })
    aiReport.value = {
      diagnostic: pq ? pq.diagnosis : (a.summary || '\u6682\u65e0\u8bca\u65ad\u4fe1\u606f'),
      steps: a.suggestions || [],
      advice: pq ? pq.hint : ''
    }
    startTyping()
  } catch (e) {
    emit('push-toast', 'error', 'AI \u5206\u6790\u5931\u8d25: ' + (e instanceof Error ? e.message : String(e)))
    isAnalyzing.value = false
  } finally {
    isAnalyzing.value = false
  }
}

const startTyping = () => {
  let i = 0
  const str = aiReport.value.diagnostic
  const tick = () => {
    if (i < str.length) {
      typedText.value += str.charAt(i)
      i++
      setTimeout(tick, 20)
    } else {
      typeset()
    }
  }
  tick()
}

const doDelete = async () => {
  if (!window.confirm('确定要从题库中永久删除这道题吗？')) return
  try {
    await api.deleteQuestion(props.question.id)
    emit('deleted', props.question.id)
    emit('push-toast', 'success', '题目已移除')
  } catch (e) {
    emit('push-toast', 'error', '删除失败')
  }
}

const changeReviewStatus = async (status) => {
  if (!props.question || props.question.review_status === status) return
  try {
    const data = await api.updateReviewStatus(props.question.id, status)
    props.question.review_status = data.review_status
    emit('review-status-changed', props.question.id, data.review_status, data.updated_at)
    emit('push-toast', 'success', `已标记为「${status}」`)
  } catch (e) {
    emit('push-toast', 'error', '更新状态失败')
  }
}

const reviewStatusOptions = [
  { value: '待复习', icon: 'fa-clock', color: 'orange' },
  { value: '复习中', icon: 'fa-spinner', color: 'amber' },
  { value: '已掌握', icon: 'fa-circle-check', color: 'emerald' },
]
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6">
        <!-- 遮罩层 -->
        <div class="absolute inset-0 bg-slate-950/60 backdrop-blur-md" @click="emit('close')"></div>
        
        <!-- 弹窗主体 -->
        <div class="relative flex h-full max-h-[90vh] w-full max-w-5xl flex-col overflow-hidden rounded-[2.5rem] border border-white/10 bg-white shadow-2xl transition-all dark:bg-[#0F111A]">
          
          <!-- 头部控制栏 -->
          <div class="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-8 py-5 dark:border-white/5 dark:bg-white/5">
            <div class="flex items-center gap-4">
              <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white shadow-lg shadow-blue-500/30">
                <i class="fa-solid fa-file-lines text-lg"></i>
              </div>
              <div>
                <h3 class="text-lg font-black tracking-tight text-slate-900 dark:text-white">题目详情分析</h3>
                <p class="text-[10px] font-black uppercase tracking-widest text-slate-400">Question Reference #{{ question?.id }}</p>
              </div>
            </div>
            
            <div class="flex items-center gap-3">
              <!-- 复习状态切换 -->
              <div class="flex items-center gap-1 rounded-xl bg-slate-100 p-1 dark:bg-white/5">
                <button v-for="opt in reviewStatusOptions" :key="opt.value"
                  @click="changeReviewStatus(opt.value)"
                  class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[10px] font-black uppercase tracking-wider transition-all"
                  :class="(question?.review_status || '待复习') === opt.value
                    ? opt.color === 'emerald' ? 'bg-emerald-500 text-white shadow-sm' : opt.color === 'amber' ? 'bg-amber-500 text-white shadow-sm' : 'bg-orange-500 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-300'">
                  <i class="fa-solid" :class="opt.icon"></i> {{ opt.value }}
                </button>
              </div>
              <div class="mx-1 h-6 w-px bg-slate-200 dark:bg-white/10"></div>
              <button @click="doDelete" class="h-10 w-10 rounded-xl text-slate-400 hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-500/10 transition-all">
                <i class="fa-regular fa-trash-can"></i>
              </button>
              <div class="mx-2 h-6 w-px bg-slate-200 dark:bg-white/10"></div>
              <button @click="emit('close')" class="h-10 w-10 rounded-xl bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-400 transition-all">
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>

          <!-- 内容主体 -->
          <div class="flex flex-1 flex-col overflow-hidden md:flex-row">
            <!-- 左侧：题干内容 (滚动区) -->
            <div class="flex-1 overflow-y-auto border-r border-slate-100 p-8 dark:border-white/5">
              <!-- 核心题干 -->
              <div class="question-view">
                <template v-for="(b, i) in question?.content_json" :key="i">
                  <div v-if="b.block_type === 'text' && isHtml(b.content)" v-html="sanitizeHtml(b.content)" class="question-text mb-6 text-lg font-bold leading-relaxed text-slate-800 dark:text-slate-200"></div>
                  <p v-else-if="b.block_type === 'text'" class="mb-6 text-lg font-bold leading-relaxed text-slate-800 dark:text-slate-200">{{ b.content }}</p>
                  <img v-else-if="b.block_type === 'image'" :src="b.content" class="mb-6 max-w-full cursor-zoom-in rounded-2xl border border-slate-200 shadow-sm dark:border-white/10" @click="emit('open-image', b.content)" />
                </template>

                <!-- 选项 -->
                <div v-if="question?.options_json" class="mt-8 grid gap-3">
                  <div v-for="(opt, idx) in question.options_json" :key="idx" class="rounded-2xl border border-slate-100 bg-slate-50/50 p-4 text-sm font-bold text-slate-700 dark:border-white/5 dark:bg-white/5 dark:text-slate-300">
                    {{ formatOption(opt) }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧：交互与分析 (侧边栏) -->
            <div class="w-full bg-slate-50/30 md:w-[400px] dark:bg-black/20">
              <!-- Tab 切换 -->
              <div class="flex border-b border-slate-100 dark:border-white/5">
                <button @click="activeTab = 'content'" class="flex-1 py-4 text-xs font-black uppercase tracking-widest transition-all" :class="activeTab === 'content' ? 'border-b-2 border-blue-600 text-blue-600 dark:text-indigo-400' : 'text-slate-400'">我的笔记</button>
                <button @click="activeTab = 'analysis'" class="flex-1 py-4 text-xs font-black uppercase tracking-widest transition-all" :class="activeTab === 'analysis' ? 'border-b-2 border-blue-600 text-blue-600 dark:text-indigo-400' : 'text-slate-400'">AI 深度解析</button>
              </div>

              <div class="h-full overflow-y-auto p-6 pb-24">
                <!-- Tab 1: 笔记与答案 -->
                <div v-if="activeTab === 'content'" class="space-y-6">
                  <div>
                    <label class="mb-3 block text-[10px] font-black uppercase tracking-widest text-slate-400">我的错因/心得笔记</label>
                    <textarea v-model="userAnswer" rows="6" placeholder="记录下当时的解题思路，或者标记这里错在哪里了..." class="w-full rounded-2xl border border-slate-200 bg-white p-4 text-sm font-medium outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 dark:border-white/5 dark:bg-white/5 dark:text-white"></textarea>
                  </div>
                  <button @click="saveAnswer" :disabled="isSaving" class="btn-primary w-full h-12">
                    <i class="fa-solid" :class="isSaving ? 'fa-circle-notch fa-spin' : 'fa-save'"></i>
                    {{ isSaving ? '同步中...' : '保存学习笔记' }}
                  </button>
                  <button @click="triggerAiAnalysis" class="group flex w-full items-center justify-center gap-2 rounded-2xl border border-blue-500/20 bg-blue-500/5 py-4 text-sm font-black text-blue-600 transition-all hover:bg-blue-500/10 dark:text-indigo-400">
                    <i class="fa-solid fa-wand-magic-sparkles animate-pulse"></i> 召唤 AI 助教分析
                  </button>
                </div>

                <!-- Tab 2: AI 解析报告 -->
                <div v-else class="space-y-6">
                  <div v-if="isAnalyzing" class="flex flex-col items-center justify-center py-20">
                    <div class="mb-4 h-12 w-12 animate-bounce rounded-full bg-indigo-500/20 flex items-center justify-center">
                       <i class="fa-solid fa-brain text-indigo-500"></i>
                    </div>
                    <p class="text-xs font-black uppercase tracking-widest text-indigo-500 animate-pulse">Thinking...</p>
                  </div>
                  <div v-else-if="aiReport" class="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
                    <div class="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-5">
                      <h4 class="mb-3 flex items-center gap-2 text-xs font-black uppercase text-indigo-600 dark:text-indigo-400">
                        <i class="fa-solid fa-microchip"></i> 认知诊断诊断报告
                      </h4>
                      <p class="text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                        {{ typedText }}<span class="inline-block h-4 w-1 animate-blink bg-indigo-500 align-middle ml-1"></span>
                      </p>
                    </div>
                    
                    <div v-if="typedText.length > 10">
                      <h4 class="mb-4 text-xs font-black uppercase tracking-widest text-slate-400">正确路径解构</h4>
                      <div class="space-y-4 border-l-2 border-slate-200 pl-6 dark:border-white/10">
                        <div v-for="(step, idx) in aiReport.steps" :key="idx" class="relative">
                          <span class="absolute -left-[31px] flex h-[14px] w-[14px] items-center justify-center rounded-full bg-blue-600 text-[8px] font-black text-white outline outline-4 outline-white dark:outline-[#0F111A]">
                            {{ idx + 1 }}
                          </span>
                          <p class="text-sm font-bold text-slate-700 dark:text-slate-300">{{ step }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="flex flex-col items-center justify-center py-20 text-slate-400">
                    <i class="fa-solid fa-robot text-4xl mb-4 opacity-20"></i>
                    <p class="text-xs font-bold uppercase tracking-widest">请先点击"召唤 AI 助教"</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-fade-enter-active, .modal-fade-leave-active { transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1); }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; transform: scale(0.95); }

@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
.animate-blink { animation: blink 0.8s infinite; }

.question-text :deep(table) {
  @apply my-6 w-full rounded-xl border border-slate-200 bg-white/50 text-sm overflow-hidden;
}
.question-text :deep(th) {
  @apply bg-slate-100 p-3 text-left font-black dark:bg-white/5;
}
.question-text :deep(td) {
  @apply border-t border-slate-100 p-3 dark:border-white/5;
}
</style>