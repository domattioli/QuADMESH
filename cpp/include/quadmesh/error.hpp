#pragma once

#include <stdexcept>
#include <string>

namespace quadmesh {

// Base class for every error the library throws. The CLI maps these to
// exit codes (contracts/cli.md).
class Error : public std::runtime_error {
public:
    explicit Error(const std::string& what) : std::runtime_error(what) {}
};

// Thrown for a removed or unknown tri2quad method name.
class InvalidMethod : public Error {
public:
    explicit InvalidMethod(const std::string& what) : Error(what) {}
};

// Input file missing or unreadable (CLI exit code 2).
class InputError : public Error {
public:
    explicit InputError(const std::string& what) : Error(what) {}
};

// Malformed .14 content (CLI exit code 3).
class ParseError : public Error {
public:
    explicit ParseError(const std::string& what) : Error(what) {}
};

// Output write failure (CLI exit code 5).
class WriteError : public Error {
public:
    explicit WriteError(const std::string& what) : Error(what) {}
};

}  // namespace quadmesh
