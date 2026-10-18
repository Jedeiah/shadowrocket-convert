#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shadowrocket 转换总项目 —— 把任意 subconverter 风格的配置（ACL4SSR 各种 ini）
批量转换成 Shadowrocket（小火箭）可导入的 .conf 配置文件。

仓库结构：
    configs/*.json   每个 JSON = 一个转换任务（源 ini + 输出文件名）
    dist/*.conf      生成物（由本脚本生成，GitHub Actions 每天自动更新）

新增一个转换：在 configs/ 里加一个 json 即可，无需改代码。

用法:
    python3 convert.py                 # 转换 configs/ 下全部启用项
    python3 convert.py --only xxx      # 只转换 id 为 xxx 的项
    BASE_RAW_URL=https://raw.githubusercontent.com/<user>/<repo>/main \
        python3 convert.py            # 写入 update-url，并生成 dist/links.md
"""
import glob
import json
import os
import sys
import urllib.request

CONFIG_DIR = "configs"
DIST_DIR = "dist"
BASE_RAW_URL = os.environ.get("BASE_RAW_URL", "").strip().rstrip("/")

# Shadowrocket 支持的规则类型
SUPPORTED_TYPES = {
    "DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX",
    "IP-CIDR", "IP-CIDR6", "IP-ASN", "GEOIP", "USER-AGENT", "URL-REGEX",
}
# iOS 上不可用 / 无意义的规则类型
SKIP_TYPES = {"PROCESS-NAME", "SRC-IP-CIDR", "DST-PORT", "PROTOCOL"}

GENERAL_SKIP_PROXY = (
    "127.0.0.1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,localhost,*.local,"
    "*.in-addr.arpa,*.ip6.arpa,captive.apple.com"
)
GENERAL_TUN_EXCLUDED = (
    "10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,"
    "192.168.0.0/16,224.0.0.0/4,255.255.255.255/32"
)

_CACHE = {}


def fetch(url: str) -> str:
    if url in _CACHE:
        return _CACHE[url]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (shadowrocket-convert)"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        text = resp.read().decode("utf-8", "replace")
    _CACHE[url] = text
    return text


def parse_ini(ini_text: str):
    rulesets, group_specs = [], []
    for raw in ini_text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("ruleset="):
            rulesets.append(line[len("ruleset="):].strip())
        elif line.startswith("custom_proxy_group="):
            group_specs.append(line[len("custom_proxy_group="):].strip())
    return rulesets, group_specs


def parse_groups(group_specs, all_names):
    parsed = []
    for spec in group_specs:
        parts = spec.split("`")
        if len(parts) < 2:
            continue
        name, kind = parts[0].strip(), parts[1].strip()
        rest = [p.strip() for p in parts[2:]]
        item = {"name": name, "kind": kind, "members": [], "regex": "",
                "url": "http://www.gstatic.com/generate_204", "interval": 300, "tolerance": 50}
        if kind == "select":
            regex = ""
            for token in rest:
                if not token:
                    continue
                if token.startswith("[]"):
                    member = token[2:]
                    if member in all_names or member in ("DIRECT", "REJECT", "PROXY"):
                        item["members"].append(member)
                else:
                    regex = token
            if regex:
                item["kind"] = "url-test"
                item["regex"] = regex
            if not item["members"] and not item["regex"]:
                item["members"] = ["PROXY", "DIRECT"]
        elif kind == "url-test":
            item["regex"] = rest[0] if len(rest) > 0 else ""
            if len(rest) > 1 and rest[1]:
                item["url"] = rest[1]
            if len(rest) > 2 and rest[2]:
                tail = rest[2].split(",")
                try:
                    if tail[0]:
                        item["interval"] = int(float(tail[0]))
                    if len(tail) > 1 and tail[-1]:
                        item["tolerance"] = int(float(tail[-1]))
                except ValueError:
                    pass
        else:
            continue
        parsed.append(item)
    return parsed


def topological_order(groups):
    names = {g["name"] for g in groups}
    deps = {g["name"]: [m for m in g["members"] if m in names] for g in groups}
    ordered, temp, done = [], set(), set()

    def visit(n):
        if n in done or n in temp:
            return
        temp.add(n)
        for d in deps.get(n, []):
            visit(d)
        temp.discard(n)
        done.add(n)
        ordered.append(n)

    for g in groups:
        visit(g["name"])
    by_name = {g["name"]: g for g in groups}
    return [by_name[n] for n in ordered if n in by_name]


def convert_rule_list(url: str, target: str):
    out, skipped = [], 0
    try:
        text = fetch(url)
    except Exception as exc:
        print(f"    [warn] 拉取失败 {url}: {exc}", file=sys.stderr)
        return out, 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//") or line.startswith(";"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        rtype = parts[0].upper()
        if rtype in SKIP_TYPES or rtype not in SUPPORTED_TYPES or len(parts) < 2 or not parts[1]:
            skipped += 1
            continue
        value = parts[1]
        extra = ""
        if rtype in ("IP-CIDR", "IP-CIDR6") and len(parts) > 2 and parts[2].lower() == "no-resolve":
            extra = ",no-resolve"
        out.append(f"{rtype},{value},{target}{extra}")
    return out, skipped


def build_conf(job: dict) -> dict:
    print(f"\n==> 转换: {job['id']}  ({job.get('title', '')})")
    ini = fetch(job["ini"])
    rulesets, group_specs = parse_ini(ini)
    all_group_names = {spec.split("`")[0].strip() for spec in group_specs}
    groups = topological_order(parse_groups(group_specs, all_group_names))

    rules = [r.strip() for r in job.get("prepend_rules", []) if r.strip()]
    skipped_total = 0
    for entry in rulesets:
        if ",[]" in entry:
            target, special = entry.split(",[]", 1)
            target, special = target.strip(), special.strip()
            parts = [p.strip() for p in special.split(",")]
            kind = parts[0].upper()
            if kind == "FINAL":
                rules.append(f"FINAL,{target}")
            elif kind == "GEOIP" and len(parts) > 1:
                rules.append(f"GEOIP,{parts[1]},{target}")
            else:
                rules.append(f"{kind},{target}")
            continue
        if "," not in entry:
            continue
        target, url = entry.split(",", 1)
        target, url = target.strip(), url.strip()
        if not url.startswith("http"):
            continue
        rules_of_list, skipped = convert_rule_list(url, target)
        rules.extend(rules_of_list)
        skipped_total += skipped
    rules.extend(r.strip() for r in job.get("append_rules", []) if r.strip())

    # 校验: 规则里的策略必须存在于分组中（DIRECT/REJECT/PROXY 除外）
    known = {g["name"] for g in groups} | {"DIRECT", "REJECT", "PROXY"}
    bad = []
    for r in rules:
        policy = r.rsplit(",", 1)[-1].strip()
        if policy == "no-resolve":
            policy = r.rsplit(",", 2)[-2].strip()
        if policy not in known:
            bad.append(r)
    if bad:
        raise ValueError(f"{job['id']}: {len(bad)} 条规则引用不存在的策略，例如 {bad[:3]}")

    lines = [
        f"# Shadowrocket 配置 —— {job.get('title', job['id'])}",
        f"# 源配置: {job['ini']}",
        "# 由 shadowrocket-convert 自动生成，请勿手工修改",
        "",
        "[General]",
    ]
    if BASE_RAW_URL:
        lines.append(f"update-url = {BASE_RAW_URL}/{job['output']}")
    lines += [
        "bypass-system = true",
        f"skip-proxy = {GENERAL_SKIP_PROXY}",
        f"tun-excluded-routes = {GENERAL_TUN_EXCLUDED}",
        "ipv6 = false",
        "prefer-ipv6 = false",
        "",
        "[Proxy Group]",
    ]
    for g in groups:
        if g["kind"] == "select":
            lines.append(f"{g['name']} = select,{','.join(g['members'])}")
        else:
            opts = [f"url={g['url']}", f"interval={g['interval']}", f"tolerance={g['tolerance']}"]
            if g["regex"] and g["regex"] not in (".*", "(.*)"):
                opts.append(f"policy-regex-filter={g['regex']}")
            lines.append(f"{g['name']} = url-test,{','.join(opts)}")
    lines += ["", "[Rule]"] + rules

    out_path = job["output"]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    stats = {
        "id": job["id"],
        "title": job.get("title", job["id"]),
        "output": out_path,
        "groups": len(groups),
        "rules": len(rules),
        "skipped": skipped_total,
    }
    print(f"    {stats['groups']} 个分组 / {stats['rules']} 条规则 -> {out_path}")
    return stats


def load_jobs(only=None):
    jobs = []
    for path in sorted(glob.glob(os.path.join(CONFIG_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            job = json.load(fh)
        if not job.get("enabled", True):
            continue
        job.setdefault("id", os.path.splitext(os.path.basename(path))[0])
        if only and job["id"] != only:
            continue
        jobs.append(job)
    return jobs


def write_links(jobs, stats):
    if not BASE_RAW_URL:
        return
    lines = ["# 生成的 Shadowrocket 配置链接", "",
             "| 配置 | 说明 | 链接 |", "|---|---|---|"]
    by_id = {s["id"]: s for s in stats}
    for job in jobs:
        s = by_id.get(job["id"])
        if not s:
            continue
        url = f"{BASE_RAW_URL}/{s['output']}"
        lines.append(f"| {job['id']} | {job.get('title', '')} | {url} |")
    path = os.path.join(DIST_DIR, "links.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"\n链接清单已写入 {path}")


def main():
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    jobs = load_jobs(only)
    if not jobs:
        print(f"[error] {CONFIG_DIR}/ 下没有找到可执行的转换任务", file=sys.stderr)
        sys.exit(1)
    print(f"共 {len(jobs)} 个转换任务")
    stats = []
    for job in jobs:
        stats.append(build_conf(job))
    write_links(jobs, stats)
    print("\n全部完成:")
    for s in stats:
        print(f"  {s['id']:<32} {s['groups']:>2} 分组 / {s['rules']:>6} 规则 / 跳过 {s['skipped']} 条 -> {s['output']}")


if __name__ == "__main__":
    main()
