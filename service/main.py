"""FastAPI service wrapping the spec2schematic core.

Endpoints:
- GET  /                  mini demo UI (static/index.html)
- GET  /api/examples      list the repo's example specs
- POST /api/generate      spec YAML -> SVG + lint findings (JSON)
- POST /api/generate/dxf  spec YAML -> DXF file download
"""
from __future__ import annotations

import concurrent.futures
import os
import tempfile
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from spec2schematic.erc import check, has_errors
from spec2schematic.layout import build_drawing
from spec2schematic.lint import lint
from spec2schematic.render_dxf import MissingDxfDependencyError, render_dxf
from spec2schematic.render_svg import render_svg
from spec2schematic.schema import Spec, SpecError, load_spec

MAX_SPEC_BYTES = 64 * 1024
GENERATE_TIMEOUT_SECONDS = 10

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="spec2schematic service")
_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


class GenerateRequest(BaseModel):
    spec: str


class GenerateResult(BaseModel):
    svg: str
    lint: list[str]


class ExampleOut(BaseModel):
    name: str
    spec: str


def _parse_spec_text(spec_text: str) -> Spec:
    if len(spec_text.encode("utf-8")) > MAX_SPEC_BYTES:
        raise HTTPException(status_code=422, detail=[f"spec exceeds {MAX_SPEC_BYTES} byte limit"])

    fd, tmp_name = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        tmp_path.write_text(spec_text, encoding="utf-8")
        return load_spec(tmp_path)
    except (SpecError, OSError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=422, detail=[str(exc)]) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _check_erc(spec: Spec) -> list[str]:
    issues = check(spec)
    if has_errors(issues):
        detail = [str(issue) for issue in issues if issue.severity == "error"]
        raise HTTPException(status_code=422, detail=detail)
    return [str(issue) for issue in issues]


def _build_and_render(spec_text: str) -> GenerateResult:
    spec = _parse_spec_text(spec_text)
    warnings = _check_erc(spec)
    drawing = build_drawing(spec)
    svg = render_svg(drawing)
    findings = [str(f) for f in lint(drawing)]
    return GenerateResult(svg=svg, lint=warnings + findings)


def _build_dxf(spec_text: str) -> tuple[Path, str]:
    spec = _parse_spec_text(spec_text)
    _check_erc(spec)
    drawing = build_drawing(spec)
    fd, tmp_name = tempfile.mkstemp(suffix=".dxf")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        render_dxf(drawing, tmp_path)
    except MissingDxfDependencyError as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail=[str(exc)]) from exc
    return tmp_path, spec.name


def _run_with_timeout(fn, *args):
    future = _executor.submit(fn, *args)
    try:
        return future.result(timeout=GENERATE_TIMEOUT_SECONDS)
    except concurrent.futures.TimeoutError:
        raise HTTPException(status_code=504, detail=["generation timed out"])


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request, exc):  # noqa: ARG001
    return JSONResponse(status_code=500, content={"detail": ["internal error"]})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/examples", response_model=list[ExampleOut])
def list_examples() -> list[ExampleOut]:
    return [
        ExampleOut(name=path.stem, spec=path.read_text(encoding="utf-8"))
        for path in sorted(EXAMPLES_DIR.glob("*.yaml"))
    ]


@app.post("/api/generate", response_model=GenerateResult)
def generate(payload: GenerateRequest) -> GenerateResult:
    return _run_with_timeout(_build_and_render, payload.spec)


@app.post("/api/generate/dxf")
def generate_dxf(payload: GenerateRequest) -> FileResponse:
    tmp_path, spec_name = _run_with_timeout(_build_dxf, payload.spec)
    return FileResponse(
        tmp_path,
        media_type="application/dxf",
        filename=f"{spec_name}.dxf",
        background=BackgroundTask(tmp_path.unlink),
    )
