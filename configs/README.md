# 转换任务定义（configs/）

本目录中每个 `*.json` 文件定义**一个转换任务**：一份 subconverter 风格 `.ini` 输入 → 一个 Shadowrocket `.conf` 产物。
`convert.py` 会按文件名的字典序依次执行所有 `enabled: true` 的任务。

## Schema

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `id` | string | 是 | 文件名（去扩展名） | 任务唯一标识，必须唯一；用于 `--only` 与产物命名建议 |
| `title` | string | 否 | 同 `id` | 任务显示名称，写入产物头部注释 |
| `enabled` | boolean | 否 | `true` | 是否启用；`false` 时跳过 |
| `ini` | string (URL) | 是 | — | subconverter 风格配置（`.ini`）的直链，需包含 `ruleset=` 与 `custom_proxy_group=` |
| `output` | string (path) | 是 | — | 产物输出路径，建议 `dist/<id>.conf` |
| `prepend_rules` | string[] | 否 | `[]` | 追加到规则最前（最高优先级）的规则，格式 `TYPE,VALUE,POLICY` |
| `append_rules` | string[] | 否 | `[]` | 追加到规则末尾（`FINAL` 之前）的规则，格式同上 |

## 约束与校验

- `id` 在同一目录内必须唯一；
- `output` 必须位于 `dist/` 下，避免与源码文件混放；
- `prepend_rules` / `append_rules` 中引用的策略名必须存在于该配置的策略分组中
  （`DIRECT`、`REJECT`、`PROXY` 为内置策略，无需定义）；
- 转换过程中若检测到规则引用了不存在的策略，`convert.py` 将以非零状态退出，GitHub Actions 构建失败。

## 示例

### 基础任务

```json
{
  "id": "acl4ssr-online-full",
  "title": "ACL4SSR Online Full（与小猫同款）",
  "enabled": true,
  "ini": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/ACL4SSR_Online_Full.ini",
  "output": "dist/acl4ssr-online-full.conf",
  "prepend_rules": [],
  "append_rules": []
}
```

### 追加自定义规则

```json
{
  "id": "acl4ssr-online-full-custom",
  "title": "ACL4SSR Online Full（自定义）",
  "enabled": true,
  "ini": "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/ACL4SSR_Online_Full.ini",
  "output": "dist/acl4ssr-online-full-custom.conf",
  "prepend_rules": [
    "DOMAIN-SUFFIX,example.com,DIRECT"
  ],
  "append_rules": [
    "DOMAIN-SUFFIX,internal.example.com,🎯 全球直连"
  ]
}
```

## 命名约定

- `id` 建议采用 `<上游>-<变体>` 形式，并全部小写、使用连字符（如 `acl4ssr-online-full`）；
- `output` 建议与 `id` 保持一致，统一输出到 `dist/`；
- `title` 使用中文描述，便于在 `dist/links.md` 中查看。
