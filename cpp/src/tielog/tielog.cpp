// SPEC-10b tie log (T024).
#include "quadmesh/tielog.hpp"

#include <fstream>
#include <sstream>

#include "quadmesh/error.hpp"

namespace quadmesh {

void TieLog::record(const std::string& spec, const std::string& py_site, std::vector<int> ids,
                    int chosen) {
    TieRecord r;
    r.spec = spec;
    r.py_site = py_site;
    r.layer = layer;
    r.ids = std::move(ids);
    r.chosen = chosen;
    r.seq = ++seq_;
    records_.push_back(std::move(r));
}

void TieLog::clear() {
    records_.clear();
    seq_ = 0;
}

std::string TieLog::to_json() const {
    std::ostringstream os;
    os << "[";
    for (std::size_t i = 0; i < records_.size(); ++i) {
        const TieRecord& r = records_[i];
        os << (i ? ",\n " : "\n ") << "{\"spec\": \"" << r.spec << "\", \"py_site\": \""
           << r.py_site << "\", \"layer\": " << r.layer << ", \"ids\": [";
        for (std::size_t k = 0; k < r.ids.size(); ++k) os << (k ? ", " : "") << r.ids[k];
        os << "], \"chosen\": " << r.chosen << ", \"seq\": " << r.seq << "}";
    }
    os << (records_.empty() ? "]" : "\n]") << "\n";
    return os.str();
}

void TieLog::write_json(const std::filesystem::path& path) const {
    std::ofstream f(path, std::ios::binary);
    if (!f) throw WriteError("cannot write tie log " + path.string());
    f << to_json();
    if (!f) throw WriteError("cannot write tie log " + path.string());
}

}  // namespace quadmesh
