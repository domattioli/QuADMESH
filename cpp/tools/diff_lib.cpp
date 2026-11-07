#include "diff_lib.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>

#include "quadmesh/error.hpp"

namespace quadmesh::difftool {

namespace fs = std::filesystem;

// ---------------------------------------------------------------- canonical

Row canonical_row(Row row) {
    while (!row.empty() && row.back() == -1) row.pop_back();
    Row out;
    for (int v : row) {
        if (out.empty() || out.back() != v) out.push_back(v);
    }
    while (out.size() > 1 && out.back() == out.front()) out.pop_back();
    if (out.empty()) return out;
    auto mn = std::min_element(out.begin(), out.end());
    std::rotate(out.begin(), mn, out.end());
    return out;
}

std::vector<Row> canonical_rows(std::vector<Row> rows) {
    for (auto& r : rows) r = canonical_row(std::move(r));
    std::sort(rows.begin(), rows.end());
    return rows;
}

// ------------------------------------------------------------------ ties

std::vector<TieRecord> ties_from_json(const json::Value& dump) {
    std::vector<TieRecord> out;
    if (!dump.has("tie_log")) return out;
    const json::Value& log = dump["tie_log"];
    for (std::size_t i = 0; i < log.size(); ++i) {
        const json::Value& t = log[i];
        TieRecord r;
        r.seq = t["seq"].as_int();
        r.spec = t["spec"].as_string();
        r.py_site = t["py_site"].as_string();
        r.layer = static_cast<int>(t["layer"].as_int());
        r.ids = t["ids"].as_int_vector();
        r.chosen = static_cast<int>(t["chosen"].as_int());
        out.push_back(std::move(r));
    }
    return out;
}

void attribute(Difference& d, const std::vector<TieRecord>& ties, long long max_seq) {
    const TieRecord* best = nullptr;
    for (const auto& t : ties) {
        if (t.seq > max_seq) continue;
        if (d.layer >= 0 && t.layer >= 0 && d.layer != t.layer) continue;
        bool hit = d.ids.count(t.chosen) > 0;
        for (int id : t.ids) hit = hit || d.ids.count(id) > 0;
        if (!hit) continue;
        if (!best || t.seq < best->seq) best = &t;
    }
    if (best) {
        d.explained = true;
        d.attribution = best->spec + " " + best->py_site + " seq " + std::to_string(best->seq);
    } else {
        d.explained = false;
        d.attribution = "unexplained";
    }
}

// ------------------------------------------------------------- pass rule

bool within_count_bound(long long cpp, long long oracle) {
    long long delta = cpp > oracle ? cpp - oracle : oracle - cpp;
    return 200 * delta <= oracle;
}

bool within_rel(double cpp, double oracle, double rel) {
    return std::fabs(cpp - oracle) <= rel * std::fabs(oracle) + 1e-12;
}

long long StageResult::unexplained() const {
    long long n = 0;
    for (const auto& d : diffs) n += d.explained ? 0 : 1;
    return n;
}

static void add_check(StageResult& r, const std::string& name, bool ok, const std::string& detail) {
    r.checks.push_back({name, ok, detail});
}

static std::string num(double v) {
    std::ostringstream s;
    s.precision(17);
    s << v;
    return s.str();
}

void apply_pass_rule(const json::Value& oracle, const json::Value& cpp, const std::string& stage,
                     const Options& opt, StageResult& r) {
    if (stage == "match") {
        long long n = cpp["n_interior_residual_tris"].as_int();
        add_check(r, "1 match: zero interior residual triangles", n == 0,
                  "cpp=" + std::to_string(n));
    }
    if (stage == "core") {
        long long res = cpp["n_interior_residual_tris"].as_int();
        long long geo = cpp["n_interior_geometric_tris"].as_int();
        add_check(r, "2 core: zero interior residual and geometric triangles",
                  res == 0 && geo == 0,
                  "residual=" + std::to_string(res) + " geometric=" + std::to_string(geo));
    }
    for (const char* key : {"n_elems", "n_verts"}) {
        long long c = cpp[key].as_int(), o = oracle[key].as_int();
        long long delta = c > o ? c - o : o - c;
        std::ostringstream d;
        d << "cpp=" << c << " oracle=" << o << " delta=" << delta;
        if (o > 0) d << " (" << 100.0 * static_cast<double>(delta) / static_cast<double>(o) << "%)";
        add_check(r, std::string("3 count ") + key + " within 0.5%", within_count_bound(c, o), d.str());
    }
    const json::Value& qc = cpp["quality"];
    const json::Value& qo = oracle["quality"];
    for (const char* key : {"n_bad", "n_concave"}) {
        long long c = qc[key].as_int(), o = qo[key].as_int();
        add_check(r, std::string("4 quality ") + key + " exact", c == o,
                  "cpp=" + std::to_string(c) + " oracle=" + std::to_string(o));
    }
    for (const char* key : {"mean", "min", "max", "std"}) {
        double c = qc[key].as_double(), o = qo[key].as_double();
        add_check(r, std::string("4 quality ") + key + " within 1e-6 rel",
                  within_rel(c, o, opt.quality_rel), "cpp=" + num(c) + " oracle=" + num(o));
    }
    bool all = true;
    for (const auto& c : r.checks) all = all && c.ok;
    r.state = all ? StageResult::State::Pass : StageResult::State::Fail;
}

// ------------------------------------------------------------------ tables

namespace {

bool is_leaf_array(const json::Value& v) {
    if (v.type != json::Value::Type::Array) return false;
    for (const auto& e : v.arr) {
        if (e.type != json::Value::Type::Number) return false;
    }
    return true;
}

void collect_ids(const json::Value& v, std::set<int>& ids) {
    if (v.type == json::Value::Type::Number) {
        if (v.num >= 0 && v.num < 1e9 && v.num == std::floor(v.num)) ids.insert(static_cast<int>(v.num));
    } else if (v.type == json::Value::Type::Array) {
        for (const auto& e : v.arr) collect_ids(e, ids);
    }
}

std::string brief(const json::Value& v) {
    if (v.type == json::Value::Type::Number) return num(v.num);
    if (v.type == json::Value::Type::Array) {
        std::string s = "[";
        for (std::size_t i = 0; i < v.arr.size() && i < 6; ++i) {
            if (i) s += ",";
            s += brief(v.arr[i]);
        }
        if (v.arr.size() > 6) s += ",...";
        return s + "]";
    }
    return "?";
}

struct Ctx {
    const Options& opt;
    const std::vector<TieRecord>& ties;
    StageResult& r;
    bool elem2edge = false;
};

void add_diff(Ctx& c, const std::string& path, const std::string& detail, const json::Value* a,
              const json::Value* b, int layer) {
    Difference d;
    d.where = path;
    d.detail = detail;
    d.layer = layer;
    if (a) collect_ids(*a, d.ids);
    if (b) collect_ids(*b, d.ids);
    attribute(d, c.ties);
    c.r.diffs.push_back(std::move(d));
}

// `keys` limits the object keys compared at the current level (empty = all).
// `index_is_layer` marks arrays whose index is a layer id.
void diff_value(Ctx& c, const std::string& path, const json::Value& o, const json::Value& p, int layer,
                const std::vector<std::string>& keys, bool index_is_layer) {
    using T = json::Value::Type;
    if (o.type == T::Array && p.type == T::Array) {
        if (is_leaf_array(o) && is_leaf_array(p)) {
            json::Value pp = p;
            if (c.elem2edge && pp.arr.size() == 4 && pp.arr[3].num == -1 && o.arr.size() == 3) pp.arr.pop_back();
            bool same = o.arr.size() == pp.arr.size();
            for (std::size_t i = 0; same && i < o.arr.size(); ++i) {
                double x = o.arr[i].num, y = pp.arr[i].num;
                same = c.opt.exact ? x == y : within_rel(y, x, c.opt.table_rel);
            }
            if (!same) add_diff(c, path, "oracle " + brief(o) + " cpp " + brief(pp), &o, &pp, layer);
            return;
        }
        std::size_t n = std::min(o.arr.size(), p.arr.size());
        for (std::size_t i = 0; i < n; ++i) {
            int li = layer;
            if (index_is_layer) {
                li = static_cast<int>(i);
                if (o.arr[i].type == T::Object && o.arr[i].has("layer")) li = static_cast<int>(o.arr[i]["layer"].as_int());
            }
            diff_value(c, path + "[" + std::to_string(i) + "]", o.arr[i], p.arr[i], li, keys, false);
        }
        for (std::size_t i = n; i < std::max(o.arr.size(), p.arr.size()); ++i) {
            const bool in_o = i < o.arr.size();
            add_diff(c, path + "[" + std::to_string(i) + "]", in_o ? "only in oracle" : "only in cpp",
                     in_o ? &o.arr[i] : nullptr, in_o ? nullptr : &p.arr[i], layer);
        }
        return;
    }
    if (o.type == T::Object && p.type == T::Object) {
        for (const auto& kv : o.obj) {
            if (!keys.empty() && std::find(keys.begin(), keys.end(), kv.first) == keys.end()) continue;
            auto it = p.obj.find(kv.first);
            if (it == p.obj.end()) {
                add_diff(c, path + "." + kv.first, "missing in cpp", &kv.second, nullptr, layer);
                continue;
            }
            bool e2e = c.elem2edge;
            if (kv.first == "elem2edge") c.elem2edge = true;
            diff_value(c, path + "." + kv.first, kv.second, it->second, layer, {}, false);
            c.elem2edge = e2e;
        }
        return;
    }
    if (o.type == T::Number && p.type == T::Number) {
        bool same = c.opt.exact ? o.num == p.num : within_rel(p.num, o.num, c.opt.table_rel);
        if (!same) add_diff(c, path, "oracle " + num(o.num) + " cpp " + num(p.num), &o, &p, layer);
        return;
    }
    add_diff(c, path, "type mismatch", &o, &p, layer);
}

}  // namespace

void diff_tables(const json::Value& oracle, const json::Value& cpp, const Options& opt,
                 const std::vector<TieRecord>& ties, StageResult& r) {
    struct Spec {
        const char* key;
        std::vector<std::string> sub;
        bool index_is_layer;
    };
    const std::vector<Spec> specs = {
        {"adjacency", {"edge2vert", "edge2elem", "elem2edge", "vert2elem"}, false},
        {"layers", {"IE", "OE", "OV", "IV"}, true},
        {"layer_priority", {}, false},
        {"per_layer", {"pairs", "removed_edges", "flagged_pairs", "leftover"}, true},
        {"inserted_points", {}, false},
    };
    Ctx c{opt, ties, r, false};
    for (const auto& s : specs) {
        if (!oracle.has(s.key)) continue;
        if (!cpp.has(s.key)) {
            r.skipped_tables.push_back(s.key);
            continue;
        }
        diff_value(c, s.key, oracle[s.key], cpp[s.key], -1, s.sub, s.index_is_layer);
    }
}

// ----------------------------------------------------------------- .14 text

Fort14Data parse_fort14_text(const std::string& text) {
    std::istringstream in(text);
    std::string line;
    std::getline(in, line);  // name
    long long ne = 0, np = 0;
    in >> ne >> np;
    if (!in) throw ParseError("bad .14 header");
    Fort14Data d;
    for (long long i = 0; i < np; ++i) {
        long long id;
        double x, y, z;
        in >> id >> x >> y >> z;
        if (!in) throw ParseError("bad .14 node line");
        d.nodes.push_back({x, y, z});
    }
    for (long long i = 0; i < ne; ++i) {
        long long id;
        int n;
        in >> id >> n;
        if (!in || n < 3 || n > 4) throw ParseError("bad .14 element line");
        Row row(static_cast<std::size_t>(n));
        for (auto& v : row) {
            in >> v;
            --v;
        }
        if (!in) throw ParseError("bad .14 element line");
        d.elems.push_back(std::move(row));
    }
    return d;
}

void diff_connectivity(const std::vector<Row>& oracle, const std::vector<Row>& cpp,
                       const std::vector<TieRecord>& ties, StageResult& r) {
    std::vector<Row> a = canonical_rows(oracle), b = canonical_rows(cpp);
    std::vector<Row> only_a, only_b;
    std::set_difference(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(only_a));
    std::set_difference(b.begin(), b.end(), a.begin(), a.end(), std::back_inserter(only_b));
    r.conn_oracle_only = static_cast<long long>(only_a.size());
    r.conn_cpp_only = static_cast<long long>(only_b.size());
    auto push = [&](const std::vector<Row>& rows, const char* side) {
        for (const auto& row : rows) {
            Difference d;
            d.where = "connectivity";
            d.detail = std::string("only in ") + side + " [";
            for (std::size_t i = 0; i < row.size(); ++i) d.detail += (i ? "," : "") + std::to_string(row[i]);
            d.detail += "]";
            d.ids.insert(row.begin(), row.end());
            attribute(d, ties);
            r.diffs.push_back(std::move(d));
        }
    };
    push(only_a, "oracle");
    push(only_b, "cpp");
}

double max_rel_coord_diff(const Fort14Data& a, const Fort14Data& b) {
    if (a.nodes.size() != b.nodes.size()) return 0.0;
    double m = 0.0;
    for (std::size_t i = 0; i < a.nodes.size(); ++i) {
        for (int k = 0; k < 3; ++k) {
            double x = a.nodes[i][k], y = b.nodes[i][k];
            m = std::max(m, std::fabs(x - y) / std::max(std::fabs(x), 1.0));
        }
    }
    return m;
}

bool timing_passes(double python_time_s, double cpp_time_s) { return cpp_time_s <= python_time_s; }

// ------------------------------------------------------------------ driver

static bool read_text(const fs::path& p, std::string& out) {
    std::ifstream f(p, std::ios::binary);
    if (!f) return false;
    std::ostringstream s;
    s << f.rdbuf();
    out = s.str();
    return true;
}

StageResult compare_stage(const std::string& oracle_dir, const std::string& cpp_dir, const std::string& mesh,
                          const std::string& stage, const Options& opt) {
    StageResult r;
    r.mesh = mesh;
    r.stage = stage;
    const std::string base = mesh + "." + stage;
    fs::path oj = fs::path(oracle_dir) / (base + ".json"), cj = fs::path(cpp_dir) / (base + ".json");
    if (!fs::exists(oj)) {
        r.state = StageResult::State::Skipped;
        r.note = "oracle dump missing: " + oj.string();
        return r;
    }
    if (!fs::exists(cj)) {
        r.state = StageResult::State::Fail;
        r.note = "C++ dump missing: " + cj.string();
        return r;
    }
    try {
        json::Value o = json::parse_file(oj), c = json::parse_file(cj);
        apply_pass_rule(o, c, stage, opt, r);
        std::vector<TieRecord> ties = ties_from_json(c);
        diff_tables(o, c, opt, ties, r);
        std::string ob, cb;
        fs::path o14 = fs::path(oracle_dir) / (base + ".14"), c14 = fs::path(cpp_dir) / (base + ".14");
        if (read_text(o14, ob) && read_text(c14, cb)) {
            r.bytes_equal = ob == cb;
            Fort14Data od = parse_fort14_text(ob), cd = parse_fort14_text(cb);
            diff_connectivity(od.elems, cd.elems, ties, r);
            r.max_rel_coord_diff = max_rel_coord_diff(od, cd);
        } else {
            r.note += "(.14 pair missing: byte and connectivity reports skipped) ";
        }
    } catch (const std::exception& e) {
        r.state = StageResult::State::Fail;
        r.note += std::string("error: ") + e.what();
    }
    return r;
}

std::string format_result(const StageResult& r, int max_diffs_shown) {
    std::ostringstream s;
    const char* st = r.state == StageResult::State::Pass ? "PASS"
                     : r.state == StageResult::State::Fail ? "FAIL" : "SKIPPED";
    s << r.mesh << " " << r.stage << ": " << st << "\n";
    if (!r.note.empty()) s << "  note: " << r.note << "\n";
    for (const auto& c : r.checks) {
        s << "  [" << (c.ok ? "ok" : "FAIL") << "] " << c.name << " (" << c.detail << ")\n";
    }
    if (r.state == StageResult::State::Skipped) return s.str();
    s << "  bytes equal: " << (r.bytes_equal ? "yes" : "no") << " (report only)\n";
    s << "  connectivity diff: oracle-only " << r.conn_oracle_only << ", cpp-only " << r.conn_cpp_only
      << " (report only)\n";
    s << "  max scaled coordinate diff: " << r.max_rel_coord_diff << " (report only)\n";
    for (const auto& t : r.skipped_tables) s << "  table not in C++ dump, skipped: " << t << "\n";
    s << "  differences: " << r.diffs.size() << ", unexplained: " << r.unexplained() << "\n";
    int shown = 0;
    for (const auto& d : r.diffs) {
        if (shown++ >= max_diffs_shown) {
            s << "    ... " << r.diffs.size() - static_cast<std::size_t>(max_diffs_shown) << " more\n";
            break;
        }
        s << "    " << d.where << ": " << d.detail << " -> " << d.attribution << "\n";
    }
    return s.str();
}

}  // namespace quadmesh::difftool
