# 上游规则源与同步聚合说明

本文档记录 `Proxy-Rules` 当前采用的活跃上游仓库、替换掉的失效/陈旧上游，以及 `scripts/sync_rules.py` 的同步、清洗、聚合与校验逻辑。

## 一、活跃上游清单（2026-11-25 核验）

| Source ID | 仓库 | 分支 | 许可证 | 引入文件数 | 用途与覆盖范围 |
| :--- | :--- | :--- | :--- | ---: | :--- |
| `ios_rule_script` | [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | `master` | GPL-2.0 | 24 | Direct、Social、Video、Tech、PayPal、Game、China、Proxy 基础规则 |
| `rule_file` | [haha-miao/rule_file](https://github.com/haha-miao/rule_file) | `main` | NOASSERTION | 3 | Emby 直连/代理、Crypto 规则 |
| `ai_proxy_rules` | [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | `main` | MIT | 7 | 每日自动同步：OpenAI / ChatGPT / Codex、Anthropic / Claude Code、Google AI / Gemini / Antigravity、xAI / Grok、Cursor、Factory、Zed（含域名、官方 CIDR/ASN、进程名） |
| `meta_rules_dat` | [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | `meta` | GPL-3.0 | 5 | 每日由 `v2fly/domain-list-community` 自动构建：`category-ai-!cn`（海外 AI 与开发工具全集）、`ibkr`（盈透 21 个全球域名含 `ibllc.com`）、`futu`、`longbridge`、`schwab` |
| `sukka_ruleset` | [SukkaLab/ruleset.skk.moe](https://github.com/SukkaLab/ruleset.skk.moe) | `master` | AGPL-3.0 | 1 | `SukkaW/Surge` 官方镜像：`Clash/ip/ai.txt`，自动同步 OpenAI 官方 `chatgpt-voice.json` 语音 IP 段与 Anthropic `AS399358` |
| `broker_rules` | [forecho/broker-rules](https://github.com/forecho/broker-rules) | `main` | AGPL-3.0 | 1 | 券商聚合规则 `rule/Clash/Broker.yaml`：富途 / Moomoo（含 macOS 16.31 实测域名与腾讯云 IM v6 端点 + 63 条交易/行情 IP-CIDR）、长桥、老虎、嘉信、雪盈、复星、华盛、TradingView、卓锐 |
| `lingjing_shadowrocket_rules` | [LingJingMaster/Shadowrocket-Rules](https://github.com/LingJingMaster/Shadowrocket-Rules) | `main` | MIT | 1 | 活跃维护的券商主源 `HK_Broker.list`（原个人 fork 的上游父仓库），补充富途 / 老虎 / 雪盈 OpenAPI / 盈透等规则 |

## 二、已替换的失效 / 陈旧上游

| 原 Source ID | 原仓库 | 停更 / 问题原因 | 替代方案 |
| :--- | :--- | :--- | :--- |
| `additional_rule_for_clash` | `Accademia/Additional_Rule_For_Clash` | 最后推送停留在 2026-05-14，仅提供 5 条 Grok 规则，且含未加 `no-resolve` 的单 IP（`17.253.4.125/32`），会提前触发本地 DNS 解析 | `ai_proxy_rules` (`rules/clash/x-ai.yaml`) + `meta_rules_dat` (`geo/geosite/category-ai-!cn.yaml`) |
| `skywalker_clash_rules` | `SkywalkerJi/Clash-Rules` | 更新滞后（2026-09-10），且 `Anthropic.yaml` 混入 `ubuntu.com`、`snapcraft.io`、`facebook.net`、`githubusercontent.com` 等污染规则；`Gemini.yaml` 含过宽 `apis.google.com` 与 `DOMAIN-KEYWORD,colab`，缺少 Antigravity 域名 | `ai_proxy_rules` (`anthropic.yaml`、`google-ai.yaml`、`cursor.yaml`) + `meta_rules_dat` (`category-ai-!cn.yaml`) + `overrides/clash/AI.yaml` |
| `shadowrocket_rules` | `hanjl7/Shadowrocket-Rules` | 为 `LingJingMaster/Shadowrocket-Rules` 的旧 fork，停留在 2026-06-19，缺少后续富途/雪盈/盈透等更新 | 直接跟踪上游 `lingjing_shadowrocket_rules` (`LingJingMaster/Shadowrocket-Rules`) + `broker_rules` + `meta_rules_dat` |
| `ios_rule_script`（仅 OpenAI 单文件） | `blackmatrix7/ios_rule_script` (`OpenAI_No_Resolve.yaml`) | OpenAI 规则更新偏慢，缺少 `chatgpt.site`、`oaistatsig.com`、`crixet.com`、OpenAI 官方 `199.47.142.0/23` / `AS401518` 与 ChatGPT Voice IP 段 | `ai_proxy_rules` (`openai.yaml`) + `meta_rules_dat` (`category-ai-!cn.yaml`) + `sukka_ruleset` (`Clash/ip/ai.txt`) |

## 三、关键目标覆盖摘要

### 1. 国外 AI / 开发工具（`rules/clash/AI.yaml` & `rules/shadowrocket/AI.list`）

- **Claude / Claude Code（Anthropic）**：
  - 域名：`anthropic.com`、`claude.ai`、`claude.com`（含 `code.claude.com` / `platform.claude.com`）、`claude.app`、`claude.dev`、`claude.new`、`claude.site`、`clau.de`、`claudeusercontent.com`、`claudemcpclient.com`、`claudemcpcontent.com`、`claudepages.dev`、`claudestudio.com`、`ant.dev`、`antspace.dev`、`modelcontextprotocol.*`、`cdn.growthbook.io`、`http-intake.logs.us5.datadoghq.com`、`o1158394.ingest.us.sentry.io`。
  - IP / ASN：`160.79.104.0/21`、`2607:6bc0::/32`、`IP-ASN,399358,no-resolve`。
- **ChatGPT / Codex（OpenAI）**：
  - 域名：`openai.com`、`openai.org`、`chatgpt.com`、`chatgpt.site`、`chat.com`、`ai.com`、`sora.com`、`oaistatic.com`、`oaiusercontent.com`、`oaistatsig.com`、`crixet.com`、Azure CDN / WebPubSub 与 LiveKit 端点。
  - IP / ASN：`199.47.142.0/23`、`2604:f20::/32`、`IP-ASN,401518,no-resolve` 及每日同步的 ChatGPT Voice IP 段。
- **Antigravity / Gemini Code Assist（Google AI）**：
  - 域名：`antigravity.google`、`antigravity.google.com`、`antigravity-unleash.goog`、`antigravity-pa.googleapis.com`、`antigravity.googleapis.com`、`cloudcode-pa.googleapis.com`、`daily-cloudcode-pa.googleapis.com`、`daily-cloudcode-pa.sandbox.googleapis.com`、`cloudcode-experiments.googleapis.com`、`jetski-webchannel.googleapis.com`、`cloudaicompanion.googleapis.com`、`aicode.googleapis.com`、`aida.googleapis.com`、`aisandbox-pa.googleapis.com`、`generativelanguage.googleapis.com`、`geller-pa.googleapis.com`、`proactivebackend-pa.googleapis.com`、`robinfrontend-pa.googleapis.com`。
- **其余海外 AI 编程工具**：Cursor、GitHub Copilot、xAI / Grok、Windsurf / Codeium、Factory、Zed、JetBrains AI、OpenRouter、Perplexity、Cline、OpenCode、Kiro 等。

### 2. 海外券商（`rules/clash/Broker.yaml` & `rules/shadowrocket/Broker.list`）

- **富途 / Moomoo**：全部 `futu*.com` / `futunn.com` / `futuhk*.com` / `futufin.com` / `futustatic.com` / `ftesop.com` / `moomoo*.com` / `collect.us.moomoocrypto.com`、腾讯云 IM 入口（`shortconn.im.qcloud.com`、`shortconnv6.im.qcloud.com`、`loginv6.im.qcloud.com`）、60+ 条腾讯云 / AWS 行情与交易 IP-CIDR，以及桌面端进程兜底（`FTNN` / `FutuNiuniu`）。
- **盈透证券（IBKR）**：`ibkr.*`、`interactivebrokers.*` 全球 21 个域名及核心交易网关主域 `ibllc.com`，配合桌面端 `IBKR Desktop` 进程路径兜底。
- **其他券商 / 金融**：长桥（Longbridge）、老虎（Tiger）、嘉信（Schwab / Thinkorswim）、雪盈（Snowball X）、复星财富、华盛、TradingView、卓锐、PayPal。

## 四、同步与聚合逻辑（`scripts/sync_rules.py`）

同步流程全部由 `sources.yaml` 声明驱动，执行 `uv run --frozen python scripts/sync_rules.py sync` 时按以下 6 步运行：

1. **Manifest 校验（`load_manifest`）**：
   - 验证版本、仓库名正则、安全相对路径、provider 与目标文件一一对应、输入三元组唯一。
   - 校验可选扩展字段：`transform`、`ensure_no_resolve`、`exclude_rules`。
2. **浅层稀疏检出（`clone_sources`）**：
   - 使用 `gh repo clone -- --depth=1 --filter=blob:none --sparse --branch <ref>` 仅拉取声明过的上游文件路径，最小化克隆体积，并打印每个上游的 `HEAD` commit SHA 便于审计。
3. **多格式解析与清洗（`build_aggregate`）**：
   - 默认输入：Clash classical YAML（`payload:` 列表）。
   - `transform: shadowrocket-list-to-clash-classical`：解析纯文本 `.list` / `.txt`（跳过空行和 `#` 注释）。
   - `transform: clash-domain-to-clash-classical`：将 Mihomo/Clash `behavior: domain` YAML 转换为 classical 规则（`+.example.com` → `DOMAIN-SUFFIX,example.com`；`*.example.com` → `DOMAIN-WILDCARD,*.example.com`；纯域名 → `DOMAIN,example.com`）。
   - `ensure_no_resolve: true`：为 `IP-CIDR`、`IP-CIDR6`、`IP-ASN` 自动补齐 `,no-resolve`，避免高优先级规则组（如 `Brokerrp`、`AIrp`）提前触发本地 DNS 解析。
   - `exclude_rules`：按精确标准化规则字符串剔除上游混入的水印域名（如 Sukka 追踪域名）或过宽的第三方共享基础设施规则（如 `DOMAIN-SUFFIX,sentry.io`、`DOMAIN-KEYWORD,datadog`、`DOMAIN,storage.googleapis.com`），避免误劫持非 AI 流量。
   - 按 `sources.yaml` 声明顺序合并所有上游与 `overrides/clash/*.yaml`，统一规范化并做精确去重，输出到暂存目录的 `rules/clash/*.yaml`。
4. **单源派生 Shadowrocket 规则（`build_shadowrocket_output`）**：
   - 直接从刚生成的 Clash classical YAML 派生 `rules/shadowrocket/*.list`，确保双端永不漂移：
     - `IP-CIDR6` 转为 `IP-CIDR`；
     - 自动忽略 Shadowrocket 不支持的规则类型（`PROCESS-NAME*`、`PROCESS-PATH*`、`DOMAIN-REGEX`）；
     - 遇到未知规则类型立即报错失败（fail-closed）。
5. **完整性与哈希校验（`validate_tree` + `checksum_document`）**：
   - 反向核验 20 个输出文件集合、Clash/Shadowrocket 逐条一致性，并生成 `checksums.sha256`。
6. **原子替换（`replace_clients`）**：
   - 仅在所有上游拉取、转换、过滤、双端校验全部成功后，才原子替换 `rules/clash` 与 `rules/shadowrocket` 目录并写入 `checksums.sha256`；任一步骤失败则完整保留上次有效快照。

## 五、自动更新机制

- `.github/workflows/sync-rules.yml` 每周一 `03:17 UTC` 定时触发，也支持在 GitHub Actions 页面手动 `workflow_dispatch` 触发。
- 工作流内执行 `sync` + `validate`，仅当 `rules/` 或 `checksums.sha256` 有实际变更时才自动提交并推送到 `main`。
