#include "mechy/arm.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mechy {

namespace {
constexpr double kPi = 3.14159265358979323846;
constexpr double kDeg = kPi / 180.0;

double wrap(double a) {
    a = std::fmod(a + kPi, 2.0 * kPi);
    if (a < 0) a += 2.0 * kPi;
    return a - kPi;
}
}  // namespace

Limits4 default_limits() {
    return {{{-150 * kDeg, 150 * kDeg},
             {-10 * kDeg, 120 * kDeg},
             {-135 * kDeg, 135 * kDeg},
             {-90 * kDeg, 90 * kDeg}}};
}

Arm::Arm(double base_height, double upper, double fore, double hand, const Limits4& limits)
    : h_(base_height), a_(upper), b_(fore), c_(hand), lim_(limits) {
    if (!(upper > 0 && fore > 0 && hand >= 0))
        throw std::invalid_argument("Arm: link lengths must be positive (hand >= 0)");
    for (const auto& l : lim_)
        if (!(l[0] <= l[1])) throw std::invalid_argument("Arm: limit lower > upper");
}

bool Arm::within_limits(const Q4& q, double tol) const {
    for (int i = 0; i < 4; ++i)
        if (!(q[i] >= lim_[i][0] - tol && q[i] <= lim_[i][1] + tol)) return false;
    return true;
}

void Arm::fk(const Q4& q, Vec3& p, double& hand_pitch) const {
    const double s1 = q[1], s12 = q[1] + q[2], s123 = q[1] + q[2] + q[3];
    const double r = a_ * std::cos(s1) + b_ * std::cos(s12) + c_ * std::cos(s123);
    const double z = h_ + a_ * std::sin(s1) + b_ * std::sin(s12) + c_ * std::sin(s123);
    p = {r * std::cos(q[0]), r * std::sin(q[0]), z};
    hand_pitch = wrap(s123);
}

bool Arm::ik(const Vec3& target, double hand_pitch, Q4& q_out, const Q4* seed) const {
    if (!std::isfinite(target.x) || !std::isfinite(target.y) || !std::isfinite(target.z) ||
        !std::isfinite(hand_pitch))
        return false;

    // 1) Base yaw points the arm plane at the target. The arm only reaches
    //    "forward" in its plane (r >= 0); reaching over the top to the back is
    //    not considered, because hand pitch is defined relative to the
    //    outward direction and would change meaning.
    const double r = std::hypot(target.x, target.y);
    double yaw;
    if (r < 1e-9)  // directly above the base axis: yaw is free, keep seed
        yaw = seed ? (*seed)[0] : 0.0;
    else
        yaw = std::atan2(target.y, target.x);

    // 2) Wrist point in the arm plane (radial, vertical from shoulder).
    const double rw = r - c_ * std::cos(hand_pitch);
    const double zw = target.z - h_ - c_ * std::sin(hand_pitch);
    const double d2 = rw * rw + zw * zw;

    // 3) Two-link planar IK for (upper, fore).
    double c2 = (d2 - a_ * a_ - b_ * b_) / (2.0 * a_ * b_);
    constexpr double kTol = 1e-9;
    if (c2 > 1.0 + kTol || c2 < -1.0 - kTol) return false;
    c2 = std::clamp(c2, -1.0, 1.0);
    const double q2abs = std::acos(c2);

    bool found = false;
    double best = std::numeric_limits<double>::infinity();
    const Q4 ref = seed ? *seed : Q4{yaw, 0.0, 0.0, 0.0};
    for (double sgn : {1.0, -1.0}) {
        const double q2 = sgn * q2abs;
        const double q1 = std::atan2(zw, rw) - std::atan2(b_ * std::sin(q2), a_ + b_ * std::cos(q2));
        Q4 q{yaw, wrap(q1), q2, 0.0};
        q[3] = wrap(hand_pitch - q[1] - q[2]);
        if (!within_limits(q)) continue;
        double cost = 0.0;
        for (int i = 0; i < 4; ++i) cost += (q[i] - ref[i]) * (q[i] - ref[i]);
        if (cost < best) {
            best = cost;
            q_out = q;
            found = true;
        }
        if (q2abs == 0.0) break;  // both branches identical
    }
    if (found)  // clamp tiny tolerance overshoots back inside the limits
        for (int i = 0; i < 4; ++i) q_out[i] = std::clamp(q_out[i], lim_[i][0], lim_[i][1]);
    return found;
}

}  // namespace mechy
