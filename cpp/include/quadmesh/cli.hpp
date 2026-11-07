#pragma once
// SPEC-11 command line (contracts/cli.md). The logic lives in the library so
// tests can drive it; src/cli/main.cpp only forwards argv.
#include <exception>
#include <functional>
#include <iosfwd>
#include <string>
#include <vector>

#include "quadmesh/mesh.hpp"

namespace quadmesh {

struct CliOptions {
    std::string input, output, polygon;
    bool no_post_process = false;
    bool no_remove_edges = false;
    int n_smooth_iter = 3;
    int max_outer_iter = 5;
    int max_inner_iter = 5;
    bool refuse_boundary_merge = false;
    bool preserve_boundary = false;
};

// Exit codes (contracts/cli.md).
enum ExitCode { kOk = 0, kBadArgs = 1, kInputMissing = 2, kMalformed = 3, kConversion = 4, kWriteFailure = 5 };

// Maps an exception to an exit code: InputError 2, ParseError 3, WriteError 5,
// any other quadmesh::Error (incl. InvalidMethod) or std::exception 4.
int exit_code_for(const std::exception& e);
// "quadmesh: error: <message>" on one line (newlines in the message become spaces).
std::string error_line(const std::exception& e);

// Parses argv (without the program name). Throws quadmesh::Error on bad
// arguments; `help` is set when -h/--help was given.
CliOptions parse_cli_args(const std::vector<std::string>& args, bool& help);

// Conversion step: tri2quad then (unless --no-post-process) post_process.
using ConvertFn = std::function<Mesh(const Mesh&, const CliOptions&)>;
Mesh default_convert(const Mesh& input, const CliOptions& opts);

// Runs the command. Writes the report to `out`, at most one error line to
// `err`, and never leaves a file at the output path on failure.
int run_cli(const std::vector<std::string>& args, std::ostream& out, std::ostream& err,
            const ConvertFn& convert = default_convert);

}  // namespace quadmesh
