# configs/ —— 转换任务定义

`convert.py` 扫描本目录下所有 `*.json`，每个文件对应**一个转换任务**（一个源配置 -> 一个 Shadowrocket `.conf`）。

## 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 任务唯一标识（也用于 `--only id`） |
| `title` | 否 | 显示名称，写进生成文件的注释头 |
| `enabled` | 否 | 默认 `true`；设为 `false` 可暂停该任务 |
| `ini` | 是 | subconverter 风格配置（`.ini`）的 URL，需含 `ruleset=` / `custom_proxy_group=` |
| `output` | 是 | 输出路径，通常 `dist/<name>.conf` |
| `prepend_rules` | 否 | 追加到规则最前面的规则（优先级最高），格式 `TYPE,VALUE,POLICY` |
| `append_rules` | 否 | 追加到规则末尾（FINAL 之前）的规则，格式同上 |

## 示例

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

## 加自己的转换

1. 找一份 subconverter 的 `.ini`（ACL4SSR 仓库的 `Clash/config/*.ini` 都可以，或其他兼容配置）；
2. 在本目录新建 `<id>.json`，填 `ini` 与 `output`；
3. 提交到 GitHub，Actions 会自动运行并生成 `dist/<id>.conf`（也可本地 `python3 convert.py`）。
