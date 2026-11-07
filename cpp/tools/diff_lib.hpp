#pragma once
// SPEC-10b diff tool core: canonical ordering, tie attribution, pass rule.
// Kept free of file and command-line code so tests/test_diff_tool.cpp can
// exercise it directly.
#include <array>
#include <climits>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

#include "quadmesh/json.hpp"

namespace quadmesh::difftool {

using Row = std::vector<int>;

// FR-022. Drops padding (a repeated trailing vertex, as in [a,b,c,c] or
// [a,b,c,a], and a trailing -1), then rotates so the smallest vertex id comes
// first. Direction is kept.
Row canonical_row(Row row);
// canonical_row on every row, then lexicographic sort.
std::vector<Row> canonical_rows(std::vector<Row> rows);

// One logged tie (C++ side only, contracts/dump-format.md).
struct TieRecord {
    long long seq = 0;
    std::string spec;
    std::string py_site;
    int layer = -1;
    std::vector<int> ids;
    int chosen = -1;
};
std::vector<TieRecord> ties_from_json(const json::Value& dump);

// A difference after canonical ordering.
struct Difference {
    std::string where;       // table or "connectivity"
    std::string detail;      // short text
    std::set<int> ids;       // vertex or element ids involved
    int layer = -1;          // sweep layer when known, else -1
    bool explained = false;
    std::string attribution;  // "SPEC-07 file:line seq N" or "unexplained"
};

// FR-023. A difference traces to a tie record when the record has seq <=
// max_seq, and its candidate ids or chosen id appear among the difference's
// ids (and its layer equals the difference's when both are known). The tie
// with the lowest seq among the matches is reported. Fills explained and
// attribution.
void attribute(Difference& d, const std::vector<TieRecord>& ties, long long max_seq = LLONG_MAX);

// Counts. FR-020 item 3: |cpp - oracle| <= 0.005 * oracle, evaluated in
// integers (200 * |cpp - oracle| <= oracle) so the bound edge is exact.
bool within_count_bound(long long cpp, long long oracle);
// Relative tolerance with an absolute floor of 1e-12: |c-o| <= rel*|o| + 1e-12.
bool within_rel(double cpp, double oracle, double rel);

struct Check {
    std::string name;
    bool ok = true;
    std::string detail;
};

struct StageResult {
    std::string mesh, stage;
    enum class State { Pass, Fail, Skipped } state = State::Skipped;
    std::string note;
    std::vector<Check> checks;           // pass rule items 1 to 4
    bool bytes_equal = false;            // report only
    long long conn_oracle_only = 0, conn_cpp_only = 0;  // report only
    std::vector<Difference> diffs;       // connectivity and table differences
    std::vector<std::string> skipped_tables;  // oracle tables absent in C++ dump
    double max_rel_coord_diff = 0.0;     // FR-024, report only
    long long unexplained() const;
};

struct Options {
    bool exact = false;   // exact: tables and coordinates compared bit for bit
    double table_rel = 1e-9;  // tolerance mode, FR-024
    double quality_rel = 1e-6;  // FR-020 item 4
};

// Pass rule items 1 to 4 over two parsed dumps. Appends to r.checks and sets
// r.state (Pass only when every check is ok).
void apply_pass_rule(const json::Value& oracle, const json::Value& cpp,
                     const std::string& stage, const Options& opt, StageResult& r);

// Compares the shared table keys (adjacency, layers, layer_priority,
// per_layer, inserted_points). Oracle keys absent from the C++ dump go to
// r.skipped_tables. Differences are appended to r.diffs and attributed.
void diff_tables(const json::Value& oracle, const json::Value& cpp, const Options& opt,
                 const std::vector<TieRecord>& ties, StageResult& r);

// Element rows of a .14 text (0-based ids, padding kept as written) and node
// coordinates.
struct Fort14Data {
    std::vector<Row> elems;
    std::vector<std::array<double, 3>> nodes;
};
Fort14Data parse_fort14_text(const std::string& text);

// Canonical connectivity diff between two element lists. Rows only in one
// side become Differences (ids = the row's vertices), attributed with `ties`.
void diff_connectivity(const std::vector<Row>& oracle, const std::vector<Row>& cpp,
                       const std::vector<TieRecord>& ties, StageResult& r);

// Max relative coordinate difference over equal-length node lists.
double max_rel_coord_diff(const Fort14Data& a, const Fort14Data& b);

// FR-027: pass when cpp_time_s <= python_time_s.
bool timing_passes(double python_time_s, double cpp_time_s);

// Full per-stage comparison of files: <oracle_dir>/<mesh>.<stage>.json/.14
// against <cpp_dir>/... Missing oracle dump gives Skipped; missing C++ dump
// gives Fail.
StageResult compare_stage(const std::string& oracle_dir, const std::string& cpp_dir,
                          const std::string& mesh, const std::string& stage, const Options& opt);

std::string format_result(const StageResult& r, int max_diffs_shown = 10);

}  // namespace quadmesh::difftool
