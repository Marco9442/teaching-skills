#!/usr/bin/env python3
"""把上游仓库里的技能做成各自能单独安装的目录。

不改写正文。技能点名的仓库文件，按同样的相对路径拷进该技能目录。
上游新增或删除技能时，下次运行自动跟上。找不到任何技能就停，不改本仓库。
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

UPSTREAM_URL = "https://github.com/YujxZJCN/teaching-skills.git"
KEEP_ROOT = {".git", ".github", "README.md"}
SKIP_DIRS = {".git", "__pycache__", ".github"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt", ".py", ".toml"}
PATH_RE = re.compile(
    r"(?<![\w./:-])((?:\.\./)*(?:[\w.-]+/)+[\w.-]+\.[A-Za-z0-9.]+)"
)
IMPORT_RE = re.compile(r"^(?:from|import)\s+([A-Za-z_][\w]*)", re.M)
RELATED_KEY_RE = re.compile(r"^[ \t]*related_skills:[ \t]*(?:\[[^\]]*\][ \t]*)?$")
RELATED_ITEM_RE = re.compile(r"^[ \t]+-[ \t]+\S")
STAGE_RE = re.compile(r'^(  pipeline_stage: )(\d+)[ \t]*$')


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    upstream, cleanup = load_upstream()
    try:
        sha = git_sha(upstream)
        skills = discover_skills(upstream)
        if not skills:
            raise SystemExit("上游没有找到技能，已停止，本仓库未改动")
        license_src = upstream / "LICENSE"
        if not license_src.is_file():
            raise SystemExit("上游没有 LICENSE，已停止，本仓库未改动")

        stage = Path(tempfile.mkdtemp(prefix="skills-stage-"))
        try:
            for skill in skills:
                closure = external_closure(upstream, skill.name)
                build_skill(upstream, skill.name, stage / skill.name, closure)
                verify_skill(upstream, skill.name, stage / skill.name, closure)
            shutil.copy2(license_src, stage / "LICENSE")
            verify_stage(stage, [s.name for s in skills])
            apply_stage(stage, repo)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    finally:
        cleanup()

    print(f"UPSTREAM_SHA={sha}")
    publish_env(sha)
    print(f"OK skills={len(skills)}")


def load_upstream() -> tuple[Path, callable]:
    override = os.environ.get("UPSTREAM_DIR")
    if override:
        return Path(override).resolve(), lambda: None
    dest = Path(tempfile.mkdtemp(prefix="upstream-"))

    def cleanup() -> None:
        shutil.rmtree(dest, ignore_errors=True)

    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--quiet", UPSTREAM_URL, str(dest)],
        check=True,
        env=env,
        timeout=180,
    )
    return dest, cleanup


def git_sha(upstream: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def publish_env(sha: str) -> None:
    env_path = os.environ.get("GITHUB_ENV")
    if env_path:
        with open(env_path, "a", encoding="utf-8") as fh:
            fh.write(f"UPSTREAM_SHA={sha}\n")


def discover_skills(upstream: Path) -> list[Path]:
    direct = sorted(p for p in upstream.iterdir() if (p / "SKILL.md").is_file())
    if direct:
        return direct
    nested = upstream / "skills"
    if nested.is_dir():
        return sorted(p for p in nested.iterdir() if (p / "SKILL.md").is_file())
    return []


def external_closure(upstream: Path, skill: str) -> list[str]:
    """技能正文（以及这些文件再点名的文件）里，落在本技能目录之外的真实文件。"""
    queued: list[str] = []
    seen: set[str] = set()
    for path in text_files(upstream / skill):
        for rel in refs_in(upstream, path):
            if is_outside(skill, rel):
                queued.append(rel)
    while queued:
        rel = queued.pop()
        if rel in seen or not is_outside(skill, rel):
            continue
        if Path(rel).name == "SKILL.md":
            continue
        seen.add(rel)
        target = upstream / rel
        if target.suffix.lower() in TEXT_SUFFIXES:
            for nxt in refs_in(upstream, target):
                if nxt not in seen and is_outside(skill, nxt):
                    queued.append(nxt)
    return sorted(seen)


def is_outside(skill: str, rel: str) -> bool:
    top = rel.split("/", 1)[0]
    return top != skill and top not in SKIP_DIRS


def text_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in TEXT_SUFFIXES and path.name != ".DS_Store":
                found.append(path)
    return found


def refs_in(upstream: Path, path: Path) -> list[str]:
    if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    found: list[str] = []
    for token in PATH_RE.findall(text):
        resolved = resolve_ref(upstream, path, token)
        if resolved:
            found.append(resolved)
    if path.suffix == ".py":
        parent = path.relative_to(upstream).parent
        for name in IMPORT_RE.findall(text):
            sibling = str(parent / f"{name}.py")
            if (upstream / sibling).is_file():
                found.append(sibling)
    return found


def resolve_ref(upstream: Path, source: Path, token: str) -> str | None:
    if token.startswith("./") or token.startswith("../"):
        candidate = (source.parent / token).resolve()
    else:
        candidate = (upstream / token).resolve()
    try:
        rel = candidate.relative_to(upstream.resolve())
    except ValueError:
        return None
    if candidate.is_file() and ".." not in rel.parts:
        return rel.as_posix()
    return None


def build_skill(upstream: Path, skill: str, dest: Path, closure: list[str]) -> None:
    copy_tree(upstream / skill, dest)
    skill_md = dest / "SKILL.md"
    skill_md.write_text(normalize_skill_md(skill_md.read_text(encoding="utf-8")), encoding="utf-8")
    for rel in closure:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise SystemExit(f"{skill} 内部已有 {rel}，不能再放入同路径文件")
        shutil.copy2(upstream / rel, target)


def copy_tree(src: Path, dest: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        relative = Path(dirpath).relative_to(src)
        (dest / relative).mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if name == ".DS_Store" or name.endswith(".pyc"):
                continue
            shutil.copy2(Path(dirpath) / name, dest / relative / name)


def normalize_skill_md(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    front = text[4:end]
    rest = text[end + 5 :]
    lines = front.splitlines()
    kept: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if RELATED_KEY_RE.fullmatch(line):
            index += 1
            if "[" not in line:
                while index < len(lines) and RELATED_ITEM_RE.match(lines[index]):
                    index += 1
            continue
        match = STAGE_RE.fullmatch(line)
        kept.append(f'{match.group(1)}"{match.group(2)}"' if match else line)
        index += 1
    body = "\n".join(kept)
    if body and not body.endswith("\n"):
        body += "\n"
    return "---\n" + body + "---\n" + rest


def verify_skill(upstream: Path, skill: str, dest: Path, closure: list[str]) -> None:
    nested = [p for p in dest.rglob("SKILL.md") if p.parent != dest]
    if nested:
        raise SystemExit(f"{skill} 内出现了第二个 SKILL.md")
    front = (dest / "SKILL.md").read_text(encoding="utf-8")
    closing = front.find("\n---\n", 4)
    if closing == -1 or "related_skills:" in front[4:closing]:
        raise SystemExit(f"{skill} 的说明头仍列出了其他技能")
    expected = {p.relative_to(upstream / skill).as_posix() for p in iter_files(upstream / skill)}
    expected |= set(closure)
    actual = {p.relative_to(dest).as_posix() for p in iter_files(dest)}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SystemExit(f"{skill} 文件集合不一致 missing={missing[:5]} extra={extra[:5]}")
    for rel in closure:
        if (upstream / rel).read_bytes() != (dest / rel).read_bytes():
            raise SystemExit(f"{skill} 内的 {rel} 与上游不一致")
    original = (upstream / skill / "SKILL.md").read_text(encoding="utf-8")
    if (dest / "SKILL.md").read_text(encoding="utf-8") != normalize_skill_md(original):
        raise SystemExit(f"{skill}/SKILL.md 与预期不一致")
    for path in iter_files(upstream / skill):
        rel = path.relative_to(upstream / skill)
        if path.name == "SKILL.md" and path.parent == upstream / skill:
            continue
        if path.read_bytes() != (dest / rel).read_bytes():
            raise SystemExit(f"{skill}/{rel.as_posix()} 与上游不一致")


def verify_stage(stage: Path, skills: list[str]) -> None:
    names = {p.name for p in stage.iterdir()}
    if names != set(skills) | {"LICENSE"}:
        raise SystemExit(f"输出目录异常: {sorted(names)}")


def apply_stage(stage: Path, repo: Path) -> None:
    incoming = {p.name for p in stage.iterdir()}
    for child in list(repo.iterdir()):
        if child.name in KEEP_ROOT or child.name in incoming:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for item in stage.iterdir():
        dest = repo / item.name
        if dest.is_dir():
            shutil.rmtree(dest)
        elif dest.exists():
            dest.unlink()
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)


def iter_files(root: Path) -> list[Path]:
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name == ".DS_Store" or name.endswith(".pyc"):
                continue
            found.append(Path(dirpath) / name)
    return found


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode or 1)
