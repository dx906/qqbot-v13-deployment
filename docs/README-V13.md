# V1.3 交付说明

> 版本代称制：V1.0 = `QQBot-test` / V1.1 = `QQBot` / V1.2 = `QQBot-v11` / **V1.3 = `QQBot-v13`（本目录）**

## 1. 定位

V1.3 = **V1.2 的全部能力** + **插件集补齐** + **端口/数据完全隔离**。

- 代码基线：`D:\AI\QQBot-v11`（V1.2）
- 插件基线：`D:\AI\QQBot`（V1.1）的 7 个插件目录
- 数据基线：`D:\AI\_data_baseline\real\`（真实对话 + 记忆库）
- 记忆基线：V1.2 的 persona 122 条 + OV `ov-v13` 1567 篇

## 2. 服务与端口（与 V1.1 / V1.2 零重叠）

| 服务 | 端口 | 启动方式 | 日志 |
|---|---|---|---|
| AstrBot | 6381 (dashboard) / 6382 (OneBot WS) | `_setup\start-v13.cmd` | `logs\astrbot-v13.log` |
| OpenViking | 1936 | `_setup\start-ov1936.cmd` | `logs\ov-v13.log` |
| persona-svc | 8127 | `_setup\start-persona-svc-v13.cmd` | `logs\persona-svc-v13.log` |
| embed-svc | 8329 | `_setup\start-embed-8329.cmd` | `logs\embed-v13.log` |
| SnowLuma | 5199 (WebUI) → ws 6382 | `SnowLuma\start-snowluma.vbs` | `SnowLuma\logs\` |

启动顺序：embed(8329) → OV(1936) → persona(8127) → AstrBot(6381/6382) → SnowLuma。

## 3. 与 V1.2 的关键差异

| 项 | V1.2 | V1.3 |
|---|---|---|
| 插件 | 6 个（缺 meme_manager） | **7 个**（补齐 `astrbot_plugin_meme_manager`） |
| venv | 独立 546 MB | **junction → `D:\AI\QQBot-v11\venv`**（节省 546 MB，见 §5 注意） |
| ov-data | `ov-v11` | `ov-v13`（1567 md） |
| persona 库 | 122 条 | 122 条 + `ov_mirror` 100 文件 |
| 端口 | 6380/1935/8126/8328 | **6381/6382/1936/8127/8329** |

## 4. 真实数据

- 真实 QQ 对话：**800 条**（SnowLuma `messages.db`，2026-10-22 23:55 → 10-25 17:20）
- 真实会话样本：33 条（AstrBot `conversations` 表 `dafeiyu:909163309`）
- 记忆：persona 122 条 / OV 1567 篇 / angel_memory 29 条
- 索引：`D:\AI\V1.3-MEMORY-TABLE.md`、`D:\AI\_v13_migration\`

## 5. 注意

1. **venv 是 junction**：`QQBot-v13\venv` → `D:\AI\QQBot-v11\venv`。升级 V1.3 依赖会**同时影响 V1.2**。若要独立，删 junction 后重建。
2. **`astrbot.exe` 不可直接用**：`venv\Scripts\astrbot.exe` 是 V1.0 遗留 launcher，内嵌 `QQBot-test\venv` 路径。启动脚本已改为 `python.exe -c "from astrbot.cli.__main__ import cli; ..."`。
3. **`ov.conf` 不入库**：含 root key，在 `.gitignore` 的黑名单里。clone 后需手工放回 `ov-v13\ov.conf`。
4. **`data\config\*.json` 不入库**：含 API key。clone 后从 V1.2 复制并改端口。
5. 日志 UTF-8：启动脚本已设 `PYTHONIOENCODING=utf-8`，否则 emoji 会让 loguru handler 崩溃。

## 6. 已验证

- 四服务全部 LISTENING（6381/1936/8127/8329）
- webchat 端到端：LLM 正常回
- **真实 QQ 端到端**：3.92 s（`在吗` → `在的，刚还坐着没动…`）
- OV 检索：1567 md 可检索
- persona：122 条，tier0 分布 11/29/82