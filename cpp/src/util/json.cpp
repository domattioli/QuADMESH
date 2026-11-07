#include "quadmesh/json.hpp"

#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iterator>

#include "quadmesh/error.hpp"

namespace quadmesh::json {

namespace {

class Parser {
public:
    explicit Parser(const std::string& s) : s_(s) {}

    Value parse_root() {
        Value v = value();
        ws();
        if (p_ != s_.size()) fail("trailing characters");
        return v;
    }

private:
    const std::string& s_;
    std::size_t p_ = 0;

    [[noreturn]] void fail(const char* msg) const {
        throw Error(std::string("json: ") + msg + " at offset " + std::to_string(p_));
    }
    void ws() {
        while (p_ < s_.size() && (s_[p_] == ' ' || s_[p_] == '\n' || s_[p_] == '\r' || s_[p_] == '\t')) ++p_;
    }
    bool lit(const char* w) {
        std::size_t n = std::char_traits<char>::length(w);
        if (s_.compare(p_, n, w) == 0) {
            p_ += n;
            return true;
        }
        return false;
    }
    Value value() {
        ws();
        if (p_ >= s_.size()) fail("unexpected end");
        Value v;
        const char c = s_[p_];
        if (c == '{') {
            v.type = Value::Type::Object;
            ++p_;
            ws();
            if (p_ < s_.size() && s_[p_] == '}') {
                ++p_;
                return v;
            }
            while (true) {
                ws();
                if (p_ >= s_.size() || s_[p_] != '"') fail("expected key");
                std::string k = string();
                ws();
                if (p_ >= s_.size() || s_[p_] != ':') fail("expected ':'");
                ++p_;
                v.obj[k] = value();
                ws();
                if (p_ < s_.size() && s_[p_] == ',') {
                    ++p_;
                    continue;
                }
                if (p_ < s_.size() && s_[p_] == '}') {
                    ++p_;
                    return v;
                }
                fail("expected ',' or '}'");
            }
        }
        if (c == '[') {
            v.type = Value::Type::Array;
            ++p_;
            ws();
            if (p_ < s_.size() && s_[p_] == ']') {
                ++p_;
                return v;
            }
            while (true) {
                v.arr.push_back(value());
                ws();
                if (p_ < s_.size() && s_[p_] == ',') {
                    ++p_;
                    continue;
                }
                if (p_ < s_.size() && s_[p_] == ']') {
                    ++p_;
                    return v;
                }
                fail("expected ',' or ']'");
            }
        }
        if (c == '"') {
            v.type = Value::Type::String;
            v.str = string();
            return v;
        }
        if (lit("true")) {
            v.type = Value::Type::Bool;
            v.b = true;
            return v;
        }
        if (lit("false")) {
            v.type = Value::Type::Bool;
            return v;
        }
        if (lit("null")) return v;
        // Python json also writes NaN, Infinity, -Infinity.
        if (lit("NaN")) {
            v.type = Value::Type::Number;
            v.num = std::nan("");
            return v;
        }
        if (lit("Infinity")) {
            v.type = Value::Type::Number;
            v.num = HUGE_VAL;
            return v;
        }
        if (lit("-Infinity")) {
            v.type = Value::Type::Number;
            v.num = -HUGE_VAL;
            return v;
        }
        const char* start = s_.c_str() + p_;
        char* end = nullptr;
        v.num = std::strtod(start, &end);
        if (end == start) fail("bad value");
        v.type = Value::Type::Number;
        p_ += static_cast<std::size_t>(end - start);
        return v;
    }
    static void utf8(std::string& out, unsigned cp) {
        if (cp < 0x80) {
            out += static_cast<char>(cp);
        } else if (cp < 0x800) {
            out += static_cast<char>(0xC0 | (cp >> 6));
            out += static_cast<char>(0x80 | (cp & 0x3F));
        } else if (cp < 0x10000) {
            out += static_cast<char>(0xE0 | (cp >> 12));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
        } else {
            out += static_cast<char>(0xF0 | (cp >> 18));
            out += static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
            out += static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
            out += static_cast<char>(0x80 | (cp & 0x3F));
        }
    }
    unsigned hex4() {
        if (p_ + 4 > s_.size()) fail("short \\u escape");
        unsigned cp = std::stoul(s_.substr(p_, 4), nullptr, 16);
        p_ += 4;
        return cp;
    }
    std::string string() {
        ++p_;  // opening quote
        std::string out;
        while (true) {
            if (p_ >= s_.size()) fail("unterminated string");
            char c = s_[p_++];
            if (c == '"') return out;
            if (c != '\\') {
                out += c;
                continue;
            }
            if (p_ >= s_.size()) fail("bad escape");
            char e = s_[p_++];
            switch (e) {
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'n': out += '\n'; break;
                case 'r': out += '\r'; break;
                case 't': out += '\t'; break;
                case 'u': {
                    unsigned cp = hex4();
                    if (cp >= 0xD800 && cp < 0xDC00 && lit("\\u")) {
                        unsigned lo = hex4();
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                    }
                    utf8(out, cp);
                    break;
                }
                default: fail("bad escape");
            }
        }
    }
};

}  // namespace

const Value& Value::operator[](const std::string& key) const {
    if (type != Type::Object) throw Error("json: not an object (key " + key + ")");
    auto it = obj.find(key);
    if (it == obj.end()) throw Error("json: missing key " + key);
    return it->second;
}

const Value& Value::operator[](std::size_t i) const {
    if (type != Type::Array) throw Error("json: not an array");
    if (i >= arr.size()) throw Error("json: index out of range");
    return arr[i];
}

std::size_t Value::size() const {
    if (type == Type::Array) return arr.size();
    if (type == Type::Object) return obj.size();
    throw Error("json: size() of a scalar");
}

double Value::as_double() const {
    if (type != Type::Number) throw Error("json: not a number");
    return num;
}

long long Value::as_int() const {
    if (type == Type::Bool) return b ? 1 : 0;
    return static_cast<long long>(as_double());
}

const std::string& Value::as_string() const {
    if (type != Type::String) throw Error("json: not a string");
    return str;
}

std::vector<int> Value::as_int_vector() const {
    std::vector<int> out;
    out.reserve(size());
    for (const Value& v : arr) out.push_back(static_cast<int>(v.as_int()));
    return out;
}

std::vector<double> Value::as_double_vector() const {
    std::vector<double> out;
    out.reserve(size());
    for (const Value& v : arr) out.push_back(v.as_double());
    return out;
}

std::vector<std::vector<int>> Value::as_int_matrix() const {
    std::vector<std::vector<int>> out;
    out.reserve(size());
    for (const Value& v : arr) out.push_back(v.as_int_vector());
    return out;
}

Value parse(const std::string& text) { return Parser(text).parse_root(); }

Value parse_file(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw Error("json: cannot open " + path.string());
    std::string data((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    return parse(data);
}

}  // namespace quadmesh::json
