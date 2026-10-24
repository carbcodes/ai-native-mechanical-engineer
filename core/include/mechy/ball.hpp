// Ball flight with quadratic air drag.
//
// Model (world frame, z up, SI units):
//   a = g_vec - k * |v| * v,   g_vec = (0, 0, -g),
//   k = 0.5 * rho * Cd * A / m,  A = pi * (d/2)^2.
// Spin (Magnus lift) is ignored. For a tennis ball (m = 57 g, d = 67 mm,
// Cd = 0.55, rho = 1.2) k ~= 0.020 1/m, so drag is ~5% of gravity at 5 m/s.
#pragma once

#include <array>
#include <cstddef>
#include <vector>

#include "mechy/vec3.hpp"

namespace mechy {

struct BallParams {
    double mass = 0.057;      // kg
    double diameter = 0.067;  // m
    double cd = 0.55;         // drag coefficient
    double rho = 1.2;         // air density, kg/m^3
    double g = 9.81;          // m/s^2

    // Drag constant k [1/m] such that a_drag = -k |v| v.
    double k() const;
};

struct BallState {
    Vec3 p;
    Vec3 v;
};

// Acceleration of the ball at velocity v.
Vec3 ball_accel(const Vec3& v, double k, double g);

// One classical RK4 step of length h.
BallState ball_rk4_step(const BallState& s, double h, double k, double g);

// Integrate from (p0, v0) at time t0 to t0 + t_max with step dt.
// Returns rows [t, x, y, z]; the first row is t0 and the last row is the
// last step that does not pass t0 + t_max (plus a final partial step so the
// trajectory ends exactly at t0 + t_max).
std::vector<std::array<double, 4>> ball_predict(const Vec3& p0, const Vec3& v0, double dt,
                                                double t_max, double t0,
                                                const BallParams& bp);

struct BallFitResult {
    Vec3 p0;          // position at t0
    Vec3 v0;          // velocity at t0
    double t0 = 0.0;  // time of the earliest sample
    double residual = 0.0;  // RMS position error over all samples, m
    int iterations = 0;
};

// Nonlinear least-squares fit (Levenberg-Marquardt, numeric Jacobian) of the
// initial state (p0, v0) at the earliest sample time. points are rows
// [t, x, y, z]; at least 3 rows with at least 2 distinct times.
// Throws std::invalid_argument on bad input.
BallFitResult ball_fit(std::vector<std::array<double, 4>> points, const BallParams& bp);

struct InterceptResult {
    bool hit = false;
    double t = 0.0;
    Vec3 p;
    Vec3 v;
};

// First moment the trajectory (rows [t, x, y, z], M rows) enters the sphere
// (center, radius). The crossing is found exactly on the straight segment
// between consecutive rows; v is that segment's velocity.
InterceptResult ball_intercept(const double* traj, std::size_t rows, const Vec3& center,
                               double radius);

}  // namespace mechy
