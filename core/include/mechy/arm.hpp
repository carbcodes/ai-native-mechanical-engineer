// 4-DOF arm kinematics: base yaw + planar 3-link (shoulder, elbow, wrist).
//
// Conventions (all angles in radians):
//   q[0] base yaw about world +z; 0 points the arm along world +x.
//   q[1] shoulder elevation of the upper arm above horizontal (0 = straight
//        out, +pi/2 = straight up).
//   q[2] elbow angle, relative to the upper arm, positive = bend up.
//   q[3] wrist angle, relative to the forearm, positive = bend up.
//   hand pitch phi = q1 + q2 + q3 = elevation of the hand link above
//        horizontal, measured in the arm's vertical plane pointing away from
//        the base axis (wrapped to [-pi, pi]).
// The tool point is the end of the hand link (catcher centre). The shoulder
// axis sits on the base axis at height base_height.
// Note: positive elevation is a rotation about the arm-plane -y axis in a
// right-handed frame; whoever writes the MJCF must flip signs accordingly.
#pragma once

#include <array>

#include "mechy/vec3.hpp"

namespace mechy {

using Q4 = std::array<double, 4>;
using Limits4 = std::array<std::array<double, 2>, 4>;

// Joint limits from contracts.md section 1.3 (degrees converted to radians).
Limits4 default_limits();

class Arm {
public:
    Arm(double base_height, double upper, double fore, double hand,
        const Limits4& limits = default_limits());

    // Analytic IK. Returns false if the target is out of reach or every
    // geometric solution violates the joint limits. Among valid solutions
    // (elbow up / elbow down) it picks the one closest to seed, or to the
    // zero pose if seed is null.
    bool ik(const Vec3& target, double hand_pitch, Q4& q_out, const Q4* seed = nullptr) const;

    void fk(const Q4& q, Vec3& p, double& hand_pitch) const;

    bool reachable(const Vec3& target, double hand_pitch) const {
        Q4 q;
        return ik(target, hand_pitch, q);
    }

    bool within_limits(const Q4& q, double tol = 1e-9) const;

    double base_height() const { return h_; }
    double upper() const { return a_; }
    double fore() const { return b_; }
    double hand() const { return c_; }
    const Limits4& limits() const { return lim_; }

private:
    double h_, a_, b_, c_;
    Limits4 lim_;
};

}  // namespace mechy
