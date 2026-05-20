// =============================================================================
// 文件名: basic_pvt_fmm.cpp
// 描述: 基于 basic-FMM，引入 basic-PVT 真实气体 PVT 表与 getProps()
//      FMM/VOI 仍为静态一次性预处理；beta_fmm = 0.00853；Ct_ref 保持 basic-FMM 设置
//      3D 三相(油气水) 黑油模型 EDFM 求解器
//      网格初始化已改为支持从 COORD.csv + ZCORN.csv 读取 corner-point grid
// 依赖: Eigen 3.3+
// 编译: g++ -O3 -std=c++17 edfm_3d_blackoil.cpp -o edfm_3d -I /path/to/eigen
// =============================================================================
#include <array>
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <fstream>
#include <iomanip>
#include <random>
#include <tuple>
#include <map>
#include <queue>
#include <limits>
#include <sstream>
#include <string>
#include <stdexcept>
#include <cctype>

#include <Eigen/Sparse>
#include <Eigen/Dense>
#include <Eigen/SparseLU>
#include <Eigen/IterativeLinearSolvers>
#include <unsupported/Eigen/AutoDiff>

using namespace std;
using namespace Eigen;

// =============================================================================
// 1. 常量与基础数据结构
// =============================================================================

const double EPSILON = 1e-8;
const double PI = 3.14159265358979323846;
// k:mD, length:m, area:m2, pressure:bar, mu:cP, time:day
const double FLOW_BETA = 0.00853;

enum FaceID {
    XM = 0, XP = 1,
    YM = 2, YP = 3,
    ZM = 4, ZP = 5
};

// 3D 点结构
struct Point3 {
    double x = 0.0, y = 0.0, z = 0.0;

    Point3 operator+(const Point3& other) const { return {x + other.x, y + other.y, z + other.z}; }
    Point3 operator-(const Point3& other) const { return {x - other.x, y - other.y, z - other.z}; }
    Point3 operator*(double s) const { return {x * s, y * s, z * s}; }
    Point3 operator/(double s) const { return {x / s, y / s, z / s}; }

    double dot(const Point3& other) const { return x * other.x + y * other.y + z * other.z; }
    Point3 cross(const Point3& other) const {
        return {
            y * other.z - z * other.y,
            z * other.x - x * other.z,
            x * other.y - y * other.x
        };
    }
    double norm() const { return std::sqrt(x*x + y*y + z*z); }
};

// =============================================================================
// 1.1 corner-point grid 输入相关数据结构
// =============================================================================

// 一根 pillar 的上下两个端点
struct Pillar {
    Point3 top{0, 0, 0};
    Point3 bot{0, 0, 0};
    bool has_top = false;
    bool has_bot = false;
};

// COORD.csv 的一行
struct CoordRow {
    int i = 0;   // 0-based pillar i
    int j = 0;   // 0-based pillar j
    bool is_top = false;
    Point3 p{0, 0, 0};
};

// ZCORN.csv 的一行
struct ZCornRow {
    int i = 0;   // 0-based cell i
    int j = 0;   // 0-based cell j
    int k = 0;   // 0-based cell k
    std::array<double, 8> z{{0, 0, 0, 0, 0, 0, 0, 0}}; // Z1~Z8
};

// =============================================================================
// 1.2 CSV / 字符串辅助函数
// =============================================================================

std::string stripUTF8BOM(const std::string& s) {
    if (s.size() >= 3 &&
        (unsigned char)s[0] == 0xEF &&
        (unsigned char)s[1] == 0xBB &&
        (unsigned char)s[2] == 0xBF) {
        return s.substr(3);
    }
    return s;
}

std::string trim(const std::string& s) {
    std::string t = stripUTF8BOM(s);
    size_t b = 0;
    size_t e = t.size();

    while (b < e && std::isspace((unsigned char)t[b])) ++b;
    while (e > b && std::isspace((unsigned char)t[e - 1])) --e;

    return t.substr(b, e - b);
}

// 简单 CSV 分割：按逗号切分，适用于本项目规则 CSV
std::vector<std::string> splitCSVSimple(const std::string& line) {
    std::vector<std::string> cols;
    std::stringstream ss(line);
    std::string item;
    while (std::getline(ss, item, ',')) {
        cols.push_back(trim(item));
    }

    // 若最后一个字符是逗号，补一个空字段
    if (!line.empty() && line.back() == ',') {
        cols.push_back("");
    }
    return cols;
}

bool parseIntStrict(const std::string& s, int& v) {
    try {
        std::string t = trim(s);
        size_t pos = 0;
        v = std::stoi(t, &pos);
        return pos == t.size();
    } catch (...) {
        return false;
    }
}

bool parseDoubleStrict(const std::string& s, double& v) {
    try {
        std::string t = trim(s);
        size_t pos = 0;
        v = std::stod(t, &pos);
        return pos == t.size();
    } catch (...) {
        return false;
    }
}

bool isTopMarker(const std::string& s) {
    std::string t = trim(s);
    if (t == "顶") return true;

    std::string low = t;
    for (char& ch : low) ch = (char)std::tolower((unsigned char)ch);
    return low == "top";
}

bool isBottomMarker(const std::string& s) {
    std::string t = trim(s);
    if (t == "底") return true;

    std::string low = t;
    for (char& ch : low) ch = (char)std::tolower((unsigned char)ch);
    return low == "bottom";
}

int flatPillarIndex(int i, int j, int npx) {
    return j * npx + i;
}

int flatCellIndex(int i, int j, int k, int Nx, int Ny) {
    return k * Nx * Ny + j * Nx + i;
}

// 裂缝定义（几何输入）
struct Fracture {
    int id = -1;
    Point3 vertices[4];   // 四个顶点，定义一个四边形面
    double aperture = 0.0;
    double perm = 0.0;

    // 新增：是否为人工裂缝
    bool is_hydraulic = false;
};

// 全局 face 几何对象
struct FaceGeom {
    int id = -1;

    // owner / neighbor: 面两侧的 cell
    // 边界面时 neighbor = -1
    int owner = -1;
    int neighbor = -1;

    // 该 face 在 owner / neighbor 中对应的局部 face 槽位，例如XP、XM等
    int local_owner_face = -1;
    int local_neighbor_face = -1;

    // 这里先按四边形面存；后续角点网格阶段仍然可沿用
    std::array<Point3, 4> vertices{};

    Point3 center{0, 0, 0};
    Point3 normal{0, 0, 0};   // 法向朝 owner 外侧
    double area = 0.0;

    Point3 bbox_min{0, 0, 0};
    Point3 bbox_max{0, 0, 0};
};

// 网格单元
struct Cell {
    int id = -1;                     // 全局索引
    int ix = 0, iy = 0, iz = 0;      // 逻辑 IJK 索引

    Point3 center{0, 0, 0};          // 几何中心（阶段A先用8角点平均）
    double dx = 0.0, dy = 0.0, dz = 0.0; // 兼容字段；后续不再作为真几何依据
    double vol = 0.0;

    double phi = 0.0;
    double K[3] = {0.0, 0.0, 0.0};
    double depth = 0.0;

    // 角点网格核心几何：8个角点
    // 约定编号：
    // 0:(xmin,ymin,zmin) 1:(xmax,ymin,zmin) 2:(xmax,ymax,zmin) 3:(xmin,ymax,zmin)
    // 4:(xmin,ymin,zmax) 5:(xmax,ymin,zmax) 6:(xmax,ymax,zmax) 7:(xmin,ymax,zmax)
    std::array<Point3, 8> corners{};

    // 该 cell 的 6 个局部面，对应到全局 faces 向量中的 face id
    std::array<int, 6> face_ids{{-1, -1, -1, -1, -1, -1}};

    // 包围盒，后续做 fracture-cell 候选筛选会用到
    Point3 bbox_min{0, 0, 0};
    Point3 bbox_max{0, 0, 0};
};

// 裂缝段 (EDFM 离散后的最小单元)
struct Segment {
    int id;             // 全局段索引
    int frac_id;        // 所属的大裂缝ID
    int cell_id;        // 所在的基质网格ID
    double area;        // 该段在网格内的截面积
    Point3 center;      // 该段的几何中心
    Point3 normal;      // 法向量
    double aperture;
    double perm;
    double T_mf;        // 基质-裂缝传导率

    // 六个宿主 cell 面上的几何信息
    // 0:x-, 1:x+, 2:y-, 3:y+, 4:z-, 5:z+
    double face_trace_len[6] = {0, 0, 0, 0, 0, 0};   // segment 在宿主 cell 的第 f 个面上的交线长度
    double face_center_dist[6] = {0, 0, 0, 0, 0, 0}; // segment 面积质心到该 face-trace 的距离
    std::vector<Point3> poly;
};

// 连接关系 (用于构建 Jacobian)
struct Connection {
    int u;      // 单元 u (可以是基质或裂缝段)
    int v;      // 单元 v
    double T;   // 传导率
    // 类型: 0=Matrix-Matrix, 1=Matrix-Fracture, 2=Fracture-Fracture
    int type;
};

// 流体物性参数
struct FluidProps {
    // ------------------------------
    // 油水相：仍保持原来的常压缩系数 + 常粘度形式
    // ------------------------------
    // 粘度 (cP)
    double mu_w = 1.0;
    double mu_o = 5.0;

    // 占位/兼容字段：
    // 真实气体版本下，不再直接使用常数 mu_g 和常数 cg 作为主计算来源
    // 这里只保留字段，便于兼容旧代码和后续对照。
    double mu_g = 0.2;  // cP, 占位
    double cg   = 1e-3; // 1/bar, 占位

    // 压缩系数 (1/bar)
    double cw = 1e-8;
    double co = 1e-5;

    // 参考压力 (bar)
    double P_ref = 100.0;

    // 相对渗透率端点
    double Swi = 0.05;
    double Sor = 0.01;
    double Sgc = 0.05;

    // ------------------------------
    // 真实气体 PVT 参数（单位严格按题目约定）
    // ------------------------------
    double gas_t_C     = 140.0;   // 摄氏度
    double gas_T_K     = 413.15;  // K，用于 Z / Cg / mu_g 公式
    // ------------------------------
    // 7 组分混合气摩尔分数（全局可调，要求总和 = 1.0）
    // 后续界面输入组分时，应直接对应修改这些 moleXXX 字段。
    // 注意：这里不用 gamma_i 命名，避免和气体相对密度 gamma_g 混淆。
    // ------------------------------
    double moleCH4     = 0.4;
    double moleC2H6    = 0.2;
    double moleC3H8    = 0.1;
    double moleN2      = 0.1;
    double moleCO2     = 0.1;
    double moleH2O     = 0.1;
    double moleUnknown = 0;

    // 兼容旧版单一甲烷参数字段：
    // 7 组分混合气版本中，Z / Cg / mu_g 不再直接使用这些字段，
    // 而是通过 computeGasMixturePseudoProps() 得到 Tpc / Ppc / Mmix。
    double gas_Mg      = 16.04;   // 旧版甲烷摩尔质量，占位/兼容字段
    double gas_Tc      = 190.58;  // 旧版甲烷临界温度, K，占位/兼容字段
    double gas_Pc_bar  = 45.44;   // 旧版甲烷临界压力, bar，占位/兼容字段
    double gas_Psc_bar = 1.01325; // 标准状态压力, bar（用于 Bg 公式）
                                   // 注意：Psc 是标准状态压力，不是临界压力 Pc

    // 气相 PVT 表范围
    double gas_table_Pmin_bar = 1.0;
    double gas_table_Pmax_bar = 1000.0;
    int    gas_table_n        = 2000;
};

typedef Eigen::Matrix<double, 3, 1> Deriv3;
typedef Eigen::AutoDiffScalar<Deriv3> AD3;

// 状态变量 (每个计算节点：基质或裂缝段)
template <typename T>
struct StateT {
    T P;   // 油相压力
    T Sw;  // 水饱和度
    T Sg;  // 气饱和度
    // So = 1 - Sw - Sg;
};
typedef StateT<double> State;
typedef StateT<AD3> StateAD3;

template <typename T>
struct PropertiesT {
    T Bw, Bo, Bg;
    T Zg, Cg, mu_g;   // 气相真实气体 PVT：偏差因子、压缩系数、黏度
    T krw, kro, krg;
    T lw, lo, lg;
};

inline double scalarValue(const double& x) { return x; }
inline double scalarValue(const AD3& x)    { return x.value(); }

// =============================================================================
// 2. 几何辅助函数：基础几何原语
// =============================================================================

Point3 pointMin(const Point3& a, const Point3& b) {
    return {std::min(a.x, b.x), std::min(a.y, b.y), std::min(a.z, b.z)};
}

Point3 pointMax(const Point3& a, const Point3& b) {
    return {std::max(a.x, b.x), std::max(a.y, b.y), std::max(a.z, b.z)};
}

Point3 averagePoints(const std::array<Point3, 4>& pts) {  // 面顶点质心
    Point3 c{0, 0, 0};
    for (const auto& p : pts) c = c + p;
    return c / 4.0;
}

Point3 averagePoints(const std::array<Point3, 8>& pts) {  // 网格顶点质心
    Point3 c{0, 0, 0};
    for (const auto& p : pts) c = c + p;
    return c / 8.0;
}

double triangleArea3D(const Point3& a, const Point3& b, const Point3& c) { // 三角形面积
    return 0.5 * ((b - a).cross(c - a)).norm();
}

double quadArea3D(const std::array<Point3, 4>& q) {  // 四边形面积
    return triangleArea3D(q[0], q[1], q[2]) + triangleArea3D(q[0], q[2], q[3]);
}

// quad 面法向（单位向量），用 Newell 方法更稳一些
Point3 quadUnitNormal(const std::array<Point3, 4>& q) {
    Point3 n{0, 0, 0};
    for (int i = 0; i < 4; ++i) {
        const Point3& p = q[i];
        const Point3& r = q[(i + 1) % 4];
        n.x += (p.y - r.y) * (p.z + r.z);
        n.y += (p.z - r.z) * (p.x + r.x);
        n.z += (p.x - r.x) * (p.y + r.y);
    }
    double nn = n.norm();
    if (nn < EPSILON) return {0, 0, 0};
    return n / nn;
}

// 调整四边形顶点顺序，使其法向朝 cell_center 外侧
void orientQuadOutward(std::array<Point3, 4>& q, const Point3& cell_center) {
    Point3 fc = averagePoints(q);
    Point3 n = quadUnitNormal(q);
    if (n.norm() < EPSILON) return;

    // 若法向没有指向“远离 cell center”的方向，则翻转顶点顺序
    if (n.dot(fc - cell_center) < 0.0) {
        std::reverse(q.begin(), q.end());
    }
}

// =============================================================================
// 3. 几何辅助函数：cell / face 几何构造
// =============================================================================

// 局部 face 槽位 -> 8角点编号映射
std::array<int, 4> getLocalFaceCornerIds(int face_id) {
    switch (face_id) {
        case XM: return {0, 4, 7, 3};
        case XP: return {1, 2, 6, 5};
        case YM: return {0, 1, 5, 4};
        case YP: return {3, 7, 6, 2};
        case ZM: return {0, 3, 2, 1};
        case ZP: return {4, 5, 6, 7};
        default: return {0, 1, 2, 3};
    }
}

std::array<Point3, 4> getCellFaceVertices(const Cell& c, int face_id) {
    auto ids = getLocalFaceCornerIds(face_id);
    return {c.corners[ids[0]], c.corners[ids[1]], c.corners[ids[2]], c.corners[ids[3]]};
}

double signedTetVolumeFromOrigin(const Point3& a, const Point3& b, const Point3& c) {
    return a.dot(b.cross(c)) / 6.0; // 有符号四面体体积
}

// 通过“外向有序的六个 face 三角化”估算一般六面体体积
double hexaVolumeFromOrientedFaces(const std::array<std::array<Point3, 4>, 6>& face_quads) {
    double v = 0.0;
    for (const auto& q : face_quads) {
        v += signedTetVolumeFromOrigin(q[0], q[1], q[2]);
        v += signedTetVolumeFromOrigin(q[0], q[2], q[3]);
    }
    return std::abs(v);
}

// 用 corners 预计算 cell 的 center / bbox / vol / depth
void computeCellDerivedGeometry(Cell& c) {
    c.center = averagePoints(c.corners);

    c.bbox_min = c.corners[0];
    c.bbox_max = c.corners[0];
    for (int n = 1; n < 8; ++n) {
        c.bbox_min = pointMin(c.bbox_min, c.corners[n]);
        c.bbox_max = pointMax(c.bbox_max, c.corners[n]);
    }

    // 为兼容后续尚未改造的旧函数，先继续填 dx/dy/dz
    c.dx = c.bbox_max.x - c.bbox_min.x;
    c.dy = c.bbox_max.y - c.bbox_min.y;
    c.dz = c.bbox_max.z - c.bbox_min.z;

    std::array<std::array<Point3, 4>, 6> face_quads;
    for (int f = 0; f < 6; ++f) {
        face_quads[f] = getCellFaceVertices(c, f);
        orientQuadOutward(face_quads[f], c.center);
    }

    c.vol = hexaVolumeFromOrientedFaces(face_quads);
    c.depth = c.center.z;
}

void computeFaceDerivedGeometry(FaceGeom& f, const Point3& owner_center) {
    orientQuadOutward(f.vertices, owner_center);

    f.center = averagePoints(f.vertices);
    f.normal = quadUnitNormal(f.vertices);
    f.area = quadArea3D(f.vertices);

    f.bbox_min = f.vertices[0];
    f.bbox_max = f.vertices[0];
    for (int i = 1; i < 4; ++i) {
        f.bbox_min = pointMin(f.bbox_min, f.vertices[i]);
        f.bbox_max = pointMax(f.bbox_max, f.vertices[i]);
    }
}

// =============================================================================
// 4. 几何辅助函数：传导率相关几何
// =============================================================================

double normalProjectedPerm(const Cell& c, const Point3& n_unit) {
    // 当前仍假设 K 为对角渗透率张量
    // k_n = n^T K n
    return
        n_unit.x * n_unit.x * c.K[0] +
        n_unit.y * n_unit.y * c.K[1] +
        n_unit.z * n_unit.z * c.K[2];
}

double centerToFaceNormalDistance(const Cell& c, const FaceGeom& f) {
    // FaceGeom::normal 约定为单位法向
    // 对 TPFA，这里取 center 到面中心沿 face 法向的投影距离
    double d = std::abs((f.center - c.center).dot(f.normal));
    return std::max(d, 1e-10);
}

double computeMMTransmissibilityTPFA(const Cell& cu,
                                     const Cell& cv,
                                     const FaceGeom& f) {
    // 共享面面积
    double Af = f.area;
    if (Af <= EPSILON) return 0.0;

    // 法向渗透率（face.normal 已为单位向量）
    double kn_u = normalProjectedPerm(cu, f.normal);
    double kn_v = normalProjectedPerm(cv, f.normal);

    if (kn_u <= EPSILON || kn_v <= EPSILON) return 0.0;

    // 两侧中心到共享面的法向距离
    double du = centerToFaceNormalDistance(cu, f);
    double dv = centerToFaceNormalDistance(cv, f);

    // 两个半传导率
    double tau_u =FLOW_BETA * kn_u * Af / du;
    double tau_v = FLOW_BETA *kn_v * Af / dv;

    if (tau_u <= EPSILON || tau_v <= EPSILON) return 0.0;

    // 调和组合
    return (tau_u * tau_v) / std::max(EPSILON, tau_u + tau_v);
}

Point3 mapHexTrilinear(const Cell& cell, double u, double v, double w) {
    const auto& c = cell.corners;

    double N0 = (1.0 - u) * (1.0 - v) * (1.0 - w);
    double N1 = u * (1.0 - v) * (1.0 - w);
    double N2 = u * v * (1.0 - w);
    double N3 = (1.0 - u) * v * (1.0 - w);
    double N4 = (1.0 - u) * (1.0 - v) * w;
    double N5 = u * (1.0 - v) * w;
    double N6 = u * v * w;
    double N7 = (1.0 - u) * v * w;

    return c[0] * N0 + c[1] * N1 + c[2] * N2 + c[3] * N3
         + c[4] * N4 + c[5] * N5 + c[6] * N6 + c[7] * N7;
}

double averageDistanceCellToPlane(const Cell& cell,
                                  const Point3& planePoint,
                                  const Point3& unitNormal,
                                  int nxs = 2, int nys = 2, int nzs = 2) {
    double sum = 0.0;
    int count = 0;

    for (int k = 0; k < nzs; ++k) {
        for (int j = 0; j < nys; ++j) {
            for (int i = 0; i < nxs; ++i) {
                double u = (i + 0.5) / (double)nxs;
                double v = (j + 0.5) / (double)nys;
                double w = (k + 0.5) / (double)nzs;

                Point3 p = mapHexTrilinear(cell, u, v, w);
                double d = std::abs((p - planePoint).dot(unitNormal));
                sum += d;
                count++;
            }
        }
    }

    if (count == 0) return 0.0;
    return sum / (double)count;
}

double computeMatrixFractureTransmissibility(const Cell& cell,
                                             const Segment& seg,
                                             int nxs = 2, int nys = 2, int nzs = 2) {
    if (seg.area <= EPSILON) return 0.0;

    // 裂缝法向应为单位向量；这里再做一次保护
    Point3 n = seg.normal;
    double nn = n.norm();
    if (nn < EPSILON) return 0.0;
    n = n * (1.0 / nn);

    // 基质渗透率沿裂缝法向的投影
    double Kn = normalProjectedPerm(cell, n);
    if (Kn <= EPSILON) return 0.0;

    // 在一般六面体内部做采样，求 cell 内各采样点到 fracture plane 的平均距离
    // 这里 planePoint 直接用 seg.center，比 poly[0] 更稳
    double d_avg = averageDistanceCellToPlane(cell, seg.center, n, nxs, nys, nzs);

    double scale = std::max(1.0, std::max(cell.dx, std::max(cell.dy, cell.dz)));
    d_avg = std::max(d_avg, 1e-10 * scale);

    // EDFM 近似：
    // Tmf = 2 * A * Kn / d_avg
    double Tmf = FLOW_BETA *2.0 * seg.area * (Kn / d_avg);

    if (!std::isfinite(Tmf) || Tmf <= EPSILON) return 0.0;
    return Tmf;
}

// =============================================================================
// 5. 几何辅助函数：裂缝局部坐标 / 等效半径
// =============================================================================

Point3 fractureCenter(const Fracture& f) {
    Point3 c{0, 0, 0};
    for (int i = 0; i < 4; ++i) c = c + f.vertices[i];
    return c / 4.0;
}

void buildPlaneBasisFromNormal(const Point3& normal, Point3& e1, Point3& e2) {
    Point3 n = normal;
    double nn = n.norm();
    if (nn < EPSILON) {
        e1 = {1, 0, 0};
        e2 = {0, 1, 0};
        return;
    }
    n = n * (1.0 / nn);

    // 选一个与 n 不太平行的参考方向
    Point3 ref;
    if (std::abs(n.x) <= std::abs(n.y) && std::abs(n.x) <= std::abs(n.z)) {
        ref = {1, 0, 0};
    } else if (std::abs(n.y) <= std::abs(n.x) && std::abs(n.y) <= std::abs(n.z)) {
        ref = {0, 1, 0};
    } else {
        ref = {0, 0, 1};
    }

    e1 = n.cross(ref);
    double ne1 = e1.norm();
    if (ne1 < EPSILON) {
        // 极端退化保护
        ref = {0, 1, 0};
        e1 = n.cross(ref);
        ne1 = e1.norm();
        if (ne1 < EPSILON) {
            e1 = {1, 0, 0};
            e2 = {0, 1, 0};
            return;
        }
    }
    e1 = e1 * (1.0 / ne1);

    e2 = n.cross(e1);
    double ne2 = e2.norm();
    if (ne2 < EPSILON) {
        e2 = {0, 1, 0};
    } else {
        e2 = e2 * (1.0 / ne2);
    }
}

bool computeSegmentLocalPlaneExtents(const Segment& seg, double& Lu, double& Lv) {
    Lu = 0.0;
    Lv = 0.0;

    if (seg.poly.size() < 3) return false;

    Point3 e1, e2;
    buildPlaneBasisFromNormal(seg.normal, e1, e2);

    double umin = 1e100, umax = -1e100;
    double vmin = 1e100, vmax = -1e100;

    for (const auto& p : seg.poly) {
        Point3 d = p - seg.center;
        double u = d.dot(e1);
        double v = d.dot(e2);

        umin = std::min(umin, u);
        umax = std::max(umax, u);
        vmin = std::min(vmin, v);
        vmax = std::max(vmax, v);
    }

    Lu = std::max(0.0, umax - umin);
    Lv = std::max(0.0, vmax - vmin);

    // 退化保护：
    // 如果某个方向数值太小，但 area 是正的，用 area/另一方向 做一个修复
    if (Lu <= EPSILON && Lv > EPSILON && seg.area > EPSILON) {
        Lu = seg.area / Lv;
    }
    if (Lv <= EPSILON && Lu > EPSILON && seg.area > EPSILON) {
        Lv = seg.area / Lu;
    }

    return (Lu > EPSILON && Lv > EPSILON);
}

double computeSegmentEquivalentRadius(const Segment& seg, double rw) {
    double Lu = 0.0, Lv = 0.0;
    bool ok = computeSegmentLocalPlaneExtents(seg, Lu, Lv);

    double re = 0.0;

    if (ok) {
        re = 0.14 * std::sqrt(Lu * Lu + Lv * Lv);
    } else {
        // 再退化保护：如果局部长宽提取失败，则用面积反推一个等效尺度
        if (seg.area > EPSILON) {
            double Leq = std::sqrt(seg.area);
            re = 0.14 * std::sqrt(2.0) * Leq;
        } else {
            re = 1.1 * rw;
        }
    }

    // 必须保证 re > rw，否则 log(re/rw) 会出问题
    re = std::max(re, 1.1 * rw);
    return re;
}

// =============================================================================
// 6. 几何辅助函数：多边形裁剪主链
// =============================================================================

// 计算多边形面积
double polygonArea(const std::vector<Point3>& poly) {
    if (poly.size() < 3) return 0.0;
    Point3 total = {0, 0, 0};
    Point3 v0 = poly[0];
    for (size_t i = 1; i < poly.size() - 1; ++i) {
        Point3 v1 = poly[i];
        Point3 v2 = poly[i+1];
        total = total + (v1 - v0).cross(v2 - v0);
    }
    return 0.5 * total.norm();
}

// 计算面积质心
Point3 polygonCenter(const std::vector<Point3>& poly) {
    Point3 c{0, 0, 0};
    if (poly.empty()) return c;
    if (poly.size() < 3) {
        for (const auto& p : poly) c = c + p;
        return c * (1.0 / poly.size());
    }

    Point3 v0 = poly[0];
    double A_total = 0.0;
    Point3 C_total{0, 0, 0};

    for (size_t i = 1; i + 1 < poly.size(); ++i) {
        Point3 v1 = poly[i];
        Point3 v2 = poly[i + 1];

        double Ai = 0.5 * ((v1 - v0).cross(v2 - v0)).norm();
        if (Ai < EPSILON) continue;

        Point3 triC = (v0 + v1 + v2) * (1.0 / 3.0);
        C_total = C_total + triC * Ai;
        A_total += Ai;
    }

    if (A_total < EPSILON) {
        for (const auto& p : poly) c = c + p;
        return c * (1.0 / poly.size());
    }

    return C_total * (1.0 / A_total);
}

// 检查点是否在平面的内侧
bool isInside(const Point3& p, const Point3& planeNormal, double planeD) {
    return (planeNormal.dot(p) + planeD) >= -1e-9;
}

// 计算线段与平面的交点
Point3 intersectPlane(const Point3& p1, const Point3& p2,
                      const Point3& planeNormal, double planeD) {
    double d1 = planeNormal.dot(p1) + planeD;
    double d2 = planeNormal.dot(p2) + planeD;

    const double eps = 1e-12;

    if (std::abs(d1) < eps) return p1;
    if (std::abs(d2) < eps) return p2;

    double denom = d1 - d2;
    if (std::abs(denom) < eps) return p1; // 退化保护

    double t = d1 / (d1 - d2);
    return p1 + (p2 - p1) * t;
}

// Sutherland-Hodgman 多边形剪裁 (针对一个平面)
std::vector<Point3> clipPolygonCurrentPlane(const std::vector<Point3>& inputPoly,
                                            const Point3& normal,
                                            double d) {
    std::vector<Point3> outputPoly;
    if (inputPoly.empty()) return outputPoly;

    for (size_t i = 0; i < inputPoly.size(); ++i) {
        Point3 cur = inputPoly[i];
        Point3 prev = inputPoly[(i + inputPoly.size() - 1) % inputPoly.size()];

        bool curIn = isInside(cur, normal, d);
        bool prevIn = isInside(prev, normal, d);

        if (curIn) {
            if (!prevIn) {
                outputPoly.push_back(intersectPlane(prev, cur, normal, d));
            }
            outputPoly.push_back(cur);
        } else if (prevIn) {
            outputPoly.push_back(intersectPlane(prev, cur, normal, d));
        }
    }
    return outputPoly;
}

bool bboxOverlap(const Point3& a_min, const Point3& a_max,
                 const Point3& b_min, const Point3& b_max,
                 double tol = 1e-12) {
    if (a_max.x < b_min.x - tol || b_max.x < a_min.x - tol) return false;
    if (a_max.y < b_min.y - tol || b_max.y < a_min.y - tol) return false;
    if (a_max.z < b_min.z - tol || b_max.z < a_min.z - tol) return false;
    return true;
}

// 清理裁剪后的 polygon：
// 1) 去掉连续重复点
// 2) 若首尾重复，去掉尾点
std::vector<Point3> cleanupPolygon3D(const std::vector<Point3>& poly, double tol) {
    std::vector<Point3> out;
    if (poly.empty()) return out;

    for (const auto& p : poly) {
        if (out.empty() || (p - out.back()).norm() > tol) {
            out.push_back(p);
        }
    }

    if (out.size() >= 2 && (out.front() - out.back()).norm() <= tol) {
        out.pop_back();
    }

    return out;
}

// 对于某个 cell 的某个局部 face，构造“朝 cell 内部”的裁剪平面
// 输出平面方程： n_in · x + d >= 0  表示在 cell 内部
bool getInwardPlaneForCellFace(const Cell& cell,
                               const std::vector<FaceGeom>& faces,
                               int local_face_id,
                               Point3& n_in,
                               double& d) {
    int fid = cell.face_ids[local_face_id];
    if (fid < 0) return false;

    const FaceGeom& fg = faces[fid];

    // fg.normal 约定为“朝 owner 外侧”
    // 对当前 cell 来说，要得到“朝内部”的法向
    if (fg.owner == cell.id) {
        n_in = fg.normal * (-1.0);
    } else if (fg.neighbor == cell.id) {
        n_in = fg.normal;
    } else {
        return false;
    }

    // face 上任取一点即可
    const Point3& p0 = fg.vertices[0];
    d = -n_in.dot(p0);
    return true;
}

// 用一个一般六面体 cell 的 6 个真实面，逐面裁剪 polygon
std::vector<Point3> clipPolygonByCell(const std::vector<Point3>& inputPoly,
                                      const Cell& cell,
                                      const std::vector<FaceGeom>& faces) {
    std::vector<Point3> poly = inputPoly;

    double scale = std::max(1.0, std::max(cell.dx, std::max(cell.dy, cell.dz)));
    double tol = 1e-10 * scale;

    for (int lf = 0; lf < 6; ++lf) {
        Point3 n_in;
        double d = 0.0;
        if (!getInwardPlaneForCellFace(cell, faces, lf, n_in, d)) {
            poly.clear();
            return poly;
        }

        poly = clipPolygonCurrentPlane(poly, n_in, d);
        poly = cleanupPolygon3D(poly, tol);

        if (poly.size() < 3) {
            poly.clear();
            return poly;
        }
    }

    return poly;
}

std::vector<Point3> clipFractureBox(const Fracture& frac,
                                    const Cell& cell,
                                    const std::vector<FaceGeom>& faces) {
    std::vector<Point3> poly;
    for (int i = 0; i < 4; ++i) poly.push_back(frac.vertices[i]);

    double scale = std::max(1.0, std::max(cell.dx, std::max(cell.dy, cell.dz)));
    double tol = 1e-10 * scale;

    poly = cleanupPolygon3D(poly, tol);
    if (poly.size() < 3) return {};

    poly = clipPolygonByCell(poly, cell, faces);
    poly = cleanupPolygon3D(poly, tol);

    if (poly.size() < 3) return {};
    return poly;
}

// =============================================================================
// 7. 几何辅助函数：face-trace 提取
// =============================================================================

void pushUniquePoint(std::vector<Point3>& pts, const Point3& p, double tol) {   // 点去重辅助
    for (const auto& q : pts) {
        if ((p - q).norm() <= tol) return;
    }
    pts.push_back(p);
}

// 3D三角形内点判断（假设点已与三角形近共面）
bool pointInTriangle3D(const Point3& p,
                       const Point3& a,
                       const Point3& b,
                       const Point3& c,
                       double tol) {
    Point3 v0 = b - a;
    Point3 v1 = c - a;
    Point3 v2 = p - a;

    double d00 = v0.dot(v0);
    double d01 = v0.dot(v1);
    double d11 = v1.dot(v1);
    double d20 = v2.dot(v0);
    double d21 = v2.dot(v1);

    double denom = d00 * d11 - d01 * d01;
    if (std::abs(denom) < EPSILON) return false;

    double v = (d11 * d20 - d01 * d21) / denom;
    double w = (d00 * d21 - d01 * d20) / denom;
    double u = 1.0 - v - w;

    return (u >= -tol && v >= -tol && w >= -tol);
}

// 凸四边形内点判断：拆成两个三角形
bool pointInConvexQuad3D(const Point3& p,
                         const std::array<Point3, 4>& q,
                         double tol) {
    return pointInTriangle3D(p, q[0], q[1], q[2], tol) ||
           pointInTriangle3D(p, q[0], q[2], q[3], tol);
}

bool pointOnCellFace(const Point3& p,
                     const Cell& cell,
                     const std::vector<FaceGeom>& faces,
                     int face_id,
                     double tol) {
    int fid = cell.face_ids[face_id];
    if (fid < 0) return false;

    const FaceGeom& fg = faces[fid];
    if (fg.area <= EPSILON) return false;

    // 1) 先判断是否在该 face 所在平面上
    const Point3& p0 = fg.vertices[0];
    double dist_to_plane = std::abs((p - p0).dot(fg.normal));
    if (dist_to_plane > tol) return false;

    // 2) 再判断是否落在 face 四边形内部
    return pointInConvexQuad3D(p, fg.vertices, tol);
}

bool extractTraceOnFace(const std::vector<Point3>& poly,
                        const Cell& cell,
                        const std::vector<FaceGeom>& faces,
                        int face_id,
                        Point3& a,
                        Point3& b,
                        double& len) {
    len = 0.0;
    if (poly.size() < 2) return false;

    int fid = cell.face_ids[face_id];
    if (fid < 0) return false;

    const FaceGeom& fg = faces[fid];
    if (fg.area <= EPSILON) return false;

    double scale = std::max(1.0, std::max(cell.dx, std::max(cell.dy, cell.dz)));
    double tol = 1e-8 * scale;

    const Point3& p0 = fg.vertices[0];
    const Point3& n = fg.normal;
    double planeD = -n.dot(p0);

    std::vector<Point3> pts;

    auto try_add_point = [&](const Point3& q) {
        if (pointOnCellFace(q, cell, faces, face_id, tol)) {
            pushUniquePoint(pts, q, tol);
        }
    };

    // 1) 先收集本来就在该 face 上的 polygon 顶点
    for (const auto& p : poly) {
        try_add_point(p);
    }

    // 2) 再检查 polygon 边与 face 平面的交点
    for (size_t i = 0; i < poly.size(); ++i) {
        const Point3& p1 = poly[i];
        const Point3& p2 = poly[(i + 1) % poly.size()];

        double d1 = n.dot(p1) + planeD;
        double d2 = n.dot(p2) + planeD;

        bool on1 = std::abs(d1) <= tol;
        bool on2 = std::abs(d2) <= tol;

        if (on1 && on2) {
            try_add_point(p1);
            try_add_point(p2);
            continue;
        }

        // 真正跨过该平面
        if ((d1 > tol && d2 < -tol) || (d1 < -tol && d2 > tol)) {
            Point3 q = intersectPlane(p1, p2, n, planeD);
            try_add_point(q);
        }
    }

    if (pts.size() < 2) return false;

    // 3) 取最远两点作为 trace 端点
    double best = -1.0;
    Point3 pa{0, 0, 0}, pb{0, 0, 0};

    for (size_t i = 0; i < pts.size(); ++i) {
        for (size_t j = i + 1; j < pts.size(); ++j) {
            double d = (pts[i] - pts[j]).norm();
            if (d > best) {
                best = d;
                pa = pts[i];
                pb = pts[j];
            }
        }
    }

    if (best <= EPSILON) return false;

    a = pa;
    b = pb;
    len = best;
    return true;
}

double pointToLineDistance3D(const Point3& p, const Point3& a, const Point3& b) { // 点到3D无限直线的距离
    Point3 ab = b - a;
    double lab = ab.norm();
    if (lab < EPSILON) return 0.0;
    return ((p - a).cross(ab)).norm() / lab;
}

void fillSegmentFaceGeom(Segment& seg,
                         const std::vector<Point3>& poly,
                         const Cell& cell,
                         const std::vector<FaceGeom>& faces) {
    for (int f = 0; f < 6; ++f) {
        seg.face_trace_len[f] = 0.0;
        seg.face_center_dist[f] = 0.0;

        Point3 a, b;
        double len = 0.0;

        if (extractTraceOnFace(poly, cell, faces, f, a, b, len)) {
            seg.face_trace_len[f] = len;

            double dist = pointToLineDistance3D(seg.center, a, b);
            seg.face_center_dist[f] = std::max(dist, 1e-10);
        }
    }
}

// =============================================================================
// 8. 几何辅助函数：裂缝-裂缝连接几何
// =============================================================================

std::pair<int,int> getSharedFaces(const Cell& c1, const Cell& c2) {  // 判断两个相邻 cell 共享哪两个面
    int dix = c2.ix - c1.ix;
    int diy = c2.iy - c1.iy;
    int diz = c2.iz - c1.iz;

    if (dix ==  1 && diy == 0 && diz == 0) return {XP, XM};
    if (dix == -1 && diy == 0 && diz == 0) return {XM, XP};

    if (dix == 0 && diy ==  1 && diz == 0) return {YP, YM};
    if (dix == 0 && diy == -1 && diz == 0) return {YM, YP};

    if (dix == 0 && diy == 0 && diz ==  1) return {ZP, ZM};
    if (dix == 0 && diy == 0 && diz == -1) return {ZM, ZP};

    return {-1, -1};
}

bool getSharedFacePairByFaceIds(const Cell& c1,  //判断两个 cell 是否共享同一个全局 face，并把这个共享面的信息找出来
                                const Cell& c2,
                                int& lf1,
                                int& lf2,
                                int& shared_fid) {
    lf1 = -1;
    lf2 = -1;
    shared_fid = -1;

    for (int f1 = 0; f1 < 6; ++f1) {
        int id1 = c1.face_ids[f1];
        if (id1 < 0) continue;

        for (int f2 = 0; f2 < 6; ++f2) {
            int id2 = c2.face_ids[f2];
            if (id2 < 0) continue;

            if (id1 == id2) {
                lf1 = f1;
                lf2 = f2;
                shared_fid = id1;
                return true;
            }
        }
    }

    return false;
}

double pointToSegmentDistance3D(const Point3& p, const Point3& a, const Point3& b) {
    Point3 ab = b - a;
    double ab2 = ab.dot(ab);
    if (ab2 < EPSILON) {
        return (p - a).norm();   // 退化成一个点
    }

    double t = (p - a).dot(ab) / ab2;
    t = std::max(0.0, std::min(1.0, t));

    Point3 q = a + ab * t;
    return (p - q).norm();
}

bool intersectTwoPlanes(const Point3& n1, const Point3& p1,
                        const Point3& n2, const Point3& p2,
                        Point3& linePoint, Point3& lineDir) {
    // 原始方向（未归一化）
    Point3 dir = n1.cross(n2);
    double dir2 = dir.dot(dir);

    // 平行或近似平行
    if (dir2 < 1e-14) {
        return false;
    }

    double d1 = n1.dot(p1);
    double d2 = n2.dot(p2);

    // 交线上一点
    Point3 term1 = n2.cross(dir) * d1;
    Point3 term2 = dir.cross(n1) * d2;
    linePoint = (term1 + term2) * (1.0 / dir2);

    // 把方向单位化，后面裁剪更方便
    lineDir = dir * (1.0 / std::sqrt(dir2));

    return true;
}

bool clipLineByConvexPolygon(const std::vector<Point3>& poly,
                             const Point3& normal,
                             const Point3& linePoint,
                             const Point3& lineDir,
                             double& tmin,
                             double& tmax) {
    if (poly.size() < 3) return false;

    Point3 centroid = polygonCenter(poly);

    tmin = -1e100;
    tmax =  1e100;

    for (size_t i = 0; i < poly.size(); ++i) {
        const Point3& vi = poly[i];
        const Point3& vj = poly[(i + 1) % poly.size()];

        Point3 e = vj - vi;

        // 候选边法向量（在 polygon 平面内）
        Point3 m = normal.cross(e);

        // 退化边跳过
        if (m.norm() < EPSILON) continue;

        // 调整方向，使其指向 polygon 内部
        if (m.dot(centroid - vi) < 0.0) {
            m = m * (-1.0);
        }

        double c = m.dot(linePoint - vi);
        double den = m.dot(lineDir);

        const double tol = 1e-12;

        // 直线与这条边界平行
        if (std::abs(den) < tol) {
            // 若 linePoint 在外侧，则整条线都在外面
            if (c < -tol) return false;
            continue;
        }

        // 不等式： c + den * t >= 0
        double tbound = -c / den;

        if (den > 0.0) {
            // t >= tbound
            tmin = std::max(tmin, tbound);
        } else {
            // t <= tbound
            tmax = std::min(tmax, tbound);
        }

        if (tmin > tmax) return false;
    }

    return true;
}

bool computeCrossIntersectionSegment(const Segment& seg1,
                                     const Segment& seg2,
                                     Point3& a,
                                     Point3& b,
                                     double& ell_int) {
    ell_int = 0.0;

    // 1) 先求两平面的交线
    Point3 linePoint, lineDir;
    if (!intersectTwoPlanes(seg1.normal, seg1.center,
                            seg2.normal, seg2.center,
                            linePoint, lineDir)) {
        return false;
    }

    // 2) 把交线裁到 seg1.poly 内
    double t1min, t1max;
    if (!clipLineByConvexPolygon(seg1.poly, seg1.normal,
                                 linePoint, lineDir,
                                 t1min, t1max)) {
        return false;
    }

    // 3) 把交线裁到 seg2.poly 内
    double t2min, t2max;
    if (!clipLineByConvexPolygon(seg2.poly, seg2.normal,
                                 linePoint, lineDir,
                                 t2min, t2max)) {
        return false;
    }

    // 4) 两段区间求交集
    double ta = std::max(t1min, t2min);
    double tb = std::min(t1max, t2max);

    if (tb - ta <= 1e-10) {
        return false;   // 无交线，或只接触于一点，或数值退化
    }

    a = linePoint + lineDir * ta;
    b = linePoint + lineDir * tb;
    ell_int = (b - a).norm();

    if (ell_int <= EPSILON) return false;

    return true;
}

bool computeCrossGeom(const Segment& seg1,
                      const Segment& seg2,
                      double& ell_int,
                      double& L1,
                      double& L2) {
    Point3 a, b;
    if (!computeCrossIntersectionSegment(seg1, seg2, a, b, ell_int)) {
        return false;
    }

    L1 = pointToSegmentDistance3D(seg1.center, a, b);
    L2 = pointToSegmentDistance3D(seg2.center, a, b);

    // 防止除零
    L1 = std::max(L1, 1e-10);
    L2 = std::max(L2, 1e-10);

    return true;
}

// =============================================================================
// 9. 物理模型辅助函数 (PVT & RelPerm)
// =============================================================================

FluidProps g_props;

// =============================================================================
// 7 组分混合气 PVT 辅助结构与函数
// 组分固定临界性质写死在代码中；摩尔分数从 g_props 读取。
// =============================================================================
struct GasComponentCritical {
    const char* name;
    double Tc_K;
    double Pc_bar;
    double MW;
};

struct GasMixturePseudoProps {
    double Tpc_K;
    double Ppc_bar;
    double Mmix;
};

static const std::array<GasComponentCritical, 7> GAS_COMPONENTS = {{
    {"CH4",     190.58,  45.44, 16.04},
    {"C2H6",    305.42,  48.16, 30.07},
    {"C3H8",    369.82,  41.94, 44.10},
    {"N2",      125.97,  33.49, 28.10},
    {"CO2",     304.25,  72.90, 44.00},
    {"H2O",     647.00, 218.30, 18.02},
    {"Unknown", 350.00,  50.00, 35.00}
}};

static std::array<double, 7> getGasMoleFractions() {
    return {{
        g_props.moleCH4,
        g_props.moleC2H6,
        g_props.moleC3H8,
        g_props.moleN2,
        g_props.moleCO2,
        g_props.moleH2O,
        g_props.moleUnknown
    }};
}

static void validateGasMoleFractions() {
    const auto mole = getGasMoleFractions();
    double sumMole = 0.0;
    for (double x : mole) sumMole += x;

    if (!std::isfinite(sumMole) || std::abs(sumMole - 1.0) > 1e-8) {
        std::ostringstream oss;
        oss << std::setprecision(16)
            << "Gas mole fractions must sum to 1.0, current sum = " << sumMole;
        throw std::runtime_error(oss.str());
    }

    for (size_t i = 0; i < mole.size(); ++i) {
        if (!std::isfinite(mole[i]) || mole[i] < 0.0) {
            std::ostringstream oss;
            oss << "Gas mole fraction of " << GAS_COMPONENTS[i].name
                << " must be finite and non-negative, current value = "
                << std::setprecision(16) << mole[i];
            throw std::runtime_error(oss.str());
        }
    }
}

static GasMixturePseudoProps computeGasMixturePseudoProps() {
    validateGasMoleFractions();

    const auto mole = getGasMoleFractions();
    GasMixturePseudoProps mix{0.0, 0.0, 0.0};
    for (size_t i = 0; i < GAS_COMPONENTS.size(); ++i) {
        mix.Tpc_K   += mole[i] * GAS_COMPONENTS[i].Tc_K;
        mix.Ppc_bar += mole[i] * GAS_COMPONENTS[i].Pc_bar;
        mix.Mmix    += mole[i] * GAS_COMPONENTS[i].MW;
    }

    if (!std::isfinite(mix.Tpc_K) || !std::isfinite(mix.Ppc_bar) || !std::isfinite(mix.Mmix) ||
        mix.Tpc_K <= 0.0 || mix.Ppc_bar <= 0.0 || mix.Mmix <= 0.0) {
        throw std::runtime_error("Invalid gas mixture pseudo properties computed from mole fractions.");
    }
    return mix;
}


// 油水相保持原状：仍采用指数型体积系数
template <typename T>
void calcLiquidPVT(const T& P, T& Bw, T& Bo, T& dBw_dP, T& dBo_dP) {
    T dP = P - g_props.P_ref;
    using std::exp;
    Bw = exp(-g_props.cw * dP);
    Bo = exp(-g_props.co * dP);

    dBw_dP = -g_props.cw * Bw;
    dBo_dP = -g_props.co * Bo;
}

// 只取值，不关心导数时的简化接口
template <typename T>
void calcLiquidPVT(const T& P, T& Bw, T& Bo) {
    T dBw_dP, dBo_dP;
    calcLiquidPVT(P, Bw, Bo, dBw_dP, dBo_dP);
}
// 计算相对渗透率 (Corey Model)
template <typename T>
void calcRelPerm(const T& Sw, const T& Sg, T& krw, T& kro, T& krg) {
    auto clamp01_T = [](const T& v) -> T {
        T zero(0.0), one(1.0);
        return (v < zero) ? zero : ((v > one) ? one : v);
    };
    T Sw_norm = (Sw - g_props.Swi) / (1.0 - g_props.Swi - g_props.Sor);
    T Sg_norm = (Sg - g_props.Sgc) / (1.0 - g_props.Sgc - g_props.Swi - g_props.Sor);
    Sw_norm = clamp01_T(Sw_norm);
    Sg_norm = clamp01_T(Sg_norm);

    krw = Sw_norm * Sw_norm;
    krg = Sg_norm * Sg_norm;
    T So_norm = clamp01_T(T(1.0) - Sw_norm - Sg_norm);
    kro = So_norm * So_norm;
}

struct GasPVTInterpResult {
    double y = 0.0;
    double slope = 0.0;   // dy/dP, 单位随 y 而定
};

struct GasPVTTable {
    std::vector<double> P_bar;
    std::vector<double> Z;
    std::vector<double> Cg;
    std::vector<double> Bg;
    std::vector<double> mu_g;

    double Pmin_bar = 1.0;
    double Pmax_bar = 1000.0;
    int n = 2000;
    bool ready = false;
};

// =============================================================================
// 10. 模拟器类
// =============================================================================

class Simulator {
public:
    // --- 基础数据 ---
    int Nx, Ny, Nz;
    double Lx, Ly, Lz;
    double dx, dy, dz;
    // 真实 corner-point grid 的全局包围盒
    // 注意：Lx/Ly/Lz 只是尺寸，不一定代表坐标从 0 开始。
    // grid_bbox_min / grid_bbox_max 才是真实空间坐标范围。
    Point3 grid_bbox_min{0, 0, 0};
    Point3 grid_bbox_max{0, 0, 0};
    bool grid_bbox_ready = false;
    std::vector<Cell> cells;
    std::vector<Fracture> fractures;
    std::vector<Segment> segments;
    std::vector<FaceGeom> faces;

    // --- 拓扑连接优化 ---
    std::vector<Connection> connections;

    struct Neighbor {
        int v;       // 邻居节点索引
        double T;    // 传导率
        int conn_idx; // 在全局 connections 中的下标
    };
    std::vector<std::vector<Neighbor>> adj;

    // 状态量
    int n_matrix;
    int n_frac_nodes;
    int n_total;

    std::vector<State> states;
    std::vector<State> states_prev;

    struct Well {
        int target_node_idx;
        double WI;
        double P_bhp;
    };
    std::vector<Well> wells;

    // 井的快速查找：well_map[node_idx] -> well_idx
    std::map<int, int> well_map;

    SparseMatrix<double> J;

    // 气相真实气体 PVT 查表（从 basic-PVT 迁移；buildGasPVTTable() 只调用一次）
    GasPVTTable gas_pvt_table;

    enum FMMNodeType {
        NODE_MATRIX = 0,
        NODE_FRACTURE = 1
    };

    enum FMMEdgeType {
        EDGE_MM = 0,
        EDGE_MF = 1,
        EDGE_FF_INTRA = 2,
        EDGE_FF_CROSS = 3
    };

    enum FMMStatus {
        FAR = 0,
        TRIAL = 1,
        ACCEPTED = 2
    };

    struct FMMEdge {
        int from = -1;
        int to = -1;
        int type = -1;
        int face_id = -1;   // MM 时使用
        double d_mf = 0.0;  // MF 时使用
        double L1 = 0.0;    // FF 时使用
        double L2 = 0.0;    // FF 时使用
        double ell_int = 0.0;
    };

    // ---------- 静态 FMM / DTOF / VOI ----------
    std::vector<int> fmm_node_type;
    std::vector<FMMEdge> fmm_edges;
    std::vector<std::vector<int>> fmm_adj;
    std::vector<double> tau_fmm;
    std::vector<double> tin_fmm;
    std::vector<int> fmm_state;
    std::vector<double> eta_node_ref;
    std::vector<double> eta_matrix_ref;
    std::vector<double> lambda_tot_ref;

    double beta_fmm = 0.00853;   // 第一版：沿论文单位换算因子，在压力为bar
    double Ct_ref_matrix = 1e-3; // 第一版简化假设
    double Ct_ref_frac   = 1e-3; // 第一版简化假设
    double phi_f_ref     = 0.5;  // 第一版简化假设
    double c_voi         = 6.0;
    double eta_ref       = 1.0;
    const double matrix_phi = 0.2;
    const double matrix_kx  = 0.005;
    const double matrix_ky  = 0.005;
    const double matrix_kz  = 0.005;

    // ---------- 当前时间步 Active 子系统 ----------
    std::vector<char> active_nodes;//全局节点是否活跃
    std::vector<int> active_local_id;        // global -> local，全局编号 → 当前活跃局部编号
    std::vector<int> active_local_to_global; // local -> global，当前活跃局部编号 → 全局编号
    std::vector<int> active_conn_indices; //当前时间步允许装配的连接
    int n_active = 0; //活跃总数
    int n_active_matrix = 0; //活跃基质数
    int n_active_frac = 0;//活跃裂缝数

    Simulator() {
        Lx = 3000; Ly = 300; Lz = 40;
        Nx = 150; Ny = 15; Nz = 2;
        dx = Lx / Nx; dy = Ly / Ny; dz = Lz / Nz;
        n_matrix = 0;
        n_frac_nodes = 0;
        n_total = 0;
    }

    int getNextFractureId() const {
        int max_id = -1;
        for (const auto& f : fractures) {
            max_id = std::max(max_id, f.id);
        }
        return max_id + 1;
    }

    static std::array<double, 11> gasDeviationCoeffs() {
        return {0.3265, -1.07, -0.5339, 0.01569, -0.05165,
                0.5475, -0.7361, 0.1844, 0.1056, 0.6134, 0.7210};
    }

    static std::array<double, 16> gasViscosityCoeffs() {
        return {-2.46211820,  2.97054714,  -0.286264054,  8.05420522e-3,
                 2.80860949, -3.49803305,   0.360373020, -0.0104432413,
                -0.793385684, 1.39643306,  -0.149144925,  4.41015512e-3,
                 0.0839387178,-0.186408848,  0.0203367881,-6.09579263e-4};
    }

    double clampGasTablePressure(double P_bar) const {
        if (gas_pvt_table.ready) {
            return std::max(gas_pvt_table.Pmin_bar, std::min(P_bar, gas_pvt_table.Pmax_bar));
        }
        return std::max(g_props.gas_table_Pmin_bar, std::min(P_bar, g_props.gas_table_Pmax_bar));
    }

    // deviation.m：先牛顿求 rhor，再算 Z
    double calcGasZReal(double P_bar) const {
        const auto A = gasDeviationCoeffs();

        GasMixturePseudoProps mix = computeGasMixturePseudoProps();
        double P_use = std::max(P_bar, 1e-12);
        double Tr = g_props.gas_T_K / mix.Tpc_K;
        double Pr = P_use / mix.Ppc_bar;

        double rhor = std::max(1e-12, 0.27 * Pr / Tr);

        for (int k = 0; k < 100; ++k) {
            double term2 = (A[0] + A[1]/Tr + A[2]/std::pow(Tr, 3.0) + A[3]/std::pow(Tr, 4.0) + A[4]/std::pow(Tr, 5.0));
            double term3 = (A[5] + A[6]/Tr + A[7]/(Tr*Tr));
            double exp_term = std::exp(-A[10] * rhor * rhor);

            double F =
                -0.27 * Pr / Tr
                + rhor
                + term2 * rhor * rhor
                + term3 * rhor * rhor * rhor
                - A[8] * (A[6]/Tr + A[7]/(Tr*Tr)) * std::pow(rhor, 6.0)
                + A[9] * (1.0 + A[10] * rhor * rhor) * (std::pow(rhor, 3.0) / std::pow(Tr, 3.0)) * exp_term;

            double dF =
                1.0
                + 2.0 * term2 * rhor
                + 3.0 * term3 * rhor * rhor
                - 6.0 * A[8] * (A[6]/Tr + A[7]/(Tr*Tr)) * std::pow(rhor, 5.0)
                + (A[9] / std::pow(Tr, 3.0))
                  * (3.0 * rhor * rhor + A[10] * (3.0 * std::pow(rhor, 4.0) - 2.0 * A[10] * std::pow(rhor, 6.0)))
                  * exp_term;

            if (!std::isfinite(F) || !std::isfinite(dF) || std::abs(dF) < 1e-14) {
                break;
            }

            double dr = F / dF;
            rhor -= dr;
            rhor = std::max(rhor, 1e-12);

            if (std::abs(F) < 1e-10) {
                break;
            }
        }

        double Z = 0.27 * Pr / std::max(rhor * Tr, 1e-12);
        if (!std::isfinite(Z) || Z <= 0.0) Z = 1.0;
        return Z;
    }

    // cg.m：先由 Z 计算 rhor，再按原式求 Cg，单位保持为 1/bar
    double calcGasCgReal(double P_bar, double Z) const {
        const auto A = gasDeviationCoeffs();

        GasMixturePseudoProps mix = computeGasMixturePseudoProps();
        double P_use = std::max(P_bar, 1e-12);
        double Tr = g_props.gas_T_K / mix.Tpc_K;
        double Pr = P_use / mix.Ppc_bar;
        double Z_use = std::max(Z, 1e-12);

        double rhor = 0.27 * Pr / (Z_use * Tr);

        double Int_A =
            A[0] + A[1]/Tr + A[2]/std::pow(Tr, 3.0) + A[3]/std::pow(Tr, 4.0) + A[4]/std::pow(Tr, 5.0)
            + 2.0 * (A[5] + A[6]/Tr + A[7]/(Tr*Tr)) * rhor
            - 5.0 * A[8] * (A[6]/Tr + A[7]/(Tr*Tr)) * std::pow(rhor, 4.0)
            + 2.0 * A[9] * (rhor + A[10] * std::pow(rhor, 3.0) - std::pow(A[10], 2.0) * std::pow(rhor, 5.0))
              * std::exp(-A[10] * rhor * rhor) / std::pow(Tr, 3.0);

        double denom = 1.0 + Pr * Int_A / Z_use;
        if (std::abs(denom) < 1e-12) {
            denom = (denom >= 0.0) ? 1e-12 : -1e-12;
        }

        double Cg = (1.0 / std::max(Pr, 1e-12)
                    - 0.27 * (Int_A / denom) / (Z_use * Z_use * Tr)) / mix.Ppc_bar;

        if (!std::isfinite(Cg) || Cg <= 0.0) Cg = std::max(g_props.cg, 1e-12);
        return Cg;
    }

        // Bg = Z * (T / Tsc) * (Psc / P)
    // 这里采用 20°C 工程标准：Tsc = 293.15 K
    // 压力单位统一为 bar，Psc 也用 bar
    double calcGasBgReal(double P_bar, double Z) const {
        const double Tsc_K = 293.15;                  // 20°C 工程标准
        const double T_K   = 273.15 + g_props.gas_t_C; // 地层温度，K

        double P_use = std::max(P_bar, 1e-12);
        double Z_use = std::max(Z, 1e-12);

        double Bg = Z_use * (T_K / Tsc_K) * (g_props.gas_Psc_bar / P_use);

        if (!std::isfinite(Bg) || Bg <= 0.0) {
            Bg = 1e-12;
        }
        return Bg;
    }

    // viscosity.m：输出单位为 mPa*s，而 1 mPa*s = 1 cP
    // 因此可直接作为当前程序中的 cP 使用
    double calcGasMuReal(double P_bar, double Z_unused = 1.0) const {
        (void)Z_unused;
        const auto A = gasViscosityCoeffs();

        GasMixturePseudoProps mix = computeGasMixturePseudoProps();
        double P_use = std::max(P_bar, 1e-12);
        double gamma_g = mix.Mmix / 28.97; // 气体相对密度，不是组分摩尔分数
        double Tr = g_props.gas_T_K / mix.Tpc_K;
        double Pr = P_use / mix.Ppc_bar;

        // 按 MATLAB 原式逐项对应实现
        double muo1 = (1.709e-5 - 2.062e-6 * gamma_g) * (1.8 * g_props.gas_T_K + 32.0)
                    + 8.118e-3 - 6.15e-3 * std::log10(gamma_g);

        double Int_A =
            A[0] + A[1]*Pr + A[2]*Pr*Pr + A[3]*Pr*Pr*Pr
            + Tr * (A[4] + A[5]*Pr + A[6]*Pr*Pr + A[7]*Pr*Pr*Pr)
            + Tr*Tr * (A[8] + A[9]*Pr + A[10]*Pr*Pr + A[11]*Pr*Pr*Pr)
            + Tr*Tr*Tr * (A[12] + A[13]*Pr + A[14]*Pr*Pr + A[15]*Pr*Pr*Pr);

        double mu_g_cp = muo1 * std::exp(Int_A) / Tr;
        if (!std::isfinite(mu_g_cp) || mu_g_cp <= 0.0) {
            mu_g_cp = std::max(g_props.mu_g, 1e-12);
        }
        return mu_g_cp;
    }

    GasPVTInterpResult interpGasTable1D(const std::vector<double>& x,
                                        const std::vector<double>& y,
                                        double xq) const {
        GasPVTInterpResult r;
        if (x.empty() || y.empty() || x.size() != y.size()) {
            return r;
        }
        if (x.size() == 1) {
            r.y = y[0];
            r.slope = 0.0;
            return r;
        }

        if (xq <= x.front()) {
            r.y = y.front();
            r.slope = 0.0; // 端点钳制：超出表范围时导数返回 0
            return r;
        }
        if (xq >= x.back()) {
            r.y = y.back();
            r.slope = 0.0; // 端点钳制：超出表范围时导数返回 0
            return r;
        }

        auto it = std::lower_bound(x.begin(), x.end(), xq);
        size_t i1 = std::distance(x.begin(), it);
        size_t i0 = i1 - 1;

        double x0 = x[i0], x1 = x[i1];
        double y0 = y[i0], y1 = y[i1];

        double dx = x1 - x0;
        if (std::abs(dx) < 1e-14) {
            r.y = y0;
            r.slope = 0.0;
            return r;
        }

        double t = (xq - x0) / dx;
        r.y = y0 + (y1 - y0) * t;
        r.slope = (y1 - y0) / dx;
        return r;
    }

    template <typename T>
    T liftInterpToAD(const T& P, double y_val, double slope) const {
        double P_val = scalarValue(P);
        // 关键：y = y_val + slope * (P - P_val)
        // 对 double，自动退化成常数；
        // 对 AutoDiff，可把线性插值局部斜率作为一阶导数回传。
        return T(y_val) + T(slope) * (P - T(P_val));
    }

    template <typename T>
    void calcGasPVT_fromTable(const T& P, T& Zg, T& Cg, T& Bg, T& mu_g) const {
        if (!gas_pvt_table.ready) {
            throw std::runtime_error("Gas PVT table is not ready. Call buildGasPVTTable() before getProps()/preprocessStaticFMM()/run().");
        }
        double P_val_raw = scalarValue(P);
        double P_val = clampGasTablePressure(std::max(P_val_raw, 1e-12));

        GasPVTInterpResult rz  = interpGasTable1D(gas_pvt_table.P_bar, gas_pvt_table.Z,    P_val);
        GasPVTInterpResult rcg = interpGasTable1D(gas_pvt_table.P_bar, gas_pvt_table.Cg,   P_val);
        GasPVTInterpResult rbg = interpGasTable1D(gas_pvt_table.P_bar, gas_pvt_table.Bg,   P_val);
        GasPVTInterpResult rmu = interpGasTable1D(gas_pvt_table.P_bar, gas_pvt_table.mu_g, P_val);

        // 若原始压力超出表范围，则采用端点钳制，导数置 0
        if (P_val_raw <= gas_pvt_table.Pmin_bar || P_val_raw >= gas_pvt_table.Pmax_bar) {
            rz.slope = rcg.slope = rbg.slope = rmu.slope = 0.0;
        }

        Zg   = liftInterpToAD(P, rz.y,  rz.slope);
        Cg   = liftInterpToAD(P, rcg.y, rcg.slope);
        Bg   = liftInterpToAD(P, rbg.y, rbg.slope);
        mu_g = liftInterpToAD(P, rmu.y, rmu.slope);
    }

    void exportGasPVTTableCSV(const std::string& filename = "gas_pvt_table.csv") const {
        if (!gas_pvt_table.ready) return;

        std::ofstream fout(filename);
        fout << "P_bar,Z,Cg_1_per_bar,Bg,mu_g_cp\n";
        fout << std::setprecision(16);
        for (size_t i = 0; i < gas_pvt_table.P_bar.size(); ++i) {
            fout << gas_pvt_table.P_bar[i] << ","
                 << gas_pvt_table.Z[i] << ","
                 << gas_pvt_table.Cg[i] << ","
                 << gas_pvt_table.Bg[i] << ","
                 << gas_pvt_table.mu_g[i] << "\n";
        }
    }

    void buildGasPVTTable() {
        validateGasMoleFractions();
        GasMixturePseudoProps mix = computeGasMixturePseudoProps();

        std::cout << "Gas mixture pseudo properties: "
                  << "Tpc = " << mix.Tpc_K << " K, "
                  << "Ppc = " << mix.Ppc_bar << " bar, "
                  << "Mmix = " << mix.Mmix << std::endl;

        gas_pvt_table.Pmin_bar = std::max(1e-6, g_props.gas_table_Pmin_bar);
        gas_pvt_table.Pmax_bar = std::max(gas_pvt_table.Pmin_bar + 1e-6, g_props.gas_table_Pmax_bar);
        gas_pvt_table.n = std::max(2, g_props.gas_table_n);

        gas_pvt_table.P_bar.resize(gas_pvt_table.n);
        gas_pvt_table.Z.resize(gas_pvt_table.n);
        gas_pvt_table.Cg.resize(gas_pvt_table.n);
        gas_pvt_table.Bg.resize(gas_pvt_table.n);
        gas_pvt_table.mu_g.resize(gas_pvt_table.n);

        double dP = (gas_pvt_table.Pmax_bar - gas_pvt_table.Pmin_bar) / (double)(gas_pvt_table.n - 1);

        for (int i = 0; i < gas_pvt_table.n; ++i) {
            double P = gas_pvt_table.Pmin_bar + i * dP;

            double Z  = calcGasZReal(P);
            double Cg = calcGasCgReal(P, Z);
            double Bg = calcGasBgReal(P, Z);
            double mu = calcGasMuReal(P, Z);

            gas_pvt_table.P_bar[i] = P;
            gas_pvt_table.Z[i] = Z;
            gas_pvt_table.Cg[i] = Cg;
            gas_pvt_table.Bg[i] = Bg;
            gas_pvt_table.mu_g[i] = mu;
        }

        gas_pvt_table.ready = true;
        //exportGasPVTTableCSV();

        std::cout << "Gas PVT table built successfully: ["
                  << gas_pvt_table.Pmin_bar << ", "
                  << gas_pvt_table.Pmax_bar << "] bar, n="
                  << gas_pvt_table.n << std::endl;
    }

    // =========================================================================
    // 10.1 读取 COORD.csv
    // =========================================================================
    bool loadCOORD(const std::string& filename,
                   std::vector<Pillar>& pillars,
                   int& coord_max_i,
                   int& coord_max_j) const {
        std::ifstream fin(filename);
        if (!fin.is_open()) {
            std::cerr << "Error: cannot open COORD file: " << filename << std::endl;
            return false;
        }

        std::string line;
        int line_no = 0;

        // 跳过首行表头
        if (!std::getline(fin, line)) {
            std::cerr << "Error: COORD file is empty: " << filename << std::endl;
            return false;
        }
        line_no++;

        std::vector<CoordRow> rows;
        coord_max_i = 0;
        coord_max_j = 0;

        while (std::getline(fin, line)) {
            line_no++;

            line = trim(line);
            if (line.empty()) continue;

            std::vector<std::string> cols = splitCSVSimple(line);
            if (cols.size() < 6) {
                std::cerr << "Error: COORD line " << line_no
                          << " has fewer than 6 columns." << std::endl;
                return false;
            }

            int i1 = 0, j1 = 0;
            double x = 0.0, y = 0.0, z = 0.0;

            if (!parseIntStrict(cols[0], i1) || !parseIntStrict(cols[1], j1)) {
                std::cerr << "Error: COORD line " << line_no
                          << " failed to parse X(I)/Y(J)." << std::endl;
                return false;
            }
            if (i1 <= 0 || j1 <= 0) {
                std::cerr << "Error: COORD line " << line_no
                          << " has non-positive pillar index." << std::endl;
                return false;
            }

            bool is_top = false;
            bool is_bot = false;
            if (isTopMarker(cols[2])) {
                is_top = true;
            } else if (isBottomMarker(cols[2])) {
                is_bot = true;
            } else {
                std::cerr << "Error: COORD line " << line_no
                          << " has invalid Z(K) marker: " << cols[2]
                          << " , expected 顶/底 or top/bottom." << std::endl;
                return false;
            }

            if (!parseDoubleStrict(cols[3], x) ||
                !parseDoubleStrict(cols[4], y) ||
                !parseDoubleStrict(cols[5], z)) {
                std::cerr << "Error: COORD line " << line_no
                          << " failed to parse 坐标X/坐标Y/坐标Z." << std::endl;
                return false;
            }

            CoordRow r;
            r.i = i1 - 1; // 文件从 1 开始，内部转 0-based
            r.j = j1 - 1;
            r.is_top = is_top;
            r.p = {x, y, z};

            rows.push_back(r);

            coord_max_i = std::max(coord_max_i, i1);
            coord_max_j = std::max(coord_max_j, j1);
        }

        if (rows.empty()) {
            std::cerr << "Error: COORD file contains no data rows." << std::endl;
            return false;
        }

        pillars.assign(coord_max_i * coord_max_j, Pillar{});

        // 回填每根 pillar 的 top / bottom
        for (const auto& r : rows) {
            int idx = flatPillarIndex(r.i, r.j, coord_max_i);
            Pillar& p = pillars[idx];

            if (r.is_top) {
                if (p.has_top) {
                    std::cerr << "Error: duplicate TOP record for pillar("
                              << (r.i + 1) << "," << (r.j + 1) << ")." << std::endl;
                    return false;
                }
                p.top = r.p;
                p.has_top = true;
            } else {
                if (p.has_bot) {
                    std::cerr << "Error: duplicate BOTTOM record for pillar("
                              << (r.i + 1) << "," << (r.j + 1) << ")." << std::endl;
                    return false;
                }
                p.bot = r.p;
                p.has_bot = true;
            }
        }

        // 完整性检查
        for (int j = 0; j < coord_max_j; ++j) {
            for (int i = 0; i < coord_max_i; ++i) {
                const Pillar& p = pillars[flatPillarIndex(i, j, coord_max_i)];

                if (!p.has_top || !p.has_bot) {
                    std::cerr << "Error: pillar(" << (i + 1) << "," << (j + 1)
                              << ") missing "
                              << ((!p.has_top && !p.has_bot) ? "top and bottom" :
                                  (!p.has_top ? "top" : "bottom"))
                              << " record." << std::endl;
                    return false;
                }

                if (std::abs(p.bot.z - p.top.z) < EPSILON) {
                    std::cerr << "Error: pillar(" << (i + 1) << "," << (j + 1)
                              << ") has Z_top == Z_bottom, cannot interpolate." << std::endl;
                    return false;
                }

                // 本项目约定：顶的 Z 更大，底的 Z 更小
                if (!(p.top.z > p.bot.z)) {
                    std::cerr << "Error: pillar(" << (i + 1) << "," << (j + 1)
                              << ") violates height convention: Z_top must be > Z_bottom."
                              << std::endl;
                    return false;
                }
            }
        }

        return true;
    }

    // =========================================================================
    // 10.2 读取 ZCORN.csv
    // =========================================================================
    bool loadZCORN(const std::string& filename,
                   std::vector<std::array<double, 8>>& zcorn_cells,
                   int& zcorn_max_i,
                   int& zcorn_max_j,
                   int& zcorn_max_k) const {
        std::ifstream fin(filename);
        if (!fin.is_open()) {
            std::cerr << "Error: cannot open ZCORN file: " << filename << std::endl;
            return false;
        }

        std::string line;
        int line_no = 0;

        // 跳过首行表头
        if (!std::getline(fin, line)) {
            std::cerr << "Error: ZCORN file is empty: " << filename << std::endl;
            return false;
        }
        line_no++;

        std::vector<ZCornRow> rows;
        zcorn_max_i = 0;
        zcorn_max_j = 0;
        zcorn_max_k = 0;

        while (std::getline(fin, line)) {
            line_no++;

            line = trim(line);
            if (line.empty()) continue;

            std::vector<std::string> cols = splitCSVSimple(line);
            if (cols.size() < 11) {
                std::cerr << "Error: ZCORN line " << line_no
                          << " has fewer than 11 columns." << std::endl;
                return false;
            }

            int i1 = 0, j1 = 0, k1 = 0;
            if (!parseIntStrict(cols[0], i1) ||
                !parseIntStrict(cols[1], j1) ||
                !parseIntStrict(cols[2], k1)) {
                std::cerr << "Error: ZCORN line " << line_no
                          << " failed to parse X(I)/Y(J)/Z(K)." << std::endl;
                return false;
            }

            if (i1 <= 0 || j1 <= 0 || k1 <= 0) {
                std::cerr << "Error: ZCORN line " << line_no
                          << " has non-positive cell index." << std::endl;
                return false;
            }

            ZCornRow zr;
            zr.i = i1 - 1; // 转 0-based
            zr.j = j1 - 1;
            zr.k = k1 - 1;

            for (int t = 0; t < 8; ++t) {
                if (!parseDoubleStrict(cols[3 + t], zr.z[t])) {
                    std::cerr << "Error: ZCORN line " << line_no
                              << " failed to parse Z" << (t + 1) << "." << std::endl;
                    return false;
                }
            }

            // 高度坐标约定：顶面四点 Z 应大于底面四点 Z
            if (!(zr.z[0] > zr.z[4] &&
                  zr.z[1] > zr.z[5] &&
                  zr.z[2] > zr.z[6] &&
                  zr.z[3] > zr.z[7])) {
                std::cerr << "Error: ZCORN line " << line_no
                          << " violates height convention: top Z must be greater than bottom Z."
                          << std::endl;
                return false;
            }

            rows.push_back(zr);

            zcorn_max_i = std::max(zcorn_max_i, i1);
            zcorn_max_j = std::max(zcorn_max_j, j1);
            zcorn_max_k = std::max(zcorn_max_k, k1);
        }

        if (rows.empty()) {
            std::cerr << "Error: ZCORN file contains no data rows." << std::endl;
            return false;
        }

        int total_cells = zcorn_max_i * zcorn_max_j * zcorn_max_k;
        zcorn_cells.assign(total_cells, std::array<double, 8>{{0, 0, 0, 0, 0, 0, 0, 0}});
        std::vector<char> seen(total_cells, 0);

        for (const auto& zr : rows) {
            int idx = flatCellIndex(zr.i, zr.j, zr.k, zcorn_max_i, zcorn_max_j);

            if (seen[idx]) {
                std::cerr << "Error: duplicate ZCORN record for cell("
                          << (zr.i + 1) << "," << (zr.j + 1) << "," << (zr.k + 1)
                          << ")." << std::endl;
                return false;
            }

            seen[idx] = 1;
            zcorn_cells[idx] = zr.z;
        }

        // 检查缺失 cell
        for (int k = 0; k < zcorn_max_k; ++k) {
            for (int j = 0; j < zcorn_max_j; ++j) {
                for (int i = 0; i < zcorn_max_i; ++i) {
                    int idx = flatCellIndex(i, j, k, zcorn_max_i, zcorn_max_j);
                    if (!seen[idx]) {
                        std::cerr << "Error: missing ZCORN record for cell("
                                  << (i + 1) << "," << (j + 1) << "," << (k + 1)
                                  << ")." << std::endl;
                        return false;
                    }
                }
            }
        }

        return true;
    }

    // =========================================================================
    // 10.3 pillar 直线插值
    // =========================================================================
    Point3 interpolateOnPillar(const Pillar& p, double zc) const {
        if (!p.has_top || !p.has_bot) {
            throw std::runtime_error("pillar missing top or bottom endpoint.");
        }

        double zt = p.top.z;
        double zb = p.bot.z;
        double denom = zb - zt;

        if (std::abs(denom) < EPSILON) {
            throw std::runtime_error("pillar has Z_top == Z_bottom, cannot interpolate.");
        }

        // 题目要求的插值公式：
        // lambda = (Zc - Zt) / (Zb - Zt)
        // Pc = Ptop + lambda * (Pbot - Ptop)
        double lambda = (zc - zt) / denom;

        Point3 pc = p.top + (p.bot - p.top) * lambda;

        // 数值上强制回写目标 Z，避免浮点误差
        pc.z = zc;
        return pc;
    }

    // =========================================================================
    // 10.4 从 COORD.csv + ZCORN.csv 初始化 corner-point grid
    // =========================================================================
    bool initGridFromCornerPointCSV(const std::string& coordFile,
                                    const std::string& zcornFile) {
        // 清空旧网格相关数据
        cells.clear();
        faces.clear();
        fractures.clear();
        segments.clear();
        connections.clear();
        wells.clear();
        well_map.clear();
        states.clear();
        states_prev.clear();
        adj.clear();

        std::vector<Pillar> pillars;
        std::vector<std::array<double, 8>> zcorn_cells;

        int coord_max_i = 0, coord_max_j = 0;
        int zcorn_max_i = 0, zcorn_max_j = 0, zcorn_max_k = 0;

        // 1) 读取 COORD.csv，恢复 pillar
        if (!loadCOORD(coordFile, pillars, coord_max_i, coord_max_j)) {
            std::cerr << "Error: failed to load COORD file." << std::endl;
            return false;
        }

        // 2) 读取 ZCORN.csv，恢复每个 cell 的 Z1~Z8
        if (!loadZCORN(zcornFile, zcorn_cells, zcorn_max_i, zcorn_max_j, zcorn_max_k)) {
            std::cerr << "Error: failed to load ZCORN file." << std::endl;
            return false;
        }

        // 3) 一致性检查
        if (coord_max_i != zcorn_max_i + 1) {
            std::cerr << "Error: inconsistent grid size in I direction: "
                      << "COORD max I = " << coord_max_i
                      << ", but ZCORN max I = " << zcorn_max_i
                      << " , expected COORD max I = ZCORN max I + 1." << std::endl;
            return false;
        }

        if (coord_max_j != zcorn_max_j + 1) {
            std::cerr << "Error: inconsistent grid size in J direction: "
                      << "COORD max J = " << coord_max_j
                      << ", but ZCORN max J = " << zcorn_max_j
                      << " , expected COORD max J = ZCORN max J + 1." << std::endl;
            return false;
        }

        // 4) 自动推断网格尺寸
        Nx = zcorn_max_i;
        Ny = zcorn_max_j;
        Nz = zcorn_max_k;

        n_matrix = Nx * Ny * Nz;
        n_frac_nodes = 0;
        n_total = n_matrix;

        cells.resize(n_matrix);

        auto getPillar = [&](int i, int j) -> const Pillar& {
            if (i < 0 || i >= coord_max_i || j < 0 || j >= coord_max_j) {
                std::ostringstream oss;
                oss << "pillar index out of range: (" << (i + 1) << "," << (j + 1) << ")";
                throw std::runtime_error(oss.str());
            }
            return pillars[flatPillarIndex(i, j, coord_max_i)];
        };

        try {
            // 5) 逐个 cell 构造 8 个完整三维角点
            for (int k = 0; k < Nz; ++k) {
                for (int j = 0; j < Ny; ++j) {
                    for (int i = 0; i < Nx; ++i) {
                        int id = flatCellIndex(i, j, k, Nx, Ny);

                        Cell c;
                        c.id = id;
                        c.ix = i;
                        c.iy = j;
                        c.iz = k;

                        // 当前 cell 对应四根 pillar：
                        // 左下：pillar(i, j)
                        // 右下：pillar(i+1, j)
                        // 左上：pillar(i, j+1)
                        // 右上：pillar(i+1, j+1)
                        const Pillar& p_ll = getPillar(i,     j    ); // 左下
                        const Pillar& p_lr = getPillar(i + 1, j    ); // 右下
                        const Pillar& p_ul = getPillar(i,     j + 1); // 左上
                        const Pillar& p_ur = getPillar(i + 1, j + 1); // 右上

                        // 取出当前 cell 的 Z1~Z8
                        const auto& z = zcorn_cells[id];
                        // z[0]=Z1, z[1]=Z2, ..., z[7]=Z8

                        // --------------------------------------------------------
                        // 严格按你的要求做 ZCORN -> corners[0..7] 映射：
                        //
                        // ZCORN 顶面/底面顺序：
                        // 顶面：Z1 Z2 Z3 Z4 = 左下 右下 左上 右上
                        // 底面：Z5 Z6 Z7 Z8 = 左下 右下 左上 右上
                        //
                        // 现有代码的 corners 顺序必须保持为：
                        // 底面：左下、右下、右上、左上
                        // 顶面：左下、右下、右上、左上
                        //
                        // 所以：
                        // corner[0] <- Z5 on 左下 pillar
                        // corner[1] <- Z6 on 右下 pillar
                        // corner[2] <- Z8 on 右上 pillar
                        // corner[3] <- Z7 on 左上 pillar
                        // corner[4] <- Z1 on 左下 pillar
                        // corner[5] <- Z2 on 右下 pillar
                        // corner[6] <- Z4 on 右上 pillar
                        // corner[7] <- Z3 on 左上 pillar
                        //
                        // 即：
                        // corners = [Z5, Z6, Z8, Z7, Z1, Z2, Z4, Z3]
                        // --------------------------------------------------------

                        c.corners[0] = interpolateOnPillar(p_ll, z[4]); // Z5
                        c.corners[1] = interpolateOnPillar(p_lr, z[5]); // Z6
                        c.corners[2] = interpolateOnPillar(p_ur, z[7]); // Z8
                        c.corners[3] = interpolateOnPillar(p_ul, z[6]); // Z7

                        c.corners[4] = interpolateOnPillar(p_ll, z[0]); // Z1
                        c.corners[5] = interpolateOnPillar(p_lr, z[1]); // Z2
                        c.corners[6] = interpolateOnPillar(p_ur, z[3]); // Z4
                        c.corners[7] = interpolateOnPillar(p_ul, z[2]); // Z3

                        // 物性参数沿用原代码默认值
                        c.phi = matrix_phi;
                        c.K[0] = matrix_kx;
                        c.K[1] = matrix_ky;
                        c.K[2] = matrix_kz;

                        // 用现有几何函数反算 center / bbox / vol / depth
                        computeCellDerivedGeometry(c);

                        cells[id] = c;
                    }
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "Error while constructing corner-point cells: "
                      << e.what() << std::endl;
            return false;
        }

        // 6) 兼容后续仍会用到的 Lx/Ly/Lz/dx/dy/dz，
        //    这里用全局 bbox 给出一个名义值
        if (!cells.empty()) {
            Point3 gmin = cells[0].bbox_min;
            Point3 gmax = cells[0].bbox_max;

            for (const auto& c : cells) {
                gmin = pointMin(gmin, c.bbox_min);
                gmax = pointMax(gmax, c.bbox_max);
            }

            // 保存真实 corner-point grid 的全局坐标范围
            grid_bbox_min = gmin;
            grid_bbox_max = gmax;
            grid_bbox_ready = true;

            // Lx/Ly/Lz 仍然作为名义尺寸保留
            Lx = gmax.x - gmin.x;
            Ly = gmax.y - gmin.y;
            Lz = gmax.z - gmin.z;

            dx = (Nx > 0) ? (Lx / Nx) : 0.0;
            dy = (Ny > 0) ? (Ly / Ny) : 0.0;
            dz = (Nz > 0) ? (Lz / Nz) : 0.0;
        } else {
            Lx = Ly = Lz = 0.0;
            dx = dy = dz = 0.0;

            grid_bbox_min = {0, 0, 0};
            grid_bbox_max = {0, 0, 0};
            grid_bbox_ready = false;
        }

        // 7) 构建全局 face 几何与 cell-face 映射
        buildGridFaces();

        std::cout << "Corner-point grid initialized from CSV successfully." << std::endl;
        std::cout << "Nx = " << Nx << ", Ny = " << Ny << ", Nz = " << Nz << std::endl;
        std::cout << "Pillars = " << coord_max_i << " x " << coord_max_j << std::endl;
        std::cout << "Cells = " << n_matrix << std::endl;

        return true;
    }

    // =========================================================================
    // 10.5 保留原 initGrid() 作为规则网格备用入口（可选）
    // =========================================================================
    void initGrid() {
        n_matrix = Nx * Ny * Nz;
        cells.resize(n_matrix);

        for (int k = 0; k < Nz; ++k) {
            for (int j = 0; j < Ny; ++j) {
                for (int i = 0; i < Nx; ++i) {
                    int id = k * Nx * Ny + j * Nx + i;

                    Cell c;
                    c.id = id;
                    c.ix = i;
                    c.iy = j;
                    c.iz = k;

                    // 规则网格的 8 个角点
                    double x0 = i * dx;
                    double x1 = (i + 1) * dx;
                    double y0 = j * dy;
                    double y1 = (j + 1) * dy;
                    double z0 = k * dz;
                    double z1 = (k + 1) * dz;

                    c.corners[0] = {x0, y0, z0};
                    c.corners[1] = {x1, y0, z0};
                    c.corners[2] = {x1, y1, z0};
                    c.corners[3] = {x0, y1, z0};
                    c.corners[4] = {x0, y0, z1};
                    c.corners[5] = {x1, y0, z1};
                    c.corners[6] = {x1, y1, z1};
                    c.corners[7] = {x0, y1, z1};

                    c.phi = matrix_phi;
                    c.K[0] = matrix_kx;
                    c.K[1] = matrix_ky;
                    c.K[2] = matrix_kz;

                    computeCellDerivedGeometry(c);

                    cells[id] = c;
                }
            }
        }

        buildGridFaces();
        grid_bbox_min = {0.0, 0.0, 0.0};
        grid_bbox_max = {Lx, Ly, Lz};
        grid_bbox_ready = true;
        n_frac_nodes = 0;
        n_total = n_matrix;
    }

    void buildGridFaces() {
        faces.clear();

        for (auto& c : cells) {
            c.face_ids = {{-1, -1, -1, -1, -1, -1}};
        }

        auto add_face = [&](int owner, int local_owner_face,
                            int neighbor, int local_neighbor_face) {
            FaceGeom f;
            f.id = (int)faces.size();
            f.owner = owner;
            f.neighbor = neighbor;
            f.local_owner_face = local_owner_face;
            f.local_neighbor_face = local_neighbor_face;

            f.vertices = getCellFaceVertices(cells[owner], local_owner_face);
            computeFaceDerivedGeometry(f, cells[owner].center);

            faces.push_back(f);

            cells[owner].face_ids[local_owner_face] = f.id;
            if (neighbor >= 0) {
                cells[neighbor].face_ids[local_neighbor_face] = f.id;
            }
        };

        for (int k = 0; k < Nz; ++k) {
            for (int j = 0; j < Ny; ++j) {
                for (int i = 0; i < Nx; ++i) {
                    int u = k * Nx * Ny + j * Nx + i;

                    // x- 边界面
                    if (i == 0) {
                        add_face(u, XM, -1, -1);
                    }
                    // y- 边界面
                    if (j == 0) {
                        add_face(u, YM, -1, -1);
                    }
                    // z- 边界面
                    if (k == 0) {
                        add_face(u, ZM, -1, -1);
                    }

                    // x+ 面：若有右邻居则创建内部面，否则创建边界面
                    if (i < Nx - 1) {
                        int v = u + 1;
                        add_face(u, XP, v, XM);
                    } else {
                        add_face(u, XP, -1, -1);
                    }

                    // y+ 面
                    if (j < Ny - 1) {
                        int v = u + Nx;
                        add_face(u, YP, v, YM);
                    } else {
                        add_face(u, YP, -1, -1);
                    }

                    // z+ 面
                    if (k < Nz - 1) {
                        int v = u + Nx * Ny;
                        add_face(u, ZP, v, ZM);
                    } else {
                        add_face(u, ZP, -1, -1);
                    }
                }
            }
        }
    }

    // 判断点是否落在某个 bbox 内，先用于快速粗筛
    bool pointInBBox(const Point3& p,
                    const Point3& bmin,
                    const Point3& bmax,
                    double tol = 1e-9) const {
        return (p.x >= bmin.x - tol && p.x <= bmax.x + tol &&
                p.y >= bmin.y - tol && p.y <= bmax.y + tol &&
                p.z >= bmin.z - tol && p.z <= bmax.z + tol);
    }

    // 判断点是否在某个真实 corner-point cell 内部
    // 核心思想：对该 cell 的 6 个真实面，点必须都在“面内侧”
    bool pointInsideCellByFaces(const Point3& p,
                                const Cell& cell,
                                double tol_factor = 1e-8) const {
        double scale = std::max(1.0, std::max(cell.dx, std::max(cell.dy, cell.dz)));
        double tol = tol_factor * scale;

        // 先用 cell bbox 粗筛，减少无意义的 face 判断
        if (!pointInBBox(p, cell.bbox_min, cell.bbox_max, tol)) {
            return false;
        }

        for (int lf = 0; lf < 6; ++lf) {
            Point3 n_in;
            double d = 0.0;

            // 复用你已有的函数：
            // n_in · x + d >= 0 表示在该 face 的 cell 内侧
            if (!getInwardPlaneForCellFace(cell, faces, lf, n_in, d)) {
                return false;
            }

            double s = n_in.dot(p) + d;

            // 如果点在某个面的外侧，说明不在这个 cell 内
            if (s < -tol) {
                return false;
            }
        }

        return true;
    }

    // 判断点是否在整个真实角点网格内部
    // 只要它落在任意一个 cell 内，就认为在储层内部
    bool pointInsideCornerPointGrid(const Point3& p) const {
        if (cells.empty()) return false;

        // 先用真实全局 bbox 粗筛
        if (grid_bbox_ready) {
            double gscale = std::max(1.0,
                            std::max(grid_bbox_max.x - grid_bbox_min.x,
                            std::max(grid_bbox_max.y - grid_bbox_min.y,
                                    grid_bbox_max.z - grid_bbox_min.z)));
            double gtol = 1e-8 * gscale;

            if (!pointInBBox(p, grid_bbox_min, grid_bbox_max, gtol)) {
                return false;
            }
        }

        // 再逐 cell 精确判断
        for (const auto& cell : cells) {
            if (pointInsideCellByFaces(p, cell)) {
                return true;
            }
        }

        return false;
    }

    // 严格判断天然裂缝四个顶点是否都在真实角点网格内部
    bool fractureFullyInsideCornerPointGrid(const Fracture& f) const {
        for (int i = 0; i < 4; ++i) {
            if (!pointInsideCornerPointGrid(f.vertices[i])) {
                return false;
            }
        }
        return true;
    }


    void generateFractures(int total_fracs = 100,
                           double min_L = 10.0, double max_L = 20.0,
                           double max_dip = PI/3.0,
                           double min_height=10.0,double max_height=20.0,
                           double min_strike = 0.0, double max_strike = PI,
                           double aperture_val = 0.1, double perm_val = 100.0,
                           double range_x_min = 0.0, double range_x_max = -1.0,
                           double range_y_min = 0.0, double range_y_max = -1.0,
                           double range_z_min = 0.0, double range_z_max = -1.0) {

        double default_x_min = grid_bbox_ready ? grid_bbox_min.x : 0.0;
        double default_y_min = grid_bbox_ready ? grid_bbox_min.y : 0.0;
        double default_z_min = grid_bbox_ready ? grid_bbox_min.z : 0.0;

        double default_x_max = grid_bbox_ready ? grid_bbox_max.x : Lx;
        double default_y_max = grid_bbox_ready ? grid_bbox_max.y : Ly;
        double default_z_max = grid_bbox_ready ? grid_bbox_max.z : Lz;

        double use_min_x = range_x_min;
        double use_min_y = range_y_min;
        double use_min_z = range_z_min;

        double use_max_x = (range_x_max < 0) ? default_x_max : range_x_max;
        double use_max_y = (range_y_max < 0) ? default_y_max : range_y_max;
        double use_max_z = (range_z_max < 0) ? default_z_max : range_z_max;

        // 如果用户没有显式给 range_x_min/y_min/z_min，默认应使用真实 grid bbox 的 min
        // 注意：你当前函数默认 range_x_min = 0.0，所以这里需要特殊处理。
        // 如果你的储层一定从 0 开始，这一步影响不大；如果不是从 0 开始，这一步很重要。
        if (grid_bbox_ready) {
            if (std::abs(range_x_min - 0.0) < 1e-12) use_min_x = default_x_min;
            if (std::abs(range_y_min - 0.0) < 1e-12) use_min_y = default_y_min;
            if (std::abs(range_z_min - 0.0) < 1e-12) use_min_z = default_z_min;
        }

        fractures.clear();

        std::mt19937 rng(42);
        std::uniform_real_distribution<double> distX(use_min_x, use_max_x);
        std::uniform_real_distribution<double> distY(use_min_y, use_max_y);
        std::uniform_real_distribution<double> distZ(use_min_z, use_max_z);
        std::uniform_real_distribution<double> distAngle(min_strike, max_strike);
        std::uniform_real_distribution<double> distDip(0, max_dip);
        std::uniform_real_distribution<double> distL(min_L, max_L);
        std::uniform_real_distribution<double> distheight(min_height, max_height);


        for (int i = 0; i < total_fracs; ++i) {
            Fracture f;
            f.id = i; // 天然裂缝从 0 开始连续编号
            f.aperture = aperture_val;
            f.perm = perm_val;
            f.is_hydraulic = false; // 明确标记为天然裂缝

            int tries = 0;
            while (true) {
                if (++tries > 200000) {
                    std::cerr << "Failed to place natural fracture " << i
                              << " fully inside domain. "
                              << "Consider reducing distL/distDip or enlarging domain.\n";
                    return;
                }

                Point3 center = {distX(rng), distY(rng), distZ(rng)};
                double len = distL(rng);
                double height = distheight(rng);
                double strike = distAngle(rng);
                double dip = distDip(rng);

                Point3 u = {cos(strike), sin(strike), 0};
                Point3 n_horiz = {-sin(strike), cos(strike), 0};
                Point3 v = {n_horiz.x * cos(dip), n_horiz.y * cos(dip), -sin(dip)};

                f.vertices[0] = center - u*(len/2) - v*(height/2);
                f.vertices[1] = center + u*(len/2) - v*(height/2);
                f.vertices[2] = center + u*(len/2) + v*(height/2);
                f.vertices[3] = center - u*(len/2) + v*(height/2);

                if (fractureFullyInsideCornerPointGrid(f)) {
                    fractures.push_back(f);
                    break;
                }
            }
        }
    }

    void generateHydraulicFractures(int total_fracs = 20,
                                    double frac_spacing = 100.0,
                                    double hf_len = 120.0,
                                    double hf_height = 30.0,
                                    double aperture_val = 0.1,
                                    double perm_val = 1000.0,
                                    double x_center = -1.0,
                                    double y_center = -1.0,
                                    double z_center = -1.0,
                                    int start_id = -1) {

        if (total_fracs <= 0) {
            std::cout << "No hydraulic fractures requested." << std::endl;
            return;
        }

        if (total_fracs > 1 && frac_spacing <= EPSILON) {
            std::cerr << "Invalid hydraulic fracture spacing: frac_spacing must be positive." << std::endl;
            return;
        }

        if (hf_len <= EPSILON || hf_height <= EPSILON) {
            std::cerr << "Invalid hydraulic fracture size: hf_len and hf_height must be positive." << std::endl;
            return;
        }

        // ------------------------------------------------------------
        // 1. 使用真实 corner-point grid 的全局 bbox 作为默认储层范围
        // ------------------------------------------------------------
        double x_min_domain = grid_bbox_ready ? grid_bbox_min.x : 0.0;
        double x_max_domain = grid_bbox_ready ? grid_bbox_max.x : Lx;

        double y_min_domain = grid_bbox_ready ? grid_bbox_min.y : 0.0;
        double y_max_domain = grid_bbox_ready ? grid_bbox_max.y : Ly;

        double z_min_domain = grid_bbox_ready ? grid_bbox_min.z : 0.0;
        double z_max_domain = grid_bbox_ready ? grid_bbox_max.z : Lz;

        double xc = (x_center < 0.0) ? 0.5 * (x_min_domain + x_max_domain) : x_center;
        double yc = (y_center < 0.0) ? 0.5 * (y_min_domain + y_max_domain) : y_center;
        double zc = (z_center < 0.0) ? 0.5 * (z_min_domain + z_max_domain) : z_center;

        // ------------------------------------------------------------
        // 2. 检查 y / z 方向的裂缝尺寸是否超出全局 bbox
        //    注意：后面还会用 fractureFullyInsideCornerPointGrid 做严格判断
        // ------------------------------------------------------------
        double y_min = yc - hf_len / 2.0;
        double y_max = yc + hf_len / 2.0;

        double z_min = zc - hf_height / 2.0;
        double z_max = zc + hf_height / 2.0;

        double domain_scale = std::max(1.0,
                            std::max(x_max_domain - x_min_domain,
                            std::max(y_max_domain - y_min_domain,
                                    z_max_domain - z_min_domain)));
        double tol = 1e-8 * domain_scale;

        if (y_min < y_min_domain - tol || y_max > y_max_domain + tol ||
            z_min < z_min_domain - tol || z_max > z_max_domain + tol) {
            std::cerr << "Hydraulic fracture geometry exceeds domain in y/z direction." << std::endl;
            std::cerr << "  y range = [" << y_min << ", " << y_max << "], domain = ["
                    << y_min_domain << ", " << y_max_domain << "]" << std::endl;
            std::cerr << "  z range = [" << z_min << ", " << z_max << "], domain = ["
                    << z_min_domain << ", " << z_max_domain << "]" << std::endl;
            return;
        }

        // ------------------------------------------------------------
        // 3. 按指定裂缝间距对称布置人工裂缝
        //
        //    核心公式：
        //    x_curr = xc + (k - 0.5 * (total_fracs - 1)) * frac_spacing
        //
        //    total_fracs = 5:
        //    xc - 2s, xc - s, xc, xc + s, xc + 2s
        //
        //    total_fracs = 4:
        //    xc - 1.5s, xc - 0.5s, xc + 0.5s, xc + 1.5s
        // ------------------------------------------------------------
        double total_span = (total_fracs > 1)
                            ? (total_fracs - 1) * frac_spacing
                            : 0.0;

        double x_first = xc - 0.5 * total_span;
        double x_last  = xc + 0.5 * total_span;

        if (x_first < x_min_domain - tol || x_last > x_max_domain + tol) {
            std::cerr << "Hydraulic fracture distribution exceeds domain in x direction." << std::endl;
            std::cerr << "  x_first = " << x_first << ", x_last = " << x_last << std::endl;
            std::cerr << "  domain x range = [" << x_min_domain << ", " << x_max_domain << "]" << std::endl;
            std::cerr << "  total_fracs = " << total_fracs
                    << ", frac_spacing = " << frac_spacing
                    << ", total_span = " << total_span << std::endl;
            return;
        }

        // 若未显式指定 start_id，则自动从当前已有裂缝编号之后开始
        int base_id = (start_id >= 0) ? start_id : getNextFractureId();

        // 先临时保存，全部检查通过后再 push 到 fractures
        // 避免中途失败时只生成一部分人工裂缝
        std::vector<Fracture> new_hydraulic_fracs;
        new_hydraulic_fracs.reserve(total_fracs);

        for (int k = 0; k < total_fracs; ++k) {
            Fracture f;
            f.id = base_id + k;
            f.aperture = aperture_val;
            f.perm = perm_val;
            f.is_hydraulic = true;

            double x_curr = xc;
            if (total_fracs > 1) {
                x_curr = xc + (k - 0.5 * (total_fracs - 1)) * frac_spacing;
            }

            // 裂缝面位于 x = x_curr，是垂直于 x 方向的 y-z 平面
            f.vertices[0] = {x_curr, yc - hf_len / 2.0,    zc - hf_height / 2.0};
            f.vertices[1] = {x_curr, yc + hf_len / 2.0,    zc - hf_height / 2.0};
            f.vertices[2] = {x_curr, yc + hf_len / 2.0,    zc + hf_height / 2.0};
            f.vertices[3] = {x_curr, yc - hf_len / 2.0,    zc + hf_height / 2.0};

            // 对 corner-point grid 做严格几何检查：
            // 四个顶点必须都在真实角点网格内部
            if (!fractureFullyInsideCornerPointGrid(f)) {
                std::cerr << "Hydraulic fracture " << f.id
                        << " is not fully inside the corner-point grid." << std::endl;
                std::cerr << "  x_curr = " << x_curr
                        << ", yc = " << yc
                        << ", zc = " << zc << std::endl;
                std::cerr << "  Consider reducing hf_len / hf_height / total_fracs / frac_spacing,"
                        << " or moving the fracture center." << std::endl;
                return;
            }

            new_hydraulic_fracs.push_back(f);
        }

        for (const auto& f : new_hydraulic_fracs) {
            fractures.push_back(f);
        }

        std::cout << "Generated " << total_fracs << " hydraulic fractures by spacing." << std::endl;
        std::cout << "  ID range: [" << base_id << ", "
                << (base_id + total_fracs - 1) << "]" << std::endl;
        std::cout << "  center = (" << xc << ", " << yc << ", " << zc << ")" << std::endl;
        std::cout << "  frac_spacing = " << frac_spacing << " m" << std::endl;
        std::cout << "  x_first = " << x_first << ", x_last = " << x_last << std::endl;
        std::cout << "  total fracture span = " << total_span << " m" << std::endl;
    }

    void processGeometry() {
        segments.clear();
        int seg_id_counter = 0;


        const double MIN_SEG_AREA = 0.001;


        for (const auto& frac : fractures) {
            // 1. fracture 自身 bbox
            Point3 fmin = frac.vertices[0];
            Point3 fmax = frac.vertices[0];
            for (int i = 1; i < 4; ++i) {
                fmin = pointMin(fmin, frac.vertices[i]);
                fmax = pointMax(fmax, frac.vertices[i]);
            }

            // 2. fracture 平面法向
            Point3 vec1 = frac.vertices[1] - frac.vertices[0];
            Point3 vec2 = frac.vertices[3] - frac.vertices[0];
            Point3 normal = vec1.cross(vec2);
            double nn = normal.norm();
            if (nn < EPSILON) {
                std::cerr << "Warning: fracture " << frac.id << " has degenerate geometry, skipped.\n";
                continue;
            }
            normal = normal * (1.0 / nn);

            // 3. 遍历所有 cell，用 bbox 粗筛，再精确裁剪
            for (int cell_idx = 0; cell_idx < n_matrix; ++cell_idx) {
                const Cell& cell = cells[cell_idx];

                // 粗筛：fracture bbox vs cell bbox
                if (!bboxOverlap(fmin, fmax, cell.bbox_min, cell.bbox_max)) {
                    continue;
                }

                // 精确裁剪：fracture quad vs arbitrary hexahedron
                std::vector<Point3> poly = clipFractureBox(frac, cell, faces);
                if (poly.size() < 3) continue;

                double area = polygonArea(poly);
                if (area <= MIN_SEG_AREA) continue;

                Segment seg;
                seg.id = seg_id_counter++;
                seg.frac_id = frac.id;
                seg.cell_id = cell_idx;
                seg.area = area;
                seg.center = polygonCenter(poly);
                seg.normal = normal;
                seg.aperture = frac.aperture;
                seg.perm = frac.perm;
                seg.poly = poly;

                // 基于真实 FaceGeom 的局部 face-trace 几何
                fillSegmentFaceGeom(seg, poly, cell, faces);

                // 一般六面体版 Tmf 计算
                seg.T_mf = computeMatrixFractureTransmissibility(cell, seg, 2, 2, 2);

                segments.push_back(seg);
            }
        }

        n_frac_nodes = (int)segments.size();
        n_total = n_matrix + n_frac_nodes;
        std::cout << "Generated " << n_frac_nodes << " fracture segments." << std::endl;
    }

    void buildConnections() {
        connections.clear();
        adj.assign(n_total, std::vector<Neighbor>());

        auto add_conn = [&](int u, int v, double T, int type) {
            if (T <= EPSILON) return;
            connections.push_back({u, v, T, type});
            int conn_idx = (int)connections.size() - 1;
            adj[u].push_back({v, T, conn_idx});
            adj[v].push_back({u, T, conn_idx});
        };

        // =========================================================
        // 1. Matrix-Matrix —— face-based TPFA
        // =========================================================
        for (const auto& f : faces) {
            if (f.owner < 0 || f.neighbor < 0) continue;

            int u = f.owner;
            int v = f.neighbor;

            double Tmm = computeMMTransmissibilityTPFA(cells[u], cells[v], f);
            if (Tmm > EPSILON) {
                add_conn(u, v, Tmm, 0);
            }
        }

        // =========================================================
        // 2. Matrix-Fracture
        // =========================================================
        for (int s = 0; s < n_frac_nodes; ++s) {
            int u = segments[s].cell_id;
            int v = n_matrix + s;
            add_conn(u, v, segments[s].T_mf, 1);
        }

        // =========================================================
        // 3. Fracture-Fracture (Intra)
        // =========================================================
        std::map<int, std::vector<int>> frac_seg_map;
        for (int s = 0; s < n_frac_nodes; ++s) {
            frac_seg_map[segments[s].frac_id].push_back(s);
        }

        for (auto& entry : frac_seg_map) {
            const std::vector<int>& segs = entry.second;

            for (size_t i = 0; i < segs.size(); ++i) {
                for (size_t j = i + 1; j < segs.size(); ++j) {
                    int s1 = segs[i];
                    int s2 = segs[j];

                    int c1 = segments[s1].cell_id;
                    int c2 = segments[s2].cell_id;
                    if (c1 == c2) continue; // 同一宿主 cell 内不属于 Intra

                    int lf1 = -1, lf2 = -1, shared_fid = -1;
                    if (!getSharedFacePairByFaceIds(cells[c1], cells[c2], lf1, lf2, shared_fid)) {
                        continue;
                    }

                    if (shared_fid < 0) continue;
                    const FaceGeom& fg = faces[shared_fid];
                    if (fg.owner < 0 || fg.neighbor < 0) continue;

                    // 两个 segment 都必须在共享 face 上有有效 trace
                    double ell1 = segments[s1].face_trace_len[lf1];
                    double ell2 = segments[s2].face_trace_len[lf2];
                    if (ell1 <= EPSILON || ell2 <= EPSILON) continue;

                    // 数值上允许略有差异，取较小值更保守
                    double ell = std::min(ell1, ell2);
                    if (ell <= EPSILON) continue;

                    // 各自中心到共享界面 trace 的距离
                    double L1 = segments[s1].face_center_dist[lf1];
                    double L2 = segments[s2].face_center_dist[lf2];
                    if (L1 <= EPSILON || L2 <= EPSILON) continue;

                    // 过流面积 A = aperture * shared-trace-length
                    double Af1 = segments[s1].aperture * ell;
                    double Af2 = segments[s2].aperture * ell;
                    if (Af1 <= EPSILON || Af2 <= EPSILON) continue;

                    // 两侧半传导率
                    double tau1 = FLOW_BETA *segments[s1].perm * Af1 / L1;
                    double tau2 = FLOW_BETA *segments[s2].perm * Af2 / L2;
                    if (tau1 <= EPSILON || tau2 <= EPSILON) continue;

                    // 调和组合
                    double Tff = (tau1 * tau2) / std::max(EPSILON, tau1 + tau2);

                    if (Tff > EPSILON) {
                        add_conn(n_matrix + s1, n_matrix + s2, Tff, 2);
                    }
                }
            }
        }

        // =========================================================
        // 4. Fracture-Fracture (Inter/Cross)
        // =========================================================
        std::map<int, std::vector<int>> cell_seg_map;
        for (int s = 0; s < n_frac_nodes; ++s) {
            cell_seg_map[segments[s].cell_id].push_back(s);
        }

        for (auto& entry : cell_seg_map) {
            const std::vector<int>& segs = entry.second;
            if (segs.size() < 2) continue;

            for (size_t i = 0; i < segs.size(); ++i) {
                for (size_t j = i + 1; j < segs.size(); ++j) {
                    int s1 = segs[i];
                    int s2 = segs[j];

                    if (segments[s1].frac_id == segments[s2].frac_id) continue;

                    double ell_int = 0.0;
                    double L1 = 0.0;
                    double L2 = 0.0;

                    bool ok = computeCrossGeom(segments[s1], segments[s2], ell_int, L1, L2);
                    if (!ok) continue;

                    if (ell_int <= EPSILON) continue;

                    L1 = std::max(L1, 1e-10);
                    L2 = std::max(L2, 1e-10);

                    double A1 = segments[s1].aperture * ell_int;
                    double A2 = segments[s2].aperture * ell_int;
                    if (A1 <= EPSILON || A2 <= EPSILON) continue;

                    double tau1 = FLOW_BETA *segments[s1].perm * A1 / L1;
                    double tau2 = FLOW_BETA *segments[s2].perm * A2 / L2;
                    if (tau1 <= EPSILON || tau2 <= EPSILON) continue;

                    double T_cross = (tau1 * tau2) / std::max(EPSILON, tau1 + tau2);

                    if (T_cross > EPSILON) {
                        add_conn(n_matrix + s1, n_matrix + s2, T_cross, 2);
                    }
                }
            }
        }

        std::cout << "Built " << connections.size() << " connections." << std::endl;
    }

    void setupWells() {
        wells.clear();
        well_map.clear();

        // 只收集人工裂缝，不再依赖固定 ID 范围
        std::vector<int> target_fracs;
        std::map<int, Point3> frac_center_map;

        for (const auto& f : fractures) {
            if (f.is_hydraulic) {
                target_fracs.push_back(f.id);
                frac_center_map[f.id] = fractureCenter(f);
            }
        }

        std::sort(target_fracs.begin(), target_fracs.end());

        for (int fid : target_fracs) {
            std::vector<int> cands;
            for (int s = 0; s < n_frac_nodes; ++s) {
                if (segments[s].frac_id == fid) {
                    cands.push_back(s);
                }
            }

            if (cands.empty()) continue;

            // 选最接近该裂缝几何中心的 segment
            int best_s = -1;
            double best_d2 = 1e100;

            Point3 fc = frac_center_map[fid];
            for (int s : cands) {
                Point3 d = segments[s].center - fc;
                double d2 = d.dot(d);
                if (d2 < best_d2) {
                    best_d2 = d2;
                    best_s = s;
                }
            }

            if (best_s != -1) {
                double rw = 0.05;

                double re = computeSegmentEquivalentRadius(segments[best_s], rw);
                double kf = segments[best_s].perm;
                double b  = segments[best_s].aperture;

                double denom = std::log(re / rw);
                if (denom <= EPSILON) continue;

                Well w;
                w.target_node_idx = n_matrix + best_s;
                w.WI = FLOW_BETA *2.0 * PI * kf * b / denom;
                w.P_bhp = 50.0;

                if (!std::isfinite(w.WI) || w.WI <= EPSILON) continue;

                wells.push_back(w);
                well_map[w.target_node_idx] = (int)wells.size() - 1;
            }
        }

        std::cout << "Setup " << wells.size() << " well connections." << std::endl;
        std::map<int, int> seg_count_by_frac;
        for (const auto& seg : segments) {
            seg_count_by_frac[seg.frac_id]++;
        }

        std::cout << "===== Segment count by hydraulic fracture =====" << std::endl;
        for (const auto& f : fractures) {
            if (f.is_hydraulic) {
                std::cout << "Frac ID " << f.id
                        << " : " << seg_count_by_frac[f.id] << " segments" << std::endl;
            }
        }
    };

    double computeCellVerticalThickness(const Cell& c) const {
        // corners[0..3] 是底面，corners[4..7] 是顶面
        double z_bot_avg = 0.25 * (
            c.corners[0].z + c.corners[1].z + c.corners[2].z + c.corners[3].z
        );

        double z_top_avg = 0.25 * (
            c.corners[4].z + c.corners[5].z + c.corners[6].z + c.corners[7].z
        );

        double h = std::abs(z_top_avg - z_bot_avg);

        if (!std::isfinite(h) || h <= EPSILON) {
            h = std::max(c.dz, 1e-10);
        }

        return h;
    }

    double computeVerticalMatrixWellWI(const Cell& c,
                                        double rw = 0.05,
                                        double skin = 0.0) const {
            double kx = std::max(c.K[0], EPSILON);
            double ky = std::max(c.K[1], EPSILON);

            double h = computeCellVerticalThickness(c);

            // 用 bbox 尺寸作为 Peaceman 公式里的 dx, dy
            double dx_cell = std::max(c.dx, 1e-10);
            double dy_cell = std::max(c.dy, 1e-10);

            // Peaceman anisotropic equivalent radius
            double ratio_yx = ky / kx;
            double ratio_xy = kx / ky;

            double numerator = 0.28 * std::sqrt(
                std::sqrt(ratio_yx) * dx_cell * dx_cell +
                std::sqrt(ratio_xy) * dy_cell * dy_cell
            );

            double denominator =
                std::pow(ratio_yx, 0.25) + std::pow(ratio_xy, 0.25);

            double re = numerator / std::max(denominator, EPSILON);

            re = std::max(re, 1.1 * rw);

            double denom = std::log(re / rw) + skin;
            if (!std::isfinite(denom) || denom <= EPSILON) {
                return 0.0;
            }

            double kh = std::sqrt(kx * ky);

            double WI = FLOW_BETA * 2.0 * PI * kh * h / denom;

            if (!std::isfinite(WI) || WI <= EPSILON) {
                return 0.0;
            }

            return WI;
    }


    int findMatrixCellClosestToReservoirCenter() const {
        if (cells.empty()) return -1;

        Point3 target;

        if (grid_bbox_ready) {
            target.x = 0.5 * (grid_bbox_min.x + grid_bbox_max.x);
            target.y = 0.5 * (grid_bbox_min.y + grid_bbox_max.y);
            target.z = 0.5 * (grid_bbox_min.z + grid_bbox_max.z);
        } else {
            target.x = 0.5 * Lx;
            target.y = 0.5 * Ly;
            target.z = 0.5 * Lz;
        }

        int best_cell = -1;
        double best_d2 = 1e100;

        for (int i = 0; i < n_matrix; ++i) {
            Point3 d = cells[i].center - target;
            double d2 = d.dot(d);

            if (d2 < best_d2) {
                best_d2 = d2;
                best_cell = i;
            }
        }

        return best_cell;
    }

    void setupCenterMatrixVerticalWell(double rw = 0.05,
                                    double skin = 0.0,
                                    double bhp = 50.0) {
        wells.clear();
        well_map.clear();

        int cell_id = findMatrixCellClosestToReservoirCenter();

        if (cell_id < 0 || cell_id >= n_matrix) {
            std::cerr << "Failed to find center matrix cell for vertical well." << std::endl;
            return;
        }

        const Cell& c = cells[cell_id];

        double WI = computeVerticalMatrixWellWI(c, rw, skin);

        if (!std::isfinite(WI) || WI <= EPSILON) {
            std::cerr << "Invalid WI for center matrix vertical well. cell_id = "
                    << cell_id << std::endl;
            return;
        }

        Well w;
        w.target_node_idx = cell_id;   // 关键：基质节点编号就是 cell_id
        w.WI = WI;
        w.P_bhp = bhp;

        wells.push_back(w);
        well_map[w.target_node_idx] = 0;

        std::cout << "Setup center matrix vertical well:" << std::endl;
        std::cout << "  cell_id = " << cell_id << std::endl;
        std::cout << "  center = ("
                << c.center.x << ", "
                << c.center.y << ", "
                << c.center.z << ")" << std::endl;
        std::cout << "  dx,dy,h = "
                << c.dx << ", "
                << c.dy << ", "
                << computeCellVerticalThickness(c) << std::endl;
        std::cout << "  WI = " << WI
                << ", P_bhp = " << bhp << std::endl;
    }


    void initState() {
        states.resize(n_total);
        states_prev.resize(n_total);
        for (int i = 0; i < n_total; ++i) {
            states[i].P = 800.0;
            states[i].Sw = 0.2;
            states[i].Sg = 0.1;
            states_prev[i] = states[i];
        }
    }

    template <typename T>
    PropertiesT<T> getProps(const StateT<T>& s) const {
        PropertiesT<T> p;

        // 油水保持原状：指数型体积系数 + 常黏度
        calcLiquidPVT(s.P, p.Bw, p.Bo);

        // 气相改为真实气体 PVT 表：Z(P), Cg(P), Bg(P), mu_g(P)
        calcGasPVT_fromTable(s.P, p.Zg, p.Cg, p.Bg, p.mu_g);

        calcRelPerm(s.Sw, s.Sg, p.krw, p.kro, p.krg);

        p.lw = p.krw / (g_props.mu_w * p.Bw);
        p.lo = p.kro / (g_props.mu_o * p.Bo);
        p.lg = p.krg / (p.mu_g * p.Bg);

        return p;
    }

    Eigen::Matrix<AD3, 3, 1> computeAccumulation_AD(double dt,
                                                    const State& s_old_val,
                                                    const StateAD3& s_new,
                                                    const PropertiesT<AD3>& p_new,
                                                    double vol,
                                                    double phi) const {
        StateAD3 s_old;
        s_old.P.value() = s_old_val.P;    s_old.P.derivatives().setZero();
        s_old.Sw.value() = s_old_val.Sw;  s_old.Sw.derivatives().setZero();
        s_old.Sg.value() = s_old_val.Sg;  s_old.Sg.derivatives().setZero();

        PropertiesT<AD3> p_old = getProps(s_old);

        AD3 accum = vol * phi / dt;
        Eigen::Matrix<AD3, 3, 1> R;
        R(0) = accum * (s_new.Sw / p_new.Bw - s_old.Sw / p_old.Bw);
        R(1) = accum * ((AD3(1.0) - s_new.Sw - s_new.Sg) / p_new.Bo - (AD3(1.0) - s_old.Sw - s_old.Sg) / p_old.Bo);
        R(2) = accum * (s_new.Sg / p_new.Bg - s_old.Sg / p_old.Bg);

        return R;
    }

    Eigen::Matrix<AD3, 3, 1> computeWell_AD(const Well& w,
                                            const StateAD3& s_new,
                                            const PropertiesT<AD3>& pu) const {
        Eigen::Matrix<AD3, 3, 1> R;
        R(0) = AD3(0.0);
        R(1) = AD3(0.0);
        R(2) = AD3(0.0);

        AD3 dP = s_new.P - w.P_bhp;
        if (dP.value() > 0.0) {
            R(0) = w.WI * pu.lw * dP;
            R(1) = w.WI * pu.lo * dP;
            R(2) = w.WI * pu.lg * dP;
        }
        return R;
    }

    struct FluxAD {
        double val[3];
        Eigen::Vector3d d_du[3];
        Eigen::Vector3d d_dv[3];
    };

    FluxAD computeFlux_FastAD(double T_trans,
                              const StateAD3& su,
                              const StateAD3& sv,
                              const PropertiesT<AD3>& pu,
                              const PropertiesT<AD3>& pv) const {
        FluxAD res;
        double dP_val = su.P.value() - sv.P.value();
        bool u_is_upwind = (dP_val >= 0.0);//如果 dP >= 0，说明从 u 流向 v，就取 u 端流度作为上风流度

        AD3 dP_u = su.P - sv.P.value();
        AD3 dP_v = su.P.value() - sv.P;

        if (u_is_upwind) {
            AD3 Fu0 = T_trans * pu.lw * dP_u;
            AD3 Fu1 = T_trans * pu.lo * dP_u;
            AD3 Fu2 = T_trans * pu.lg * dP_u;

            res.val[0] = Fu0.value(); res.d_du[0] = Fu0.derivatives();
            res.val[1] = Fu1.value(); res.d_du[1] = Fu1.derivatives();
            res.val[2] = Fu2.value(); res.d_du[2] = Fu2.derivatives();

            res.d_dv[0] = T_trans * pu.lw.value() * dP_v.derivatives();
            res.d_dv[1] = T_trans * pu.lo.value() * dP_v.derivatives();
            res.d_dv[2] = T_trans * pu.lg.value() * dP_v.derivatives();
        } else {
            AD3 Fv0 = T_trans * pv.lw * dP_v;
            AD3 Fv1 = T_trans * pv.lo * dP_v;
            AD3 Fv2 = T_trans * pv.lg * dP_v;

            res.val[0] = Fv0.value(); res.d_dv[0] = Fv0.derivatives();
            res.val[1] = Fv1.value(); res.d_dv[1] = Fv1.derivatives();
            res.val[2] = Fv2.value(); res.d_dv[2] = Fv2.derivatives();

            res.d_du[0] = T_trans * pv.lw.value() * dP_u.derivatives();
            res.d_du[1] = T_trans * pv.lo.value() * dP_u.derivatives();
            res.d_du[2] = T_trans * pv.lg.value() * dP_u.derivatives();
        }
        return res;
    }

    Point3 getNodeCenter(int node) const {
        if (node < n_matrix) return cells[node].center;
        return segments[node - n_matrix].center;
    }

    double getNodeVolume(int node) const {
        if (node < n_matrix) return cells[node].vol;
        const Segment& seg = segments[node - n_matrix];
        return std::max(seg.area * seg.aperture, EPSILON);
    }

    double getNodeAccumPorosity(int node) const {
        if (node < n_matrix) return std::max(cells[node].phi, EPSILON);
        return std::max(phi_f_ref, EPSILON);
    }

    static std::string nodeTypeName(int type) {
        return (type == NODE_MATRIX) ? "Matrix" : "Fracture";
    }

    void addFMMEdge(const FMMEdge& e) {
        int idx = (int)fmm_edges.size();//边编号
        fmm_edges.push_back(e);
        fmm_adj[e.from].push_back(idx);
        fmm_adj[e.to].push_back(idx);
    }

    void buildFMMData() {
        fmm_node_type.assign(n_total, NODE_MATRIX);
        for (int i = n_matrix; i < n_total; ++i) fmm_node_type[i] = NODE_FRACTURE;

        fmm_edges.clear();
        fmm_adj.assign(n_total, std::vector<int>());

        // 1) Matrix-Matrix
        for (const auto& f : faces) {
            if (f.owner < 0 || f.neighbor < 0) continue;
            FMMEdge e;
            e.from = f.owner; //from和to表示“边的两个端点”，不是真正有方向的单向边
            e.to = f.neighbor;
            e.type = EDGE_MM;
            e.face_id = f.id;
            addFMMEdge(e);
        }

        // 2) Matrix-Fracture
        for (int s = 0; s < n_frac_nodes; ++s) {
            int m = segments[s].cell_id;
            int fnode = n_matrix + s;
            Point3 n = segments[s].normal;
            double nn = n.norm();
            if (nn < EPSILON) continue;
            n = n / nn;

            FMMEdge e;
            e.from = m;
            e.to = fnode;
            e.type = EDGE_MF;
            e.d_mf = averageDistanceCellToPlane(cells[m], segments[s].center, n, 2, 2, 2);
            e.d_mf = std::max(e.d_mf, 1e-10);
            addFMMEdge(e);
        }

        // 3) Fracture-Fracture intra
        std::map<int, std::vector<int>> frac_seg_map;  //裂缝包括哪些裂缝段segment
        for (int s = 0; s < n_frac_nodes; ++s) {
            frac_seg_map[segments[s].frac_id].push_back(s);
        }

        for (auto& entry : frac_seg_map) {
            const std::vector<int>& segs_same_frac = entry.second;
            for (size_t i = 0; i < segs_same_frac.size(); ++i) {
                for (size_t j = i + 1; j < segs_same_frac.size(); ++j) {
                    int s1 = segs_same_frac[i];
                    int s2 = segs_same_frac[j];

                    int c1 = segments[s1].cell_id;
                    int c2 = segments[s2].cell_id;
                    if (c1 == c2) continue;

                    int lf1 = -1, lf2 = -1, shared_fid = -1;
                    if (!getSharedFacePairByFaceIds(cells[c1], cells[c2], lf1, lf2, shared_fid)) {//这要求两个宿主 cell 必须共享一个 face
                        continue;
                    }

                    double ell1 = segments[s1].face_trace_len[lf1];
                    double ell2 = segments[s2].face_trace_len[lf2];
                    if (ell1 <= EPSILON || ell2 <= EPSILON) continue;

                    double L1 = std::max(segments[s1].face_center_dist[lf1], 1e-10);
                    double L2 = std::max(segments[s2].face_center_dist[lf2], 1e-10);

                    FMMEdge e;
                    e.from = n_matrix + s1;
                    e.to = n_matrix + s2;
                    e.type = EDGE_FF_INTRA;
                    e.face_id = shared_fid;
                    e.L1 = L1;
                    e.L2 = L2;
                    e.ell_int = std::min(ell1, ell2);
                    addFMMEdge(e);
                }
            }
        }

        // 4) Fracture-Fracture cross
        std::map<int, std::vector<int>> cell_seg_map;
        for (int s = 0; s < n_frac_nodes; ++s) {
            cell_seg_map[segments[s].cell_id].push_back(s);
        }

        for (auto& entry : cell_seg_map) {
            const std::vector<int>& segs_same_cell = entry.second;
            if (segs_same_cell.size() < 2) continue;

            for (size_t i = 0; i < segs_same_cell.size(); ++i) {
                for (size_t j = i + 1; j < segs_same_cell.size(); ++j) {
                    int s1 = segs_same_cell[i];
                    int s2 = segs_same_cell[j];
                    if (segments[s1].frac_id == segments[s2].frac_id) continue;

                    double ell_int = 0.0, L1 = 0.0, L2 = 0.0;
                    if (!computeCrossGeom(segments[s1], segments[s2], ell_int, L1, L2)) continue;

                    FMMEdge e;
                    e.from = n_matrix + s1;
                    e.to = n_matrix + s2;
                    e.type = EDGE_FF_CROSS;
                    e.L1 = std::max(L1, 1e-10);
                    e.L2 = std::max(L2, 1e-10);
                    e.ell_int = ell_int;
                    addFMMEdge(e);
                }
            }
        }

        std::cout << "Built FMM data: " << fmm_edges.size() << " hybrid edges." << std::endl;
    }

    void computeReferenceEtaField() {
        lambda_tot_ref.assign(n_total, 0.0);
        eta_node_ref.assign(n_total, 0.0);
        eta_matrix_ref.assign(n_matrix, 0.0);
  
        for (int i = 0; i < n_total; ++i) {
            PropertiesT<double> p = getProps(states[i]);
            double lambdaTot = std::max(p.lw + p.lo + p.lg, EPSILON);

            lambda_tot_ref[i] = lambdaTot;

            if (i < n_matrix) {
                const Cell& c = cells[i];
                double k_avg = std::max((c.K[0] + c.K[1] + c.K[2]) / 3.0, EPSILON);//工程近似，渗透率用三方向平均值 k_avg
                double phi = std::max(c.phi, EPSILON);
                double eta = beta_fmm * k_avg * lambdaTot / std::max(phi * Ct_ref_matrix, EPSILON);
                eta_matrix_ref[i] = eta;
                eta_node_ref[i] = eta;
            } else {
                const Segment& seg = segments[i - n_matrix];
                double eta = beta_fmm * std::max(seg.perm, EPSILON) * lambdaTot /
                             std::max(phi_f_ref * Ct_ref_frac, EPSILON);
                eta_node_ref[i] = eta;
            }
        }
    }

    void computeEtaRefForC() {//从所有基质单元的 eta_matrix_ref 中算一个体积加权全局参考扩散率 eta_ref，再据此设置 c_voi
        double num = 0.0;//分子
        double den = 0.0;//分母
        for (int i = 0; i < n_matrix; ++i) {
            double v = std::max(cells[i].vol, EPSILON);
            num += v * eta_matrix_ref[i];
            den += v;
        }
        eta_ref = (den > EPSILON) ? (num / den) : 1.0;
        if (eta_ref > 1.0) c_voi = 6.0;
        else c_voi = 6.0 / std::max(eta_ref, EPSILON);
        
        std::cout << "Static FMM eta_ref(matrix volume-weighted) = " << eta_ref
                  << ", c_voi = " << c_voi << std::endl;
    }

    double computeMatrixFaceEta(int m, const Point3& n_unit) const { //计算带有法相的eta，适用于计算M-M和M-F的S时所需的eta
        double kn = std::max(normalProjectedPerm(cells[m], n_unit), EPSILON);
        double phi = std::max(cells[m].phi, EPSILON);
        return beta_fmm * kn * std::max(lambda_tot_ref[m], EPSILON) /
               std::max(phi * Ct_ref_matrix, EPSILON);
    }

    double computeMMFaceSlowness(int u, int v, int face_id) const {
        const FaceGeom& f = faces[face_id];
        Point3 n = f.normal;
        double nn = n.norm();
        if (nn < EPSILON) return std::numeric_limits<double>::infinity();
        n = n / nn;

        double du = centerToFaceNormalDistance(cells[u], f);
        double dv = centerToFaceNormalDistance(cells[v], f);
        double eta_u = computeMatrixFaceEta(u, n);
        double eta_v = computeMatrixFaceEta(v, n);

        return du / std::sqrt(std::max(eta_u, EPSILON)) +
               dv / std::sqrt(std::max(eta_v, EPSILON));
    }

    double computeMFSlowness(const FMMEdge& e) const {
        int m = (e.from < n_matrix) ? e.from : e.to;
        int fnode = (e.from < n_matrix) ? e.to : e.from;
        (void)fnode;

        Point3 n = segments[fnode - n_matrix].normal;
        double nn = n.norm();
        if (nn < EPSILON) return std::numeric_limits<double>::infinity();
        n = n / nn;

        double eta_mf = computeMatrixFaceEta(m, n);
        return std::max(e.d_mf, 1e-10) / std::sqrt(std::max(eta_mf, EPSILON));
    }

    double computeFFIntraSlowness(const FMMEdge& e) const {
        double eta1 = std::max(eta_node_ref[e.from], EPSILON);
        double eta2 = std::max(eta_node_ref[e.to], EPSILON);
        return std::max(e.L1, 1e-10) / std::sqrt(eta1) +
               std::max(e.L2, 1e-10) / std::sqrt(eta2);
    }

    double computeFFCrossSlowness(const FMMEdge& e) const {
        double eta1 = std::max(eta_node_ref[e.from], EPSILON);
        double eta2 = std::max(eta_node_ref[e.to], EPSILON);
        return std::max(e.L1, 1e-10) / std::sqrt(eta1) +
               std::max(e.L2, 1e-10) / std::sqrt(eta2);
    }

    bool solveLocalEikonal(const std::vector<std::pair<double, double>>& dirs,
                           int count,
                           double& tau_out) const { //取 dirs 里前 cnt 个方向
        if (count <= 0) return false;
        if (count == 1) {
            tau_out = dirs[0].first + dirs[0].second;
            return std::isfinite(tau_out);
        }

        double A = 0.0, B = 0.0, C = -1.0;
        double tau_max = -1e100;

        for (int i = 0; i < count; ++i) {
            double ti = dirs[i].first;
            double Si = std::max(dirs[i].second, 1e-12);
            double wi = 1.0 / (Si * Si);
            A += wi;
            B += -2.0 * ti * wi;
            C += ti * ti * wi;
            tau_max = std::max(tau_max, ti);
        }

        double disc = B * B - 4.0 * A * C;
        if (disc < 0.0) {
            if (disc > -1e-12) disc = 0.0;
            else return false;
        }

        double tau = (-B + std::sqrt(disc)) / (2.0 * A);
        if (!std::isfinite(tau)) return false;
        if (tau + 1e-12 < tau_max) return false;//如果解出来的当前点 tau 比某个参与方向的已知邻居时间还小，那这个解不合法

        tau_out = tau;
        return true;
    }

    double updateMatrixTauByQuadratic(int m) const {//分别在x，y，z每个方向只选一个最优邻居
        std::vector<std::pair<double, double>> dirs; //返回当前 matrix 节点 m 通过 M-M 局部二次更新得到的最优候选 tau。
        //dirs 里的每一个元素都是一个方向贡献对
        auto collect_dir = [&](int f1, int f2) {
            bool found = false;
            double best_score = std::numeric_limits<double>::infinity();
            std::pair<double, double> best_pair{0.0, 0.0};

            int faces_dir[2] = {f1, f2};
            for (int kk = 0; kk < 2; ++kk) {
                int lf = faces_dir[kk];
                int fid = cells[m].face_ids[lf];
                if (fid < 0) continue;

                const FaceGeom& fg = faces[fid];
                int nb = -1;
                if (fg.owner == m) nb = fg.neighbor;
                else if (fg.neighbor == m) nb = fg.owner;
                if (nb < 0 || nb >= n_matrix) continue;
                if (fmm_state[nb] != ACCEPTED) continue;

                double S = computeMMFaceSlowness(m, nb, fid);
                double score = tau_fmm[nb] + S;
                if (score < best_score) {
                    best_score = score;
                    best_pair = {tau_fmm[nb], S};
                    found = true;
                }
            }

            if (found) dirs.push_back(best_pair);
        };

        collect_dir(XM, XP);
        collect_dir(YM, YP);
        collect_dir(ZM, ZP);

        if (dirs.empty()) return std::numeric_limits<double>::infinity();
        std::sort(dirs.begin(), dirs.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });

        double best = dirs[0].first + dirs[0].second;
        for (int cnt = 2; cnt <= (int)dirs.size(); ++cnt) {
            double tau_cand = best;
            if (solveLocalEikonal(dirs, cnt, tau_cand)) {
                best = tau_cand;
            } else {
                break;
            }
        }
        return best;
    }

    double computeNodeTauCandidate(int node) const {  //给任意一个 FMM 节点 node 计算“当前时刻最好的候选 DTOF（tau）
        double best = std::numeric_limits<double>::infinity();

        if (node < n_matrix) {
            best = std::min(best, updateMatrixTauByQuadratic(node)); //M-M路径
            for (int eidx : fmm_adj[node]) {  //M-F路径
                const FMMEdge& e = fmm_edges[eidx];
                if (e.type != EDGE_MF) continue;
                int nb = (e.from == node) ? e.to : e.from;
                if (fmm_state[nb] != ACCEPTED) continue;
                best = std::min(best, tau_fmm[nb] + computeMFSlowness(e));
            }
        } else {
            for (int eidx : fmm_adj[node]) {
                const FMMEdge& e = fmm_edges[eidx];
                int nb = (e.from == node) ? e.to : e.from;
                if (fmm_state[nb] != ACCEPTED) continue;

                if (e.type == EDGE_MF) {
                    best = std::min(best, tau_fmm[nb] + computeMFSlowness(e));
                } else if (e.type == EDGE_FF_INTRA) {
                    best = std::min(best, tau_fmm[nb] + computeFFIntraSlowness(e));
                } else if (e.type == EDGE_FF_CROSS) {
                    best = std::min(best, tau_fmm[nb] + computeFFCrossSlowness(e));
                }
            }
        }

        return best;
    }

    void pushTrialUpdate(int node,  //如果某个未接受节点能通过当前已接受前沿得到更小的候选 tau，就刷新它、把它标成 TRIAL，并压入最小优先队列。
                         std::priority_queue<std::pair<double, int>,
                                             std::vector<std::pair<double, int>>, //pair是<cand,node>
                                             std::greater<std::pair<double, int>>>& pq) {
        if (node < 0 || node >= n_total) return; //这个队列存储的是trial
        if (fmm_state[node] == ACCEPTED) return;

        double cand = computeNodeTauCandidate(node);
        if (!std::isfinite(cand)) return;

        if (cand + 1e-12 < tau_fmm[node]) {
            tau_fmm[node] = cand;
            fmm_state[node] = TRIAL;
            pq.push({cand, node});
        }
    }

    void computeStaticFMMTau() {
        const double INF = std::numeric_limits<double>::infinity();
        tau_fmm.assign(n_total, INF);
        tin_fmm.assign(n_total, INF);
        fmm_state.assign(n_total, FAR);

        std::priority_queue<std::pair<double, int>,
                            std::vector<std::pair<double, int>>,
                            std::greater<std::pair<double, int>>> pq;

        std::vector<char> seeded(n_total, 0);
        int seed_count = 0;
        for (const auto& w : wells) {
            int seed = w.target_node_idx;
            if (seed < 0 || seed >= n_total) continue;
            if (seeded[seed]) continue;
            seeded[seed] = 1;
            tau_fmm[seed] = 0.0;
            fmm_state[seed] = ACCEPTED;
            ++seed_count;
        }

        if (seed_count == 0) {
            std::cerr << "Warning: no well seed for FMM. tau/tin remain INF." << std::endl;
            return;
        }

        for (int seed = 0; seed < n_total; ++seed) {//用种子点先刷新一圈邻居，把第一层 TRIAL 建起来
            if (!seeded[seed]) continue;
            for (int eidx : fmm_adj[seed]) {
                int nb = (fmm_edges[eidx].from == seed) ? fmm_edges[eidx].to : fmm_edges[eidx].from;
                pushTrialUpdate(nb, pq);
            }
        }

        while (!pq.empty()) {
            auto item = pq.top();
            pq.pop();

            double key = item.first;
            int node = item.second;
            if (fmm_state[node] == ACCEPTED) continue;
            if (key > tau_fmm[node] + 1e-12) continue; //过期候选

            fmm_state[node] = ACCEPTED;

            for (int eidx : fmm_adj[node]) {
                int nb = (fmm_edges[eidx].from == node) ? fmm_edges[eidx].to : fmm_edges[eidx].from;
                pushTrialUpdate(nb, pq);
            }
        }

        int reachable = 0;
        for (double t : tau_fmm) if (std::isfinite(t)) ++reachable;
        std::cout << "Static FMM finished. Reachable nodes = " << reachable
                  << " / " << n_total << std::endl;
    }

    void convertTauToTin() {
        tin_fmm.assign(n_total, std::numeric_limits<double>::infinity());
        for (int i = 0; i < n_total; ++i) {
            if (std::isfinite(tau_fmm[i])) {
                tin_fmm[i] = tau_fmm[i] * tau_fmm[i] / std::max(c_voi, EPSILON);
            }
        }
    }

    void exportFMMResults() const {
        std::ofstream tf("fmm_tau.csv");
        tf << "node_id,node_type,tau,tin,x,y,z\n";
        for (int i = 0; i < n_total; ++i) {
            Point3 c = getNodeCenter(i);
            tf << i << "," << nodeTypeName(fmm_node_type[i]) << ","
               << tau_fmm[i] << "," << tin_fmm[i] << ","
               << c.x << "," << c.y << "," << c.z << "\n";
        }
        tf.close();

        std::ofstream ef("fmm_eta.csv");
        ef << "node_id,node_type,eta_reference,x,y,z\n";
        for (int i = 0; i < n_total; ++i) {
            Point3 c = getNodeCenter(i);
            ef << i << "," << nodeTypeName(fmm_node_type[i]) << ","
               << eta_node_ref[i] << ","
               << c.x << "," << c.y << "," << c.z << "\n";
        }
        ef.close();

        std::cout << "Exported FMM results: fmm_tau.csv, fmm_eta.csv" << std::endl;
    }

    void preprocessStaticFMM() {
        std::cout << "FMM preprocessing started." << std::endl;
        std::cout << "beta_fmm = " << beta_fmm
                  << ", Ct_ref_matrix = " << Ct_ref_matrix
                  << ", Ct_ref_frac = " << Ct_ref_frac << std::endl;

        if (!gas_pvt_table.ready) {
            throw std::runtime_error("Gas PVT table is not ready before preprocessStaticFMM().");
        }
        if (!states.empty()) {
            PropertiesT<double> p0 = getProps(states[0]);
            std::cout << "Initial representative gas PVT: Bg=" << p0.Bg
                      << ", mu_g=" << p0.mu_g
                      << ", lambdaTot=" << (p0.lw + p0.lo + p0.lg) << std::endl;
            std::cout << "Initial relperm and mobility:" << std::endl;
            std::cout << "  krw = " << p0.krw
                    << ", kro = " << p0.kro
                    << ", krg = " << p0.krg << std::endl;

            std::cout << "  Bw = " << p0.Bw
                    << ", Bo = " << p0.Bo
                    << ", Bg = " << p0.Bg << std::endl;

            std::cout << "  mu_w = " << g_props.mu_w
                    << ", mu_o = " << g_props.mu_o
                    << ", mu_g = " << p0.mu_g << std::endl;

            std::cout << "  lw = " << p0.lw
                    << ", lo = " << p0.lo
                    << ", lg = " << p0.lg << std::endl;

            std::cout << "  lg/lo = " << p0.lg / std::max(p0.lo, 1e-30)
                    << ", lg/lw = " << p0.lg / std::max(p0.lw, 1e-30)
                    << std::endl;
        }

        buildFMMData();
        computeReferenceEtaField();
        computeEtaRefForC();
        computeStaticFMMTau();
        convertTauToTin();
        exportFMMResults();
        std::cout << "FMM preprocessing finished." << std::endl;
    }

    void updateActiveSet(double step_end_time) {//在当前时间步末时刻 step_end_time，根据静态 FMM 算出来的 tin_fmm，决定哪些节点进入本步的 VOI 活跃子系统；
        const double tiny_tol = 1e-12;  //然后只保留“活跃-活跃”的连接，供后续残差和雅各比矩阵装配使用

        active_nodes.assign(n_total, 0);
        active_local_id.assign(n_total, -1);
        active_local_to_global.clear();
        active_conn_indices.clear();
        n_active = 0;
        n_active_matrix = 0;
        n_active_frac = 0;

        for (int i = 0; i < n_total; ++i) {
            if (i < (int)tin_fmm.size() && tin_fmm[i] <= step_end_time + tiny_tol) {
                active_nodes[i] = 1; //1表示这个全局节点在当前步活跃
                active_local_id[i] = n_active;
                active_local_to_global.push_back(i);
                ++n_active;
                if (i < n_matrix) ++n_active_matrix;
                else ++n_active_frac;
            }
        }

        for (size_t ci = 0; ci < connections.size(); ++ci) {
            int u = connections[ci].u;
            int v = connections[ci].v;
            if (active_nodes[u] && active_nodes[v]) {
                active_conn_indices.push_back((int)ci);
            }
        }
    }

    void exportVOIStatus(int step_idx, double step_end_time) const {
        std::ostringstream oss;
        oss << "voi_status_step_" << std::setw(4) << std::setfill('0') << step_idx << ".csv";
        std::ofstream vf(oss.str());
        vf << "node_id,node_type,active,tin,step_end_time,x,y,z\n";
        for (int i = 0; i < n_total; ++i) {
            Point3 c = getNodeCenter(i);
            int flag = (i < (int)active_nodes.size()) ? (int)active_nodes[i] : 0;
            vf << i << "," << nodeTypeName(fmm_node_type[i]) << ","
               << flag << "," << tin_fmm[i] << "," << step_end_time << ","
               << c.x << "," << c.y << "," << c.z << "\n";
        }
    }

    void assembleActiveSystem(double dt, VectorXd& Rg, SparseMatrix<double>* Jptr) {
        int nvar = 3 * n_active;
        Rg = VectorXd::Zero(nvar);

        std::vector<Triplet<double>> trips;
        if (Jptr != nullptr) {
            trips.reserve(n_active * 9 + active_conn_indices.size() * 36);
        }

        std::vector<StateAD3> states_ad(n_active);
        std::vector<PropertiesT<AD3>> props_ad(n_active);

        for (int a = 0; a < n_active; ++a) {
            int g = active_local_to_global[a];
            states_ad[a].P.value()  = states[g].P;  states_ad[a].P.derivatives()  = Eigen::Vector3d::Unit(0);
            states_ad[a].Sw.value() = states[g].Sw; states_ad[a].Sw.derivatives() = Eigen::Vector3d::Unit(1);
            states_ad[a].Sg.value() = states[g].Sg; states_ad[a].Sg.derivatives() = Eigen::Vector3d::Unit(2);
            props_ad[a] = getProps(states_ad[a]);
        }

        for (int a = 0; a < n_active; ++a) {
            int g = active_local_to_global[a];
            double vol = getNodeVolume(g);
            double phi = getNodeAccumPorosity(g);

            auto R_acc = computeAccumulation_AD(dt, states_prev[g], states_ad[a], props_ad[a], vol, phi);
            if (well_map.count(g)) {
                auto R_well = computeWell_AD(wells[well_map[g]], states_ad[a], props_ad[a]);
                R_acc(0) += R_well(0);
                R_acc(1) += R_well(1);
                R_acc(2) += R_well(2);
            }

            for (int eq = 0; eq < 3; ++eq) {
                Rg(3 * a + eq) += R_acc(eq).value();
                if (Jptr != nullptr) {
                    Deriv3 d = R_acc(eq).derivatives();
                    for (int var = 0; var < 3; ++var) {
                        trips.emplace_back(3 * a + eq, 3 * a + var, d(var));
                    }
                }
            }
        }

        for (int conn_idx : active_conn_indices) {
            const Connection& conn = connections[conn_idx];
            int au = active_local_id[conn.u];
            int av = active_local_id[conn.v];
            if (au < 0 || av < 0) continue;

            auto F_uv = computeFlux_FastAD(conn.T,
                                           states_ad[au], states_ad[av],
                                           props_ad[au], props_ad[av]);

            for (int eq = 0; eq < 3; ++eq) {
                Rg(3 * au + eq) += F_uv.val[eq];
                Rg(3 * av + eq) -= F_uv.val[eq];

                if (Jptr != nullptr) {
                    for (int var = 0; var < 3; ++var) {
                        double dFdu = F_uv.d_du[eq](var);
                        double dFdv = F_uv.d_dv[eq](var);
                        trips.emplace_back(3 * au + eq, 3 * au + var,  dFdu);
                        trips.emplace_back(3 * av + eq, 3 * au + var, -dFdu);
                        trips.emplace_back(3 * au + eq, 3 * av + var,  dFdv);
                        trips.emplace_back(3 * av + eq, 3 * av + var, -dFdv);
                    }
                }
            }
        }

        if (Jptr != nullptr) {
            Jptr->resize(nvar, nvar);
            Jptr->setFromTriplets(trips.begin(), trips.end(), [](double a, double b) { return a + b; });
            Jptr->makeCompressed();
        }
    }

    bool solveStepVOI(double dt, double& step_oil, double& step_water, double& step_gas, int& iter_out) {
        int max_iter = 15;
        double tol = 1e-3;

        if (n_active <= 0) {
            iter_out = 0;
            return true;
        }

        std::vector<State> states_backup = states;

        for (int iter = 0; iter < max_iter; ++iter) {
            iter_out = iter + 1;

            VectorXd Rg;
            assembleActiveSystem(dt, Rg, &J);
            double max_resid = (Rg.size() > 0) ? Rg.lpNorm<Infinity>() : 0.0;

            if (max_resid < tol) {
                for (const auto& w : wells) {
                    int u = w.target_node_idx;
                    if (u < 0 || u >= n_total) continue;
                    if (!active_nodes[u]) continue;
                    double dP = states[u].P - w.P_bhp;
                    if (dP > 0.0) {
                        PropertiesT<double> p = getProps(states[u]);
                        step_water += w.WI * p.lw * dP * dt;
                        step_oil   += w.WI * p.lo * dP * dt;
                        step_gas   += w.WI * p.lg * dP * dt;
                    }
                }
                return true;
            }

            BiCGSTAB<SparseMatrix<double>, IncompleteLUT<double>> solver;
            solver.preconditioner().setDroptol(1e-5);
            solver.preconditioner().setFillfactor(40);
            solver.setTolerance(1e-5);
            solver.setMaxIterations(500);
            solver.compute(J);

            if (solver.info() != Success) {
                states = states_backup;
                return false;
            }

            VectorXd delta = solver.solve(-Rg);
            if (solver.info() != Success) {
                states = states_backup;
                return false;
            }

            double alpha = 1.0;
            bool accepted = false;
            double norm_old = Rg.norm();
            std::vector<State> states_before_ls = states;

            for (int ls = 0; ls < 3; ++ls) {
                double damping = 1.0;
                double max_delta_P = 0.0;
                double max_delta_S = 0.0;
                for (int a = 0; a < n_active; ++a) {
                    max_delta_P = std::max(max_delta_P, std::abs(delta(3 * a + 0) * alpha));
                    max_delta_S = std::max(max_delta_S, std::abs(delta(3 * a + 1) * alpha));
                    max_delta_S = std::max(max_delta_S, std::abs(delta(3 * a + 2) * alpha));
                }

                if (max_delta_P > 20.0) damping = std::min(damping, 20.0 / max_delta_P);
                if (max_delta_S > 0.1)  damping = std::min(damping, 0.1 / max_delta_S);

                for (int a = 0; a < n_active; ++a) {
                    int g = active_local_to_global[a];
                    states[g].P  = states_before_ls[g].P  + delta(3 * a + 0) * damping * alpha;
                    states[g].Sw = states_before_ls[g].Sw + delta(3 * a + 1) * damping * alpha;
                    states[g].Sg = states_before_ls[g].Sg + delta(3 * a + 2) * damping * alpha;

                    states[g].P  = std::max(1.0, states[g].P);
                    states[g].Sw = std::max(0.0, std::min(1.0, states[g].Sw));
                    states[g].Sg = std::max(0.0, std::min(1.0, states[g].Sg));
                    if (states[g].Sw + states[g].Sg > 1.0) {
                        double sum = std::max(states[g].Sw + states[g].Sg, EPSILON);
                        states[g].Sw /= sum;
                        states[g].Sg /= sum;
                    }
                }

                VectorXd R_trial;
                assembleActiveSystem(dt, R_trial, nullptr);
                double norm_new = R_trial.norm();

                if (norm_new < norm_old || iter == 0) {
                    accepted = true;
                    break;
                } else {
                    alpha *= 0.5;
                    states = states_before_ls;
                }
            }

            if (!accepted && iter > 0) {
                states = states_backup;
                return false;
            }
        }

        states = states_backup;
        return false;
    }

    void exportStaticGeometry() {
        // 1. 在交互界面输出网格基础信息，不再单独输出 grid_info.csv
        std::cout << "\n========== Grid Info ==========\n";
        std::cout << "Nx, Ny, Nz = " << Nx << ", " << Ny << ", " << Nz << "\n";
        std::cout << "Lx, Ly, Lz = " << Lx << ", " << Ly << ", " << Lz << " m\n";
        std::cout << "dx, dy, dz = " << dx << ", " << dy << ", " << dz << " m\n";
        std::cout << "Matrix cells = " << cells.size() << "\n";
        std::cout << "Fracture segments = " << segments.size() << "\n";
        std::cout << "Total nodes = " << cells.size() + segments.size() << "\n";
        std::cout << "================================\n" << std::endl;

        // 2. 导出 cell 几何
        std::ofstream cellFile("cell_geometry.csv");
        cellFile
            << "cell_id,ix,iy,iz,"
            << "cx,cy,cz,vol,"
            << "bbox_min_x,bbox_min_y,bbox_min_z,"
            << "bbox_max_x,bbox_max_y,bbox_max_z,";

        for (int n = 0; n < 8; ++n) {
            cellFile << "c" << n << "_x,c" << n << "_y,c" << n << "_z,";
        }
        cellFile << "face0,face1,face2,face3,face4,face5\n";

        for (const auto& c : cells) {
            cellFile
                << c.id << ","
                << c.ix << "," << c.iy << "," << c.iz << ","
                << c.center.x << "," << c.center.y << "," << c.center.z << ","
                << c.vol << ","
                << c.bbox_min.x << "," << c.bbox_min.y << "," << c.bbox_min.z << ","
                << c.bbox_max.x << "," << c.bbox_max.y << "," << c.bbox_max.z << ",";

            for (int n = 0; n < 8; ++n) {
                cellFile << c.corners[n].x << "," << c.corners[n].y << "," << c.corners[n].z << ",";
            }

            cellFile
                << c.face_ids[0] << "," << c.face_ids[1] << "," << c.face_ids[2] << ","
                << c.face_ids[3] << "," << c.face_ids[4] << "," << c.face_ids[5] << "\n";
        }
        cellFile.close();

        // 3. 导出 face 几何
        // std::ofstream faceFile("face_geometry.csv");
        // faceFile
        //     << "face_id,owner,neighbor,local_owner_face,local_neighbor_face,"
        //     << "cx,cy,cz,nx,ny,nz,area,"
        //     << "bbox_min_x,bbox_min_y,bbox_min_z,"
        //     << "bbox_max_x,bbox_max_y,bbox_max_z,"
        //     << "v0_x,v0_y,v0_z,v1_x,v1_y,v1_z,v2_x,v2_y,v2_z,v3_x,v3_y,v3_z\n";

        // for (const auto& f : faces) {
        //     faceFile
        //         << f.id << ","
        //         << f.owner << ","
        //         << f.neighbor << ","
        //         << f.local_owner_face << ","
        //         << f.local_neighbor_face << ","
        //         << f.center.x << "," << f.center.y << "," << f.center.z << ","
        //        << f.normal.x << "," << f.normal.y << "," << f.normal.z << ","
        //         << f.area << ","
        //         << f.bbox_min.x << "," << f.bbox_min.y << "," << f.bbox_min.z << ","
        //         << f.bbox_max.x << "," << f.bbox_max.y << "," << f.bbox_max.z << ",";

        //     for (int i = 0; i < 4; ++i) {
        //         faceFile << f.vertices[i].x << "," << f.vertices[i].y << "," << f.vertices[i].z;
        //         if (i < 3) faceFile << ",";
        //     }
        //     faceFile << "\n";
        // }
        // faceFile.close();

        // 4. 裂缝几何导出
        std::ofstream fracFile("fracture_geometry.csv");

        // 新增两个字段：frac_type 和 is_hydraulic
        // frac_type: natural / hydraulic，方便画图和人工查看
        // is_hydraulic: 0 / 1，方便 MATLAB / Python 按数值筛选
        fracFile << "id,frac_type,is_hydraulic,"
                << "x0,y0,z0,x1,y1,z1,x2,y2,z2,x3,y3,z3\n";

        for (const auto& f : fractures) {
            std::string frac_type = f.is_hydraulic ? "hydraulic" : "natural";
            int hydraulic_flag = f.is_hydraulic ? 1 : 0;

            fracFile << f.id << ","
                    << frac_type << ","
                    << hydraulic_flag;

            for (int i = 0; i < 4; ++i) {
                fracFile << ","
                        << f.vertices[i].x << ","
                        << f.vertices[i].y << ","
                        << f.vertices[i].z;
            }

            fracFile << "\n";
        }

        fracFile.close();

        std::cout << "Geometry exported: grid_info.csv, cell_geometry.csv, face_geometry.csv, fracture_geometry.csv" << std::endl;
    }

    void exportWells() {
        std::ofstream wellFile("well_info.csv");
        wellFile << "well_id,node_idx,type,x,y,z,WI,P_bhp\n";

        for (size_t i = 0; i < wells.size(); ++i) {
            int u = wells[i].target_node_idx;
            double x, y, z;
            std::string type;

            if (u < n_matrix) {
                x = cells[u].center.x;
                y = cells[u].center.y;
                z = cells[u].center.z;
                type = "Matrix";
            } else {
                int seg_idx = u - n_matrix;
                x = segments[seg_idx].center.x;
                y = segments[seg_idx].center.y;
                z = segments[seg_idx].center.z;
                type = "Fracture";
            }

            wellFile << i << "," << u << "," << type << ","
                     << x << "," << y << "," << z << ","
                     << wells[i].WI << "," << wells[i].P_bhp << "\n";
        }
        wellFile.close();
        std::cout << "Wells exported: well_info.csv" << std::endl;
    }

    void run(double total_time_days) {
        std::ofstream file("output_sim.csv");
        file << "Time,CumOil,CumWater,CumGas,AvgPressure,DT,ActiveNodes,ActiveMatrix,ActiveFracture\n";
 
        std::ofstream activeFile("active_node_ratio.csv");
        activeFile << "step,time,active_node,active_matrix_node,active_fracture_node,"
                << "total_node,total_matrix_node,total_fracture_node,"
                << "active_node_ratio,active_matrix_node_ratio,active_fracture_node_ratio\n";


        double current_time = 0.0;
        double dt = 0.001;
        double dt_min = 1e-6;
        double dt_max = 100.0;

        int target_iter = 6;
        double tot_oil = 0.0, tot_water = 0.0, tot_gas = 0.0;
        int step_count = 0;

        std::cout << std::fixed << std::setprecision(4);

        while (current_time < total_time_days) {
            step_count++;

            double step_oil = 0.0, step_water = 0.0, step_gas = 0.0;
            bool success = false;
            int actual_iter = 0;

            if (current_time + dt > total_time_days) {
                dt = total_time_days - current_time;
            }

            while (!success) {
                if (dt < dt_min) {
                    std::cerr << "Time step too small, simulation failed." << std::endl;
                    return;
                }

                double step_end_time = current_time + dt;
                updateActiveSet(step_end_time);

                std::cout << "Step " << step_count
                          << " @ T=" << current_time
                          << " trying dt=" << dt
                          << " ; active nodes = " << n_active
                          << " (matrix=" << n_active_matrix
                          << ", frac=" << n_active_frac << ") ... " << std::flush;

                success = solveStepVOI(dt, step_oil, step_water, step_gas, actual_iter);

                if (success) {
                    std::cout << "Converged in " << actual_iter << " iters." << std::endl;
                    current_time += dt;
                    states_prev = states;

                    tot_oil += step_oil;
                    tot_water += step_water;
                    tot_gas += step_gas;

                    double avgP = 0.0;
                    for (int i = 0; i < n_matrix; ++i) avgP += states[i].P;
                    avgP /= std::max(n_matrix, 1);

                    file << current_time << "," << tot_oil << "," << tot_water << "," << tot_gas << ","
                         << avgP << "," << dt << ","
                         << n_active << "," << n_active_matrix << "," << n_active_frac << "\n";
                    file.flush();

                    double active_node_ratio = (n_total > 0)
                        ? static_cast<double>(n_active) / static_cast<double>(n_total)
                        : 0.0;

                    double active_matrix_node_ratio = (n_matrix > 0)
                        ? static_cast<double>(n_active_matrix) / static_cast<double>(n_matrix)
                        : 0.0;

                    double active_fracture_node_ratio = (n_frac_nodes > 0)
                        ? static_cast<double>(n_active_frac) / static_cast<double>(n_frac_nodes)
                        : 0.0;

                    activeFile << step_count << ","
                            << current_time << ","
                            << n_active << ","
                            << n_active_matrix << ","
                            << n_active_frac << ","
                            << n_total << ","
                            << n_matrix << ","
                            << n_frac_nodes << ","
                            << active_node_ratio << ","
                            << active_matrix_node_ratio << ","
                            << active_fracture_node_ratio << "\n";

                    activeFile.flush();




                   // exportVOIStatus(step_count, current_time);

                    double fac = std::pow((double)target_iter / (double)std::max(1, actual_iter), 0.5);
                    fac = std::max(0.5, std::min(1.5, fac));
                    dt = std::min(dt_max, dt * fac);
                } else {
                    std::cout << "Failed. Cutting timestep." << std::endl;
                    dt *= 0.25;
                }
            }
        }

        file.close();

        // std::ofstream field("final_field.csv");
        // field << "cell_id,x,y,z,P,Sw,Sg\n";
        // for (int i = 0; i < n_matrix; ++i) {
        //     field << i << ","
        //           << cells[i].center.x << ","
        //           << cells[i].center.y << ","
        //           << cells[i].center.z << ","
        //           << states[i].P << ","
        //           << states[i].Sw << ","
        //           << states[i].Sg << "\n";
        // }
        // field.close();
    }
};

int main() {
    Simulator sim;

    std::cout << "Initializing Corner-Point Grid from CSV..." << std::endl;
    if (!sim.initGridFromCornerPointCSV("COORD.csv", "ZCORN.csv")) {
        std::cerr << "Failed to initialize corner-point grid from CSV." << std::endl;
        return 1;
    }

    std::cout << "Generating Fractures..." << std::endl;
    sim.generateFractures();
    sim.generateHydraulicFractures();

    std::cout << "Processing Geometry..." << std::endl;
    sim.processGeometry();

    std::cout << "Building Connections..." << std::endl;
    sim.buildConnections();

    std::cout << "Setting up Wells..." << std::endl;
    // 方案 B：中心基质竖直井模型
    //sim.setupCenterMatrixVerticalWell(0.05, 0.0, 50.0);

    // 方案 A：人工裂缝井 / 水平井模型
    sim.setupWells();

    //sim.exportWells();

    sim.initState();

    // 构建气相真实气体 PVT 表（只构建一次；必须早于 preprocessStaticFMM() 和 run()）
    sim.buildGasPVTTable();

    std::cout << "Exporting Geometry for Visualization..." << std::endl;
    sim.exportStaticGeometry();

    std::cout << "Precomputing static FMM DTOF / tin / VOI..." << std::endl;
    sim.preprocessStaticFMM();

    std::cout << "Starting Simulation..." << std::endl;
    sim.run(1000.0);

    std::cout << "Done. Results saved to CSV." << std::endl;
    return 0;
}

