"""Experiment harness.

Every run is append-only: it gets a fresh UTC timestamp + nonce directory under
``experiments/<id>/runs/<run_id>/``.  Raw trials are written as JSON Lines while
the experiment runs, so a crash still leaves usable data.  Processed summaries
and reports are derived files inside the same run directory; the experiment's
``LATEST`` pointer is the only file that is intentionally replaced.

An experiment is a :class:`ExperimentSpec` plus a ``run(ctx)`` function.  The
function must call :meth:`RunContext.record` for every trial and
:meth:`RunContext.conclude` once.  It must not fabricate measurements: all
numbers come from the code under ``otl/`` or from the standard library.
"""

from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import importlib.metadata
import json
import os
import platform
import secrets
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from otl import __version__
from otl.config import ExperimentConfig, config_to_dict

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = ROOT / "experiments"
RESULTS = ROOT / "results"


# ---------------------------------------------------------------------------
# Spec and context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    title: str
    hypothesis: str
    classification: str
    controlled: tuple[str, ...]
    independent: tuple[str, ...]
    dependent: tuple[str, ...]
    procedure: tuple[str, ...]
    run: Callable[["RunContext"], None]
    # Evidence defaults keep every software/simulation experiment honest.  A
    # physical experiment overrides these at run time from its session manifest.
    evidence_source: str = "SIMULATED / SOFTWARE"
    simulation_only: bool = True
    device_required: bool = False


@dataclass
class RunContext:
    spec: ExperimentSpec
    run_id: str
    out_dir: Path
    quick: bool = False
    options: dict[str, Any] = field(default_factory=dict)

    trials: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    conclusion: str = ""
    failures: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    evidence_source: str = "SIMULATED / SOFTWARE"
    simulation_only: bool = True
    device: dict[str, Any] | None = None
    classification: str | None = None
    _raw: Any = None

    def __post_init__(self) -> None:
        self.evidence_source = self.spec.evidence_source
        self.simulation_only = self.spec.simulation_only
        self.classification = self.spec.classification

    # -- recording ---------------------------------------------------------

    def record(
        self,
        *,
        config: dict[str, Any] | None = None,
        inputs: dict[str, Any] | None = None,
        outputs: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        trial = {
            "experiment": self.spec.id,
            "run_id": self.run_id,
            "trial": len(self.trials),
            "config": _clean(config or {}),
            "inputs": _clean(inputs or {}),
            "outputs": _clean(outputs or {}),
            "metrics": _clean(metrics or {}),
            "errors": _clean(errors or []),
            "notes": notes,
        }
        self.trials.append(trial)
        assert self._raw is not None
        self._raw.write(json.dumps(trial, sort_keys=True, default=_default) + "\n")
        self._raw.flush()
        return trial

    def conclude(self, text: str) -> None:
        self.conclusion = text.strip()

    def fail(self, text: str) -> None:
        self.failures.append(text)

    def artifact(self, name: str, path: Path) -> None:
        self.artifacts[name] = str(path.relative_to(self.out_dir))

    # -- convenience -------------------------------------------------------

    def summary_stats(self, values: Iterable[float]) -> dict[str, float]:
        from otl.metrics import Aggregate

        agg = Aggregate()
        for value in values:
            agg.add(float(value))
        return agg.to_dict()


# ---------------------------------------------------------------------------
# Environment / serialisation
# ---------------------------------------------------------------------------


def _default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    if dataclasses.is_dataclass(value):
        return config_to_dict(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    if dataclasses.is_dataclass(value):
        return _clean(config_to_dict(value))
    return value


def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment(
    *,
    device: dict[str, Any] | None = None,
    simulation_only: bool = True,
    evidence_source: str = "SIMULATED / SOFTWARE",
) -> dict[str, Any]:
    import numpy

    try:
        import cv2

        opencv = cv2.__version__
    except Exception:  # pragma: no cover
        opencv = None
    try:
        import PIL

        pillow = PIL.__version__
    except Exception:  # pragma: no cover
        pillow = None
    return {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "otl_version": __version__,
        "numpy": numpy.__version__,
        "opencv": opencv,
        "pillow": pillow,
        "zstandard": _version("zstandard"),
        "pytest": _version("pytest"),
        # Policy rule 6: name the device or say "none".  Software experiments
        # pass the defaults; a physical experiment passes its session device.
        "device": device,
        "simulation_only": simulation_only,
        "evidence_source": evidence_source,
    }


def _run_id(spec_id: str) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{secrets.token_hex(3)}"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_experiment(
    spec: ExperimentSpec,
    *,
    quick: bool = False,
    options: dict[str, Any] | None = None,
) -> Path:
    run_id = _run_id(spec.id)
    out_dir = EXPERIMENTS / spec.id / "runs" / run_id
    raw_dir = out_dir / "raw"
    processed = out_dir / "processed"
    figures = out_dir / "figures"
    artifacts = out_dir / "artifacts"
    for directory in (raw_dir, processed, figures, artifacts):
        directory.mkdir(parents=True, exist_ok=False)

    ctx = RunContext(
        spec=spec, run_id=run_id, out_dir=out_dir, quick=quick, options=dict(options or {})
    )
    started = time.perf_counter()
    raw_path = raw_dir / "trials.jsonl"
    with raw_path.open("w", encoding="utf-8") as raw:
        ctx._raw = raw
        try:
            spec.run(ctx)
        except Exception as exc:  # a failed run is data too
            ctx.fail(f"{type(exc).__name__}: {exc}")
            ctx.conclude(
                "The run did not complete. Raw trials written before the failure are "
                "retained; see failures and the traceback in manifest.json."
            )
            import traceback

            (out_dir / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        finally:
            ctx._raw = None
    wall_s = time.perf_counter() - started

    if not ctx.conclusion:
        ctx.conclude(
            "No conclusion was recorded by the experiment. Treat all numbers as "
            "incomplete observations."
        )

    manifest = {
        "run_id": run_id,
        "spec": _spec_dict(spec),
        "quick": quick,
        "environment": environment(
            device=ctx.device,
            simulation_only=ctx.simulation_only,
            evidence_source=ctx.evidence_source,
        ),
        "config_defaults": config_to_dict(ExperimentConfig()),
        "experiment_metadata": _clean(ctx.metadata),
        "wall_s": wall_s,
        "n_trials": len(ctx.trials),
        "failures": ctx.failures,
        "artifacts": ctx.artifacts,
        "raw": "raw/trials.jsonl",
        "simulation_only": ctx.simulation_only,
        "classification": ctx.classification or spec.classification,
        "evidence_source": ctx.evidence_source,
        "device": ctx.device,
    }
    _write_json(out_dir / "manifest.json", manifest)
    _write_json(
        processed / "summary.json",
        {
            "run_id": run_id,
            "experiment": spec.id,
            "title": spec.title,
            "classification": ctx.classification or spec.classification,
            "simulation_only": ctx.simulation_only,
            "evidence_source": ctx.evidence_source,
            "device": ctx.device,
            "n_trials": len(ctx.trials),
            "wall_s": wall_s,
            "experiment_metadata": _clean(ctx.metadata),
            "summary": ctx.summary,
            "conclusion": ctx.conclusion,
            "failures": ctx.failures,
        },
    )
    _write_csv(processed / "summary.csv", ctx.trials)
    (out_dir / "REPORT.md").write_text(_report(spec, ctx, manifest), encoding="utf-8")
    _write_experiment_readme(spec)
    (EXPERIMENTS / spec.id / "LATEST").write_text(run_id + "\n", encoding="utf-8")
    _update_index(spec, run_id, ctx, wall_s)
    return out_dir


def _spec_dict(spec: ExperimentSpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "title": spec.title,
        "hypothesis": spec.hypothesis,
        "classification": spec.classification,
        "controlled": list(spec.controlled),
        "independent": list(spec.independent),
        "dependent": list(spec.dependent),
        "procedure": list(spec.procedure),
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_default) + "\n",
        encoding="utf-8",
    )


def _write_csv(path: Path, trials: list[dict[str, Any]]) -> None:
    metric_keys: list[str] = []
    seen: set[str] = set()
    for trial in trials:
        for key in trial["metrics"]:
            if key not in seen:
                seen.add(key)
                metric_keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["trial", *metric_keys])
        for trial in trials:
            writer.writerow(
                [trial["trial"], *[_csv_value(trial["metrics"].get(k)) for k in metric_keys]]
            )


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


def _report(spec: ExperimentSpec, ctx: RunContext, manifest: dict[str, Any]) -> str:
    lines = [
        f"# {spec.id} — {spec.title}",
        "",
        f"- Run: `{ctx.run_id}`",
        f"- Classification: **{ctx.classification or spec.classification}**",
        f"- Evidence source: **{ctx.evidence_source}**",
        *(
            [f"- Device: **{ctx.device.get('model', 'unknown')}**"]
            if ctx.device
            else ["- Device: none (no physical capture)"]
        ),
        f"- Trials: {len(ctx.trials)}",
        f"- Wall time: {manifest['wall_s']:.2f} s",
        f"- Quick mode: {ctx.quick}",
        "",
        "## Hypothesis",
        "",
        spec.hypothesis,
        "",
        "## Controlled variables",
        "",
        *[f"- {item}" for item in spec.controlled],
        "",
        "## Independent variables",
        "",
        *[f"- {item}" for item in spec.independent],
        "",
        "## Dependent variables",
        "",
        *[f"- {item}" for item in spec.dependent],
        "",
        "## Procedure",
        "",
        *[f"{i}. {step}" for i, step in enumerate(spec.procedure, 1)],
        "",
        *(
            [
                "## Experiment metadata",
                "",
                "```json",
                json.dumps(_clean(ctx.metadata), indent=2, sort_keys=True, default=_default),
                "```",
                "",
            ]
            if ctx.metadata
            else []
        ),
        "## Processed results",
        "",
        "```json",
        json.dumps(ctx.summary, indent=2, sort_keys=True, default=_default),
        "```",
        "",
        "Raw measurements: `raw/trials.jsonl` (one JSON object per trial).",
        "Tabular metrics: `processed/summary.csv`.",
        "",
        "## Failures",
        "",
        *([f"- {item}" for item in ctx.failures] if ctx.failures else ["- None recorded."]),
        "",
        "## Conclusion",
        "",
        ctx.conclusion,
        "",
        "## Reproduction",
        "",
        "```bash",
        f"cd {ROOT}",
        f"python3 -m experiments.run_all --only {spec.id}"
        + (" --quick" if ctx.quick else ""),
        "```",
        "",
        "The run directory is immutable; re-running creates a new run id.",
        "",
        "## Environment",
        "",
        "```json",
        json.dumps(manifest["environment"], indent=2, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines)


def _write_experiment_readme(spec: ExperimentSpec) -> None:
    path = EXPERIMENTS / spec.id / "README.md"
    text = f"""# {spec.id} — {spec.title}

Hypothesis: {spec.hypothesis}

This directory is append-only. Every invocation creates
`runs/<UTC timestamp>-<nonce>/` containing:

- `manifest.json` — spec, environment, wall time, failures
- `raw/trials.jsonl` — one JSON object per trial, written while running
- `processed/summary.json` — processed aggregates and conclusion
- `processed/summary.csv` — one row per trial
- `REPORT.md` — human-readable report
- `artifacts/` — any images or hashes produced by the experiment

`LATEST` contains the newest run id. Nothing in an older run directory is
modified by a later run.

Run it with:

```bash
cd {ROOT}
python3 -m experiments.run_all --only {spec.id}
```
"""
    path.write_text(text, encoding="utf-8")


def _update_index(
    spec: ExperimentSpec, run_id: str, ctx: RunContext, wall_s: float
) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    index_path = RESULTS / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index = {"experiments": {}}
    index.setdefault("experiments", {})[spec.id] = {
        "title": spec.title,
        "classification": ctx.classification or spec.classification,
        "latest_run": run_id,
        "n_trials": len(ctx.trials),
        "wall_s": wall_s,
        "conclusion": ctx.conclusion,
        "summary": ctx.summary,
        "evidence_source": ctx.evidence_source,
        "simulation_only": ctx.simulation_only,
        "device": ctx.device,
        "report": str(
            (EXPERIMENTS / spec.id / "runs" / run_id / "REPORT.md").relative_to(ROOT)
        ),
        "updated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    _write_json(index_path, index)
    lines = [
        "# Experiment results",
        "",
        "Evidence source is recorded per experiment. E01–E10 are **SIMULATED / "
        "SOFTWARE**; E11 is **PHYSICAL / CAMERA CAPTURE** only when its session "
        "contains real camera images, otherwise it is **BLOCKED** or a "
        "**SOFTWARE FIXTURE**; E12 is **PHYSICAL / CAMERA CAPTURE** only when it "
        "reads at least one finalized camera session, otherwise **BLOCKED**. "
        "Check the per-run report before citing a result.",
        "",
        "| ID | Title | Classification | Evidence | Trials | Latest run | Conclusion |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for exp_id in sorted(index["experiments"]):
        entry = index["experiments"][exp_id]
        conclusion = str(entry["conclusion"]).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {exp_id} | {entry['title']} | {entry['classification']} | "
            f"{entry.get('evidence_source', 'SIMULATED / SOFTWARE')} | "
            f"{entry['n_trials']} | `{entry['latest_run']}` | {conclusion} |"
        )
    lines.append("")
    (RESULTS / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
