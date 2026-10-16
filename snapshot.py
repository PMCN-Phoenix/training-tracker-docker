# -*- coding: utf-8 -*-
"""
全量历史快照工具 —— training-tracker-docker

每次运行时生成一份"当时是什么样"的完整快照，放在项目同级目录：

    D:\\11.project\\iwen-codex\\codex-list\\training-tracker-snapshots\\
        <时间戳>-<原因>/
            MANIFEST.json        机器可读的清单（校验和 / 统计 / 容器状态）
            MANIFEST.md          人可读的摘要（打开先看这个）
            repo/                git 全量归档（含全部历史）+ 工作区文件副本
            data/influx/         InfluxDB 成绩数据导出
            data/runtime/        nodered_data / grafana 配置 / reports 等的文件副本
            docker/              容器状态 + 镜像清单 + compose 配置
            RESTORE.md           如何从这份快照恢复

用法：
    python snapshot.py                       # 默认原因 auto
    python snapshot.py --reason "M6 收货页上线"

设计约束：
    * 只读源项目 —— 绝不修改、移动或删除被快照的任何内容。
    * 幂等 —— 同一秒内重复运行会复用同一目录并覆盖，不会堆积垃圾。
    * 容器没起也不失败 —— 数据库导出与容器清单会优雅降级为"跳过"。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 常量

PROJECT = Path(__file__).resolve().parent
SNAPSHOT_ROOT = PROJECT.parent / "training-tracker-snapshots"

# 只复制"受版本管理"和"明确要保的"文件；运行时数据卷不在其中
ALLOWED_TOP_DIRS = {"docs", "reports", "web", "grafana", "nodered_data", "_verify"}
ALLOWED_TOP_FILES = {"docker-compose.yml", ".gitignore", "snapshot.py"}
SKIP_DIR_NAMES = {"node_modules", ".git", "__pycache__", ".vite", ".pytest_cache"}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".bak"}

INFLUX_CONTAINER = "training-influxdb"
DATA_CONTAINERS = (INFLUX_CONTAINER, "training-grafana", "training-nodered")
COMPOSE_FILES = ("docker-compose.yml",)

# 大文件阈值：超过则记入 MANIFEST 提示，便于发现异常膨胀
BIG_FILE_BYTES = 5 * 1024 * 1024


# ---------------------------------------------------------------- 小工具


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str]:
    """跑一条命令，永远不抛异常；返回 (返回码, 合并输出)。"""
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        out = (p.stdout or b"") + (p.stderr or b"")
        return p.returncode, decode(out)
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"
    except Exception as exc:  # noqa: BLE001 —— 快照工具不该因为任何原因崩掉
        return 1, f"{type(exc).__name__}: {exc}"


def decode(raw: bytes) -> str:
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def sha256(path: Path, buf: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(buf):
            h.update(chunk)
    return h.hexdigest()


def human(n: int) -> str:
    step = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if step < 1024 or unit == "GB":
            return f"{step:.1f} {unit}" if unit != "B" else f"{int(step)} B"
        step /= 1024
    return f"{step:.1f} GB"


def tree_size(root: Path) -> tuple[int, int]:
    """返回 (文件数, 总字节)。"""
    count = 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
                count += 1
            except OSError:
                pass
    return count, total


# ---------------------------------------------------------------- 快照步骤


class Snapshot:
    def __init__(self, reason: str) -> None:
        self.reason = reason or "auto"
        self.stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir = SNAPSHOT_ROOT / f"{self.stamp}-{slug(self.reason)}"
        self.notes: list[str] = []
        self.warnings: list[str] = []

    def note(self, msg: str) -> None:
        self.notes.append(msg)
        print(f"  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  ! {msg}")

    # -- 1. git 全量归档（含全部历史） --------------------------------

    def step_git_bundle(self) -> dict:
        out = self.dir / "repo"
        out.mkdir(parents=True, exist_ok=True)

        rc, head = run(["git", "rev-parse", "HEAD"], cwd=PROJECT)
        rc2, branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=PROJECT)
        rc3, log = run(["git", "log", "--oneline", "-1"], cwd=PROJECT)
        rc4, remote = run(["git", "remote", "get-url", "origin"], cwd=PROJECT)
        rc5, dirty = run(["git", "status", "--porcelain"], cwd=PROJECT)
        rc6, tracked = run(["git", "ls-files"], cwd=PROJECT)

        bundle = out / "repo.bundle"
        rc_b, msg_b = run(
            ["git", "bundle", "create", str(bundle), "--all"], cwd=PROJECT, timeout=300
        )
        if rc_b == 0 and bundle.exists():
            self.note(f"git bundle 已归档：{bundle.name}（{human(bundle.stat().st_size)}，含全部历史与分支）")
        else:
            self.warn(f"git bundle 生成失败：{msg_b.strip()[:200]}")

        # 未提交改动打包，避免"最后一次改动没进快照"
        rc_s, _ = run(["git", "diff", "HEAD", "--quiet"], cwd=PROJECT)
        if rc_s != 0 and dirty.strip():
            patch = out / "uncommitted-changes.patch"
            rc_p, msg_p = run(["git", "diff", "HEAD", "--binary"], cwd=PROJECT)
            if rc_p == 0:
                patch.write_text(msg_p, encoding="utf-8", errors="replace")
                self.note(f"未提交改动已单独留档：{patch.name}（{len(dirty.strip().splitlines())} 处变更）")
            else:
                self.warn("未提交改动留档失败")

        return {
            "head": head.strip(),
            "branch": branch.strip(),
            "head_subject": log.strip(),
            "remote": remote.strip(),
            "tracked_files": len(tracked.strip().splitlines()) if rc6 == 0 else None,
            "dirty": bool(dirty.strip()),
            "dirty_lines": len(dirty.strip().splitlines()) if dirty.strip() else 0,
            "bundle": bundle.name if bundle.exists() else None,
        }

    # -- 2. 工作区文件副本 --------------------------------------------

    def step_worktree_copy(self) -> dict:
        dest_root = self.dir / "repo" / "worktree"
        files: list[dict] = []
        skipped: list[str] = []

        for path in iter_project_files():
            rel = path.relative_to(PROJECT)
            dest = dest_root / rel
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
            except OSError:
                # 多半是 Windows 长路径限制；退一步试 \\?\ 前缀
                try:
                    long_dest = Path("\\\\?\\" + str(dest.resolve()))
                    long_dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, long_dest)
                except OSError as exc:
                    skipped.append(f"{rel.as_posix()}: {exc}")
                    continue
            try:
                size = path.stat().st_size
                files.append({"path": rel.as_posix(), "bytes": size, "sha256": sha256(path)})
            except OSError as exc:
                skipped.append(f"{rel.as_posix()}: 已复制但无法读取属性（{exc}）")

        total = sum(f["bytes"] for f in files)
        self.note(f"工作区副本：{len(files)} 个文件，{human(total)}")
        if skipped:
            self.warn(f"{len(skipped)} 个文件复制失败（详见 MANIFEST）")

        big = [f for f in files if f["bytes"] > BIG_FILE_BYTES]
        for f in big:
            self.warn(f"大文件：{f['path']}（{human(f['bytes'])}）")

        return {"file_count": len(files), "total_bytes": total, "files": files, "skipped": skipped}

    # -- 3. InfluxDB 数据导出 -----------------------------------------

    def step_influx(self) -> dict:
        out = self.dir / "data" / "influx"
        out.mkdir(parents=True, exist_ok=True)

        rc, msg = run(["docker", "inspect", "-f", "{{.State.Running}}", INFLUX_CONTAINER])
        if rc != 0 or "true" not in msg:
            self.warn("InfluxDB 容器未运行 → 跳过数据导出（文件副本仍然完整）")
            return {"status": "skipped", "detail": msg.strip()[:200]}

        rc, msg = run(["docker", "exec", INFLUX_CONTAINER, "influx", "backup", "/tmp/snap"], timeout=600)
        if rc != 0:
            self.warn(f"InfluxDB 官方导出失败：{msg.strip()[:200]} → 降级为直接复制数据文件")
            return self._influx_file_fallback(out)

        rc, msg = run(["docker", "cp", f"{INFLUX_CONTAINER}:/tmp/snap", str(out)], timeout=600)
        run(["docker", "exec", INFLUX_CONTAINER, "rm", "-rf", "/tmp/snap"])
        if rc != 0:
            self.warn(f"从容器取回导出失败：{msg.strip()[:200]} → 降级为直接复制数据文件")
            return self._influx_file_fallback(out)

        count, size = tree_size(out)
        self.note(f"InfluxDB 官方导出完成：{count} 个文件，{human(size)}")
        return {"status": "ok", "method": "influx backup", "file_count": count, "total_bytes": size}

    def _influx_file_fallback(self, out: Path) -> dict:
        src = PROJECT.parent / "influxdb_data"
        if not src.is_dir():
            src = PROJECT / "influxdb_data"
        if not src.is_dir():
            self.warn("找不到 influxdb_data 目录，数据库未能留档")
            return {"status": "failed", "detail": "influxdb_data not found"}

        tarball = out / "influxdb_data.tar.gz"
        try:
            with tarfile.open(tarball, "w:gz") as tar:
                tar.add(src, arcname="influxdb_data")
        except OSError as exc:
            self.warn(f"打包 influxdb_data 失败：{exc}")
            return {"status": "failed", "detail": str(exc)}

        self.note(f"InfluxDB 数据文件已打包（冷备）：{human(tarball.stat().st_size)}")
        return {"status": "ok", "method": "file copy (cold)", "total_bytes": tarball.stat().st_size}

    # -- 4. 运行态配置副本 --------------------------------------------

    def step_runtime(self) -> dict:
        out = self.dir / "data" / "runtime"
        out.mkdir(parents=True, exist_ok=True)
        copied: list[str] = []

        targets = [PROJECT / "nodered_data", PROJECT / "grafana", PROJECT / "reports"]
        for src in targets:
            if not src.is_dir():
                continue
            dest = out / src.name
            try:
                shutil.copytree(
                    src, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("node_modules", ".npm", "__pycache__"),
                )
                copied.append(src.name)
            except OSError as exc:
                self.warn(f"复制 {src.name} 失败：{exc}")

        count, size = tree_size(out)
        self.note(f"运行态配置副本：{', '.join(copied) or '无'}（{count} 个文件，{human(size)}）")
        return {"copied": copied, "file_count": count, "total_bytes": size}

    # -- 5. 容器 / 镜像状态 -------------------------------------------

    def step_docker(self) -> dict:
        out = self.dir / "docker"
        out.mkdir(parents=True, exist_ok=True)

        rc, ps = run(["docker", "ps", "-a", "--format", "{{.Names}}\t{{.Image}}\t{{.Status}}"])
        rc2, images = run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.ID}}"])
        rc3, compose = run(["docker", "compose", "config"], cwd=PROJECT, timeout=60)

        (out / "containers.txt").write_text(ps or "(docker 不可用)", encoding="utf-8")
        (out / "images.txt").write_text(images or "(docker 不可用)", encoding="utf-8")
        if rc3 == 0:
            (out / "compose-resolved.yml").write_text(compose, encoding="utf-8")
        for name in COMPOSE_FILES:
            f = PROJECT / name
            if f.exists():
                shutil.copy2(f, out / name)

        if rc != 0:
            self.warn("Docker 不可用 → 容器状态仅记录为不可用")
        else:
            self.note(f"容器状态已记录（{len([l for l in ps.splitlines() if l.strip()])} 个容器）")
        return {"docker_available": rc == 0, "ps_lines": ps.strip().splitlines(),
                "images": images.strip().splitlines(), "compose_resolved": rc3 == 0}

    # -- 6. 清单落盘 ---------------------------------------------------

    def write_manifests(self, payload: dict) -> None:
        payload["snapshot"] = {
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "stamp": self.stamp,
            "reason": self.reason,
            "path": str(self.dir),
            "project": str(PROJECT),
            "project_name": PROJECT.name,
        }
        payload["notes"] = self.notes
        payload["warnings"] = self.warnings

        count, size = tree_size(self.dir)
        payload["snapshot"]["file_count"] = count
        payload["snapshot"]["total_bytes"] = size

        (self.dir / "MANIFEST.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.dir / "MANIFEST.md").write_text(render_manifest_md(payload), encoding="utf-8")
        (self.dir / "RESTORE.md").write_text(RESTORE_MD, encoding="utf-8")


# ---------------------------------------------------------------- 主流程


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="为 training-tracker-docker 生成一份全量历史快照",
    )
    parser.add_argument(
        "--reason", "-r", default="auto",
        help='快照原因，会写进目录名与清单，例如 "M6 收货页上线"',
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="只输出最终结果行",
    )
    args = parser.parse_args(argv)

    global print  # noqa: PLW0603 —— --quiet 时抑制过程输出
    if args.quiet:
        def print(*_a, **_k):  # type: ignore[no-redef]
            pass

    started = time.time()
    snap = Snapshot(args.reason)

    print(f"\n快照开始 → {snap.dir}")
    print("-" * 60)

    if snap.dir.exists():
        # 同一秒内重复运行：复用目录，避免堆积空快照
        snap.warn("目标目录已存在，本次就地覆盖")

    payload: dict = {}
    try:
        payload["git"] = snap.step_git_bundle()
        payload["worktree"] = snap.step_worktree_copy()
        payload["influx"] = snap.step_influx()
        payload["runtime"] = snap.step_runtime()
        payload["docker"] = snap.step_docker()
    except KeyboardInterrupt:
        print("\n被中断 —— 已写入的部分留在快照目录里，可安全删除后重跑")
        return 130
    except Exception as exc:  # noqa: BLE001
        snap.warn(f"意外错误：{type(exc).__name__}: {exc}")

    snap.write_manifests(payload)

    count, size = tree_size(snap.dir)
    elapsed = time.time() - started
    print("-" * 60)
    print(f"完成：{human(size)}，{count} 个文件，用时 {elapsed:.1f}s")
    print(f"清单：{snap.dir / 'MANIFEST.md'}")
    if snap.warnings:
        print(f"注意：{len(snap.warnings)} 条提示，见 MANIFEST.md 末尾")
    print()
    return 0


# ---------------------------------------------------------------- 辅助


def slug(text: str) -> str:
    keep = []
    for ch in text.strip():
        if ch.isalnum() or ch in "-_":
            keep.append(ch)
        elif ch in " \t/\\:，,。.":
            keep.append("-")
    out = "".join(keep).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return (out or "auto")[:48]


def iter_project_files():
    """遍历项目里应当入快照的文件（对齐 .gitignore 的口径）。"""
    for entry in sorted(PROJECT.iterdir(), key=lambda p: p.name):
        name = entry.name
        if entry.is_file():
            if name in ALLOWED_TOP_FILES:
                yield entry
            continue
        if not entry.is_dir() or name not in ALLOWED_TOP_DIRS:
            continue
        for dirpath, dirnames, filenames in os.walk(entry):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
            for fn in sorted(filenames):
                if Path(fn).suffix in SKIP_FILE_SUFFIXES:
                    continue
                p = Path(dirpath) / fn
                if p.is_symlink():
                    continue
                yield p


def render_manifest_md(p: dict) -> str:
    s = p["snapshot"]
    g = p.get("git", {})
    wt = p.get("worktree", {})
    inf = p.get("influx", {})
    rt = p.get("runtime", {})
    dk = p.get("docker", {})

    lines = [
        f"# 快照 · {s['created_at']}",
        "",
        f"- **原因**：{s['reason']}",
        f"- **目录**：`{s['path']}`",
        f"- **项目**：`{s['project']}`",
        f"- **体积**：{human(s['total_bytes'])}（{s['file_count']} 个文件）",
        "",
        "## 版本锚点",
        "",
        f"- 分支：`{g.get('branch', '?')}`",
        f"- 提交：`{g.get('head', '?')[:12]}` — {g.get('head_subject', '')}",
        f"- 远程：`{g.get('remote', '无')}`",
        f"- 受版本管理文件：{g.get('tracked_files', '?')} 个",
        f"- 未提交改动：{'有（' + str(g.get('dirty_lines', 0)) + ' 处，已存 uncommitted-changes.patch）' if g.get('dirty') else '无'}",
        "",
        "## 内容清单",
        "",
        "| 部分 | 内容 | 状态 |",
        "|---|---|---|",
        f"| `repo/repo.bundle` | git 全量归档（全部历史/分支） | {'✅' if g.get('bundle') else '⚠️ 缺失'} |",
        f"| `repo/worktree/` | 工作区文件副本 | ✅ {wt.get('file_count', 0)} 个文件，{human(wt.get('total_bytes', 0))} |",
        f"| `data/influx/` | InfluxDB 成绩数据 | {'✅ ' + inf.get('method', '') if inf.get('status') == 'ok' else '⚠️ ' + str(inf.get('status'))} |",
        f"| `data/runtime/` | nodered_data / grafana / reports 配置 | ✅ {', '.join(rt.get('copied', [])) or '无'} |",
        f"| `docker/` | 容器与镜像状态、compose 实际配置 | {'✅' if dk.get('docker_available') else '⚠️ Docker 不可用'} |",
        "",
        "## 恢复",
        "",
        "见同目录 `RESTORE.md`。核心一句：`git clone repo.bundle` 拿回全部代码与历史，"
        "`data/influx/` 覆盖回 `influxdb_data/` 拿回成绩数据。",
        "",
    ]

    if wt.get("files"):
        big = sorted(wt["files"], key=lambda f: -f["bytes"])[:10]
        lines += ["## 最大的 10 个文件", "", "| 文件 | 体积 |", "|---|---|"]
        lines += [f"| `{f['path']}` | {human(f['bytes'])} |" for f in big]
        lines += [""]

    if p.get("notes"):
        lines += ["## 执行记录", ""] + [f"- {n}" for n in p["notes"]] + [""]
    if p.get("warnings"):
        lines += ["## 需要注意", ""] + [f"- ⚠️ {w}" for w in p["warnings"]] + [""]

    return "\n".join(lines)


RESTORE_MD = """# 如何从这份快照恢复

快照是只读档案，源项目没有被改动过。恢复时把内容放回一个新目录即可。

## 1. 拿回代码与全部 git 历史

```bash
git clone repo/repo.bundle training-tracker-docker-restored
cd training-tracker-docker-restored
git remote set-url origin git@github.com:PMCN-Phoenix/training-tracker-docker.git
```

`repo.bundle` 是 git 的完整归档，包含所有提交、所有分支。
克隆后 `git log` 能看到与快照时刻完全一致的历史。

## 2. 拿回未提交的改动（如果有）

```bash
cd training-tracker-docker-restored
git apply ../repo/uncommitted-changes.patch
```

若快照的 MANIFEST.md 里显示"未提交改动：无"，则本步骤跳过。

## 3. 拿回成绩数据

**方式 A：官方导出（推荐，`data/influx/` 里有内容时）**

```bash
# 先把 influxdb 容器跑起来（初始化参数见 docker-compose.yml）
docker compose up -d influxdb
docker cp data/influx/. training-influxdb:/tmp/restore
docker exec training-influxdb influx restore /tmp/restore
docker compose restart influxdb
```

**方式 B：冷备压缩包（`data/influx/influxdb_data.tar.gz`）**

```bash
tar -xzf data/influx/influxdb_data.tar.gz -C <项目目录>
docker compose restart influxdb
```

## 4. 拿回运行态配置

```bash
cp -r data/runtime/nodered_data/. <项目目录>/nodered_data/
cp -r data/runtime/grafana/.      <项目目录>/grafana/
cp -r data/runtime/reports/.      <项目目录>/reports/
docker compose restart nodered grafana
```

## 5. 起服务并确认

```bash
docker compose up -d
docker compose ps                   # 期望 3 个 Up
curl http://localhost:3000/api/health
```

## 6. 完全对不上的时候

`repo/worktree/` 是快照时刻的工作区文件逐字节副本（MANIFEST.json 里带每个文件的 sha256）。
真的需要"一模一样"时，直接用它覆盖项目目录即可，跳过所有 git 步骤。

---

修复校验：`MANIFEST.json` 的 `worktree.files[].sha256` 可用于确认恢复后文件未被改动。
"""


if __name__ == "__main__":
    sys.exit(main())
