# QQBot V1.3 部署方案

> 大肥鱼 QQ 机器人（AstrBot + OpenViking + persona-base + SnowLuma）V1.3 完整部署方案与落地记录。
> 版本代称制：V1.0 = `QQBot-test` / V1.1 = `QQBot` / V1.2 = `QQBot-v11` / **V1.3 = `QQBot-v13`**

## 1. V1.3 是什么

V1.3 = **V1.2 全部能力** + **插件集补齐** + **端口/数据完全隔离** + **C 方案记忆判据**。

| 项 | 内容 |
|---|---|
| 代码基线 | `D:\AI\QQBot-v11`（V1.2） |
| 插件基线 | `D:\AI\QQBot`（V1.1）的 7 个插件目录 |
| 数据基线 | `D:\AI\_data_baseline\real\`（800 条真实 QQ 对话 + 记忆库） |
| 记忆基线 | persona 122 条 + OpenViking `ov-v13` 1567 篇 |
| 落地时间 | 2026-10-27 03:47（Asia/Shanghai） |
| 状态 | **正式版**，V1.0 / V1.1 / V1.2 全部冻结（端口释放、自启禁用、数据只读保留） |

## 2. 五服务栈

| 顺序 | 服务 | 端口 | 数据目录 | 冷启动耗时 |
|---|---|---|---|---|
| 1 | embed（语义嵌入，minilm-384） | 8329 | `persona-base\_embed` | 17 s |
| 2 | OpenViking（记忆库 L1/L2） | 1936 | `ov-data` | 34 s |
| 3 | persona-base（L3 事实 + 遗忘曲线） | 8127 | `persona-base\data\memory.db` | 2 s |
| 4 | AstrBot（机器人主体） | 6381（Dashboard）/ 6382（OneBot WS） | `data` | 21 s |
| 5 | SnowLuma（QQ 客户端） | 5199（WebUI） | `SnowLuma\data` | 2 s |

- **整栈冷启动 141 s**；二次执行 5 s 全跳过——幂等成立。
- 外部依赖（不归 V1.3 管理）：`8326` LLM 网关、`8331` VLM shim。
- 端口与 V1.1 / V1.2 零重叠：V1.2 为 6380 / 1935 / 8126 / 8328。

## 3. 启动与停止

### 启动（幂等，可重复执行）

```powershell
wscript "D:\AI\QQBot-v13\_setup\start-v13-stack.vbs"
```

- Windows 登录后自动执行（快捷方式 `Startup\V13-Stack.vbs.lnk`），桌面 `V1.3.lnk` 可手动启动
- 服务已在跑时不会起第二个进程
- 日志：`D:\AI\QQBot-v13\logs\stack.log`

### 停止

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\AI\QQBot-v13\_setup\stop-v13-stack.ps1"
```

只停 6381/6382/1936/8127/8329/5199 且校验命令行归属；`8326`、`8331` 等外部端口不受影响。

### 为什么必须用 VBScript

2026-10-27 03:20 曾出现 embed / OV / persona 三个服务同时消失，日志末尾是一个 `^C`——它们从 bash/pwsh 会话启动，会话销毁时整个控制台组收到 Ctrl+C。
`wscript.exe` 没有控制台，`Run(..., 0, ...)` 使每个子进程获得隐藏窗口，整条链不再依附任何 shell。**不要再用 bash 或 pwsh 直接起这些服务。**

## 4. 落地验证证据

| 检查 | 结果 | 证据 |
|---|---|---|
| 冷启动 | 141 s，五服务全就绪 | `logs\stack.log` |
| 幂等 | 二次执行 5 s，全跳过 | `logs\stack.log` |
| embed health | `200` `{"ok":true,"port":8329}` | `/health` |
| OV health | `200` `{"status":"ok","healthy":true,"version":"0.5.1.1"}` | `/health` |
| persona health | `200` `{"ok":true,"count":135,...}` | `/health` |
| AstrBot | 6381/6382 LISTENING，`/api/stat` 401（需认证＝活着） | netstat |
| SnowLuma | `[Hook] login detected: UIN=3752002377`，WS 已连 6382 | `logs\snowluma.log` |
| QQ 端到端 | 3.92 s，回复无思维链污染 | `astrbot-v13.log` |

## 5. 记忆层

- persona 135 条：tier0 13 / tier1 39 / tier2 83
- C 方案四件套已接：`RECALL_LEAD_MIN`（领先度判据）、`PROTECTED_TIERS`（protected 豁免）、`cohit`（共激活边）、`TERM_TIERS`（术语分级表）
- 全部新功能**默认关闭**，向后兼容验证通过（新旧参数召回结果逐字相同）
- 13 条真实关系事实来自 SnowLuma 800 条真实对话（id 123–135）

## 6. 回滚

V1.2 环境完整保留在 `D:\AI\QQBot-v11`（冻结，数据未动）。

```powershell
# 1) 停 V1.3
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\AI\QQBot-v13\_setup\stop-v13-stack.ps1"

# 2) 恢复 V1.1/V1.2 自启
powershell -NoProfile -ExecutionPolicy Bypass -File "D:\AI\_governance\scripts\restore_autostart_v11_v12.ps1"

# 3) 禁用 V1.3 自启
Rename-Item "${env:APPDATA}\Microsoft\Windows\Start Menu\Programs\Startup\V13-Stack.vbs.lnk" "V13-Stack.vbs.lnk.disabled"
```

## 7. 已知限制

1. **webchat 回复带思维链前缀**——AstrBot 对 webchat 强制流式，非流式入口未生效；QQ 通道（aiocqhttp）`support_streaming_message=False`，完全干净。
2. **`api.soulter.top` 偶发超时**——t2i 图床，失败不影响文字回复。
3. **TTS 已关闭**——`provider_tts_settings.enable=false`、`kokoro-tts` enable=false，避免 8124 未监听时拖慢回复。
4. **`data_v4.db` 的 `updated_at` 不随新消息更新**——AstrBot `update_conversation()` 不写该字段；按时间查对话以 QQ 客户端为准，已知不修。
5. **venv 是 junction**——`QQBot-v13\venv` → `D:\AI\QQBot-v11\venv`；升级依赖会同时影响 V1.2。
6. **单盘风险**——SnowLuma 与 V1.3 同盘（D:），800 条真实对话副本在 `D:\AI\_data_baseline\real\`。

## 8. 文档索引

| 文档 | 内容 |
|---|---|
| [docs/V1.3-LANDING.md](docs/V1.3-LANDING.md) | 正式落地记录：五服务栈、启动方式、验证证据、回滚 |
| [docs/README-V13.md](docs/README-V13.md) | 交付说明：与 V1.2 的关键差异、数据来源、注意事项 |
| [docs/DELIVERY-ENV-BUILDER.md](docs/DELIVERY-ENV-BUILDER.md) | 交付环境构建方案 |
| [docs/ISOLATION-V11.md](docs/ISOLATION-V11.md) | 版本隔离设计（端口/数据/进程归属） |
| [docs/V1.3-MEMORY-TABLE.md](docs/V1.3-MEMORY-TABLE.md) | 记忆表：persona / OV / 真实对话索引 |
| [docs/V1.3-TERM-MAP.md](docs/V1.3-TERM-MAP.md) | 术语分级表 |
| [docs/V1.3-C-PLAN-CALIBRATION.md](docs/V1.3-C-PLAN-CALIBRATION.md) | C 方案校准 |
| [docs/V1.3-HISTORY-EXTRACT-DECISION.md](docs/V1.3-HISTORY-EXTRACT-DECISION.md) | 历史记忆抽取决策 |
| [docs/V1.3-HISTORY-EXTRACT-REVIEW.md](docs/V1.3-HISTORY-EXTRACT-REVIEW.md) | 历史记忆抽取复核 |
| [docs/V1.3-未完成项-进展-20261027.md](docs/V1.3-未完成项-进展-20261027.md) | 未完成项与进展 |
| [setup/start-v13-stack.vbs](setup/start-v13-stack.vbs) | 幂等启动器（VBScript） |
| [setup/stop-v13-stack.ps1](setup/stop-v13-stack.ps1) | 停止脚本（校验端口归属） |
| [setup/verify_runtime_v11.py](setup/verify_runtime_v11.py) | 运行时自检 |
| [setup/verify_tech_facts_recall.py](setup/verify_tech_facts_recall.py) | 技术事实召回校验 |

## 9. 仓库边界

本仓库只收录**部署方案文档 + 启动/停止/校验脚本**。以下内容不收录：

- `venv/`、`tts/`、`SnowLuma/` 等二进制运行时
- `data/`、`ov-data/`、`logs/`、`*.db` 等运行数据
- `data/cmd_config.json`、`data/config/*.json`、`ov.conf` 等含密钥配置

复现完整运行环境需要按 `docs/DELIVERY-ENV-BUILDER.md` 补齐上述四类内容。

---

*本方案由本地 V1.3 落地记录整理，文档时间戳以各文件标注为准。*