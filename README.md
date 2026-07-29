# Proxy-Rules

`Proxy-Rules` 是个人维护的多客户端代理规则快照仓库。目前同时提供 Clash
classical rule-provider 与 Shadowrocket RULE-SET 文件；客户端格式统一放在
`rules/<client>/` 目录下。

## Clash

规则文件位于 [`rules/clash`](rules/clash)。引用格式：

```yaml
url: https://raw.githubusercontent.com/hanjl7/Proxy-Rules/refs/heads/main/rules/clash/Direct.yaml
```

本仓库仅保存规则，不包含代理订阅、节点、密钥或完整 Clash 配置。

## Shadowrocket

纯文本规则文件位于 [`rules/shadowrocket`](rules/shadowrocket)，可直接通过
`RULE-SET` 引用：

```ini
RULE-SET,https://raw.githubusercontent.com/hanjl7/Proxy-Rules/refs/heads/main/rules/shadowrocket/AI.list,AI服务
```

Shadowrocket 不支持 Clash YAML 的 `payload:` 外壳，也不支持 iOS 上的进程名
匹配。同步脚本会从同一份 Clash 聚合快照派生 `.list`：把 `IP-CIDR6` 转换为
Shadowrocket 使用的 `IP-CIDR`，并过滤 `PROCESS-NAME`、`PROCESS-PATH` 和
`PROCESS-NAME-REGEX`。

## 更新

GitHub Actions 每周一 `03:17 UTC` 自动同步，也可以从 Actions 页面手动触发。
同步过程通过 `gh repo clone` 对上游仓库做浅层稀疏检出，全部文件验证成功后才
替换当前快照。任一上游不可用或规则格式无效时，现有快照保持不变。

本地运行：

```bash
uv run --frozen python scripts/sync_rules.py sync
uv run --frozen python scripts/sync_rules.py validate
```

规则来源和目标路径由 [`sources.yaml`](sources.yaml) 管理。34 份上游输入会去重
合并为 10 个类别，并各自生成 Clash 与 Shadowrocket 两种格式：

`AI`、`Crypto`、`Social`、`Video`、`Tech`、`Broker`、`Game`、`Direct`、
`China` 和 `Proxy`。

`sources.yaml` 的 `overrides` 可为指定 provider 合并本仓库维护的补充规则。
补充规则保存在 [`overrides/clash`](overrides/clash)，同步时参与去重和格式校验；
Shadowrocket 输出会自动过滤不支持的进程规则。

其中 `AI.list` 和 `HK_Broker.list` 会先从 Shadowrocket list 格式转换，再并入
对应聚合文件。20 个生成文件的校验值记录在
[`checksums.sha256`](checksums.sha256)。

## 来源与许可

规则内容归各上游项目及贡献者所有。具体来源与许可证状态见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本仓库不会用单一许可证
覆盖来自不同项目的第三方规则。
