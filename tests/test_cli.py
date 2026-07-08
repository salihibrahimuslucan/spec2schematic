import os
import subprocess
import sys
from pathlib import Path

from spec2schematic.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
DIVIDER = str(EXAMPLES / "divider.yaml")


def _write(tmp_path, text):
    path = tmp_path / "spec.yaml"
    path.write_text(text, encoding="utf-8")
    return str(path)


BROKEN = (
    "name: broken\n"
    "components:\n"
    "  - {id: A, type: part, ports: [p]}\n"
    "nets:\n"
    "  - {name: N1, connects: [A.p, GHOST.x]}\n"
)


def test_check_clean_spec_exits_zero(capsys):
    assert main(["check", DIVIDER]) == 0
    out = capsys.readouterr().out
    assert "ERC: clean" in out
    assert "net MID: R1.b, R2.a" in out


def test_check_erc_error_exits_one(tmp_path, capsys):
    assert main(["check", _write(tmp_path, BROKEN)]) == 1
    assert "E002" in capsys.readouterr().out


def test_check_missing_file_exits_two(capsys):
    assert main(["check", "no-such-file.yaml"]) == 2
    assert "spec error" in capsys.readouterr().out


def test_render_writes_svg(tmp_path, capsys):
    out = tmp_path / "divider.svg"
    assert main(["render", DIVIDER, "-o", str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<svg ")
    assert f"wrote {out}" in capsys.readouterr().out


def test_render_refuses_spec_with_erc_errors(tmp_path, capsys):
    out = tmp_path / "broken.svg"
    assert main(["render", _write(tmp_path, BROKEN), "-o", str(out)]) == 1
    assert not out.exists()
    assert "render blocked" in capsys.readouterr().out


def test_render_rejects_unknown_format(tmp_path, capsys):
    assert main(["render", DIVIDER, "-o", str(tmp_path / "out.pdf")]) == 2
    assert "unsupported output format" in capsys.readouterr().out


def test_render_writes_dxf(tmp_path):
    import pytest

    pytest.importorskip("ezdxf")
    out = tmp_path / "divider.dxf"
    assert main(["render", DIVIDER, "-o", str(out)]) == 0
    head = out.read_bytes()[:64]
    assert b"SECTION" in head  # DXF header structure


def test_lint_clean_example(capsys):
    assert main(["lint", DIVIDER]) == 0
    assert "lint clean" in capsys.readouterr().out


def test_lint_reports_erc_errors(tmp_path, capsys):
    assert main(["lint", _write(tmp_path, BROKEN)]) == 1
    assert "E002" in capsys.readouterr().out


def test_lint_reports_open_pin_geometry(tmp_path, capsys):
    spec = (
        "name: open-pin\n"
        "components:\n"
        "  - {id: A, type: part, ports: [p, spare]}\n"
        "  - {id: B, type: part, ports: [p]}\n"
        "nets:\n"
        "  - {name: N1, connects: [A.p, B.p]}\n"
    )
    assert main(["lint", _write(tmp_path, spec)]) == 1
    assert "L004" in capsys.readouterr().out


def test_no_command_is_usage_error(capsys):
    assert main([]) == 2


def test_render_is_deterministic_across_hash_seeds(tmp_path):
    """Byte-identical output even under different PYTHONHASHSEED values."""
    outputs = []
    for seed in ("0", "424242"):
        out = tmp_path / f"divider_{seed}.svg"
        env = dict(os.environ, PYTHONHASHSEED=seed)
        subprocess.run(
            [sys.executable, "-m", "spec2schematic.cli", "render", DIVIDER, "-o", str(out)],
            check=True,
            env=env,
            capture_output=True,
        )
        outputs.append(out.read_bytes())
    assert outputs[0] == outputs[1]
