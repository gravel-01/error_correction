# PR: 错题本功能完善 — 错题库 + 复习状态 + Dashboard 重构 + AI 错题分析 + 导入/导出分离

**分支**: `feature/mistake_notebook`
**基于**: `main` (fd8a1d6)

---

## 一、变更概览

本分支在前一次 PR（前后端分离重构 + UI 升级）基础上，实现了五大功能模块：

1. **错题库模块 (ErrorBank)** — 全新的错题浏览、筛选、搜索、导出页面
2. **复习状态系统** — Question 新增 `review_status` 字段，支持「待复习 → 复习中 → 已掌握」状态流转
3. **Dashboard 重构** — 从静态示例数据改为真实后端数据驱动（统计卡片、Chart.js 图表、待复习列表）
4. **AI 错题分析** — 前端完整实现（批量选题分析 + 单题分析），后端骨架路由已就绪（**待接入 LLM**）
5. **导入/导出分离** — 分割页面的「导出错题本」（下载 Markdown）和「导入错题库」（存入数据库）拆分为独立按钮

---

## 二、文件变更清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `backend/db/migrate.py` | 数据库迁移脚本（自动添加 user_answer / updated_at / review_status 列） |
| `frontend/src/components/ErrorBank.vue` | 错题库页面（多条件筛选、分页、批量导出、复习状态显示） |
| `frontend/src/components/QuestionDetailModal.vue` | 题目详情弹窗（笔记编辑、复习状态切换、单题 AI 分析） |
| `frontend/src/components/AiAnalysisModal.vue` | AI 批量错题分析结果展示弹窗 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `backend/db/models.py` | Question 新增 `user_answer`、`updated_at`、`review_status` 三个字段 |
| `backend/db/crud.py` | 新增 `update_user_answer`、`update_review_status`、`get_review_status_stats`、`get_daily_counts`、`get_existing_question_types`、`get_questions_by_ids`、`query_questions` 等函数 |
| `backend/web_app.py` | 新增 8 个 API 路由（见下方 API 清单），`_serialize_question_detail` 增加 review_status/user_answer 等字段；导出路由不再入库 |
| `backend/src/utils.py` | `export_wrongbook` 移除入库逻辑，只负责生成 Markdown 文件 |
| `frontend/src/api.js` | 新增 `fetchErrorBank`、`fetchSubjects`、`fetchQuestionTypes`、`fetchTagNames`、`saveAnswer`、`saveToDb`、`exportFromDb`、`deleteQuestion`、`updateReviewStatus`、`fetchDashboardStats`、`requestAiAnalysis` |
| `frontend/src/components/Dashboard.vue` | 完全重写：移除硬编码数据，改用真实后端 API；新增选题模式 + AI 分析按钮 |
| `frontend/src/components/ActionBar.vue` | 新增「导入错题库」按钮，emit `save-to-db` 事件 |
| `frontend/src/App.vue` | 新增 `error-bank` 视图路由、ErrorBank 组件引入、`doSaveToDb` 处理函数、Dashboard emits 更新 |
| `backend/tests/test_crud.py` | 新增 `TestUpdateReviewStatus`、`TestGetReviewStatusStats`、`TestQueryQuestionsReviewStatus`、`TestGetDailyCounts` 等测试类 |
| `backend/tests/test_web_routes.py` | 新增 `TestUpdateReviewStatusRoute`、`TestDashboardStatsRoute`、`TestErrorBankReviewStatusFilter`、`TestAiAnalysisRoute` 等测试类 |

---

## 三、新增 API 端点

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/api/error-bank` | 错题库统一查询（支持 subject/keyword/question_type/knowledge_tag/review_status/日期/分页） | 完成 |
| GET | `/api/subjects` | 获取所有科目列表 | 完成 |
| GET | `/api/question-types` | 获取所有题型列表 | 完成 |
| PATCH | `/api/question/<id>/answer` | 保存用户答案/笔记 | 完成 |
| PATCH | `/api/question/<id>/review-status` | 更新复习状态（待复习/复习中/已掌握） | 完成 |
| GET | `/api/dashboard-stats` | Dashboard 统计数据（复习状态计数、每日新增、知识点分布） | 完成 |
| POST | `/api/save-to-db` | 将分割好的题目导入错题库（仅入库，不导出文件） | 完成 |
| POST | `/api/export-from-db` | 从数据库按 ID 列表导出 Markdown | 完成 |
| POST | `/api/ai-analysis` | AI 错题分析 | **骨架已就绪，待接入 LLM** |

### 已修改的 API

| 方法 | 路径 | 变更说明 |
|------|------|----------|
| POST | `/api/export` | 不再自动入库数据库，只生成 Markdown 文件并返回下载路径 |

---

## 四、数据库完整模型文档

### 4.1 表结构总览

```
upload_batches  ──1:N──  questions  ──M:N──  knowledge_tags
                              │                    │
                              └── question_tag_mapping ──┘
```

### 4.2 `upload_batches` — 上传批次表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, 自增 | 批次 ID |
| `original_filename` | VARCHAR(255) | NOT NULL | 原始文件名 |
| `subject` | VARCHAR(50) | 可空 | 科目（由 AI 识别） |
| `file_path` | TEXT | 可空 | 文件存储路径 |
| `upload_time` | DATETIME | 默认 UTC now | 上传时间 |
| `created_at` | DATETIME | 默认 UTC now | 记录创建时间 |

### 4.3 `questions` — 题目表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, 自增 | 题目 ID |
| `batch_id` | INTEGER | FK → upload_batches.id | 所属批次 |
| `content_hash` | VARCHAR(64) | UNIQUE, NOT NULL | SHA256 内容指纹（去重用） |
| `question_type` | VARCHAR(20) | 可空 | 题型（选择题/填空题/解答题等） |
| `content_json` | TEXT | 可空 | 题干内容 JSON 字符串，格式见下方 |
| `options_json` | TEXT | 可空 | 选项 JSON 字符串（选择题才有） |
| `has_formula` | BOOLEAN | 默认 False | 是否含公式 |
| `has_image` | BOOLEAN | 默认 False | 是否含图片 |
| `image_refs_json` | TEXT | 可空 | 图片引用列表 JSON |
| `needs_correction` | BOOLEAN | 默认 False | 是否需要 OCR 纠错 |
| `ocr_issues_json` | TEXT | 可空 | OCR 问题列表 JSON |
| `user_answer` | TEXT | 可空 | **[新增]** 用户填写的答案/笔记 |
| `updated_at` | DATETIME | 可空 | **[新增]** 最后更新时间 |
| `review_status` | VARCHAR(10) | 默认 '待复习' | **[新增]** 复习状态：待复习/复习中/已掌握 |
| `created_at` | DATETIME | 默认 UTC now | 记录创建时间 |

#### `content_json` 格式

```json
[
  {"block_type": "text", "content": "已知函数 $f(x) = \\sin(\\omega x + \\varphi)$..."},
  {"block_type": "image", "content": "/images/xxx.png"}
]
```

`block_type` 只有两种：`text`（文本，可含 LaTeX 公式）和 `image`（图片路径）。

#### `options_json` 格式

```json
[
  {"label": "A", "content": "$x = 1$"},
  {"label": "B", "content": "$x = 2$"}
]
```

### 4.4 `knowledge_tags` — 知识点标签表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, 自增 | 标签 ID |
| `tag_name` | VARCHAR(50) | NOT NULL | 标签名称 |
| `subject` | VARCHAR(50) | 可空 | 所属科目 |
| `created_at` | DATETIME | 默认 UTC now | 创建时间 |

唯一约束：`UNIQUE(tag_name, subject)`

### 4.5 `question_tag_mapping` — 题目-标签关联表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `question_id` | INTEGER | PK, FK → questions.id | 题目 ID |
| `tag_id` | INTEGER | PK, FK → knowledge_tags.id | 标签 ID |

### 4.6 数据库迁移

迁移脚本 `backend/db/migrate.py` 在应用启动时自动执行（`web_app.py` 的 `__main__` 块中调用）。

迁移是幂等的：检测列是否已存在，已存在则跳过。新增的三个字段：

```sql
ALTER TABLE questions ADD COLUMN user_answer TEXT;
ALTER TABLE questions ADD COLUMN updated_at DATETIME;
ALTER TABLE questions ADD COLUMN review_status VARCHAR(10) DEFAULT '待复习';
```

---

## 五、导入/导出流程说明

### 分割页面（workspace）的两个按钮

| 按钮 | 调用 API | 功能 |
|------|----------|------|
| 导出错题本（绿色） | `POST /api/export` | 将选中题目生成 Markdown 文件并触发浏览器下载 |
| 导入错题库（靛蓝色） | `POST /api/save-to-db` | 将选中题目存入数据库（去重），不生成文件 |

两个操作互相独立，用户可以只导入不导出，也可以两个都做。

### `/api/save-to-db` 请求/响应

```
POST /api/save-to-db
Content-Type: application/json

{"selected_ids": ["q_0", "q_1", "q_2"]}
```

```json
{
  "success": true,
  "message": "已导入 3 道题目（跳过 0 道重复）",
  "created": 3,
  "duplicates": 0
}
```

入库使用 `content_hash`（SHA256）去重，同一道题不会重复入库。

---

## 六、AI 错题分析 — 后端对接指南

### 6.1 当前状态

前端已完整实现两个 AI 分析入口，都调用同一个后端 API：

| 入口 | 位置 | 说明 |
|------|------|------|
| 批量分析 | Dashboard 页面 → 选择题目 → 「AI 错题分析」按钮 | 选多道题，结果展示在 `AiAnalysisModal.vue` |
| 单题分析 | QuestionDetailModal → 「召唤 AI 助教分析」按钮 | 传单个题目 ID，结果展示在弹窗右侧面板 |

两者都调用 `POST /api/ai-analysis`，区别只是 `question_ids` 数组长度不同。

后端骨架路由已写好（`web_app.py` 中的 `/api/ai-analysis`），当前返回占位数据。

### 6.2 对接步骤

1. **找到骨架路由**：`backend/web_app.py` 中搜索 `@app.route('/api/ai-analysis'`

2. **替换 TODO 区域**：在 `# ── TODO: 替换为真实 AI 分析逻辑 ──` 和 `# ── END TODO ──` 之间实现真实逻辑

3. **可用数据**：
   ```python
   # 题目数据已通过 crud.get_questions_by_ids() 查询好，存在 questions 变量中
   # 每个 question 对象（ORM）包含：
   #
   #   q.id              → 题目 ID（int）
   #   q.content_json    → 题干 JSON 字符串（需 json.loads 解析）
   #   q.options_json    → 选项 JSON 字符串（可能为 None）
   #   q.user_answer     → 用户填写的答案/笔记（可能为 None）
   #   q.question_type   → 题型字符串（选择题/填空题/解答题等）
   #   q.review_status   → 复习状态（待复习/复习中/已掌握）
   #   q.has_formula     → 是否含公式（bool）
   #   q.has_image       → 是否含图片（bool）
   #   q.batch           → 关联的 UploadBatch 对象（q.batch.subject 获取科目）
   #   q.tags            → 关联的标签映射列表
   #                       获取标签名：[m.tag.tag_name for m in q.tags if m.tag]
   ```

4. **建议实现流程**：
   ```python
   from llm import init_model  # 项目已有的 LLM 初始化函数
   import json

   # 1. 构建 prompt
   prompt_parts = []
   for q in questions:
       content = json.loads(q.content_json) if q.content_json else []
       text = " ".join(b["content"] for b in content if b.get("block_type") == "text")
       tags = [m.tag.tag_name for m in (q.tags or []) if m.tag]
       prompt_parts.append(f"题目#{q.id}（{q.question_type}）：{text}\n知识点：{', '.join(tags)}\n用户笔记：{q.user_answer or '无'}")

   # 2. 调用 LLM（建议使用 with_structured_output 或 JSON mode）
   model = init_model("deepseek")  # 或 "ernie"
   # ... 发送 prompt，解析返回

   # 3. 填充 analysis dict（格式见下方）
   ```

5. **返回格式**（前端已按此结构渲染，字段名不可更改）：
   ```json
   {
     "success": true,
     "analysis": {
       "summary": "综合诊断摘要文本",
       "weak_points": ["知识点A", "知识点B"],
       "error_patterns": [
         {
           "pattern": "错因类型名称",
           "description": "详细描述",
           "question_ids": [1, 2]
         }
       ],
       "suggestions": ["建议1", "建议2"],
       "per_question": [
         {
           "question_id": 1,
           "diagnosis": "该题错因分析",
           "hint": "解题提示"
         }
       ]
     }
   }
   ```

6. **限制**：单次最多 20 道题目（前端和后端都有校验）

7. **可选优化**：
   - 将分析结果缓存到数据库（可在 Question 表新增 `ai_analysis_json` 字段）
   - 支持流式返回（SSE），前端可改为逐步渲染

### 6.3 单题分析的前端适配

`QuestionDetailModal.vue` 中的 `triggerAiAnalysis()` 调用 `requestAiAnalysis([question.id])`（传单个 ID 的数组），然后从返回结果中提取该题的 `per_question` 条目：

```javascript
const pq = (a.per_question || []).find(p => p.question_id === props.question.id)
aiReport.value = {
  diagnostic: pq ? pq.diagnosis : a.summary,  // 优先用逐题诊断
  steps: a.suggestions,                         // 复习建议作为步骤展示
  advice: pq ? pq.hint : ''                     // 解题提示
}
```

后端无需为单题分析做特殊处理，统一走 `/api/ai-analysis` 即可。

### 6.4 测试

已有测试覆盖：`backend/tests/test_web_routes.py::TestAiAnalysisRoute`
- `test_empty_ids` — 空 ID 列表返回 400
- `test_missing_ids` — 缺少字段返回 400
- `test_too_many_ids` — 超过 20 道返回 400
- `test_nonexistent_ids` — 不存在的 ID 返回 404
- `test_success` — 正常返回分析结果结构

接入真实 LLM 后，建议补充集成测试（带 `skip_no_api_key` 保护）。

---

## 七、CRUD 函数速查

后端开发者在对接时可能用到的 `backend/db/crud.py` 函数：

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `get_questions_by_ids(db, ids)` | `List[int]` | `List[Question]` | 按 ID 批量查询（含 batch/tags 预加载） |
| `query_questions(db, ...)` | 多条件筛选 | `(List[Question], total)` | 统一查询（科目/标签/题型/关键字/日期/复习状态/分页） |
| `update_review_status(db, id, status)` | `str` | `Question` | 更新复习状态（自动更新 updated_at） |
| `update_user_answer(db, id, answer)` | `str` | `Question` | 更新用户答案 |
| `get_review_status_stats(db)` | 无 | `Dict[str, int]` | 按复习状态分组统计 |
| `get_daily_counts(db, days)` | `int` | `List[Dict]` | 最近 N 天每日新增数 |
| `save_questions_to_db(db, questions, batch_info)` | 题目列表 + 批次信息 | `Dict` | 批量入库（content_hash 去重） |
| `compute_content_hash(content_blocks)` | `List[Dict]` | `str` | 计算题目内容 SHA256 |

---

## 八、测试验证

```bash
# 后端测试（87 passed: 51 crud + 36 routes）
cd backend
D:/Miniforge3/envs/3.13_langchian/python.exe -m pytest tests/test_crud.py tests/test_web_routes.py -v

# 全量后端测试（270 passed, 7 xfailed）
D:/Miniforge3/envs/3.13_langchian/python.exe -m pytest tests/ -v --ignore=tests/test_web_helpers.py

# 前端构建
cd frontend && npx vite build
```

> 注：`test_web_helpers.py` 的 import 错误是之前遗留的（引用了已删除的 `_vite_collect_imports`），非本分支引入。

---

## 九、前端页面结构

```
App.vue
├── workspace    — 录题工作台（上传 → 分割 → 导出/导入）
│   └── ActionBar.vue  — 「导出错题本」+「导入错题库」+「重新开始」
├── dashboard    — 我的错题本（统计 + 待复习列表 + AI 批量分析）
│   ├── QuestionDetailModal.vue  — 题目详情（笔记 + 单题 AI 分析）
│   └── AiAnalysisModal.vue      — AI 批量分析报告
└── error-bank   — 错题库（全量浏览 + 多条件筛选）
    └── QuestionDetailModal.vue  — 题目详情（复用）
```
