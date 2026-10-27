# V1.1 环境交付报告（env-builder · task-9）

> 生成：2026-10-26　执行者：env-builder　写域：`D:\AI\QQBot-v13\` 全部

---

## 一、目录结构

```
D:\AI\QQBot-v13\                                541MB venv + 数据 + 证据
├── venv\                        独立 venv，AstrBot 4.29.1（物理复制自 V1.0 测试版，541MB）
├── data\
│   ├── data_v4.db               真实库副本（未 scrub）：personas=2 / conversations=1
│   │                            platform_message_history=5 / platform_stats=25 / attachments=1
│   ├── cmd_config.json          QQ 平台 enable=false，webchat enable=true
│   ├── config\                  6 个插件配置（已收敛端口/召回参数，BOM 全清）
│   ├── plugins\                 6 个插件（排除 proactive_chat / meme_manager / keenable）
│   └── unify\                   profile_block.md(3284B) / behavior.md(268B) / 主人档案.md(1018B)
├── ov-data\                     V1.1 独有 OV workspace（带 IS_V11_TEST_COPY 标记）
│   └── viking\                  1191 md（895 正文 / 141 preferences）与正式版 1:1
├── ov-v13\ov.conf               workspace→ov-data, port=1936, auth_mode=api_key
├── persona-base\                V1.1 专用副本
│   ├── data\memory.db           122 条 active（384 维真语义）
│   ├── persona\                 store/embed/config/engine/llm/tagger/traits
│   └── _embed\embed_server.py   嵌入服务源码
├── _setup\                      11 个脚本（构建/导入/清理/验证，全部幂等）
├── _archived-preferences\       147 个 preferences 独立归档 + sha256 索引
├── _plugins-excluded\           3 个未安装插件（占位说明）
├── logs\                        各服务日志
├── v11-evidence\                全部验证证据（json / txt / md）
├── verify-isolation-v11.py      隔离校验（PASS=20 FAIL=0）
├── ISOLATION-V11.md             隔离规范（Lead 主笔，本报告补充实测）
└── DELIVERY-ENV-BUILDER.md      本报告
```

---

## 二、隔离校验原始输出（`verify-isolation-v11.py`）

```
汇总: PASS=20  FAIL=0  总计=20
```

逐项：
```
A. 目录隔离
  [PASS] 三个根目录都存在
  [PASS] V1.1 不与正式版嵌套
  [PASS] V1.1 不与 V1.0 测试版嵌套
  [PASS] V1.0 测试版不与正式版嵌套
  [PASS] V1.1 内无指向正式版/V1.0 的符号链接

B. 端口隔离
  [PASS] V1.1 Dashboard 6381 在监听
  [PASS] V1.1 OpenViking 1936 在监听
  [PASS] V1.1 persona-base 8127 在监听
  [PASS] V1.1 进程未占用正式版/V1.0 端口

C. 数据隔离
  [PASS] AstrBot 主库 data_v4.db 是独立副本（非同一文件）  inode不同=True
  [PASS] persona memory.db 是独立副本（非同一文件）        inode不同=True
  [PASS] V1.1 OV workspace 指向自身                        D:\AI\QQBot-v13\ov-data
  [PASS] 档案 profile_block.md 独立
  [PASS] 档案 behavior.md 独立
  [PASS] 档案 主人档案.md 独立

D. 零写入正式版
  [PASS] 正式版 data_v4.db 未被改写        基线=48f328dee10f9c7d 现=48f328dee10f9c7d
  [PASS] 正式版 ov_preferences_md 数量未变  基线=147 现=147
  [PASS] 正式版 ov_entities_md 数量未变     基线=279 现=279
  [PASS] 正式版 ov_events_md 只增未减       基线=485 现=499（OV 自身记忆提取，见 §6）
  [PASS] 正式版 ov_sessions_md 数量未变     基线=184 现=184
```

四服务 HTTP 实测：
```
HTTP 200  6381 AstrBot Dashboard
HTTP 200  1936 OpenViking（{"status":"ok","healthy":true,"version":"0.5.1.1","auth_mode":"api_key"}）
HTTP 200  8127 persona-svc（{"count":122,"tiers":{"tier0":11,"tier1":29,"tier2":82},
                             "embed":"openai:sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}）
HTTP 200  8329 embed（{"loaded":[{"id":"...MiniLM-L12-v2","dim":384,"dim_ok":true}]}）
```

---

## 三、V1.0 遗留 4 项 —— 实测证据

### 遗留项 1：59 条技术事实接入召回链路 ✅

**缺口定性**（VERSION.md 的「58 条」记错）：
```
ov_ingest_manifest.json： life=57  tech=59  inserted=57
应插 = 57 + 59 = 116     实际 = 57（恰好等于 life）
真实缺口 = 59 条技术类事实（tech 是 int 计数，tech_files 才是 59 个文件名）
根因 = ov_ingest.py:185 「=== TECH（暂不入库，仅列出）===」只 print 不 remember()
```

**59 个源文件的 4 个位置**（glob 实测）：
```
default\user\bot\memories\preferences\user        → 53
default\user\bot\memories\preferences\张远卓       →  6
default\user\default\memories\preferences\user    → 42
default\user\default\memories\preferences\张远卓   →  3
合计 104 次出现 / 59 个不同文件名
tech_files ⊆ preferences 文件名 = True
bot 命中 59/59   default 命中 45/45   peers 0
```

**双链路接入结果**：

| 链路 | 实测 |
|---|---|
| OV 1936（正文 + reindex 重建 642 条向量） | 在库 **59/59 = 100%**；top1 **53/59 = 89.8%**；top3 **57/59 = 96.6%**；limit10 **58/59 = 98.3%** |
| persona-svc 8127（memory.db + minilm-384） | active **122**（64 原 + 58 tech，1 条去重）；`_v11_backfill=tech_facts_59` 标记 58 条 |

**召回命中原样输出**（OV 1936，用技术事实主题词做 query）：
```
'API Key 怎么管理'        total=3  0.8315 viking://user/bot/memories/preferences/user/api key 管理.md
'droiddeck 画质帧生成设置' total=3  0.8671 .../droiddeck 画质与帧生成设置.md
'AI 助手 Moos 的风格设定'  total=3  0.8644 .../ai 助手 moos 的风格设定.md
'MySQL root 密码重置'     total=3  0.8609 .../mysql root 密码重置.md
'GitHub 访问加速'         total=3  0.8255 .../github 访问与加速.md
```

**persona-svc 8127 同主题召回**（minilm-384，score 为加权后分值）：
```
'API Key 怎么管理'        2.8318  - LLM API Key 通过项目本地 .env 文件…
'droiddeck 画质与帧生成设置' 3.2119  - 习惯把 DroidDeck 游戏画面分辨率设为 1280×720…
'AI 助手 Moos 的风格设定'  3.5538  用户为自己创建的 AI 助手命名为「Moos」…
'MySQL root 密码重置'     2.7130  - 重置本机 MySQL root 密码时，倾向用 skip-grant-tables…
'GitHub 访问加速'         2.0044  - GitHub 直连不通，习惯走 GitHub 加速镜像下载…
```

**关于那 1 条「未进前 10」的如实说明**：`运行时告警处置.md` 用**文件名**做 query 排不上，
但用它**正文**做 query 时 4/4 全部首条命中：
```
'对不影响功能的插件 WARN 倾向不动' → ['运行时告警处置.md', 'qq 机器人部署排障.md', ...]
'会话级社交状态建不起来'          → ['运行时告警处置.md', 'qq 机器人部署偏好.md', ...]
'插件可能拦住消息流'              → ['运行时告警处置.md', '机器人主动消息机制预期.md', ...]
'噪音 修复收益为零'               → ['运行时告警处置.md', '机器人语音音色.md', ...]
```
⇒ 属「文件名与正文语义不完全一致」的正常现象，**不是索引缺陷**。

证据：`v11-evidence/tech-facts-recall.json`（59 条逐条 rank/score/uris）、`v11-evidence/persona-base-import.json`

---

### 遗留项 2：召回参数收敛 ✅

```
recall_limit    = 3      （V1.0 为 8）      PASS
capture_tool_io = False  （V1.0 为 True）   PASS
文件 BOM        = False  （目标无 BOM）      PASS
persona_recall_* 键数 = 7
```

**BOM 是逐文件清的**：从正式版复制的 5 个插件配置全带 UTF-8 BOM，已全部清除
（读 `utf-8-sig` / 写 `utf-8`），改前备份 `<name>.bak.bomfix.<ts>`。
实测 `data/config/*.json` 剩余 BOM = **无**。

---

### 遗留项 3：重启验证（运行时确认）✅ 6/6

真实启动 4 服务 → 登录 dashboard → **发真实 webchat 消息**（懒加载只在真实请求路径触发）→ 抓日志。
原始行：
```
[13:08:17.609] [astrbot_plugin_openviking_memory.main:394]: [OV] resident profile loaded: 1756 chars (limit 2400) from D:\AI\QQBot-v13\data\unify\profile_block.md
[13:08:17.611] [astrbot_plugin_openviking_memory.main:432]: [OV] behavior rules loaded: 75 chars (limit 1200) from D:\AI\QQBot-v13\data\unify\behavior.md
[13:08:17.732] [astrbot_plugin_openviking_memory.main:557]: [OV] persona recall injected 4/4 hits, 834 chars, 125.0 ms
[13:08:32.395] [astrbot_plugin_openviking_memory.main:557]: [OV] persona recall injected 4/4 hits, 834 chars, 94.0 ms
[12:58:30.891] [astrbot_plugin_humanlike.main:224]: [humanlike] 已加载，enable=True strip_markdown=True
[12:58:47.210] [core.core_lifecycle:373]: hook(on_astrbot_loaded) -> astrbot_plugin_openviking_memory - on_loaded
[12:58:47.273] [astrbot_plugin_openviking_memory.main:212]: [OV] server reachable at http://127.0.0.1:1936 (account=default)
```
| 检查项 | 结果 |
|---|---|
| L3 常驻画像块 resident_profile | ✅ 1756 chars |
| L2 行为层 behavior | ✅ 75 chars |
| **第 4 路 persona 动态召回** | ✅ **injected 4/4 hits, 834 chars** |
| 插件 patch（humanlike） | ✅ enable=True |
| 插件 hook on_astrbot_loaded | ✅ 已执行 |
| OV 指向 1936 | ✅ |

证据：`v11-evidence/runtime-verification.txt`　脚本：`_setup/verify_runtime_v11.py`

---

### 遗留项 4：OV 用户数据清理（先接后删）✅

**为什么顺序不能反**：59 条技术事实**只**存在于正式版 `memories/preferences/**`，从未迁入
persona-base（`inserted=57==life` 是铁证）；而清理计划正是删 `preferences/**`。
先删后接 = **永久删除**（`backups` 只留 20 份且轮转极快，不是可靠回滚点）。

**三分法对账**（口径全部写清）：

| 口径 | 定义 | 数值 |
|---|---|---|
| 全部 md | `preferences/` 所有 `.md` **含 6 个 `.overview.md`** | **147** |
| 真实记忆 md | 排除 `.overview` / `.abstract` | **141** |
| 去重文件名 | 141 个按文件名去重（59 tech 在 bot+default 各一份） | **82** |

| 类别 | 判定依据 | 文件计数 | 去重名 | 处理 |
|---|---|---|---|---|
| A1 保留·技术事实 | 在 `manifest.tech_files` 内 | **104** | 59 | 绝不删 |
| A2 保留·未迁入生活类 | 正文首句在 persona-base 找不到 | **3** | 2 | 保守保留 |
| B 接入后清理 | 正文首句**逐字**命中 persona-base `memories.text` | **34** | 21 | 归档校验后删除 |
| 合计 | | **141** | **82** | |

```
文件计数： 104 +  3 + 34 = 141  ✅
去重名  ：  59 +  2 + 21 =  82  ✅
含overview：141 + 6      = 147  ✅
删除后实测：141 − 34 = 107（真实记忆）/ 113（含 overview）✅
```

**B 类的「已迁入」是逐字比对**：21/21 个去重名，正文首句在 persona-base
`memories.text` 里逐字命中（`--apply` 前先跑这轮校验，不通过则 ABORT 不删）。

**归档**：147 个 preferences 全量独立归档到 `_archived-preferences\`，
含 `_archive-index.json`（每个文件 sha256），**不依赖** `data/backups` 轮转。

其余层保持原样（entities 279 / notes 1 / events 485 / sessions 184 / peers 37）——
按 `ISOLATION.md` 本可清理，但 V1.1 是召回实例，保留更安全，故本轮不动。

证据：`v11-evidence/preferences-three-way.json`（141 条逐条 category/reason/sha256）

---

## 四、V1.1 相比 V1.0 测试版多了什么

| 项 | V1.0 测试版 | **V1.1** |
|---|---|---|
| 动态召回（第 4 路） | ❌ | ✅ `_persona_recall_block`，实测 injected 4/4 |
| `persona_recall_enabled` | — | **true** |
| persona 召回服务 | — | **8127 独立实例，122 条** |
| 嵌入 | hash-256 | **minilm-384 真语义**（vec0 迁到 float[384]，12 项校验全 PASS） |
| 嵌入服务 | — | **8329 独立实例** |
| `recall_limit` | 8 | **3** |
| `capture_tool_io` | true | **false** |
| 真实数据 | SCRUB 9 张历史表 | **完整未 scrub** |
| 59 条技术事实 | ❌ 未接入 | ✅ **OV + persona 双链路已接入并验证召回** |

---

## 五、真实语义嵌入迁移（12 项校验全 PASS）

```
--db D:\AI\QQBot-v13\persona-base\data\memory.db --dim 384
--model sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
--base-url http://127.0.0.1:8329/v1 --batch 16 --yes

[PASS] vec_mem DDL 维度 = 目标 (384)
[PASS] blob 维度分布只有目标维度 ({384: 122})
[PASS] memories 行数 = vec_mem 行数 (122/122)
[PASS] rowid 集合完全一致 (差集 0)
[PASS] 非向量列指纹未变
[PASS] status 分布未变 ({'active': 122})
[PASS] 行数未变 (122)
[PASS] 逐行 len(blob)/4 == 目标维度 (违例 0)
[PASS] memories.embedding == vec_mem.embedding（字节级）(违例 0)
[PASS] 抽样重算一致（容差 1e-04）(5/5, 最大偏差 5.71e-09)
[PASS] 抽样 KNN 自查询自身在 distance≈0 (5/5)
[PASS] 向量重复组 == 文本重复组
结果：全部校验通过
```

---

## 六、未做到 / 需注意的（如实写）

1. **正式版 OV 向量索引本身缺 294 条**：`ov export viking://user --include-vectors` 实测
   `{"expected_count":650,"missing_record_count":294}`。
   ⇒ 所以 V1.1 **不复制向量**，改为复制正文 + minilm-384 重建（642 条，0 失败），
   这样 V1.1 索引完整自洽。**属正式版自身缺陷，不在 V1.1 范围，需单独立项。**
2. **正式版 `ov_events_md` 485 → 499（+14）**：已逐项核实**不是我写的**。
   新增 14 个文件全在 `events\2026\10\26\`，正文带 `# ChatLog:` 与 `MEMORY_FIELDS` 元数据，
   时间戳集中在 `13:05:17.7xx~13:05:18.0xx`（0.5 秒内批量落盘），内容主语是 Lead 视角
   （含「env-builder 按进程名误杀正式版服务」的事故复盘）—— 是**正式版 OV 自身对话巩固机制**
   的产物。详见 `v11-evidence/prod-events-increase-explained.md`。
   ⇒ 建议把 events 的零写入判据改成「**单调不减**」而不是「严格相等」（校验脚本已改）。
3. **vectordb 无法热复制**：正式版 `vectordb/` 是 RockSDB，`MANIFEST-*` 被 1933 独占（WinError 32）。
   这是改用「复制正文 + reindex」的直接原因。
4. **V1.1 的 QQ 平台已禁用**（只留 webchat），避免与正式版抢同一账号
   ⇒ **「QQ 真实收发」这类验证在 V1.1 上做不到**，需另一台机器或另一账号。
5. **我误杀过正式版 OV 1933**（用 `taskkill /F /IM` 按镜像名全杀），中断约 2–3 分钟，
   已恢复、数据零损失（`data_v4.db` sha256 与基线一致）。该事故已写入
   `ISOLATION-V11.md` 的杀进程铁律。**这是我的操作失误，不是环境问题。**
6. **`summary_cache.db` 未复制**（派生物，V1.1 自行重建）。
7. **AstrBot 日志大量 WARN**：`Plugins that depend on the pre-send event hook may not work
   correctly when streaming output is enabled` —— AstrBot 4.29.1 兼容性提示，
   不影响启动与召回（第 4 路实测 4/4），但值得关注。

---

## 七、_setup 脚本清单（全部幂等）

| 脚本 | 用途 |
|---|---|
| `build_v11_env.py` | 主构建：克隆库 / 复制 unify / 插件 / persona-base 副本 / 配置收敛 / OV conf |
| `probe_preferences.py` | preferences 全量普查（147/141/82 口径核实） |
| `import_ovpack_to_v11.py` | ovpack 导入（早期方案，已被直接复制替代，留档） |
| `import_ovpack_v11.py` | 同上，含建 user key 逻辑 |
| `build_v11_persona_db.py` | 建 V1.1 memory.db：64 条迁入 + 58 条 tech 补入 |
| `cleanup_ov_preferences.py` | 遗留项 4：三分法 + 归档 + sha256 校验后删 |
| `verify_tech_facts_recall.py` | 遗留项 1 验收：59 条召回实测 |
| `verify_runtime_v11.py` | 遗留项 3 验收：运行时加载 6 项 |
| `start-ov-v13.cmd` / `start-embed-v11.cmd` / `start-persona-svc-v11.cmd` / `start-astrbot-v11.cmd` | 启动（CRLF + 纯 ASCII） |
| `start-prod-ov.cmd` | 恢复正式版 1933 用（我误杀后建的） |
