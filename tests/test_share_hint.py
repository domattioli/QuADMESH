"""The share-your-mesh hint prints to stderr once per process and honors the opt-out."""

import numpy as np
import pytest

import quadmesh.cli as cli
import quadmesh.share_hint as hint_mod
from quadmesh.share_hint import maybe_log_share_hint


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv("QUADMESH_NO_SHARE_HINT", raising=False)
    monkeypatch.setattr(hint_mod, "_hint_shown", False)


def test_hint_emitted_once(capsys):
    maybe_log_share_hint()
    maybe_log_share_hint()
    err = capsys.readouterr().err
    assert err.count("valence-intake") == 1


def test_hint_suppressed_by_env(capsys, monkeypatch):
    monkeypatch.setenv("QUADMESH_NO_SHARE_HINT", "1")
    maybe_log_share_hint()
    assert capsys.readouterr().err == ""


def test_cli_main_emits_hint_on_stderr(capsys, monkeypatch, tmp_path):
    class FakeMesh:
        n_elems, n_verts, n_layers = 1, 3, 1

        def write_to_fort14(self, path):
            pass

    src = tmp_path / "in.14"
    src.write_text("x")
    monkeypatch.setattr(cli.CHILmesh, "read_from_fort14", staticmethod(lambda p: FakeMesh()))
    monkeypatch.setattr(cli, "run_pipeline", lambda mesh, **kw: mesh)
    monkeypatch.setattr(cli, "compute_quality_stats", lambda m: {})
    monkeypatch.setattr(cli, "format_quality_report", lambda s: "report")
    assert cli.main([str(src), "-o", str(tmp_path / "out.14")]) == 0
    cap = capsys.readouterr()
    assert "valence-intake" in cap.err
    assert "valence-intake" not in cap.out
