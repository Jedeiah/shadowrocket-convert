# Shadowrocket 转换总项目

一个仓库 = **多个规则转换任务**。把 subconverter 风格的配置（ACL4SSR 各种 ini）批量转换成 Shadowrocket（小火箭）可导入的 `.conf`，并通过 GitHub Actions **每天自动更新**。

```
configs/*.json   每个 JSON 定义"一个转换"（源 ini URL -> 输出 conf 文件名）
convert.py       通用转换器（读 configs/，生成 dist/）
dist/*.conf      生成物（GitHub Actions 每天自动刷新）
dist/links.md    所有成品配置的 raw 链接清单（自动生成）
```

## 内置的转换（可在 configs/ 增删）

| id | 说明 |
|---|---|
| `acl4ssr-online-full` | **ACL4SSR Online Full**（29 组，与你 Clash Verge 小猫当前同款） |
| `acl4ssr-online` | ACL4SSR Online 原版（11 组） |
| `acl4ssr-mini-ai` | ACL4SSR Online Mini_Ai（精简 6 组 + 💬 Ai平台 组） |
| `acl4ssr-full-adblockplus` | ACL4SSR Online Full AdblockPlus（更强广告拦截，**约 9.6 万条规则、文件 4.8MB，较重，默认关闭**；需要时把该 json 的 `enabled` 改 `true`） |

## 怎么用（3 步）

1. **把本仓库传到 GitHub**（Public），`configs/`、`convert.py`、`.github/workflows/update.yml` 一起上传；
2. 仓库 → Settings → Actions → General → Workflow permissions → **Read and write**；
3. 在 Actions 页手动运行一次「Update Shadowrocket configs」；完成后打开 `dist/links.md`，
   里面每个配置的 raw 链接就是小火箭要填的订阅/配置地址。

### 小火箭导入

1. Shadowrocket → **配置** → 右上角 `+` → 粘贴某个 `.conf` 的 raw 链接 → 下载；
2. 点该配置 → 设为**使用中**；
3. 长按配置 → 打开 **自动更新**（建议 24 小时）；
4. 首页 → `+` → 类型 **Subscribe** → 粘贴机场订阅（节点与规则分开更新）；
5. 在配置详情 → 策略组里逐组选节点（例如把 `💬 Ai平台` 设为 `🇺🇸 美国节点`）。

## 新增一个转换（不用改代码）

在 `configs/` 里加一个 JSON 即可，例如：

```json
{
  "id": "my-custom",
  "title": "我的自定义配置",
  "enabled": true,
  "ini": "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>.ini",
  "output": "dist/my-custom.conf",
  "prepend_rules": ["DOMAIN-SUFFIX,example.com,🚀 节点选择"],
  "append_rules": []
}
```

字段说明见 [configs/README.md](configs/README.md)。`ini` 不限于 ACL4SSR：任何 subconverter 风格的 `.ini`（含 `ruleset=`、`custom_proxy_group=`）都可以。

## 关于仓库体积 / Actions 产物

- 工作流**不使用** `upload-artifact`，不会产生 Actions 产物占用你的存储；
- 只会把 `dist/*.conf` 提交回仓库（体积：Full ≈ 470KB、Online ≈ 160KB、Mini_Ai ≈ 160KB；总量约 0.8MB）；
- 较重的 Full_AdblockPlus（4.8MB）默认 `enabled: false`，不生成、不占空间；
- `main` 分支每次 push 会触发一次更新（由 `permissions.contents: write` 的 `GITHUB_TOKEN` 提交，不会循环触发）；
- 每天 03:17 UTC 定时更新一次。

## 本地手动生成（不用 GitHub）

```bash
python3 convert.py                 # 全部任务
python3 convert.py --only acl4ssr-online-full
```

生成的文件在 `dist/`。没有 GitHub 时可用本地 HTTP / AirDrop 传到手机导入，但没有自动更新。

## 与 Clash 版的已知差异

| 项 | 说明 |
|---|---|
| `PROCESS-NAME` 等 iOS 不支持的规则 | 跳过（如 Viu 的 3 条） |
| 「🚀 手动切换」组 | Clash 是"手动选全部节点"，小火箭里转为 url-test（手动选节点 = 首页 PROXY） |
| 「🎥 奈飞节点」「🎶 网易音乐」 | select+正则 → url-test 自动匹配 |
| DNS | 使用小火箭默认策略（未强塞 DoH，可按需在 `[General]` 添加 `dns-server`） |
| 组名匹配 | 依赖节点名关键词（xxjc 带国旗 emoji、AgentNEO 含「香港/日本/美国」均可匹配） |
