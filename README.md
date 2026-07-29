# Proxy-Rules

`Proxy-Rules` 是个人维护的多客户端代理规则快照仓库。首版提供 Clash
classical rule-provider 文件；未来的客户端格式统一放在 `rules/<client>/`
目录下。

## Clash

规则文件位于 [`rules/clash`](rules/clash)。引用格式：

```yaml
url: https://raw.githubusercontent.com/hanjl7/Proxy-Rules/refs/heads/main/rules/clash/Direct.yaml
```

本仓库仅保存规则，不包含代理订阅、节点、密钥或完整 Clash 配置。

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
合并为 10 个 Clash rule-provider：

`AI`、`Crypto`、`Social`、`Video`、`Tech`、`Broker`、`Game`、`Direct`、
`China` 和 `Proxy`。

其中 `AI.list` 和 `HK_Broker.list` 会先从 Shadowrocket list 格式转换，再并入
对应聚合文件。文件校验值记录在 [`checksums.sha256`](checksums.sha256)。

## 来源与许可

规则内容归各上游项目及贡献者所有。具体来源与许可证状态见
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本仓库不会用单一许可证
覆盖来自不同项目的第三方规则。
