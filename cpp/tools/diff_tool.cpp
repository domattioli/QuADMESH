// SPEC-10b diff tool: Python oracle dumps against C++ dumps.
//   diff_tool --cpp DIR [--oracle DIR] [--mesh NAME]... [--stage S]...
//             [--mode tolerance|exact] [--require-empty-diff]
//             [--python-time-s X --cpp-time-s Y]
// Exit 0: every compared stage passes. 1: a failure. 2: usage error.
// Timing (FR-027) is only read from the two medians on the command line,
// never from a dump's time_s.
#include <algorithm>
#include <filesystem>
#include <iostream>
#include <set>
#include <string>
#include <vector>

#include "diff_lib.hpp"

namespace fs = std::filesystem;
using namespace quadmesh::difftool;

static int usage(const std::string& msg) {
    std::cerr << "diff_tool: " << msg << "\n"
              << "usage: diff_tool --cpp DIR [--oracle DIR] [--mesh NAME]... [--stage match|core|full]...\n"
              << "                 [--mode tolerance|exact] [--require-empty-diff]\n"
              << "                 [--python-time-s X --cpp-time-s Y]\n";
    return 2;
}

int main(int argc, char** argv) {
    std::string cpp_dir, oracle_dir = ".scratch/cpp-port/ground_truth/expected";
    std::vector<std::string> meshes, stages;
    Options opt;
    bool require_empty = false;
    double py_t = -1, cpp_t = -1;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        auto val = [&](std::string& out) {
            if (i + 1 >= argc) return false;
            out = argv[++i];
            return true;
        };
        std::string v;
        if (a == "--cpp") { if (!val(cpp_dir)) return usage("--cpp needs a value"); }
        else if (a == "--oracle") { if (!val(oracle_dir)) return usage("--oracle needs a value"); }
        else if (a == "--mesh") { if (!val(v)) return usage("--mesh needs a value"); meshes.push_back(v); }
        else if (a == "--stage") {
            if (!val(v)) return usage("--stage needs a value");
            if (v != "match" && v != "core" && v != "full") return usage("bad stage " + v);
            stages.push_back(v);
        } else if (a == "--mode") {
            if (!val(v)) return usage("--mode needs a value");
            if (v == "exact") opt.exact = true;
            else if (v != "tolerance") return usage("bad mode " + v);
        } else if (a == "--require-empty-diff") require_empty = true;
        else if (a == "--python-time-s" || a == "--cpp-time-s") {
            if (!val(v)) return usage(a + " needs a value");
            try { (a == "--cpp-time-s" ? cpp_t : py_t) = std::stod(v); }
            catch (...) { return usage("bad number for " + a); }
        } else return usage("unknown argument " + a);
    }
    if (cpp_dir.empty()) return usage("--cpp is required");
    if ((py_t >= 0) != (cpp_t >= 0)) return usage("give both --python-time-s and --cpp-time-s");
    if (stages.empty()) stages = {"match", "core", "full"};
    if (meshes.empty()) {
        std::set<std::string> found;
        if (fs::exists(oracle_dir)) {
            for (const auto& e : fs::directory_iterator(oracle_dir)) {
                std::string n = e.path().filename().string();
                for (const auto& s : stages) {
                    std::string suf = "." + s + ".json";
                    if (n.size() > suf.size() && n.compare(n.size() - suf.size(), suf.size(), suf) == 0)
                        found.insert(n.substr(0, n.size() - suf.size()));
                }
            }
        }
        meshes.assign(found.begin(), found.end());
    }
    if (meshes.empty()) return usage("no oracle dumps found in " + oracle_dir);
    if (py_t >= 0 && meshes.size() != 1)
        return usage("timing medians are per conversion: select one mesh with --mesh");

    bool failed = false;
    int compared = 0;
    for (const auto& m : meshes) {
        for (const auto& s : stages) {
            StageResult r = compare_stage(oracle_dir, cpp_dir, m, s, opt);
            std::cout << format_result(r);
            if (r.state == StageResult::State::Skipped) continue;
            ++compared;
            if (r.state == StageResult::State::Fail) failed = true;
            if (require_empty && r.unexplained() > 0) {
                std::cout << "  FAIL: " << r.unexplained() << " unexplained difference(s) (--require-empty-diff)\n";
                failed = true;
            }
        }
    }
    if (py_t >= 0) {
        bool ok = timing_passes(py_t, cpp_t);
        std::cout << meshes[0] << " timing: python " << py_t << " s, cpp " << cpp_t << " s: "
                  << (ok ? "PASS" : "FAIL") << " (FR-027)\n";
        if (!ok) failed = true;
    }
    std::cout << "compared " << compared << " stage(s): " << (failed ? "FAIL" : "PASS") << "\n";
    return failed ? 1 : 0;
}
