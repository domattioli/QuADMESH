#include <catch_amalgamated.hpp>

#include <filesystem>
#include <fstream>
#include <sstream>

#include "quadmesh/cli.hpp"
#include "quadmesh/error.hpp"

using namespace quadmesh;
namespace fs = std::filesystem;

namespace {
struct Run {
    int code;
    std::string out, err;
};

Run run(const std::vector<std::string>& args, const ConvertFn& f = default_convert) {
    std::ostringstream o, e;
    int code = run_cli(args, o, e, f);
    return {code, o.str(), e.str()};
}

int lines(const std::string& s) {
    int n = 0;
    for (char c : s) n += c == '\n';
    return n;
}

fs::path tmp_dir() {
    fs::path d = fs::temp_directory_path() / "quadmesh_cli_test";
    fs::create_directories(d);
    return d;
}

void check_failure(const Run& r, int code, const fs::path& out) {
    REQUIRE(r.code == code);
    REQUIRE(lines(r.err) == 1);
    REQUIRE(r.err.rfind("quadmesh: error: ", 0) == 0);
    REQUIRE_FALSE(fs::exists(out));
}
}  // namespace

TEST_CASE("cli: missing -o exits 1", "[cli]") {
    auto r = run({"in.14"});
    REQUIRE(r.code == 1);
    REQUIRE(lines(r.err) == 1);
}

TEST_CASE("cli: bad arguments exit 1 with one stderr line", "[cli]") {
    for (auto args : std::vector<std::vector<std::string>>{
             {}, {"-o", "x.14"}, {"in.14", "-o"}, {"in.14", "-o", "x.14", "--method", "layered"},
             {"in.14", "-o", "x.14", "--n-smooth-iter", "abc"}, {"a.14", "b.14", "-o", "x.14"}}) {
        auto r = run(args);
        REQUIRE(r.code == 1);
        REQUIRE(lines(r.err) == 1);
        REQUIRE_FALSE(fs::exists("x.14"));
    }
}

TEST_CASE("cli: missing input file exits 2 and leaves no output", "[cli]") {
    fs::path out = tmp_dir() / "missing_out.14";
    fs::remove(out);
    auto r = run({(tmp_dir() / "does_not_exist.14").string(), "-o", out.string()});
    check_failure(r, 2, out);
    REQUIRE(r.err.find("does_not_exist.14") != std::string::npos);
}

TEST_CASE("cli: malformed .14 exits 3 and leaves no output", "[cli]") {
    fs::path in = tmp_dir() / "bad.14", out = tmp_dir() / "bad_out.14";
    fs::remove(out);
    std::ofstream(in) << "broken\nthis is not a mesh\n";
    check_failure(run({in.string(), "-o", out.string()}), 3, out);
}

TEST_CASE("cli: injected conversion error exits 4 and leaves no output", "[cli]") {
    fs::path in = tmp_dir() / "tri.14", out = tmp_dir() / "tri_out.14";
    fs::remove(out);
    std::ofstream(in) << "tri\n1 3\n1 0.0 0.0 0.0\n2 1.0 0.0 0.0\n3 0.0 1.0 0.0\n1 3 1 2 3\n"
                         "0 = Number of open boundaries\n0 = Total number of open boundary nodes\n"
                         "0 = Number of land boundaries\n0 = Total number of land boundary nodes\n";
    ConvertFn boom = [](const Mesh&, const CliOptions&) -> Mesh { throw Error("layer sweep failed"); };
    auto r = run({in.string(), "-o", out.string()}, boom);
    check_failure(r, 4, out);
    REQUIRE(r.err.find("layer sweep failed") != std::string::npos);
}

TEST_CASE("cli: unwritable output path exits 5 and leaves no output", "[cli]") {
    fs::path in = tmp_dir() / "tri2.14";
    std::ofstream(in) << "tri\n1 3\n1 0.0 0.0 0.0\n2 1.0 0.0 0.0\n3 0.0 1.0 0.0\n1 3 1 2 3\n"
                         "0 = Number of open boundaries\n0 = Total number of open boundary nodes\n"
                         "0 = Number of land boundaries\n0 = Total number of land boundary nodes\n";
    fs::path out = tmp_dir() / "no_such_dir" / "out.14";
    ConvertFn id = [](const Mesh& m, const CliOptions&) { return m; };
    check_failure(run({in.string(), "-o", out.string()}, id), 5, out);
}

TEST_CASE("cli: success writes the file, load line and report", "[cli]") {
    fs::path in = tmp_dir() / "tri3.14", out = tmp_dir() / "ok_out.14";
    fs::remove(out);
    std::ofstream(in) << "tri\n1 3\n1 0.0 0.0 0.0\n2 1.0 0.0 0.0\n3 0.0 1.0 0.0\n1 3 1 2 3\n"
                         "0 = Number of open boundaries\n0 = Total number of open boundary nodes\n"
                         "0 = Number of land boundaries\n0 = Total number of land boundary nodes\n";
    ConvertFn id = [](const Mesh& m, const CliOptions&) { return m; };
    auto r = run({in.string(), "-o", out.string()}, id);
    REQUIRE(r.code == 0);
    REQUIRE(r.err.empty());
    REQUIRE(fs::exists(out));
    REQUIRE(r.out.rfind("loaded: tri3.14", 0) == 0);
    REQUIRE(r.out.find("quality: mean=") != std::string::npos);
    REQUIRE_FALSE(fs::exists(out.string() + ".tmp"));
}

TEST_CASE("cli: error mapper table", "[cli]") {
    REQUIRE(exit_code_for(InputError("x")) == 2);
    REQUIRE(exit_code_for(ParseError("x")) == 3);
    REQUIRE(exit_code_for(Error("x")) == 4);
    REQUIRE(exit_code_for(InvalidMethod("matching")) == 4);
    REQUIRE(exit_code_for(WriteError("x")) == 5);
    REQUIRE(exit_code_for(std::runtime_error("x")) == 4);
    REQUIRE(error_line(Error("a\nb")) == "quadmesh: error: a b");
}
