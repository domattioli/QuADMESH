#include "quadmesh/cli.hpp"

#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <sstream>

#include "quadmesh/error.hpp"
#include "quadmesh/fort14.hpp"
#include "quadmesh/quality.hpp"

#if __has_include("quadmesh/tri2quad.hpp") && __has_include("quadmesh/post_process.hpp")
#include "quadmesh/post_process.hpp"
#include "quadmesh/tri2quad.hpp"
#define QUADMESH_CLI_CONVERT 1
#endif

namespace quadmesh {

namespace {
// Distinct type so argument errors map to exit code 1.
class ArgError : public Error {
public:
    explicit ArgError(const std::string& m) : Error(m) {}
};

int to_int(const std::string& flag, const std::string& v) {
    char* end = nullptr;
    errno = 0;
    long x = std::strtol(v.c_str(), &end, 10);
    if (v.empty() || *end != '\0' || errno != 0 || x < 0 || x > 1000000)
        throw ArgError("invalid value for " + flag + ": '" + v + "'");
    return static_cast<int>(x);
}

std::string fixed(double v, int prec) {
    std::ostringstream s;
    s.setf(std::ios::fixed);
    s.precision(prec);
    s << v;
    return s.str();
}
}  // namespace

int exit_code_for(const std::exception& e) {
    if (dynamic_cast<const ArgError*>(&e)) return kBadArgs;
    if (dynamic_cast<const InputError*>(&e)) return kInputMissing;
    if (dynamic_cast<const ParseError*>(&e)) return kMalformed;
    if (dynamic_cast<const WriteError*>(&e)) return kWriteFailure;
    return kConversion;
}

std::string error_line(const std::exception& e) {
    std::string m = e.what();
    for (char& c : m) {
        if (c == '\n' || c == '\r') c = ' ';
    }
    return "quadmesh: error: " + m;
}

CliOptions parse_cli_args(const std::vector<std::string>& args, bool& help) {
    CliOptions o;
    help = false;
    bool have_output = false;
    for (std::size_t i = 0; i < args.size(); ++i) {
        const std::string& a = args[i];
        auto next = [&]() -> const std::string& {
            if (i + 1 >= args.size()) throw ArgError("missing value for " + a);
            return args[++i];
        };
        if (a == "-h" || a == "--help") help = true;
        else if (a == "-o" || a == "--output") { o.output = next(); have_output = true; }
        else if (a == "--polygon") o.polygon = next();
        else if (a == "--no-post-process") o.no_post_process = true;
        else if (a == "--no-remove-edges") o.no_remove_edges = true;
        else if (a == "--n-smooth-iter") o.n_smooth_iter = to_int(a, next());
        else if (a == "--max-outer-iter") o.max_outer_iter = to_int(a, next());
        else if (a == "--max-inner-iter") o.max_inner_iter = to_int(a, next());
        else if (a == "--refuse-boundary-merge") o.refuse_boundary_merge = true;
        else if (a == "--preserve-boundary") o.preserve_boundary = true;
        else if (a.size() > 1 && a[0] == '-') throw ArgError("unknown option " + a);
        else if (o.input.empty()) o.input = a;
        else throw ArgError("unexpected extra argument " + a);
    }
    if (help) return o;
    if (o.input.empty()) throw ArgError("missing input file");
    if (!have_output || o.output.empty()) throw ArgError("missing required -o OUTPUT");
    return o;
}

Mesh default_convert(const Mesh& input, const CliOptions& opts) {
#ifdef QUADMESH_CLI_CONVERT
    Tri2QuadOptions t;
    t.can_remove_edges = !opts.no_remove_edges;
    t.refuse_boundary_merge = opts.refuse_boundary_merge;
    Mesh q = tri2quad(input, t);
    if (opts.no_post_process) return q;
    PostProcessOptions p;
    p.can_remove_edges = !opts.no_remove_edges;
    p.n_smooth_iter = opts.n_smooth_iter;
    p.max_outer_iter = opts.max_outer_iter;
    p.max_inner_iter = opts.max_inner_iter;
    p.preserve_boundary = opts.preserve_boundary;
    return post_process(q, p);
#else
    (void)input;
    (void)opts;
    throw Error("conversion is not built into this binary");
#endif
}

static std::string quality_line(const QualityStats& s) {
    return "quality: mean=" + fixed(s.mean, 3) + "  min=" + fixed(s.min, 3) + "  std=" + fixed(s.std, 3) +
           "  bad(<0.3)=" + std::to_string(s.n_bad) + "/" + std::to_string(s.n_elems) + " (" +
           fixed(s.pct_bad, 1) + "%)  concave=" + std::to_string(s.n_concave);
}

int run_cli(const std::vector<std::string>& args, std::ostream& out, std::ostream& err,
            const ConvertFn& convert) {
    try {
        bool help = false;
        CliOptions o = parse_cli_args(args, help);
        if (help) {
            out << "usage: quadmesh INPUT.14 -o OUTPUT.14 [--polygon FILE] [--no-post-process] [--no-remove-edges]\n"
                   "                [--n-smooth-iter N] [--max-outer-iter N] [--max-inner-iter N]\n"
                   "                [--refuse-boundary-merge] [--preserve-boundary]\n";
            return kOk;
        }
        if (!o.polygon.empty()) throw ArgError("--polygon is not supported by the C++ port");
        Mesh in = read_fort14(o.input);
        std::string label = std::filesystem::path(o.input).filename().string();
        out << "loaded: " << label << " \xe2\x80\x94 " << in.n_elems() << " elems, " << in.n_verts()
            << " verts, " << in.n_layers() << " layers\n";
        Mesh q = convert(in, o);
        out << "output: " << q.n_elems() << " elems, " << q.n_verts() << " verts\n";
        out << quality_line(compute_quality_stats(q)) << "\n";
        write_fort14(q, o.output);
        out << "written: " << o.output << "\n";
        return kOk;
    } catch (const std::exception& e) {
        err << error_line(e) << "\n";
        return exit_code_for(e);
    }
}

}  // namespace quadmesh
