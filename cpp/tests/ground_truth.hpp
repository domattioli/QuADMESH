#pragma once
// Shared helpers for oracle-backed tests. The ground-truth directory comes
// from the QUADMESH_GT_DIR environment variable, else the compile-time
// default (repo .scratch/cpp-port/ground_truth). It holds meshes/<name>.14
// and ref/<name>.json written by ref_tables.py.
#include <cstdlib>
#include <filesystem>
#include <map>
#include <string>
#include <vector>

#include "quadmesh/fort14.hpp"
#include "quadmesh/json.hpp"

namespace gt {

inline const std::vector<std::string>& mesh_names() {
    static const std::vector<std::string> names = {"Block_O", "WNAT_Test", "Lake_Michigan_mesh",
                                                   "structuredMesh1"};
    return names;
}

inline std::filesystem::path dir() {
    if (const char* e = std::getenv("QUADMESH_GT_DIR")) return e;
#ifdef QUADMESH_GT_DIR_DEFAULT
    return QUADMESH_GT_DIR_DEFAULT;
#else
    return {};
#endif
}

inline std::filesystem::path mesh_path(const std::string& name) {
    return dir() / "meshes" / (name + ".14");
}
inline std::filesystem::path ref_path(const std::string& name) {
    return dir() / "ref" / (name + ".json");
}
inline bool available(const std::string& name) {
    return std::filesystem::exists(mesh_path(name)) && std::filesystem::exists(ref_path(name));
}

// Parsed once per process; the larger dumps take a moment to read.
inline const quadmesh::json::Value& ref(const std::string& name) {
    static std::map<std::string, quadmesh::json::Value> cache;
    auto it = cache.find(name);
    if (it == cache.end()) it = cache.emplace(name, quadmesh::json::parse_file(ref_path(name))).first;
    return it->second;
}

inline const quadmesh::Mesh& mesh(const std::string& name) {
    static std::map<std::string, quadmesh::Mesh> cache;
    auto it = cache.find(name);
    if (it == cache.end()) it = cache.emplace(name, quadmesh::read_fort14(mesh_path(name))).first;
    return it->second;
}

// Count of differing entries plus the first difference, for messages.
struct Diff {
    std::size_t n = 0;
    std::string first;
    void add(const std::string& what) {
        if (n++ == 0) first = what;
    }
};

}  // namespace gt
