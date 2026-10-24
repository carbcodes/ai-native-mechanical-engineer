// pybind11 bindings: the `mechy_core` Python module (contracts.md section 7).
#include <pybind11/numpy.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <algorithm>
#include <cmath>
#include <thread>
#include <vector>

#include "mechy/arm.hpp"
#include "mechy/ball.hpp"
#include "mechy/motion.hpp"

namespace py = pybind11;
using namespace mechy;

using DArray = py::array_t<double, py::array::c_style | py::array::forcecast>;

namespace {

Vec3 to_vec3(const DArray& a, const char* name) {
    if (a.size() != 3) throw py::value_error(std::string(name) + " must have 3 elements");
    const double* d = a.data();
    return {d[0], d[1], d[2]};
}

py::array_t<double> from_vec3(const Vec3& v) {
    py::array_t<double> out(3);
    auto m = out.mutable_unchecked<1>();
    m(0) = v.x;
    m(1) = v.y;
    m(2) = v.z;
    return out;
}

template <std::size_t N>
py::array_t<double> from_array(const std::array<double, N>& v) {
    py::array_t<double> out(N);
    std::copy(v.begin(), v.end(), out.mutable_data());
    return out;
}

py::array_t<double> from_vector(const std::vector<double>& v) {
    py::array_t<double> out(static_cast<py::ssize_t>(v.size()));
    std::copy(v.begin(), v.end(), out.mutable_data());
    return out;
}

std::vector<double> to_vector(const DArray& a, std::size_t n, const char* name) {
    if (static_cast<std::size_t>(a.size()) != n)
        throw py::value_error(std::string(name) + " must have " + std::to_string(n) + " elements");
    return std::vector<double>(a.data(), a.data() + n);
}

Q4 to_q4(const DArray& a, const char* name) {
    if (a.size() != 4) throw py::value_error(std::string(name) + " must have 4 elements");
    return {a.data()[0], a.data()[1], a.data()[2], a.data()[3]};
}

BallParams make_params(double mass, double diameter, double cd, double rho, double g) {
    BallParams bp;
    bp.mass = mass;
    bp.diameter = diameter;
    bp.cd = cd;
    bp.rho = rho;
    bp.g = g;
    if (!(mass > 0 && diameter > 0 && cd >= 0 && rho >= 0))
        throw py::value_error("ball parameters must be positive");
    return bp;
}

Limits4 to_limits(const py::object& obj) {
    if (obj.is_none()) return default_limits();
    DArray a = DArray::ensure(obj);
    if (!a || a.ndim() != 2 || a.shape(0) != 4 || a.shape(1) != 2)
        throw py::value_error("limits must have shape (4, 2) [lower, upper] in radians");
    Limits4 l;
    for (int i = 0; i < 4; ++i) l[i] = {a.at(i, 0), a.at(i, 1)};
    return l;
}

py::array_t<double> limits_array(const Limits4& l) {
    py::array_t<double> out({4, 2});
    auto m = out.mutable_unchecked<2>();
    for (int i = 0; i < 4; ++i) {
        m(i, 0) = l[i][0];
        m(i, 1) = l[i][1];
    }
    return out;
}

Stepper make_stepper(const DArray& curve, double gear_ratio, double rotor_inertia,
                     double max_speed_rps) {
    if (curve.ndim() != 2 || curve.shape(1) != 2)
        throw py::value_error("torque_curve must have shape (K, 2) [rev/s, N*m]");
    std::vector<std::pair<double, double>> c;
    for (py::ssize_t i = 0; i < curve.shape(0); ++i) c.emplace_back(curve.at(i, 0), curve.at(i, 1));
    try {
        return Stepper(std::move(c), gear_ratio, rotor_inertia, max_speed_rps);
    } catch (const std::invalid_argument& e) {
        throw py::value_error(e.what());
    }
}

// Per-joint optional array: None -> zeros, else n values.
std::vector<double> optional_joint_vec(const py::object& obj, std::size_t n, const char* name) {
    if (obj.is_none()) return std::vector<double>(n, 0.0);
    return to_vector(DArray::ensure(obj), n, name);
}

// Broadcast an argument that is either (J,) or (N, J) to N rows of J.
std::vector<double> rows_of(const DArray& a, std::size_t N, std::size_t J, const char* name) {
    std::vector<double> out(N * J);
    if (a.ndim() == 1 && static_cast<std::size_t>(a.shape(0)) == J) {
        for (std::size_t r = 0; r < N; ++r) std::copy(a.data(), a.data() + J, out.begin() + r * J);
    } else if (a.ndim() == 2 && static_cast<std::size_t>(a.shape(0)) == N &&
               static_cast<std::size_t>(a.shape(1)) == J) {
        std::copy(a.data(), a.data() + N * J, out.begin());
    } else {
        throw py::value_error(std::string(name) + " must have shape (" + std::to_string(J) +
                              ",) or (" + std::to_string(N) + ", " + std::to_string(J) + ")");
    }
    return out;
}

py::dict move_to_dict(const MoveResult& r) {
    py::dict d;
    d["feasible"] = r.feasible;
    d["t_needed"] = r.t_needed;
    d["t_per_joint"] = from_vector(r.t_per_joint);
    d["peak_torque_frac"] = from_vector(r.peak_torque_frac);
    d["limiting_joint"] = r.limiting_joint;
    return d;
}

}  // namespace

PYBIND11_MODULE(_mechy_core, m) {
    m.doc() = "Mechy core math: ball flight, 4-DOF arm kinematics, stepper-limited moves.";

    // ------------------------------------------------------------------ ball
    m.def(
        "ball_drag_k",
        [](double mass, double diameter, double cd, double rho) {
            return make_params(mass, diameter, cd, rho, 9.81).k();
        },
        py::arg("mass") = 0.057, py::arg("diameter") = 0.067, py::arg("cd") = 0.55,
        py::arg("rho") = 1.2, "Drag constant k [1/m] with a_drag = -k |v| v.");

    m.def(
        "ball_fit",
        [](const DArray& points, double mass, double diameter, double cd, double rho, double g) {
            if (points.ndim() != 2 || points.shape(1) != 4)
                throw py::value_error("points must have shape (N, 4) [t, x, y, z]");
            std::vector<std::array<double, 4>> pts(points.shape(0));
            for (py::ssize_t i = 0; i < points.shape(0); ++i)
                for (int j = 0; j < 4; ++j) pts[i][j] = points.at(i, j);
            const BallParams bp = make_params(mass, diameter, cd, rho, g);
            BallFitResult r;
            try {
                py::gil_scoped_release nogil;
                r = ball_fit(std::move(pts), bp);
            } catch (const std::invalid_argument& e) {
                throw py::value_error(e.what());
            }
            py::dict d;
            d["p0"] = from_vec3(r.p0);
            d["v0"] = from_vec3(r.v0);
            d["t0"] = r.t0;
            d["residual"] = r.residual;
            d["iterations"] = r.iterations;
            return d;
        },
        py::arg("points"), py::arg("mass") = 0.057, py::arg("diameter") = 0.067,
        py::arg("cd") = 0.55, py::arg("rho") = 1.2, py::arg("g") = 9.81,
        "Least-squares fit of the ball's initial state under quadratic drag.\n"
        "points: (N, 4) [t, x, y, z], N >= 3. Returns dict(p0, v0, t0, residual, iterations):\n"
        "position/velocity at t0 (the earliest sample time) and RMS position error in m.");

    m.def(
        "ball_predict",
        [](const DArray& p0, const DArray& v0, double dt, double t_max, double mass,
           double diameter, double cd, double rho, double g, double t0) {
            const Vec3 p = to_vec3(p0, "p0"), v = to_vec3(v0, "v0");
            const BallParams bp = make_params(mass, diameter, cd, rho, g);
            std::vector<std::array<double, 4>> rows;
            try {
                py::gil_scoped_release nogil;
                rows = ball_predict(p, v, dt, t_max, t0, bp);
            } catch (const std::invalid_argument& e) {
                throw py::value_error(e.what());
            }
            py::array_t<double> out({static_cast<py::ssize_t>(rows.size()), py::ssize_t(4)});
            std::copy(&rows[0][0], &rows[0][0] + rows.size() * 4, out.mutable_data());
            return out;
        },
        py::arg("p0"), py::arg("v0"), py::arg("dt") = 0.002, py::arg("t_max") = 2.0,
        py::arg("mass") = 0.057, py::arg("diameter") = 0.067, py::arg("cd") = 0.55,
        py::arg("rho") = 1.2, py::arg("g") = 9.81, py::arg("t0") = 0.0,
        "RK4 ball flight from (p0, v0) at time t0. Returns (M, 4) [t, x, y, z].");

    m.def(
        "ball_intercept",
        [](const DArray& traj, const DArray& center, double radius) -> py::object {
            if (traj.ndim() != 2 || traj.shape(1) != 4)
                throw py::value_error("traj must have shape (M, 4) [t, x, y, z]");
            const Vec3 c = to_vec3(center, "center");
            const InterceptResult r =
                ball_intercept(traj.data(), static_cast<std::size_t>(traj.shape(0)), c, radius);
            if (!r.hit) return py::none();
            py::dict d;
            d["t"] = r.t;
            d["p"] = from_vec3(r.p);
            d["v"] = from_vec3(r.v);
            return std::move(d);
        },
        py::arg("traj"), py::arg("center"), py::arg("radius"),
        "First time the trajectory enters the sphere -> dict(t, p, v) or None.");

    // ------------------------------------------------------------------- arm
    py::class_<Arm>(m, "Arm", "4-DOF arm: base yaw + planar shoulder/elbow/wrist pitch.")
        .def(py::init([](double base_height, double upper, double fore, double hand,
                         const py::object& limits) {
                 try {
                     return Arm(base_height, upper, fore, hand, to_limits(limits));
                 } catch (const std::invalid_argument& e) {
                     throw py::value_error(e.what());
                 }
             }),
             py::arg("base_height") = 0.12, py::arg("upper") = 0.22, py::arg("fore") = 0.20,
             py::arg("hand") = 0.06, py::arg("limits") = py::none(),
             "limits: (4, 2) [lower, upper] radians; default = contracts.md 1.3.")
        .def(
            "ik",
            [](const Arm& a, const DArray& target, double hand_pitch,
               const py::object& seed) -> py::object {
                const Vec3 t = to_vec3(target, "target_xyz");
                Q4 q, s;
                const Q4* sp = nullptr;
                if (!seed.is_none()) {
                    s = to_q4(DArray::ensure(seed), "seed");
                    sp = &s;
                }
                if (!a.ik(t, hand_pitch, q, sp)) return py::none();
                return from_array(q);
            },
            py::arg("target_xyz"), py::arg("hand_pitch"), py::arg("seed") = py::none(),
            "Analytic IK -> (4,) joint angles or None if unreachable / outside limits.\n"
            "seed: optional (4,) pose; the valid solution closest to it is returned.")
        .def(
            "fk",
            [](const Arm& a, const DArray& q) {
                Vec3 p;
                double pitch;
                a.fk(to_q4(q, "q"), p, pitch);
                return py::make_tuple(from_vec3(p), pitch);
            },
            py::arg("q"), "Forward kinematics -> (p (3,), hand_pitch).")
        .def(
            "reachable",
            [](const Arm& a, const DArray& target, double hand_pitch) {
                return a.reachable(to_vec3(target, "target_xyz"), hand_pitch);
            },
            py::arg("target_xyz"), py::arg("hand_pitch"))
        .def(
            "within_limits", [](const Arm& a, const DArray& q) { return a.within_limits(to_q4(q, "q")); },
            py::arg("q"))
        .def_property_readonly("base_height", &Arm::base_height)
        .def_property_readonly("upper", &Arm::upper)
        .def_property_readonly("fore", &Arm::fore)
        .def_property_readonly("hand", &Arm::hand)
        .def_property_readonly("limits", [](const Arm& a) { return limits_array(a.limits()); })
        .def(py::pickle(
            [](const Arm& a) {
                return py::make_tuple(a.base_height(), a.upper(), a.fore(), a.hand(),
                                      limits_array(a.limits()));
            },
            [](py::tuple t) {
                return Arm(t[0].cast<double>(), t[1].cast<double>(), t[2].cast<double>(),
                           t[3].cast<double>(), to_limits(t[4]));
            }))
        .def("__repr__", [](const Arm& a) {
            return "Arm(base_height=" + std::to_string(a.base_height()) +
                   ", upper=" + std::to_string(a.upper()) + ", fore=" + std::to_string(a.fore()) +
                   ", hand=" + std::to_string(a.hand()) + ")";
        });

    // --------------------------------------------------------------- stepper
    py::class_<Stepper>(m, "Stepper", "Stepper motor + reduction with a pull-out torque curve.")
        .def(py::init(&make_stepper), py::arg("torque_curve"), py::arg("gear_ratio") = 1.0,
             py::arg("rotor_inertia") = 5.4e-6, py::arg("max_speed_rps") = -1.0,
             "torque_curve: (K, 2) [rev/s, N*m] at the motor shaft. max_speed_rps <= 0:\n"
             "use the last curve speed.")
        .def("torque_at", &Stepper::torque_at, py::arg("rps"),
             "Pull-out torque (N*m) at motor speed rps (rev/s).")
        .def_property_readonly("torque_curve",
                               [](const Stepper& s) {
                                   const auto& c = s.curve();
                                   py::array_t<double> out({static_cast<py::ssize_t>(c.size()), py::ssize_t(2)});
                                   auto m2 = out.mutable_unchecked<2>();
                                   for (std::size_t i = 0; i < c.size(); ++i) {
                                       m2(i, 0) = c[i].first;
                                       m2(i, 1) = c[i].second;
                                   }
                                   return out;
                               })
        .def_property_readonly("gear_ratio", &Stepper::gear_ratio)
        .def_property_readonly("rotor_inertia", &Stepper::rotor_inertia)
        .def_property_readonly("max_speed_rps", &Stepper::max_speed_rps)
        .def_property_readonly("max_joint_speed", &Stepper::max_joint_speed,
                               "Max joint speed in rad/s.")
        .def(py::pickle(
            [](const Stepper& s) {
                py::list c;
                for (const auto& p : s.curve()) c.append(py::make_tuple(p.first, p.second));
                return py::make_tuple(c, s.gear_ratio(), s.rotor_inertia(), s.max_speed_rps());
            },
            [](py::tuple t) {
                return make_stepper(DArray::ensure(t[0]), t[1].cast<double>(),
                                    t[2].cast<double>(), t[3].cast<double>());
            }))
        .def("__repr__", [](const Stepper& s) {
            return "Stepper(gear_ratio=" + std::to_string(s.gear_ratio()) +
                   ", rotor_inertia=" + std::to_string(s.rotor_inertia()) +
                   ", max_speed_rps=" + std::to_string(s.max_speed_rps()) + ")";
        });

    m.def(
        "min_move_time",
        [](const Stepper& s, double load_inertia, double dist, double safety, double load_torque) {
            return min_move_time(s, load_inertia, load_torque, dist, safety);
        },
        py::arg("motor"), py::arg("load_inertia"), py::arg("dist"), py::arg("safety") = 0.7,
        py::arg("load_torque") = 0.0,
        "Minimum rest-to-rest time (s) for one joint to move dist rad.");

    // ---------------------------------------------------------------- motion
    m.def(
        "plan_move",
        [](const DArray& q0, const DArray& q1, const std::vector<Stepper>& motors,
           const DArray& load_inertia, double t_avail, double safety,
           const py::object& load_torque) {
            const std::size_t n = motors.size();
            if (n == 0) throw py::value_error("motors is empty");
            auto a = to_vector(q0, n, "q0");
            auto b = to_vector(q1, n, "q1");
            auto J = to_vector(load_inertia, n, "load_inertia");
            auto tl = optional_joint_vec(load_torque, n, "load_torque");
            MoveResult r;
            {
                py::gil_scoped_release nogil;
                r = plan_move(a, b, motors, J, tl, t_avail, safety);
            }
            return move_to_dict(r);
        },
        py::arg("q0"), py::arg("q1"), py::arg("motors"), py::arg("load_inertia"),
        py::arg("t_avail"), py::arg("safety") = 0.7, py::arg("load_torque") = py::none(),
        "Time-optimal, torque-limited rest-to-rest move, each joint independent.\n"
        "load_inertia: (J,) kg*m^2 about each joint axis (joint side).\n"
        "load_torque: optional (J,) static joint torque, N*m (e.g. gravity).\n"
        "Returns dict(feasible, t_needed, t_per_joint (J,), peak_torque_frac (J,),\n"
        "limiting_joint). t_per_joint uses `safety` x pull-out torque;\n"
        "peak_torque_frac is the smallest fraction of pull-out torque that still\n"
        "finishes within t_avail (inf if impossible). feasible <=> all t_per_joint <= t_avail.");

    m.def(
        "plan_batch",
        [](const DArray& q0, const DArray& Q1, const std::vector<Stepper>& motors,
           const DArray& load_inertia, const DArray& T_avail, double safety,
           const py::object& load_torque, int threads) {
            const std::size_t J = motors.size();
            if (J == 0) throw py::value_error("motors is empty");
            if (Q1.ndim() != 2 || static_cast<std::size_t>(Q1.shape(1)) != J)
                throw py::value_error("Q1 must have shape (N, J)");
            const std::size_t N = static_cast<std::size_t>(Q1.shape(0));
            const auto Q0 = rows_of(q0, N, J, "q0");
            const auto L = rows_of(load_inertia, N, J, "load_inertia");
            std::vector<double> TL(N * J, 0.0);
            if (!load_torque.is_none()) TL = rows_of(DArray::ensure(load_torque), N, J, "load_torque");
            std::vector<double> T(N);
            if (T_avail.size() == 1)
                std::fill(T.begin(), T.end(), T_avail.data()[0]);
            else if (static_cast<std::size_t>(T_avail.size()) == N)
                std::copy(T_avail.data(), T_avail.data() + N, T.begin());
            else
                throw py::value_error("T_avail must be a scalar or have shape (N,)");
            const double* q1p = Q1.data();

            std::vector<unsigned char> feas(N);
            std::vector<double> tneed(N), tper(N * J), frac(N * J);
            std::vector<int> lim(N);
            {
                py::gil_scoped_release nogil;
                unsigned nt = threads > 0 ? static_cast<unsigned>(threads)
                                          : std::max(1u, std::thread::hardware_concurrency());
                nt = static_cast<unsigned>(std::min<std::size_t>(nt, std::max<std::size_t>(1, N / 16)));
                auto work = [&](std::size_t lo, std::size_t hi) {
                    std::vector<double> a(J), b(J), l(J), tl(J);
                    for (std::size_t i = lo; i < hi; ++i) {
                        for (std::size_t j = 0; j < J; ++j) {
                            a[j] = Q0[i * J + j];
                            b[j] = q1p[i * J + j];
                            l[j] = L[i * J + j];
                            tl[j] = TL[i * J + j];
                        }
                        const MoveResult r = plan_move(a, b, motors, l, tl, T[i], safety);
                        feas[i] = r.feasible;
                        tneed[i] = r.t_needed;
                        lim[i] = r.limiting_joint;
                        for (std::size_t j = 0; j < J; ++j) {
                            tper[i * J + j] = r.t_per_joint[j];
                            frac[i * J + j] = r.peak_torque_frac[j];
                        }
                    }
                };
                if (nt <= 1) {
                    work(0, N);
                } else {
                    std::vector<std::thread> pool;
                    const std::size_t chunk = (N + nt - 1) / nt;
                    for (unsigned t = 0; t < nt; ++t) {
                        const std::size_t lo = t * chunk, hi = std::min(N, lo + chunk);
                        if (lo < hi) pool.emplace_back(work, lo, hi);
                    }
                    for (auto& th : pool) th.join();
                }
            }
            py::array_t<bool> f(static_cast<py::ssize_t>(N));
            std::copy(feas.begin(), feas.end(), f.mutable_data());
            py::array_t<double> tn(static_cast<py::ssize_t>(N));
            std::copy(tneed.begin(), tneed.end(), tn.mutable_data());
            py::array_t<double> tp({static_cast<py::ssize_t>(N), static_cast<py::ssize_t>(J)});
            std::copy(tper.begin(), tper.end(), tp.mutable_data());
            py::array_t<double> fr({static_cast<py::ssize_t>(N), static_cast<py::ssize_t>(J)});
            std::copy(frac.begin(), frac.end(), fr.mutable_data());
            py::array_t<int> lj(static_cast<py::ssize_t>(N));
            std::copy(lim.begin(), lim.end(), lj.mutable_data());
            py::dict d;
            d["feasible"] = f;
            d["t_needed"] = tn;
            d["t_per_joint"] = tp;
            d["peak_torque_frac"] = fr;
            d["limiting_joint"] = lj;
            return d;
        },
        py::arg("q0"), py::arg("Q1"), py::arg("motors"), py::arg("load_inertia"),
        py::arg("T_avail"), py::arg("safety") = 0.7, py::arg("load_torque") = py::none(),
        py::arg("threads") = 0,
        "plan_move over N targets on all cores. q0, load_inertia, load_torque: (J,) or\n"
        "(N, J); Q1: (N, J); T_avail: scalar or (N,). Returns a dict of arrays with the\n"
        "same keys as plan_move (feasible (N,) bool, t_needed (N,), t_per_joint (N, J),\n"
        "peak_torque_frac (N, J), limiting_joint (N,)).");
}
