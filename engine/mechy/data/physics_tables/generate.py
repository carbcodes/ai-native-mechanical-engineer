"""Regenerates the computed tables in this folder (stdlib only).

    python3 -I generate.py

Writes: physical_constants.csv (parsed from raw/nist_codata_allascii.txt),
standard_atmosphere.csv, air_properties_vs_T.csv, water_properties_vs_T.csv,
ball_properties.csv (terminal velocity computed from mass, diameter, Cd).
Hand-curated tables (drag, COR, efficiencies, ...) are edited directly.
"""
import csv
import math
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NIST_URL = "https://physics.nist.gov/cuu/Constants/Table/allascii.txt"

# (NIST quantity name, symbol, short id)
CONSTANTS = [
    ("speed of light in vacuum", "c", "c"),
    ("Planck constant", "h", "h"),
    ("reduced Planck constant", "hbar", "hbar"),
    ("elementary charge", "e", "e"),
    ("Boltzmann constant", "k_B", "k_B"),
    ("Avogadro constant", "N_A", "N_A"),
    ("molar gas constant", "R", "R"),
    ("Newtonian constant of gravitation", "G", "G"),
    ("standard acceleration of gravity", "g_n", "g_n"),
    ("standard atmosphere", "atm", "atm"),
    ("Stefan-Boltzmann constant", "sigma", "sigma_SB"),
    ("vacuum electric permittivity", "epsilon_0", "epsilon_0"),
    ("vacuum mag. permeability", "mu_0", "mu_0"),
    ("electron mass", "m_e", "m_e"),
    ("proton mass", "m_p", "m_p"),
    ("atomic mass constant", "m_u", "m_u"),
    ("Faraday constant", "F", "F"),
    ("fine-structure constant", "alpha", "alpha"),
    ("Wien wavelength displacement law constant", "b", "b_Wien"),
    ("molar volume of ideal gas (273.15 K, 101.325 kPa)", "V_m", "V_m_STP"),
]


def _num(s):
    s = s.replace(" ", "").replace("...", "")
    return float(s)


def parse_nist(path):
    out = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if len(line) < 60 or line.startswith(("-", " ")):
                continue
            name = line[:60].strip()
            value = line[60:85].strip()
            unc = line[85:110].strip()
            unit = line[110:].strip()
            try:
                out[name] = (_num(value), unc, unit)
            except ValueError:
                pass
    return out


def write_csv(name, header, rows):
    with open(os.path.join(HERE, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {name}: {len(rows)} rows")


def constants():
    table = parse_nist(os.path.join(HERE, "raw", "nist_codata_allascii.txt"))
    rows = []
    for qname, sym, cid in CONSTANTS:
        v, unc, unit = table[qname]
        exact = unc == "(exact)"
        rel = ""
        if not exact:
            u = _num(unc)
            rel = f"{u / v:.2e}"
        rows.append([cid, qname, sym, repr(v), unit.replace(" ", "*"), str(exact).lower(),
                     rel, "CODATA 2022", NIST_URL, "standard"])
    write_csv("physical_constants.csv",
              ["id", "name", "symbol", "value_SI", "unit", "exact", "rel_uncertainty",
               "edition", "source_url", "value_type"], rows)


# --- air -------------------------------------------------------------------
R_AIR = 287.05287       # J/(kg K), ISO 2533 / US Std Atm 1976
GAMMA = 1.4
G0 = 9.80665


def mu_air(T):
    """Sutherland viscosity, Pa*s."""
    return 1.716e-5 * (T / 273.15) ** 1.5 * (273.15 + 110.4) / (T + 110.4)


def k_air(T):
    """Sutherland-form thermal conductivity, W/(m K)."""
    return 0.0241 * (T / 273.15) ** 1.5 * (273.15 + 194.0) / (T + 194.0)


def cp_air(T):
    """Simple fit valid ~250-1050 K, J/(kg K)."""
    return 1002.5 + 275e-6 * (T - 200.0) ** 2


def isa(h):
    """ISA (troposphere, tropopause, lower stratosphere) up to 32 km."""
    T0, p0 = 288.15, 101325.0
    if h <= 11000:
        T = T0 - 0.0065 * h
        p = p0 * (T / T0) ** (G0 / (0.0065 * R_AIR))
    elif h <= 20000:
        T11 = 216.65
        p11 = p0 * (T11 / T0) ** (G0 / (0.0065 * R_AIR))
        T = T11
        p = p11 * math.exp(-G0 * (h - 11000) / (R_AIR * T11))
    else:
        T11 = 216.65
        p11 = p0 * (T11 / T0) ** (G0 / (0.0065 * R_AIR))
        p20 = p11 * math.exp(-G0 * 9000 / (R_AIR * T11))
        T = T11 + 0.001 * (h - 20000)
        p = p20 * (T / T11) ** (-G0 / (0.001 * R_AIR))
    rho = p / (R_AIR * T)
    a = math.sqrt(GAMMA * R_AIR * T)
    mu = mu_air(T)
    return T, p, rho, a, mu, mu / rho


def atmosphere():
    hs = list(range(0, 3000, 250)) + list(range(3000, 32001, 1000))
    rows = []
    for h in hs:
        T, p, rho, a, mu, nu = isa(h)
        rows.append([h, f"{T:.2f}", f"{p:.1f}", f"{rho:.5f}", f"{a:.2f}", f"{mu:.4e}",
                     f"{nu:.4e}",
                     "https://ntrs.nasa.gov/citations/19770009539", "standard"])
    write_csv("standard_atmosphere.csv",
              ["altitude_m", "temperature_K", "pressure_Pa", "density_kg_m3",
               "speed_of_sound_m_s", "dynamic_viscosity_Pa_s", "kinematic_viscosity_m2_s",
               "source_url", "value_type"], rows)


def air():
    rows = []
    for tc in range(-40, 201, 10):
        T = tc + 273.15
        rho = 101325.0 / (R_AIR * T)
        mu, k, cp = mu_air(T), k_air(T), cp_air(T)
        rows.append([tc, f"{T:.2f}", f"{rho:.4f}", f"{mu:.4e}", f"{mu / rho:.4e}",
                     f"{k:.5f}", f"{cp:.1f}", f"{mu * cp / k:.4f}",
                     f"{math.sqrt(GAMMA * R_AIR * T):.2f}",
                     "https://www.grc.nasa.gov/www/k-12/airplane/viscosity.html",
                     "handbook_typical"])
    write_csv("air_properties_vs_T.csv",
              ["temperature_C", "temperature_K", "density_kg_m3", "dynamic_viscosity_Pa_s",
               "kinematic_viscosity_m2_s", "thermal_conductivity_W_mK",
               "specific_heat_cp_J_kgK", "prandtl", "speed_of_sound_m_s",
               "source_url", "value_type"], rows)


# --- water (1 atm; saturated above 100 C not included) ----------------------
# T_C, rho, mu_mPa_s, k, cp_kJ, sigma_mN_m, p_vap_kPa  (IAPWS-based handbook values)
WATER = [
    (0, 999.84, 1.792, 0.561, 4.217, 75.6, 0.611),
    (10, 999.70, 1.306, 0.580, 4.192, 74.2, 1.228),
    (20, 998.21, 1.002, 0.598, 4.182, 72.7, 2.339),
    (30, 995.65, 0.797, 0.615, 4.178, 71.2, 4.247),
    (40, 992.22, 0.653, 0.631, 4.179, 69.6, 7.384),
    (50, 988.03, 0.547, 0.644, 4.181, 67.9, 12.35),
    (60, 983.20, 0.467, 0.654, 4.185, 66.2, 19.95),
    (70, 977.76, 0.404, 0.663, 4.190, 64.4, 31.20),
    (80, 971.79, 0.355, 0.670, 4.197, 62.6, 47.41),
    (90, 965.31, 0.315, 0.675, 4.205, 60.8, 70.18),
    (100, 958.35, 0.282, 0.679, 4.216, 58.9, 101.42),
]


def water():
    rows = []
    for tc, rho, mu, k, cp, sig, pv in WATER:
        mu_si = mu * 1e-3
        cp_si = cp * 1000
        rows.append([tc, rho, f"{mu_si:.4e}", f"{mu_si / rho:.4e}", k, cp_si,
                     f"{mu_si * cp_si / k:.3f}", sig / 1000, pv * 1000,
                     "https://webbook.nist.gov/chemistry/fluid/", "handbook_typical"])
    write_csv("water_properties_vs_T.csv",
              ["temperature_C", "density_kg_m3", "dynamic_viscosity_Pa_s",
               "kinematic_viscosity_m2_s", "thermal_conductivity_W_mK",
               "specific_heat_cp_J_kgK", "prandtl", "surface_tension_N_m",
               "vapor_pressure_Pa", "source_url", "value_type"], rows)


# --- balls -----------------------------------------------------------------
RHO_AIR_20C = 101325.0 / (R_AIR * 293.15)
# object, body, m_min,m_nom,m_max (g), d_min,d_nom,d_max (mm), Cd, COR, notes, url, type
BALLS = [
    ("table tennis ball (40+)", "ITTF", 2.67, 2.70, 2.77, 40.0, 40.2, 40.6, 0.50, 0.89,
     "Light; strongly affected by drag and spin (Magnus)", "https://www.ittf.com/handbook/", "standard"),
    ("tennis ball (type 2)", "ITF", 56.0, 57.7, 59.4, 65.4, 67.0, 68.6, 0.55, 0.75,
     "", "https://www.itftennis.com/en/about-us/governance/rules-and-regulations/", "standard"),
    ("baseball", "MLB", 142.0, 145.0, 149.0, 72.9, 73.8, 74.8, 0.35, 0.546,
     "Circumference 9-9.25 in", "https://www.mlb.com/glossary/rules", "standard"),
    ("golf ball", "USGA/R&A", 45.0, 45.9, 45.93, 42.67, 42.7, 43.0, 0.25, 0.78,
     "Mass max 45.93 g; diameter min 42.67 mm", "https://www.usga.org/equipment-standards.html", "standard"),
    ("softball (12 in)", "ASA/USA Softball", 178.0, 188.0, 198.0, 95.5, 96.3, 97.1, 0.40, 0.47,
     "Circumference 11.88-12.12 in", "https://www.usasoftball.com/", "standard"),
    ("juggling beanbag (thud/beanbag)", "none", 100.0, 125.0, 150.0, 60.0, 65.0, 70.0, 0.50, 0.05,
     "Deforms on catch; easiest to grip", "https://en.wikipedia.org/wiki/Juggling_ball", "estimate"),
    ("juggling stage/russian ball", "none", 100.0, 130.0, 160.0, 62.0, 67.0, 72.0, 0.47, 0.1,
     "Partly filled shell; minimal bounce", "https://en.wikipedia.org/wiki/Juggling_ball", "estimate"),
    ("juggling silicone bounce ball", "none", 110.0, 140.0, 170.0, 63.0, 68.0, 70.0, 0.47, 0.85,
     "", "https://en.wikipedia.org/wiki/Juggling_ball", "estimate"),
    ("squash ball", "WSF", 23.0, 24.0, 25.0, 39.5, 40.0, 40.5, 0.50, 0.37,
     "", "https://www.worldsquash.org/rules/", "standard"),
    ("lacrosse ball", "World Lacrosse", 140.0, 145.0, 149.0, 62.7, 63.7, 64.7, 0.45, 0.65,
     "", "https://worldlacrosse.sport/", "standard"),
    ("cricket ball (men)", "MCC", 155.9, 159.0, 163.0, 71.3, 72.0, 72.9, 0.40, 0.55,
     "Circumference 224-229 mm", "https://www.lords.org/mcc/the-laws-of-cricket", "standard"),
    ("volleyball", "FIVB", 260.0, 270.0, 280.0, 207.0, 210.0, 213.0, 0.45, 0.75,
     "Circumference 65-67 cm", "https://www.fivb.com/", "standard"),
    ("football/soccer ball (size 5)", "FIFA/IFAB", 410.0, 430.0, 450.0, 216.0, 220.0, 223.0, 0.25, 0.80,
     "Cd ~0.25 supercritical at kick speeds, ~0.45 slow", "https://www.theifab.com/laws/latest/the-ball/", "standard"),
    ("basketball (size 7)", "FIBA", 567.0, 600.0, 650.0, 238.0, 242.0, 248.0, 0.50, 0.85,
     "Circumference 749-780 mm", "https://www.fiba.basketball/documents", "standard"),
    ("badminton shuttlecock (skirt diameter)", "BWF", 4.74, 5.10, 5.50, 58.0, 65.0, 68.0, 0.60, 0.0,
     "Measured terminal speed ~6.7 m/s", "https://corporate.bwfbadminton.com/statutes/", "standard"),
    ("foam practice ball (70 mm)", "none", 5.0, 8.0, 12.0, 65.0, 70.0, 75.0, 0.50, 0.35,
     "", "https://en.wikipedia.org/wiki/Foam_ball", "estimate"),
]


def balls():
    rows = []
    for (obj, body, m0, m1, m2, d0, d1, d2, cd, cor, notes, url, vt) in BALLS:
        m = m1 / 1000
        d = d1 / 1000
        area = math.pi * d * d / 4
        vt_ms = math.sqrt(2 * m * G0 / (RHO_AIR_20C * cd * area))
        rows.append([obj, body, m0 / 1000, m, m2 / 1000, d0 / 1000, d, d2 / 1000, cd, cor,
                     f"{vt_ms:.2f}", notes, url, vt])
    write_csv("ball_properties.csv",
              ["object", "governing_body", "mass_kg_min", "mass_kg_nominal", "mass_kg_max",
               "diameter_m_min", "diameter_m_nominal", "diameter_m_max", "Cd_typical",
               "COR_typical", "terminal_velocity_m_s", "notes", "source_url", "value_type"],
              rows)


if __name__ == "__main__":
    constants()
    atmosphere()
    air()
    water()
    balls()
