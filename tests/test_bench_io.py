"""Round trips for the benchmark interchange formats (spec 058 R4)."""
from __future__ import annotations

import numpy as np

from quadmesh.benchmark._io import read_msh2, read_obj, write_msh2, write_obj

P = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0.5, 0]], float)
TRI = np.array([[0, 1, 2], [0, 2, 3]])
MIXED = np.array([[0, 1, 2, 3], [1, 4, 2, 2]])  # quad + padded triangle


def _rows(c):
    return [tuple(dict.fromkeys(int(x) for x in r if x >= 0)) for r in c]


def test_msh_roundtrip_tri(tmp_path):
    f = tmp_path / "a.msh"
    write_msh2(f, P, TRI)
    p, c = read_msh2(f)
    assert np.allclose(p, P) and np.array_equal(c, TRI)


def test_msh_roundtrip_mixed_and_one_based(tmp_path):
    f = tmp_path / "a.msh"
    write_msh2(f, P, MIXED)
    text = f.read_text()
    assert text.startswith("$MeshFormat\n2.2 0 8")
    assert "\n1 0 0 0\n" in text  # node ids 1-based, z = 0
    p, c = read_msh2(f)
    assert _rows(c) == _rows(MIXED)


def test_obj_roundtrip(tmp_path):
    f = tmp_path / "a.obj"
    write_obj(f, P, MIXED)
    lines = f.read_text().splitlines()
    assert lines[0] == "v 0 0 0"
    assert "f 1 2 3 4" in lines and "f 2 5 3" in lines
    p, c = read_obj(f)
    assert np.allclose(p, P) and _rows(c) == _rows(MIXED)


def test_obj_strips_texture_indices(tmp_path):
    f = tmp_path / "t.obj"
    f.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1/1/1 2/2/2 3/3/3\n")
    p, c = read_obj(f)
    assert c.tolist() == [[0, 1, 2]]


def test_roundtrip_bundled_mesh(tmp_path):
    import chilmesh, os
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(os.path.join(
        os.path.dirname(chilmesh.__file__), "data", "donut_domain.fort.14"))
    for w, r, n in ((write_msh2, read_msh2, "x.msh"), (write_obj, read_obj, "x.obj")):
        f = tmp_path / n
        w(f, m.points, m.connectivity_list)
        p, c = r(f)
        assert np.allclose(p[:, :2], m.points[:, :2])
        assert np.array_equal(c, m.connectivity_list)
