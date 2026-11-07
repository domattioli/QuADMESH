#pragma once
// Minimal JSON reader for oracle dumps (tests and the SPEC-10b diff tool).
// Numbers are parsed with strtod, so repr-printed doubles round-trip exactly.
#include <filesystem>
#include <map>
#include <memory>
#include <string>
#include <vector>

namespace quadmesh::json {

class Value {
public:
    enum class Type { Null, Bool, Number, String, Array, Object };
    Type type = Type::Null;
    bool b = false;
    double num = 0.0;
    std::string str;
    std::vector<Value> arr;
    std::map<std::string, Value> obj;

    bool is_null() const { return type == Type::Null; }
    // Throws quadmesh::Error on a missing key or wrong type.
    const Value& operator[](const std::string& key) const;
    const Value& operator[](std::size_t i) const;
    bool has(const std::string& key) const { return type == Type::Object && obj.count(key) > 0; }
    std::size_t size() const;
    double as_double() const;
    long long as_int() const;
    const std::string& as_string() const;
    std::vector<int> as_int_vector() const;
    std::vector<double> as_double_vector() const;
    std::vector<std::vector<int>> as_int_matrix() const;
};

Value parse(const std::string& text);
Value parse_file(const std::filesystem::path& path);

}  // namespace quadmesh::json
