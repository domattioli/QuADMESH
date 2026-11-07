#pragma once
// SPEC-12 skew quality (chilmesh.quality.element_quality(metric="skew") and
// quadmesh.quality_report.compute_quality_stats).
#include <vector>

#include "quadmesh/mesh.hpp"

namespace quadmesh {

struct QualityStats {
    double mean = 0.0, min = 0.0, max = 0.0, std = 0.0;
    int n_bad = 0;       // skew < 0.3
    double pct_bad = 0.0;
    int n_elems = 0;
    int n_concave = 0;   // quads with a reflex corner
};

// Per-element skew in [0, 1]; triangles (is_tri) scored as triangles,
// concave or degenerate elements score 0.0.
std::vector<double> element_skew(const std::vector<Point>& points, const std::vector<Elem>& elems);
int count_concave_quads(const std::vector<Point>& points, const std::vector<Elem>& elems);
QualityStats compute_quality_stats(const Mesh& mesh);

}  // namespace quadmesh
