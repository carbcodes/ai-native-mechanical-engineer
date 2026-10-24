#include "mechy/ball.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mechy {

namespace {
constexpr double kPi = 3.14159265358979323846;
// Largest RK4 step used inside the fitter (s). Flight times are < 1.5 s, so
// this is at most ~750 steps per simulated trajectory.
constexpr double kFitStep = 0.002;
}  // namespace

double BallParams::k() const {
    const double area = kPi * 0.25 * diameter * diameter;
    return 0.5 * rho * cd * area / mass;
}

Vec3 ball_accel(const Vec3& v, double k, double g) {
    const double s = v.norm();
    return Vec3{-k * s * v.x, -k * s * v.y, -g - k * s * v.z};
}

BallState ball_rk4_step(const BallState& s, double h, double k, double g) {
    // State derivative: (p', v') = (v, a(v)). a does not depend on p.
    const Vec3 k1v = s.v;
    const Vec3 k1a = ball_accel(s.v, k, g);
    const Vec3 k2v = s.v + k1a * (0.5 * h);
    const Vec3 k2a = ball_accel(k2v, k, g);
    const Vec3 k3v = s.v + k2a * (0.5 * h);
    const Vec3 k3a = ball_accel(k3v, k, g);
    const Vec3 k4v = s.v + k3a * h;
    const Vec3 k4a = ball_accel(k4v, k, g);
    BallState out;
    out.p = s.p + (k1v + 2.0 * k2v + 2.0 * k3v + k4v) * (h / 6.0);
    out.v = s.v + (k1a + 2.0 * k2a + 2.0 * k3a + k4a) * (h / 6.0);
    return out;
}

std::vector<std::array<double, 4>> ball_predict(const Vec3& p0, const Vec3& v0, double dt,
                                                double t_max, double t0,
                                                const BallParams& bp) {
    if (!(dt > 0.0)) throw std::invalid_argument("dt must be > 0");
    if (!(t_max >= 0.0)) throw std::invalid_argument("t_max must be >= 0");
    const double k = bp.k();
    const auto n_full = static_cast<std::size_t>(std::floor(t_max / dt + 1e-9));
    std::vector<std::array<double, 4>> out;
    out.reserve(n_full + 2);
    BallState s{p0, v0};
    double t = 0.0;
    out.push_back({t0, s.p.x, s.p.y, s.p.z});
    for (std::size_t i = 0; i < n_full; ++i) {
        s = ball_rk4_step(s, dt, k, bp.g);
        t = static_cast<double>(i + 1) * dt;  // avoid accumulated rounding
        out.push_back({t0 + t, s.p.x, s.p.y, s.p.z});
    }
    const double rest = t_max - t;
    if (rest > 1e-9 * dt) {
        s = ball_rk4_step(s, rest, k, bp.g);
        out.push_back({t0 + t_max, s.p.x, s.p.y, s.p.z});
    }
    return out;
}

namespace {

// Simulate from (p0, v0) at tau = 0 and write positions at each sample time
// tau[j] (sorted, >= 0) into out (3 * n doubles).
void simulate_at(const double* params, const std::vector<double>& tau, double k, double g,
                 std::vector<double>& out) {
    BallState s{{params[0], params[1], params[2]}, {params[3], params[4], params[5]}};
    double t = 0.0;
    for (std::size_t j = 0; j < tau.size(); ++j) {
        const double gap = tau[j] - t;
        if (gap > 0.0) {
            const int n = std::max(1, static_cast<int>(std::ceil(gap / kFitStep)));
            const double h = gap / n;
            for (int i = 0; i < n; ++i) s = ball_rk4_step(s, h, k, g);
            t = tau[j];
        }
        out[3 * j + 0] = s.p.x;
        out[3 * j + 1] = s.p.y;
        out[3 * j + 2] = s.p.z;
    }
}

// Solve the 6x6 system A x = b in place (Gaussian elimination, partial
// pivoting). Returns false if A is singular.
bool solve6(double A[6][6], double b[6], double x[6]) {
    for (int c = 0; c < 6; ++c) {
        int piv = c;
        for (int r = c + 1; r < 6; ++r)
            if (std::fabs(A[r][c]) > std::fabs(A[piv][c])) piv = r;
        if (std::fabs(A[piv][c]) < 1e-300) return false;
        if (piv != c) {
            for (int j = 0; j < 6; ++j) std::swap(A[c][j], A[piv][j]);
            std::swap(b[c], b[piv]);
        }
        for (int r = c + 1; r < 6; ++r) {
            const double f = A[r][c] / A[c][c];
            for (int j = c; j < 6; ++j) A[r][j] -= f * A[c][j];
            b[r] -= f * b[c];
        }
    }
    for (int r = 5; r >= 0; --r) {
        double acc = b[r];
        for (int j = r + 1; j < 6; ++j) acc -= A[r][j] * x[j];
        x[r] = acc / A[r][r];
    }
    return true;
}

double sum_sq_residual(const std::vector<double>& sim, const std::vector<double>& meas) {
    double s = 0.0;
    for (std::size_t i = 0; i < sim.size(); ++i) {
        const double d = sim[i] - meas[i];
        s += d * d;
    }
    return s;
}

}  // namespace

BallFitResult ball_fit(std::vector<std::array<double, 4>> points, const BallParams& bp) {
    const std::size_t n = points.size();
    if (n < 3) throw std::invalid_argument("ball_fit needs at least 3 points");
    std::sort(points.begin(), points.end(),
              [](const auto& a, const auto& b) { return a[0] < b[0]; });
    const double t0 = points.front()[0];
    if (!(points.back()[0] - t0 > 0.0))
        throw std::invalid_argument("ball_fit needs at least 2 distinct sample times");
    for (const auto& r : points)
        for (double v : r)
            if (!std::isfinite(v)) throw std::invalid_argument("ball_fit: non-finite input");

    std::vector<double> tau(n), meas(3 * n);
    for (std::size_t j = 0; j < n; ++j) {
        tau[j] = points[j][0] - t0;
        meas[3 * j + 0] = points[j][1];
        meas[3 * j + 1] = points[j][2];
        meas[3 * j + 2] = points[j][3];
    }

    // Initial guess: drag-free ballistic fit, linear in (p0, v0) per axis:
    //   x(tau) - 0.5 * g_axis * tau^2 = p0 + v0 * tau.
    double params[6];
    {
        double S0 = 0, S1 = 0, S2 = 0;
        for (double t : tau) {
            S0 += 1;
            S1 += t;
            S2 += t * t;
        }
        const double det = S0 * S2 - S1 * S1;
        for (int ax = 0; ax < 3; ++ax) {
            double B0 = 0, B1 = 0;
            for (std::size_t j = 0; j < n; ++j) {
                double y = meas[3 * j + ax];
                if (ax == 2) y += 0.5 * bp.g * tau[j] * tau[j];
                B0 += y;
                B1 += y * tau[j];
            }
            params[ax] = (S2 * B0 - S1 * B1) / det;
            params[3 + ax] = (S0 * B1 - S1 * B0) / det;
        }
    }

    const double k = bp.k();
    std::vector<double> sim(3 * n), sim_eps(3 * n), J(3 * n * 6);
    simulate_at(params, tau, k, bp.g, sim);
    double cost = sum_sq_residual(sim, meas);
    double lambda = 1e-3;
    int it = 0;
    for (; it < 30; ++it) {
        // Numeric Jacobian, forward differences.
        for (int p = 0; p < 6; ++p) {
            double pp[6];
            std::copy(params, params + 6, pp);
            const double h = 1e-6 * std::max(1.0, std::fabs(params[p]));
            pp[p] += h;
            simulate_at(pp, tau, k, bp.g, sim_eps);
            for (std::size_t i = 0; i < 3 * n; ++i) J[i * 6 + p] = (sim_eps[i] - sim[i]) / h;
        }
        double JtJ[6][6] = {}, Jtr[6] = {};
        for (std::size_t i = 0; i < 3 * n; ++i) {
            const double r = sim[i] - meas[i];
            for (int a = 0; a < 6; ++a) {
                Jtr[a] += J[i * 6 + a] * r;
                for (int b = 0; b < 6; ++b) JtJ[a][b] += J[i * 6 + a] * J[i * 6 + b];
            }
        }
        bool improved = false;
        double step_norm = 0.0;
        for (int tries = 0; tries < 10 && !improved; ++tries) {
            double A[6][6], b[6], dx[6];
            for (int a = 0; a < 6; ++a) {
                for (int c = 0; c < 6; ++c) A[a][c] = JtJ[a][c];
                A[a][a] += lambda * std::max(JtJ[a][a], 1e-12);
                b[a] = -Jtr[a];
            }
            if (!solve6(A, b, dx)) {
                lambda *= 10.0;
                continue;
            }
            double trial[6];
            step_norm = 0.0;
            for (int a = 0; a < 6; ++a) {
                trial[a] = params[a] + dx[a];
                step_norm += dx[a] * dx[a];
            }
            simulate_at(trial, tau, k, bp.g, sim_eps);
            const double c = sum_sq_residual(sim_eps, meas);
            if (c <= cost) {
                std::copy(trial, trial + 6, params);
                sim.swap(sim_eps);
                cost = c;
                lambda = std::max(lambda * 0.1, 1e-12);
                improved = true;
            } else {
                lambda *= 10.0;
            }
        }
        if (!improved || std::sqrt(step_norm) < 1e-10) break;
    }

    BallFitResult res;
    res.p0 = {params[0], params[1], params[2]};
    res.v0 = {params[3], params[4], params[5]};
    res.t0 = t0;
    res.residual = std::sqrt(cost / static_cast<double>(n));
    res.iterations = it + 1;
    return res;
}

InterceptResult ball_intercept(const double* traj, std::size_t rows, const Vec3& center,
                               double radius) {
    InterceptResult res;
    if (rows == 0 || !(radius >= 0.0)) return res;
    auto pos = [&](std::size_t i) { return Vec3{traj[4 * i + 1], traj[4 * i + 2], traj[4 * i + 3]}; };
    auto seg_vel = [&](std::size_t i) {  // velocity of segment i -> i+1
        const double dt = traj[4 * (i + 1)] - traj[4 * i];
        return dt > 0.0 ? (pos(i + 1) - pos(i)) / dt : Vec3{};
    };
    const double r2 = radius * radius;
    Vec3 prev = pos(0);
    if ((prev - center).dot(prev - center) <= r2) {
        res.hit = true;
        res.t = traj[0];
        res.p = prev;
        res.v = rows > 1 ? seg_vel(0) : Vec3{};
        return res;
    }
    // Walk the segments. A segment counts as a hit if its straight line
    // enters the sphere anywhere in [prev, cur], so a fast ball cannot skip
    // through a small sphere between two samples.
    for (std::size_t i = 1; i < rows; ++i) {
        const Vec3 cur = pos(i);
        // Solve |prev + s * d - c|^2 = r^2 for the first s in [0, 1].
        const Vec3 d = cur - prev;
        const Vec3 f = prev - center;
        const double A = d.dot(d);
        const double B = 2.0 * f.dot(d);
        const double C = f.dot(f) - r2;  // > 0: prev is outside
        const double disc = B * B - 4.0 * A * C;
        if (A > 0.0 && disc >= 0.0) {
            const double s = (-B - std::sqrt(disc)) / (2.0 * A);
            if (s >= 0.0 && s <= 1.0) {
                const double ta = traj[4 * (i - 1)], tb = traj[4 * i];
                res.hit = true;
                res.t = ta + s * (tb - ta);
                res.p = prev + d * s;
                res.v = seg_vel(i - 1);
                return res;
            }
        }
        prev = cur;
    }
    return res;
}

}  // namespace mechy
