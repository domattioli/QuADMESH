#pragma once
// SPEC-10b tie log (FR-011, FR-012, ADR 0001). Where Python breaks a tie by
// set or dict iteration order, the port iterates ascending id and writes one
// record here, so a diff against the oracle can attribute a difference to a
// logged tie site that happened at or before it (seq).
#include <filesystem>
#include <string>
#include <vector>

namespace quadmesh {

struct TieRecord {
    std::string spec;     // for example "SPEC-07"
    std::string py_site;  // Python file:line of the tie
    int layer = -1;       // layer being swept, -1 outside the sweep
    std::vector<int> ids; // candidates, in the order the port visits them
    int chosen = -1;      // candidate the port took (-1: order only, no pick)
    long long seq = 0;    // global visit counter
};

class TieLog {
public:
    // Appends one record; seq is the running counter.
    void record(const std::string& spec, const std::string& py_site, std::vector<int> ids,
                int chosen);
    // Advances the visit counter without writing (one call per routed tri or
    // merge site, so seq orders records against the sweep).
    void tick() { ++seq_; }
    long long seq() const { return seq_; }
    int layer = -1;  // set by the driver before each layer

    const std::vector<TieRecord>& records() const { return records_; }
    std::size_t size() const { return records_.size(); }
    void clear();
    std::string to_json() const;
    void write_json(const std::filesystem::path& path) const;

private:
    std::vector<TieRecord> records_;
    long long seq_ = 0;
};

}  // namespace quadmesh
