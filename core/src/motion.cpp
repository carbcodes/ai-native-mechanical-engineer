#include "mechy/motion.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace mechy {

namespace {
constexpr double kTwoPi = 6.28318530717958647692;
constexpr double kInf = std::numeric_limits<double>::infinity();
constexpr int kGrid = 48;         // speed cells in the acceleration phase
constexpr double kCapFrac = 0.95; // cruise at 95% of the zero-accel speed
}  // namespace

Stepper::Stepper(std::vector<std::pair<double, double>> curve, double gear_ratio,
                 double rotor_inertia, double max_speed_rps)
    : curve_(std::move(curve)), ratio_(gear_ratio), j_rotor_(rotor_inertia) {
    if (curve_.empty()) throw std::invalid_argument("Stepper: torque curve is empty");
    for (std::size_t i = 0; i < curve_.size(); ++i) {
        if (!(curve_[i].first >= 0.0) || !(curve_[i].second >= 0.0))
            throw std::invalid_argument("Stepper: curve speeds and torques must be >= 0");
        if (i > 0 && !(curve_[i].first > curve_[i - 1].first))
            throw std::invalid_argument("Stepper: curve speeds must be strictly increasing");
    }
    if (!(gear_ratio > 0.0)) throw std::invalid_argument("Stepper: gear_ratio must be > 0");
    if (!(rotor_inertia >= 0.0)) throw std::invalid_argument("Stepper: rotor_inertia must be >= 0");
    max_rps_ = max_speed_rps > 0.0 ? max_speed_rps : curve_.back().first;
    if (!(max_rps_ > 0.0)) throw std::invalid_argument("Stepper: max speed must be > 0");
}

double Stepper::torque_at(double rps) const {
    rps = std::fabs(rps);
    if (rps > max_rps_ * (1.0 + 1e-12)) return 0.0;
    if (rps <= curve_.front().first) return curve_.front().second;
    if (rps >= curve_.back().first) return curve_.back().second;
    for (std::size_t i = 1; i < curve_.size(); ++i) {
        if (rps <= curve_[i].first) {
            const auto& a = curve_[i - 1];
            const auto& b = curve_[i];
            const double u = (rps - a.first) / (b.first - a.first);
            return a.second + u * (b.second - a.second);
        }
    }
    return curve_.back().second;
}

double Stepper::max_joint_speed() const { return kTwoPi * max_rps_ / ratio_; }

double min_move_time(const Stepper& m, double load_inertia, double load_torque,
                     double dist_joint, double s) {
    const double N = m.gear_ratio();
    const double D = std::fabs(dist_joint) * N;  // motor radians
    if (D == 0.0) return 0.0;
    const double J = m.rotor_inertia() + std::max(0.0, load_inertia) / (N * N);
    const double tl = std::fabs(load_torque) / N;
    if (!(J > 0.0)) throw std::invalid_argument("min_move_time: zero total inertia");

    // Net accelerating torque available at motor speed w (rad/s).
    auto net = [&](double w) { return s * m.torque_at(w / kTwoPi) - tl; };
    if (!(net(0.0) > 0.0)) return kInf;

    // Find the cruise speed w_c: first zero of net() on [0, w_max], else w_max.
    // net() is piecewise linear in speed, so check it at the curve knots.
    const double w_max = kTwoPi * m.max_speed_rps();
    double w_c = w_max;
    {
        std::vector<double> knots{0.0};
        for (const auto& pt : m.curve())
            if (pt.first > 0.0 && pt.first * kTwoPi < w_max) knots.push_back(pt.first * kTwoPi);
        knots.push_back(w_max);
        for (std::size_t i = 1; i < knots.size(); ++i) {
            const double fb = net(knots[i] * (1.0 - 1e-12));
            if (fb <= 0.0) {
                const double fa = net(knots[i - 1]);
                const double w0 = knots[i - 1] + (knots[i] - knots[i - 1]) * fa / (fa - fb);
                w_c = kCapFrac * w0;
                break;
            }
        }
    }

    // Integrate the acceleration phase from rest to w_c.
    const double dw = w_c / kGrid;
    double t_acc = 0.0, d_acc = 0.0;
    const double half = 0.5 * D;
    for (int k = 0; k < kGrid; ++k) {
        const double wa = k * dw, wb = wa + dw;
        const double alpha = net(wa + 0.5 * dw) / J;  // > 0 below the zero
        const double dd = (wb * wb - wa * wa) / (2.0 * alpha);
        if (d_acc + dd >= half) {
            // Peak speed reached inside this cell: bang-bang, no cruise.
            const double wp = std::sqrt(wa * wa + 2.0 * alpha * (half - d_acc));
            return 2.0 * (t_acc + (wp - wa) / alpha);
        }
        d_acc += dd;
        t_acc += dw / alpha;
    }
    // Bang-coast-bang: accelerate, cruise at w_c, brake.
    return 2.0 * t_acc + (D - 2.0 * d_acc) / w_c;
}

double required_torque_fraction(const Stepper& m, double load_inertia, double load_torque,
                                double dist_joint, double t_avail, double s_max,
                                double s_known, double t_known) {
    if (dist_joint == 0.0) return 0.0;
    if (!(t_avail > 0.0)) return kInf;
    // Lowest fraction that can even hold the load at standstill.
    const double t0 = m.torque_at(0.0);
    double lo = t0 > 0.0 ? std::fabs(load_torque) / m.gear_ratio() / t0 : 0.0;
    double hi = s_max;
    // Use a known (fraction, time) pair to halve the bracket: this also makes
    // "fraction <= safety" agree exactly with "time at safety <= t_avail".
    if (s_known > 0.0 && s_known < s_max) {
        if (t_known <= t_avail)
            hi = s_known;
        else
            lo = std::max(lo, s_known);
    }
    if (hi == s_max && min_move_time(m, load_inertia, load_torque, dist_joint, s_max) > t_avail)
        return kInf;
    while (hi - lo > 1e-5) {
        const double mid = 0.5 * (lo + hi);
        if (min_move_time(m, load_inertia, load_torque, dist_joint, mid) <= t_avail)
            hi = mid;
        else
            lo = mid;
    }
    return hi;  // conservative end of the bracket
}

MoveResult plan_move(const std::vector<double>& q0, const std::vector<double>& q1,
                     const std::vector<Stepper>& motors, const std::vector<double>& load_inertia,
                     const std::vector<double>& load_torque, double t_avail, double safety) {
    const std::size_t n = motors.size();
    if (q0.size() != n || q1.size() != n || load_inertia.size() != n || load_torque.size() != n)
        throw std::invalid_argument("plan_move: q0, q1, motors, load_inertia, load_torque sizes differ");
    MoveResult r;
    r.t_per_joint.resize(n);
    r.peak_torque_frac.resize(n);
    r.t_needed = 0.0;
    for (std::size_t i = 0; i < n; ++i) {
        const double d = q1[i] - q0[i];
        r.t_per_joint[i] = min_move_time(motors[i], load_inertia[i], load_torque[i], d, safety);
        r.peak_torque_frac[i] =
            required_torque_fraction(motors[i], load_inertia[i], load_torque[i], d, t_avail, 4.0,
                                     safety, r.t_per_joint[i]);
        if (r.limiting_joint < 0 || r.t_per_joint[i] > r.t_needed) {
            r.t_needed = r.t_per_joint[i];
            r.limiting_joint = static_cast<int>(i);
        }
    }
    r.feasible = std::isfinite(r.t_needed) && r.t_needed <= t_avail;
    return r;
}

}  // namespace mechy
