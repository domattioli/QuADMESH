// T040: doublet_collapse.py and quad_vertex_merge.py.
#include <algorithm>

#include "common.hpp"
#include "quadmesh/cpython_set.hpp"
#include "quadmesh/post_process.hpp"

namespace quadmesh {

using post_detail::boundary_mask;
using post_detail::has_quad;
using post_detail::rebuild;

namespace {
std::vector<int> uniq(const Elem& r) {
    std::vector<int> s(r.begin(), r.end());
    std::sort(s.begin(), s.end());
    s.erase(std::unique(s.begin(), s.end()), s.end());
    return s;
}
}  // namespace

Mesh doublet_collapse(const Mesh& mesh, TieLog* tielog) {
    if (!has_quad(mesh)) return mesh;  // Python: connectivity has 3 columns
    const std::vector<char> bdy = boundary_mask(mesh);
    const int ne = mesh.n_elems();
    std::vector<char> consumed(ne, 0);
    std::vector<Elem> rows = mesh.elems;

    for (int v = 0; v < mesh.n_verts(); ++v) {
        if (bdy[v]) continue;
        const std::vector<int>& elems = mesh.get_vertex_elements(v);
        if (elems.size() != 2) continue;
        // Tie site doublet_collapse.py:43: Python unpacks list(set) of the two
        // elements, so ea (the surviving row) is the first in CPython set
        // iteration order. Reproduced exactly (FR-020); CHILmesh builds the
        // set from ascending element ids and get_vertex_elements copies it.
        const std::vector<int> order = cpython_set_order(elems);
        const int ea = order[0], eb = order[1];
        if (tielog) tielog->record("SPEC-09", "doublet_collapse.py:43", order, ea);
        if (consumed[ea] || consumed[eb]) continue;
        if (is_tri(rows[ea]) || is_tri(rows[eb])) continue;
        const Elem ra = rows[ea], rb = rows[eb];
        const std::vector<int> sa = uniq(ra), sb = uniq(rb);
        int common = 0, unique_b = -1;
        for (int x : sb) {
            if (std::binary_search(sa.begin(), sa.end(), x)) ++common;
            else if (unique_b < 0) unique_b = x;  // smallest of rb - ra
        }
        if (common != 3 || unique_b < 0) continue;
        Elem merged = ra;
        for (int& x : merged)
            if (x == v) x = unique_b;
        if (uniq(merged).size() != 4) continue;
        rows[ea] = merged;
        consumed[eb] = 1;
    }
    if (std::find(consumed.begin(), consumed.end(), 1) == consumed.end()) return mesh;
    std::vector<Elem> keep;
    keep.reserve(ne);
    for (int e = 0; e < ne; ++e)
        if (!consumed[e]) keep.push_back(rows[e]);
    return remove_unused(rebuild(mesh, mesh.points, std::move(keep)), post_detail::adj_only());
}

Mesh quad_vertex_merge(const Mesh& mesh) {
    if (!has_quad(mesh)) return mesh;
    const std::vector<char> bdy = boundary_mask(mesh);
    const std::vector<Elem>& cl = mesh.elems;
    const int ne = mesh.n_elems();
    struct Merge { int elem, keep, drop; std::vector<int> side2; };
    std::vector<Merge> eligible;
    std::vector<char> consumed(ne, 0);

    for (int e = 0; e < ne; ++e) {
        const Elem& row = cl[e];
        if (is_tri(row)) continue;
        const int diags[2][2] = {{row[0], row[2]}, {row[1], row[3]}};
        for (const auto& d : diags) {
            const int v1 = d[0], v2 = d[1];
            if (bdy[v1] || bdy[v2]) continue;
            const std::vector<int>& e1 = mesh.get_vertex_elements(v1);
            const std::vector<int>& e2 = mesh.get_vertex_elements(v2);
            if (e1.size() != 3 || e2.size() != 3) continue;
            std::vector<int> nb;
            for (int x : e1) if (x != e) nb.push_back(x);
            for (int x : e2) if (x != e) nb.push_back(x);
            std::sort(nb.begin(), nb.end());
            nb.erase(std::unique(nb.begin(), nb.end()), nb.end());
            bool any_tri = false;
            for (int n : nb) any_tri = any_tri || is_tri(cl[n]);
            if (any_tri) continue;
            bool taken = consumed[e] != 0;
            for (int n : nb) taken = taken || consumed[n];
            if (taken) continue;
            Merge m{e, v1, v2, {}};
            for (int x : e2) if (x != e) m.side2.push_back(x);
            eligible.push_back(std::move(m));
            consumed[e] = 1;
            for (int n : nb) consumed[n] = 1;
            break;  // one diagonal per quad
        }
    }
    if (eligible.empty()) return mesh;
    std::vector<Elem> rows = cl;
    std::vector<char> del(ne, 0);
    for (const Merge& m : eligible) {
        for (int n : m.side2)
            for (int& x : rows[n])
                if (x == m.drop) x = m.keep;
        del[m.elem] = 1;
    }
    std::vector<Elem> keep;
    for (int e = 0; e < ne; ++e)
        if (!del[e]) keep.push_back(rows[e]);
    return remove_unused(rebuild(mesh, mesh.points, std::move(keep)), post_detail::adj_only());
}

}  // namespace quadmesh
