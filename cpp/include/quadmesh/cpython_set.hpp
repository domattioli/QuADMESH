#pragma once
// Iteration order of a CPython (3.14) set of non-negative ints, so the port
// can reproduce a Python tie broken by set order exactly (FR-020).
//
// Models setobject.c: hash(i) == i, table starts at 8 slots, probe =
// LINEAR_PROBES (9) adjacent slots while they fit in the table, then
// perturb >>= 5; i = (i*5 + 1 + perturb) & mask. Resize when fill*5 >=
// mask*3 to the smallest power of two > used*4 (used*2 above 50000),
// reinserting in old table order. set.copy() (set_merge into an empty set)
// copies the layout when the table sizes match, else reinserts in order.
// No deletions are modelled (CHILmesh Vert2Elem sets are never edited).
// Checked against real Python by tests/test_cpython_set.cpp.
#include <cstddef>
#include <cstdint>
#include <vector>

namespace quadmesh {

namespace cpython_detail {
struct Table {
    std::size_t mask = 7, fill = 0;
    std::vector<long long> slot = std::vector<long long>(8, -1);

    static std::size_t find_free(const std::vector<long long>& t, std::size_t mask, long long key) {
        std::size_t perturb = static_cast<std::size_t>(key);
        std::size_t i = perturb & mask;
        for (;;) {
            const std::size_t probes = (i + 9 <= mask) ? 9 : 0;
            for (std::size_t j = 0; j <= probes; ++j) {
                if (t[i + j] == -1 || t[i + j] == key) return i + j;
            }
            perturb >>= 5;
            i = (i * 5 + 1 + perturb) & mask;
        }
    }
    void resize(std::size_t minused) {
        std::size_t n = 8;
        while (n <= minused) n <<= 1;
        std::vector<long long> nt(n, -1);
        for (long long k : slot)
            if (k != -1) nt[find_free(nt, n - 1, k)] = k;
        slot.swap(nt);
        mask = n - 1;
    }
    void add(long long key) {
        const std::size_t i = find_free(slot, mask, key);
        if (slot[i] == key) return;
        slot[i] = key;
        ++fill;
        if (fill * 5 >= mask * 3) resize(fill > 50000 ? fill * 2 : fill * 4);
    }
};
}  // namespace cpython_detail

// list(set(insertion_order).copy()) for non-negative ints.
inline std::vector<int> cpython_set_order(const std::vector<int>& insertion_order) {
    cpython_detail::Table src;
    for (int k : insertion_order) src.add(k);
    std::vector<long long> order;
    if (src.fill > 0) {
        cpython_detail::Table dst;
        if (src.fill * 5 >= dst.mask * 3) dst.resize(src.fill * 2);
        if (dst.mask == src.mask) {
            dst.slot = src.slot;
        } else {
            for (long long k : src.slot)
                if (k != -1) dst.slot[cpython_detail::Table::find_free(dst.slot, dst.mask, k)] = k;
        }
        for (long long k : dst.slot)
            if (k != -1) order.push_back(k);
    }
    return std::vector<int>(order.begin(), order.end());
}

}  // namespace quadmesh
