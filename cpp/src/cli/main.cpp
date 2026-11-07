// quadmesh command (contracts/cli.md). All logic is in src/cli/cli.cpp.
#include <iostream>
#include <string>
#include <vector>

#include "quadmesh/cli.hpp"

int main(int argc, char** argv) {
    std::vector<std::string> args(argv + 1, argv + argc);
    return quadmesh::run_cli(args, std::cout, std::cerr);
}
