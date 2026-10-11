"""Build a Freya phone agent from a bank's brief files and its tool API file. One command.

    python3 builder/build.py <tool_api_file> <brief_file> [<brief_file> ...]

Needs FREYA_API_KEY, FREYA_BANK_TEAM_KEY and ANTHROPIC_API_KEY (or a Claude login).
Writes: out/<slot>/ (everything the run made), traces/<slot>-<time>.jsonl (the trace),
submission/<slot>.workflow.json (the exported agent). <slot> comes from the brief file names.
Nothing in this file is specific to one brief.
"""
import asyncio
import dataclasses
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "builder"))

BUDGET_S = int(os.environ.get("BUILD_BUDGET_S", str(25 * 60)))     # rule: 30 minutes per brief, tests included
MODEL = os.environ.get("BUILDER_MODEL", "claude-opus-5-5")
KIT_FILES = ["freya.py", "docs", "tools", "examples/base-agent.json", "public-test-set.json"]
# builder/tests is staged for its invented example spec (test_generate.py); it has no brief values.
BUILDER_FILES = ["builder/lib", "builder/validate.py", "builder/smoke.py", "builder/reference", "builder/tests", "builder/PATTERNS.md"]
SKILLS_DIR = ROOT / "builder" / "skills"
SECRET_PATTERNS = [re.compile(r"fak_[A-Za-z0-9_\-]+"), re.compile(r"sk-ant-[A-Za-z0-9_\-]+")]


class Trace:
    """Plain JSON lines: start, end, every model call, Freya objects, tests. No keys."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        path.parent.mkdir(exist_ok=True)
        self.f = path.open("w")
        self.secrets = [v for k, v in os.environ.items()
                        if k in ("FREYA_API_KEY", "FREYA_BANK_TEAM_KEY", "ANTHROPIC_API_KEY") and len(v) >= 8]

    def scrub(self, text: str) -> str:
        for s in self.secrets:
            text = text.replace(s, "[REDACTED]")
        for p in SECRET_PATTERNS:
            text = p.sub("[REDACTED]", text)
        return text

    def log(self, event: str, **data) -> None:
        line = json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, **data}, default=str)
        self.f.write(self.scrub(line) + "\n")
        self.f.flush()

    def close(self) -> None:
        self.f.close()


def slot_name(briefs: list) -> str:
    stems = [re.sub(r"[^a-z0-9]+", "-", pathlib.Path(b).stem.lower()).strip("-") for b in briefs]
    return "-".join(stems)[:60] or "brief"


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        return "unknown"


def stage(slot: str, api_file: pathlib.Path, briefs: list) -> pathlib.Path:
    """A clean working folder OUTSIDE the repository (so no project memory, no parent CLAUDE.md, no
    git history): kit files, our library, the inputs. No dev/, results/ or other briefs."""
    st = pathlib.Path(tempfile.mkdtemp(prefix=f"bb-{slot}-")) / "stage"
    (st / "input").mkdir(parents=True)
    for rel in KIT_FILES + BUILDER_FILES:
        src = ROOT / rel
        if src.is_dir():
            shutil.copytree(src, st / rel, ignore=shutil.ignore_patterns("__pycache__"))
        elif src.exists():
            (st / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, st / rel)
    if SKILLS_DIR.exists():
        shutil.copytree(SKILLS_DIR, st / ".claude" / "skills")
    shutil.copy2(api_file, st / "input" / api_file.name)
    for b in briefs:
        shutil.copy2(b, st / "input" / pathlib.Path(b).name)
    state = ROOT / ".freya-agents.json"          # same slot -> same workflow on every run (rule 5)
    if not state.exists():
        state.write_text("{}")
    (st / ".freya-agents.json").symlink_to(state)
    (st / "work").mkdir()
    (st / "results").mkdir()                     # tools/run_cases.py appends to results/log.jsonl
    return st


def prompt_for(slot: str, api_name: str, brief_names: list, deadline: float) -> str:
    practice = os.environ.get("BUILD_PRACTICE", "").strip()       # e.g. "A" when the bank has practice customers
    tests = (f"The bank has practice customers for this brief: tools/run_cases.py --brief {practice}. "
             if practice else "The bank has NO practice customers for this brief: do not run tools/run_cases.py at all. ")
    return (
        f"Build a Freya phone agent. Slot: {slot}. Tool API file: input/{api_name}. "
        f"Brief files: {', '.join('input/' + b for b in brief_names)}. "
        "Use the read-brief, design-agent and check-agent skills in that order. "
        "Work only inside this folder. Write the final workflow to work/workflow.json and copy every version that "
        "passes builder/validate.py to work/good.workflow.json. "
        f"Hard time limit: finish before {time.strftime('%H:%M', time.localtime(deadline))} local time, "
        "tests included. When in doubt, stop testing and leave a valid work/workflow.json. "
        "Run every command in the foreground and wait for it: never use nohup, & or background jobs. " + tests
    )


async def run_model(st: pathlib.Path, prompt: str, trace: Trace) -> None:
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, ToolUseBlock, query
    options = ClaudeAgentOptions(
        cwd=st, model=MODEL, setting_sources=["project"],
        skills=[p.name for p in (st / ".claude" / "skills").iterdir()] if (st / ".claude" / "skills").exists() else [],
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"], permission_mode="dontAsk", max_turns=150,
        env={"BASH_DEFAULT_TIMEOUT_MS": "900000", "BASH_MAX_TIMEOUT_MS": "1200000", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1"},
    )
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            texts = [b.text for b in message.content if isinstance(b, TextBlock) and b.text.strip()]
            tools = [b for b in message.content if isinstance(b, ToolUseBlock)]
            purpose = (texts[0].splitlines()[0][:160] if texts else
                       ", ".join(f"{t.name}: {str(t.input.get('description') or t.input.get('skill') or t.input.get('command') or t.input.get('file_path') or '')[:100]}"
                                 for t in tools))
            trace.log("model_call", model=getattr(message, "model", MODEL), purpose=purpose)
            for t in tools:
                cmd = str(t.input.get("command", ""))
                if "run_cases.py" in cmd or "validate" in cmd or "unittest" in cmd:
                    trace.log("test", tool=t.name, command=cmd[:400])
                if "save_workflow" in cmd:
                    trace.log("freya_save", command=cmd[:400])
        elif isinstance(message, ResultMessage):
            trace.log("model_done", turns=message.num_turns, seconds=round(message.duration_ms / 1000),
                      cost_usd=round(message.total_cost_usd or 0, 4))
        trace.log("message", kind=type(message).__name__, body=dataclasses.asdict(message))


def final_rules(st: pathlib.Path) -> dict:
    """The validator rules the run wrote, plus every call variable its spec names."""
    def load(name: str) -> dict:
        try:
            return json.loads((st / "work" / name).read_text())
        except (OSError, ValueError):
            return {}
    rules, spec = load("validate-rules.json"), load("spec.json")
    names = set(rules.get("call_variables") or [])
    names |= {spec.get("customer_variable"), spec.get("now_variable")} - {None}
    names |= set(re.findall(r"\{\{\s*(\w+)\s*\}\}", json.dumps([spec.get("address_as"), spec.get("opening")])))
    return dict(rules, call_variables=sorted(names))


def pick_workflow(st: pathlib.Path, api: dict, trace: Trace) -> dict | None:
    """The final workflow if it validates, else the last one that did."""
    import validate as V
    rules = final_rules(st)
    for name in ("workflow.json", "good.workflow.json"):
        p = st / "work" / name
        if not p.exists():
            continue
        try:
            wf = json.loads(p.read_text())
        except ValueError as e:
            trace.log("candidate_unreadable", file=name, error=str(e))
            continue
        errors = [m for level, m in V.validate(wf, api, rules) if level == V.ERROR]
        spec_file = st / "work" / "spec.json"
        if not errors and spec_file.exists():
            import smoke
            try:
                errors = smoke.run(wf, api, json.loads(spec_file.read_text()))
            except Exception as e:          # an unreadable spec or schema must not hide a valid workflow
                trace.log("smoke_skipped", error=repr(e)[:300])
        trace.log("validate", file=name, errors=errors[:20])
        if not errors:
            return wf
    return None


def generate_from_spec(st: pathlib.Path, api_file: pathlib.Path, trace: Trace) -> None:
    """Last resort: build work/workflow.json from work/spec.json with the reference generator."""
    gen = st / "work" / "reference" / "generate.py"
    if not gen.exists():
        gen = st / "builder" / "reference" / "generate.py"
    if not (st / "work" / "spec.json").exists() or not gen.exists():
        trace.log("fallback_skipped", reason="no spec.json or generator")
        return
    out = st / "work" / "fallback.workflow.json"
    r = subprocess.run([sys.executable, str(gen), str(st / "work" / "spec.json"), str(st / "input" / api_file.name), str(out)],
                       cwd=st, capture_output=True, text=True)
    trace.log("fallback_generate", returncode=r.returncode, stderr=r.stderr[-500:])
    if r.returncode == 0 and out.exists():
        shutil.copy2(out, st / "work" / "workflow.json")


def main(argv: list) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    api_file, briefs = pathlib.Path(argv[1]).resolve(), [str(pathlib.Path(b).resolve()) for b in argv[2:]]
    slot = os.environ.get("BUILD_SLOT") or slot_name(briefs)     # override only for practice runs
    start = time.time()
    trace = Trace(ROOT / "traces" / f"{slot}-{time.strftime('%Y%m%d-%H%M%S')}.jsonl")
    trace.log("start", slot=slot, commit=git_commit(), model=MODEL, budget_s=BUDGET_S,
              inputs={p: sha(pathlib.Path(p)) for p in [str(api_file)] + briefs})
    st = stage(slot, api_file, briefs)
    prompt = prompt_for(slot, api_file.name, [pathlib.Path(b).name for b in briefs], start + BUDGET_S)
    trace.log("prompt", text=prompt)
    try:
        asyncio.run(asyncio.wait_for(run_model(st, prompt, trace), timeout=BUDGET_S))
    except asyncio.TimeoutError:
        trace.log("budget_exceeded", seconds=round(time.time() - start))
    except Exception as e:  # the model run failing must not stop the save of a valid workflow
        trace.log("model_error", error=repr(e)[:500])
    keep = ROOT / "out" / slot
    if keep.exists():
        shutil.rmtree(keep)
    shutil.copytree(st / "work", keep / "work")                  # everything the run made, kept with the repo
    trace.log("work_kept", path=str(keep.relative_to(ROOT)))
    api = json.loads(api_file.read_text())
    wf = pick_workflow(st, api, trace)
    if wf is None:
        generate_from_spec(st, api_file, trace)
        wf = pick_workflow(st, api, trace)
    if wf is None:
        trace.log("end", ok=False, reason="no valid workflow", seconds=round(time.time() - start))
        trace.close()
        print("FAILED: no valid workflow. Trace:", trace.path)
        return 1
    import freya
    os.chdir(ROOT)
    saved = freya.save_workflow(slot, wf)
    trace.log("freya_saved", **saved)
    folder = ROOT / ("out" if os.environ.get("BUILD_SLOT") else "submission")    # practice runs never touch submission/
    folder.mkdir(exist_ok=True)
    export = folder / f"{slot}.workflow.json"
    freya.export_workflow(saved["workflow_id"], str(export))
    nodes = wf.get("nodes", {})
    trace.log("end", ok=True, seconds=round(time.time() - start), workflow_id=saved["workflow_id"],
              agent_id=saved["agent_id"], nodes=len(nodes), tools=sum(len(n.get("tools", [])) for n in nodes.values()),
              export=str(export.relative_to(ROOT)))
    trace.close()
    print(f"saved {slot}: workflow {saved['workflow_id']}, agent {saved['agent_id']}, {round(time.time() - start)} s. Trace: {trace.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
