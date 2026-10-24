// Stepper-limited point-to-point joint moves.
//
// Physical model, per joint (everything referred to the MOTOR shaft):
//   N        gear (belt) reduction, joint angle q = motor angle / N.
//   J_m      = J_rotor + J_load / N^2       effective inertia at the motor,
//            J_load is the inertia the joint drives, about the joint axis.
//            (Equivalently J_rotor * N^2 + J_load at the joint side.)
//   tau_l    = |tau_load| / N               static load torque (e.g. gravity)
//            at the motor; it is assumed to oppose motion in both the
//            accelerating and the braking phase (conservative).
//   T(w)     pull-out torque at motor speed w, piecewise-linear interpolation
//            of the datasheet curve, 0 above the motor's max speed.
//   s        fraction of T(w) we allow ourselves to use (0.7 by default) so
//            the motor keeps a margin against skipped steps (resonance,
//            supply sag, curve uncertainty).
//   motor acceleration limit   alpha(w) = (s * T(w) - tau_l) / J_m.
// Gear/belt losses and friction are ignored (efficiency 1).
//
// Time-optimal rest-to-rest move of distance D (motor radians): accelerate at
// alpha(w) until either half the distance is used (bang-bang) or the cruise
// speed w_c is reached (bang-coast-bang), then mirror the acceleration phase
// to brake. Braking is assumed to need the same torque as accelerating
// (a stepper must actively brake the load). w_c is the motor max speed, or
// 95% of the speed where alpha falls to zero, whichever is lower (the last 5%
// would take very long for little gain).
//
// The acceleration phase is integrated numerically on a speed grid with
// alpha held at its mid-cell value, so time and distance per cell are exact
// for that constant alpha.
#pragma once

#include <array>
#include <utility>
#include <vector>

namespace mechy {

class Stepper {
public:
    // curve: rows (rev/s, N*m), increasing speed. max_speed_rps <= 0 means
    // "last curve point".
    Stepper(std::vector<std::pair<double, double>> curve, double gear_ratio,
            double rotor_inertia, double max_speed_rps = -1.0);

    // Pull-out torque at motor speed rps (N*m). Below the first point the
    // first value is used; above max_speed_rps it is 0.
    double torque_at(double rps) const;

    const std::vector<std::pair<double, double>>& curve() const { return curve_; }
    double gear_ratio() const { return ratio_; }
    double rotor_inertia() const { return j_rotor_; }
    double max_speed_rps() const { return max_rps_; }
    // Max joint speed, rad/s.
    double max_joint_speed() const;

private:
    std::vector<std::pair<double, double>> curve_;
    double ratio_, j_rotor_, max_rps_;
};

// Minimum time for one joint to move dist_joint radians rest-to-rest using
// at most fraction s of pull-out torque. Returns +inf if impossible
// (load torque >= s * T(0)).
double min_move_time(const Stepper& m, double load_inertia, double load_torque,
                     double dist_joint, double s);

// Smallest torque fraction s for which the joint finishes within t_avail
// (bisection, 1e-5 absolute, rounded up). 0 for a zero-length move, +inf if
// even s = s_max cannot make it. Optionally pass an already computed
// t_known = min_move_time(..., s_known) to narrow the search.
double required_torque_fraction(const Stepper& m, double load_inertia, double load_torque,
                                double dist_joint, double t_avail, double s_max = 4.0,
                                double s_known = -1.0, double t_known = 0.0);

struct MoveResult {
    bool feasible = false;
    double t_needed = 0.0;             // max over joints of t_per_joint
    std::vector<double> t_per_joint;   // min time at the safety fraction
    std::vector<double> peak_torque_frac;  // see required_torque_fraction
    int limiting_joint = -1;           // argmax of t_per_joint
};

// q0, q1, load_inertia, load_torque and motors all have one entry per joint.
MoveResult plan_move(const std::vector<double>& q0, const std::vector<double>& q1,
                     const std::vector<Stepper>& motors, const std::vector<double>& load_inertia,
                     const std::vector<double>& load_torque, double t_avail,
                     double safety = 0.7);

}  // namespace mechy
