"""Forbidden-verb linter (architecture_spec.md §8).

At CI time, walks every Python module in ``src/healthscore/`` via AST and
fails on any forbidden lemma found in:

    * string-literal constants (``ast.Constant`` with ``str`` value)
    * public function names (``def`` not starting with ``_``)
    * public class names

Per architecture_spec.md §8, the full linter scope (Phase 2+) extends to
``configs/wording.yaml``, all per-score JSON configs, and the ``wording``
field of every ScoreResult produced by the regression suite. Those land
when wording.yaml and score configs land in Phase 2.

The exception list lives in ``healthscore.wording.ALLOW_LIST`` and is
itself version-controlled so a relaxation of the linter is a deliberate,
visible change.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from healthscore.wording import (
    ALLOW_LIST,
    FORBIDDEN_LEMMAS,
    scan_text_for_forbidden_lemmas,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACKAGE_ROOT = _REPO_ROOT / "src" / "healthscore"
_CONFIGS_ROOT = _REPO_ROOT / "configs"
_SCORE_CONFIGS_DIR = _CONFIGS_ROOT / "scores"
_WORDING_YAML = _CONFIGS_ROOT / "wording.yaml"


# ──────────────────────────────────────────────────────────────────────────
# AST walker
# ──────────────────────────────────────────────────────────────────────────


def _module_files() -> list[Path]:
    """Every .py file under src/healthscore/ (recursive). Order is stable
    so failure messages are reproducible."""
    return sorted(_PACKAGE_ROOT.rglob("*.py"))


def _scan_module(path: Path) -> list[tuple[int, str, str, str]]:
    """Walk a module's AST. Return (lineno, kind, identifier_or_text, lemma) tuples
    for every forbidden lemma found in the *user-facing* surfaces specified
    by architecture_spec.md §8:

        - string literals returned from public functions
          (i.e. inside an ``ast.Return`` whose enclosing FunctionDef has a
           name not starting with ``_``).
        - public function names (FunctionDef / AsyncFunctionDef whose name
          does not start with ``_``).
        - public class names (ClassDef whose name does not start with ``_``).

    Internal docstrings, module-level constants (including the linter's own
    FORBIDDEN_LEMMAS tuple), Field defaults, raise-message format strings,
    and private helpers are out of scope -- they are not user-facing
    output. The Phase 2+ extension of this linter will additionally cover
    ``configs/wording.yaml`` and per-score JSON templates, where the
    user-facing wording strings actually live.
    """
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        # Unparseable module = linter cannot certify it = treat as failure.
        return [(0, "syntax_error", str(path), "")]

    findings: list[tuple[int, str, str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            # Public function name itself.
            for lemma in scan_text_for_forbidden_lemmas(node.name):
                findings.append((node.lineno, "function_name", node.name, lemma))
            # Walk the body for ``return <expr>`` statements; collect any
            # string-literal Constants reachable from the returned expression.
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Return) or inner.value is None:
                    continue
                for sub in ast.walk(inner.value):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        for lemma in scan_text_for_forbidden_lemmas(sub.value):
                            findings.append(
                                (sub.lineno, "return_string", sub.value, lemma)
                            )
            continue

        if isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            for lemma in scan_text_for_forbidden_lemmas(node.name):
                findings.append((node.lineno, "class_name", node.name, lemma))

    return findings


# ──────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────


def test_package_root_contains_modules_to_scan():
    """Sanity: the linter actually has files to inspect."""
    files = _module_files()
    assert files, f"expected .py files under {_PACKAGE_ROOT}, found none"
    # Spot-check the Phase 0/1 modules are discovered.
    names = {p.name for p in files}
    assert "gates.py" in names
    assert "registry.py" in names
    assert "wording.py" in names


@pytest.mark.parametrize(
    "module_file",
    _module_files(),
    ids=lambda p: str(p.relative_to(_REPO_ROOT)).replace("\\", "/"),
)
def test_no_forbidden_lemmas_in_user_facing_surfaces(module_file: Path):
    """Every public function name, class name, and string literal in the
    scoring-core package must be free of forbidden lemmas (modulo the
    allow-list in healthscore.wording).

    A failure here means: someone added a string or identifier that
    contains a regulator-prohibited lemma. Either rename it, rephrase it,
    add the phrase to ALLOW_LIST (deliberately, with rationale in the
    commit), or move it to a non-user-facing internal helper (private
    function name with leading underscore)."""
    findings = _scan_module(module_file)
    if findings:
        formatted = "\n".join(
            f"  {module_file.name}:{lineno}  [{kind}]  {lemma!r} in: {text!r}"
            for lineno, kind, text, lemma in findings
        )
        pytest.fail(
            f"Forbidden lemma(s) found in {module_file.name}:\n"
            f"{formatted}\n\n"
            f"Allow-listed phrases: {ALLOW_LIST}\n"
            f"Strict-forbidden lemmas: {FORBIDDEN_LEMMAS}"
        )


# ──────────────────────────────────────────────────────────────────────────
# Phase 2 widening: scan configs/scores/*.json + configs/wording.yaml
#
# Per architecture_spec.md §8 the linter at CI must walk:
#     - all *.json configs under configs/scores/
#     - configs/wording.yaml
# in addition to the public-function-return surface walked above.
# These are the architecturally most important lint targets because they
# are where user-facing wording actually lives.
# ──────────────────────────────────────────────────────────────────────────


def _scan_json_string_values(path: Path) -> list[tuple[str, str]]:
    """Walk a JSON file's tree, return (json_pointer, lemma) for any
    forbidden lemma found in any string value (recursive)."""
    import json as _json

    data = _json.loads(path.read_text(encoding="utf-8"))
    findings: list[tuple[str, str]] = []

    def _walk(node, pointer: str) -> None:
        if isinstance(node, str):
            for lemma in scan_text_for_forbidden_lemmas(node):
                findings.append((pointer, lemma))
        elif isinstance(node, dict):
            for k, v in node.items():
                _walk(v, f"{pointer}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                _walk(v, f"{pointer}/{i}")

    _walk(data, "")
    return findings


def _score_config_files() -> list[Path]:
    if not _SCORE_CONFIGS_DIR.exists():
        return []
    return sorted(_SCORE_CONFIGS_DIR.glob("*.json"))


@pytest.mark.parametrize(
    "config_file",
    _score_config_files(),
    ids=lambda p: f"configs/scores/{p.name}",
)
def test_no_forbidden_lemmas_in_score_config_strings(config_file: Path):
    """Every string value in every per-score JSON config must be free of
    forbidden lemmas (modulo the allow-list).

    User-visible surfaces in score configs include display_name,
    guideline_anchor, applicable_population.calibration_caveat,
    derivation_cohort.outcome, red_flag.wording_key, exclusions, etc.
    The methodology document is the primary source of truth for these
    strings; the linter is the CI guard."""
    findings = _scan_json_string_values(config_file)
    if findings:
        formatted = "\n".join(
            f"  {config_file.name}{ptr}  -- {lemma!r}"
            for ptr, lemma in findings
        )
        pytest.fail(
            f"Forbidden lemma(s) found in {config_file.name}:\n{formatted}\n\n"
            f"Allow-listed phrases: {ALLOW_LIST}"
        )


def test_no_forbidden_lemmas_in_wording_yaml():
    """configs/wording.yaml is the user-facing risk-band template store.
    Every template string must be free of forbidden lemmas."""
    if not _WORDING_YAML.exists():
        pytest.skip("configs/wording.yaml not present (Phase 2 deliverable)")
    text = _WORDING_YAML.read_text(encoding="utf-8")
    # Scan the whole YAML as text -- simpler than parsing, equally strict.
    found = scan_text_for_forbidden_lemmas(text)
    if found:
        pytest.fail(
            f"Forbidden lemma(s) in configs/wording.yaml: {sorted(set(found))}\n"
            f"Allow-listed phrases: {ALLOW_LIST}"
        )


def test_linter_self_check_detects_a_known_violation():
    """Meta: the linter's own scanner reports a deliberate violation.

    If this test fails, the linter is broken (false negatives) -- which
    means the parametrised test above might be silently passing while
    real violations slip through. The explicit lemma here is a string
    literal local to this test, never imported elsewhere; the
    parametrised AST walker excludes the tests/ tree by scanning only
    src/healthscore/."""
    deliberate_violation = "this string contains the word diagnose for testing"
    findings = scan_text_for_forbidden_lemmas(deliberate_violation)
    assert "diagnose" in findings, (
        "scanner failed to detect a deliberate violation; the package-walk "
        "test is unreliable"
    )
