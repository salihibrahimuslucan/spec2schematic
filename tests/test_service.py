from __future__ import annotations

from fastapi.testclient import TestClient

from service.main import MAX_SPEC_BYTES, app

client = TestClient(app)

VALID_SPEC = """
name: two-resistor
components:
  - id: R1
    type: resistor
    ports: [a, b]
  - id: R2
    type: resistor
    ports: [a, b]
nets:
  - name: MID
    connects: [R1.b, R2.a]
"""

BROKEN_SPEC = """
name: broken
components:
  - id: R1
    type: resistor
    ports: [a, b]
nets:
  - name: BAD
    connects: [R1.a, R2.b]
"""


def test_generate_returns_svg_and_lint():
    res = client.post("/api/generate", json={"spec": VALID_SPEC})
    assert res.status_code == 200
    body = res.json()
    assert "<svg" in body["svg"]
    assert isinstance(body["lint"], list)


def test_generate_rejects_erc_errors_with_readable_message():
    res = client.post("/api/generate", json={"spec": BROKEN_SPEC})
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert isinstance(detail, list) and detail
    assert any("R2" in msg for msg in detail)


def test_generate_rejects_malformed_yaml_without_traceback():
    res = client.post("/api/generate", json={"spec": "not: [valid"})
    assert res.status_code == 422
    body = res.json()
    assert "Traceback" not in str(body)


def test_generate_rejects_oversized_spec():
    huge = "name: x\ncomponents: []\nnets: []\n# " + ("a" * (MAX_SPEC_BYTES + 1))
    res = client.post("/api/generate", json={"spec": huge})
    assert res.status_code == 422
    assert "byte limit" in res.json()["detail"][0]


def test_examples_endpoint_lists_repo_examples():
    res = client.get("/api/examples")
    assert res.status_code == 200
    names = {item["name"] for item in res.json()}
    assert {"divider", "dol_starter", "tank_level"} <= names
    for item in res.json():
        assert item["spec"].strip()


def test_generate_dxf_returns_downloadable_file():
    res = client.post("/api/generate/dxf", json={"spec": VALID_SPEC})
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/dxf"
    assert "attachment" in res.headers["content-disposition"]
    assert res.content.startswith(b"  0\r\nSECTION") or b"SECTION" in res.content[:50]


def test_generate_dxf_rejects_erc_errors():
    res = client.post("/api/generate/dxf", json={"spec": BROKEN_SPEC})
    assert res.status_code == 422


def test_index_serves_html_ui():
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "spec2schematic" in res.text
