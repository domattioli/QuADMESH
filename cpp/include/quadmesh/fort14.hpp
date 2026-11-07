#pragma once
// SPEC-02 ADCIRC fort.14 I/O (CHILmesh.read_from_fort14 / write_fort14).
#include <filesystem>

#include "quadmesh/mesh.hpp"

namespace quadmesh {

// Parses nodes and elements like CHILmesh.read_from_fort14 (triangles become
// [a,b,c,-1]), keeps the boundary block as raw bytes, then builds the mesh
// with `opts` (default: adjacencies and layers, as CHILmesh does).
// Throws InputError (missing/unreadable) or ParseError (malformed).
Mesh read_fort14(const std::filesystem::path& path, const MeshOptions& opts = {});

// Writes `.10f` coordinates, 3-node triangle rows and the raw boundary block
// (canonical 0/0/0/0 block when the mesh has none). Writes `<path>.tmp` and
// renames it; throws WriteError and leaves no file on failure.
void write_fort14(const Mesh& mesh, const std::filesystem::path& path);

}  // namespace quadmesh
