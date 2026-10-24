"""Regenerates every CSV/JSON in this folder (Python stdlib only).

Hand-entered tables are compiled from standards summaries and manufacturer catalogues (see README.md);
derived tables (threads, stress areas, torques, pulleys, shaft masses, ISO 286 limits) are computed here
from the standard formulas so the numbers stay internally consistent.

Run: python3 -I build.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEEL_KG_MM3 = 7.85e-6

SRC = {
    "skf_dgbb": "https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings",
    "iso15": "https://www.iso.org/standard/69707.html",
    "mini": "https://www.nmbtc.com/bearings/ (miniature catalogue; ratings estimated)",
    "skf_thrust": "https://www.skf.com/group/products/rolling-bearings/ball-bearings/thrust-ball-bearings",
    "skf_acbb": "https://www.skf.com/group/products/rolling-bearings/ball-bearings/angular-contact-ball-bearings",
    "ina_needle": "https://medias.schaeffler.com/ (INA drawn cup HK / NA49 catalogue)",
    "lmuu": "https://www.thk.com/ (THK LM linear bushing catalogue); https://us.misumi-ec.com/",
    "hiwin_mg": "https://damencnc.com/userdata/file/3455-3_HIWIN_MGN_and_MGW_Product_Catalog_2023.pdf",
    "hiwin_hg": "https://www.hiwin.com/linear-guideways/ (HG series catalogue; cross-checked https://www.slideshare.net/slideshow/dre-linear-guide/50125925)",
    "igus": "https://www.igus.com/iglidur/",
    "ggb_du": "https://www.ggbearings.com/en/products/metal-polymer/du",
    "iso4762": "https://www.iso.org/standard/34003.html",
    "iso7380": "https://www.iso.org/standard/52585.html",
    "iso10642": "https://www.iso.org/standard/34004.html",
    "iso4032": "https://www.iso.org/standard/45689.html",
    "iso7089": "https://www.iso.org/standard/38893.html",
    "iso273": "https://www.iso.org/standard/4189.html",
    "iso898": "https://www.iso.org/standard/60374.html",
    "iso3506": "https://www.iso.org/standard/72427.html",
    "vdi2230": "https://www.vdi.de/richtlinien/details/vdi-2230-blatt-1 (formula); computed",
    "inserts": "https://www.ruthex.de/ ; https://cnckitchen.store/ (heat-set insert datasheets)",
    "iso_thread": "https://en.wikipedia.org/wiki/ISO_metric_screw_thread (ISO 68-1 / 261 / 724 / 898-1 formulas)",
    "gates": "https://www.gates.com/us/en/power-transmission/synchronous-belts.html (PowerGrip GT/HTD design manuals)",
    "openbuilds": "https://openbuildspartstore.com/v-slot-20x20-linear-rail/ ; https://us.misumi-ec.com/ (HFS5/HFS6/HFS8)",
    "shaft": "https://us.misumi-ec.com/ (linear shafts SFJ); mass computed",
    "din6885": "https://en.wikipedia.org/wiki/Key_(engineering) ; DIN 6885-1 / ISO 773 tables",
    "din471": "https://www.din.de/ (DIN 471 / DIN 472 circlip tables, as reproduced by e.g. https://www.misumi-ec.com/)",
    "iso8734": "https://www.iso.org/standard/15880.html",
    "iso2338": "https://www.iso.org/standard/36906.html",
    "shigley": "Shigley's Mechanical Engineering Design, Tables 10-4/10-5 (spring wire A, m, E, G)",
    "lovejoy": "https://cad.timken.com/item/standard-jaw-couplings-l-type/l-type-solid-hubs/68514410218 (Lovejoy L-type)",
    "hobby_coupling": "Typical AliExpress/Misumi hobby coupling listings (estimate)",
    "iso2904": "https://www.iso.org/standard/7830.html (ISO 2904 trapezoidal threads, formulas)",
    "tbi": "https://www.tbimotion.com.tw/ (TBI SFU catalogue); https://anaheimautomation.com/linear-components/ball-screws/tbi-ball-screws/",
    "iso286": "https://www.iso.org/standard/45975.html (ISO 286-2 tables)",
}


def write_csv(name, header, rows):
    path = os.path.join(HERE, name)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            assert len(r) == len(header), (name, r)
            w.writerow(["" if v is None else (round(v, 6) if isinstance(v, float) else v) for v in r])
    print(f"{name}: {len(rows)} rows")


def ring_mass(d, D, B, fill=0.66):
    """Estimated bearing mass from envelope (calibrated on 608 / 6205: fill ~0.66)."""
    return round(fill * math.pi / 4 * (D * D - d * d) * B * STEEL_KG_MM3, 4)


# ---------------------------------------------------------------- deep-groove ball bearings
def deep_groove():
    hdr = ["designation", "series", "d_mm", "D_mm", "B_mm", "C_kN", "C0_kN", "reference_speed_rpm",
           "limiting_speed_rpm", "mass_kg", "flange_D_mm", "flange_width_mm", "notes", "source_url", "value_type"]
    rows = []
    # SKF-style catalogue values (open bearing). designation: d, D, B, C, C0, ref, lim, mass
    skf = {
        "623": (3, 10, 4, 0.54, 0.18, None, None, None),
        "624": (4, 13, 5, 0.936, 0.29, 130000, 80000, 0.0031),
        "625": (5, 16, 5, 1.14, 0.38, 110000, 67000, 0.005),
        "626": (6, 19, 6, 2.34, 0.95, 95000, 60000, 0.0084),
        "627": (7, 22, 7, 3.45, 1.37, 85000, 53000, 0.013),
        "608": (8, 22, 7, 3.45, 1.37, 75000, 48000, 0.012),
        "629": (9, 26, 8, 4.75, 1.96, 67000, 40000, 0.020),
        "6000": (10, 26, 8, 4.75, 1.96, 67000, 40000, 0.019),
        "6001": (12, 28, 8, 5.4, 2.36, 60000, 38000, 0.022),
        "6002": (15, 32, 9, 5.85, 2.85, 50000, 32000, 0.030),
        "6003": (17, 35, 10, 6.37, 3.25, 45000, 28000, 0.039),
        "6004": (20, 42, 12, 9.95, 5.0, 38000, 24000, 0.069),
        "6005": (25, 47, 12, 11.9, 6.55, 32000, 20000, 0.080),
        "6006": (30, 55, 13, 13.8, 8.3, 28000, 17000, 0.12),
        "6007": (35, 62, 14, 16.8, 10.2, 24000, 15000, 0.16),
        "6008": (40, 68, 15, 17.8, 11.6, 22000, 14000, 0.19),
        "6009": (45, 75, 16, 22.1, 14.6, 20000, 12000, 0.25),
        "6010": (50, 80, 16, 22.9, 16.0, 18000, 11000, 0.26),
        "6200": (10, 30, 9, 5.4, 2.36, 56000, 34000, 0.032),
        "6201": (12, 32, 10, 7.28, 3.1, 50000, 32000, 0.037),
        "6202": (15, 35, 11, 8.06, 3.75, 43000, 28000, 0.045),
        "6203": (17, 40, 12, 9.95, 4.75, 38000, 24000, 0.065),
        "6204": (20, 47, 14, 13.5, 6.55, 32000, 20000, 0.11),
        "6205": (25, 52, 15, 14.8, 7.8, 28000, 18000, 0.13),
        "6206": (30, 62, 16, 20.3, 11.2, 24000, 15000, 0.20),
        "6207": (35, 72, 17, 27.0, 15.3, 20000, 13000, 0.29),
        "6208": (40, 80, 18, 32.5, 19.0, 18000, 11000, 0.37),
        "6209": (45, 85, 19, 35.1, 21.6, 17000, 11000, 0.41),
        "6210": (50, 90, 20, 37.1, 23.2, 15000, 10000, 0.46),
        "6800": (10, 19, 5, 1.38, 0.585, None, None, 0.0055),
        "6801": (12, 21, 5, 1.43, 0.67, None, None, 0.0063),
        "6802": (15, 24, 5, 1.56, 0.8, None, None, 0.0074),
        "6803": (17, 26, 5, 1.68, 0.93, None, None, 0.0082),
        "6804": (20, 32, 7, 4.03, 2.32, None, None, 0.018),
        "6805": (25, 37, 7, 4.36, 2.6, None, None, 0.022),
        "6806": (30, 42, 7, 4.49, 2.9, None, None, 0.026),
        "6900": (10, 22, 6, 2.7, 1.27, None, None, 0.010),
        "6901": (12, 24, 6, 2.91, 1.46, None, None, 0.011),
        "6902": (15, 28, 7, 4.36, 2.24, None, None, 0.016),
        "6903": (17, 30, 7, 4.62, 2.55, None, None, 0.018),
        "6904": (20, 37, 9, 6.37, 3.65, None, None, 0.038),
        "6905": (25, 42, 9, 7.02, 4.3, None, None, 0.045),
        "6906": (30, 47, 9, 7.28, 4.55, None, None, 0.050),
    }
    for des, (d, D, B, C, C0, ref, lim, m) in skf.items():
        series = "6xx" if len(des) == 3 else des[:2] + "xx"
        notes = "open bearing; -2Z ~0.8x and -2RS ~0.5x limiting speed"
        vt = "handbook_typical"
        if des.startswith(("68", "69")):
            notes += "; SKF designation 618xx/619xx; limiting speed estimated 700000/dm"
        if lim is None:
            dm = (d + D) / 2
            lim = int(round(700000 / dm, -3))
            vt = "estimate" if des == "623" else vt
        if m is None:
            m = ring_mass(d, D, B)
            vt = "estimate"
        rows.append([des, series, d, D, B, C, C0, ref, lim, m, None, None, notes, SRC["skf_dgbb"], vt])
    # Miniature (ZZ widths), ratings estimated
    mini = {
        "683ZZ": (3, 7, 3, 0.39, 0.13), "684ZZ": (4, 9, 4, 0.64, 0.23), "685ZZ": (5, 11, 5, 0.71, 0.28),
        "686ZZ": (6, 13, 5, 1.08, 0.44), "687ZZ": (7, 14, 5, 1.17, 0.51), "688ZZ": (8, 16, 5, 1.33, 0.59),
        "689ZZ": (9, 17, 5, 1.33, 0.63), "693ZZ": (3, 8, 4, 0.56, 0.18), "694ZZ": (4, 11, 4, 0.71, 0.28),
        "695ZZ": (5, 13, 4, 1.08, 0.43), "696ZZ": (6, 15, 5, 1.35, 0.53), "697ZZ": (7, 17, 5, 1.61, 0.71),
        "698ZZ": (8, 19, 6, 1.92, 0.81), "699ZZ": (9, 20, 6, 2.03, 0.88),
        "MR63ZZ": (3, 6, 2.5, 0.21, 0.06), "MR74ZZ": (4, 7, 2.5, 0.26, 0.09), "MR85ZZ": (5, 8, 2.5, 0.31, 0.12),
        "MR95ZZ": (5, 9, 3, 0.43, 0.17), "MR105ZZ": (5, 10, 4, 0.43, 0.17), "MR115ZZ": (5, 11, 4, 0.71, 0.28),
        "MR106ZZ": (6, 10, 3, 0.50, 0.22), "MR126ZZ": (6, 12, 4, 0.71, 0.29), "MR128ZZ": (8, 12, 3.5, 0.56, 0.27),
        "MR148ZZ": (8, 14, 4, 0.82, 0.41),
    }
    for des, (d, D, B, C, C0) in mini.items():
        series = "MR" if des.startswith("MR") else des[:2] + "x"
        lim = int(round(560000 / ((d + D) / 2), -3))
        rows.append([des, "miniature_" + series, d, D, B, C, C0, None, lim, ring_mass(d, D, B), None, None,
                     "shielded (ZZ) width; open 68x are thinner; C/C0 and speed estimated",
                     SRC["mini"], "estimate"])
    # Flanged: base designation -> flange OD, flange width
    flanged = {
        "F683ZZ": ("683ZZ", 8.1, 0.8), "F684ZZ": ("684ZZ", 10.3, 1.0), "F685ZZ": ("685ZZ", 12.5, 1.0),
        "F686ZZ": ("686ZZ", 15.0, 1.1), "F687ZZ": ("687ZZ", 16.0, 1.1), "F688ZZ": ("688ZZ", 18.0, 1.1),
        "F689ZZ": ("689ZZ", 19.0, 1.1), "F693ZZ": ("693ZZ", 9.5, 0.7), "F694ZZ": ("694ZZ", 12.5, 1.0),
        "F695ZZ": ("695ZZ", 15.0, 1.0), "F696ZZ": ("696ZZ", 17.0, 1.2), "F697ZZ": ("697ZZ", 19.0, 1.2),
        "F698ZZ": ("698ZZ", 22.0, 1.5), "F623ZZ": ("623", 11.5, 1.0), "F624ZZ": ("624", 15.0, 1.0),
        "F625ZZ": ("625", 18.0, 1.0), "F626ZZ": ("626", 22.0, 1.5), "F608ZZ": ("608", 25.0, 1.5),
        "MF63ZZ": ("MR63ZZ", 7.2, 0.6), "MF74ZZ": ("MR74ZZ", 8.2, 0.6), "MF85ZZ": ("MR85ZZ", 9.2, 0.6),
        "MF105ZZ": ("MR105ZZ", 11.2, 0.8), "MF128ZZ": ("MR128ZZ", 13.6, 0.8), "MF148ZZ": ("MR148ZZ", 15.6, 0.8),
    }
    base = {r[0]: r for r in rows}
    for des, (b, fD, fB) in flanged.items():
        r = base[b]
        m = round(r[9] + fill_flange(r[3], fD, fB), 4)
        rows.append([des, "flanged", r[2], r[3], r[4], r[5], r[6], r[7], int(r[8] * 0.8), m, fD, fB,
                     f"flanged version of {b}; ratings as base bearing; shielded speed ~0.8x",
                     SRC["mini"], "handbook_typical" if b[0].isdigit() and b in skf else "estimate"])
    write_csv("bearings_deep_groove.csv", hdr, rows)


def fill_flange(D, fD, fB):
    return math.pi / 4 * (fD * fD - D * D) * fB * STEEL_KG_MM3


def thrust():
    hdr = ["designation", "d_mm", "D_mm", "H_mm", "C_kN", "C0_kN", "limiting_speed_rpm", "mass_kg",
           "notes", "source_url", "value_type"]
    data = {
        "51100": (10, 24, 9, 10.1, 14.0, 0.019), "51101": (12, 26, 9, 10.4, 15.3, 0.021),
        "51102": (15, 28, 9, 10.6, 16.6, 0.024), "51103": (17, 30, 9, 11.4, 19.0, 0.025),
        "51104": (20, 35, 10, 15.9, 25.5, 0.037), "51105": (25, 42, 11, 19.9, 33.5, 0.056),
        "51106": (30, 47, 11, 20.8, 37.5, 0.063), "51107": (35, 52, 12, 22.1, 43.0, 0.080),
        "51108": (40, 60, 13, 27.6, 55.0, 0.12), "51109": (45, 65, 14, 28.1, 60.0, 0.14),
        "51110": (50, 70, 14, 28.6, 63.0, 0.15),
    }
    rows = []
    for des, (d, D, H, C, C0, m) in data.items():
        lim = int(round(300000 / ((d + D) / 2), -2))
        rows.append([des, d, D, H, C, C0, lim, m,
                     "single-direction, axial load only; needs min axial preload; limiting speed estimated",
                     SRC["skf_thrust"], "handbook_typical"])
    write_csv("bearings_thrust.csv", hdr, rows)


def angular():
    hdr = ["designation", "d_mm", "D_mm", "B_mm", "contact_angle_deg", "C_kN", "C0_kN",
           "limiting_speed_rpm", "mass_kg", "notes", "source_url", "value_type"]
    data = {
        "7200 BE": (10, 30, 9, 7.02, 3.35, 0.03), "7201 BE": (12, 32, 10, 7.61, 3.8, 0.036),
        "7202 BE": (15, 35, 11, 8.84, 4.8, 0.045), "7203 BE": (17, 40, 12, 11.1, 6.1, 0.065),
        "7204 BE": (20, 47, 14, 14.3, 8.3, 0.11), "7205 BE": (25, 52, 15, 15.6, 10.0, 0.13),
        "7206 BE": (30, 62, 16, 24.0, 15.6, 0.21), "7207 BE": (35, 72, 17, 31.0, 20.8, 0.30),
        "7208 BE": (40, 80, 18, 36.4, 26.0, 0.37),
    }
    rows = []
    for des, (d, D, B, C, C0, m) in data.items():
        lim = int(round(600000 / ((d + D) / 2), -2))
        rows.append([des, d, D, B, 40, C, C0, lim, m,
                     "single row, use in pairs (DB/DF) for combined loads; limiting speed estimated",
                     SRC["skf_acbb"], "handbook_typical"])
    data2 = {"3200 A-2RS1": (10, 30, 14, 7.61, 4.3), "3201 A-2RS1": (12, 32, 15.9, 10.1, 5.6),
             "3202 A-2RS1": (15, 35, 15.9, 11.2, 6.8), "3203 A-2RS1": (17, 40, 17.5, 14.3, 8.8),
             "3204 A-2RS1": (20, 47, 20.6, 20.0, 12.0), "3205 A-2RS1": (25, 52, 20.6, 21.6, 14.3)}
    for des, (d, D, B, C, C0) in data2.items():
        rows.append([des, d, D, B, 30, C, C0, int(round(250000 / ((d + D) / 2), -2)), ring_mass(d, D, B, 0.62),
                     "double row sealed; takes axial both directions; ratings/speed/mass estimated",
                     SRC["skf_acbb"], "estimate"])
    write_csv("bearings_angular_contact.csv", hdr, rows)


def needle():
    hdr = ["designation", "type", "Fw_mm", "d_mm", "D_mm", "B_mm", "C_kN", "C0_kN", "notes",
           "source_url", "value_type"]
    rows = []
    hk = {"HK0306": (3, 6.5, 6, 0.9, 0.7), "HK0408": (4, 8, 8, 1.75, 1.5), "HK0509": (5, 9, 9, 2.2, 2.0),
          "HK0608": (6, 10, 8, 2.75, 2.6), "HK0709": (7, 11, 9, 3.3, 3.4), "HK0810": (8, 12, 10, 4.3, 4.9),
          "HK1010": (10, 14, 10, 5.0, 6.3), "HK1210": (12, 18, 10, 5.9, 6.4), "HK1512": (15, 21, 12, 7.6, 9.5),
          "HK2016": (20, 26, 16, 13.0, 20.5), "HK2520": (25, 32, 20, 18.9, 33.5)}
    for des, (Fw, D, B, C, C0) in hk.items():
        rows.append([des, "drawn_cup_HK", Fw, None, D, B, C, C0,
                     "runs directly on hardened shaft (HRC58+, h6); housing bore N6/R6 press fit; ratings estimated",
                     SRC["ina_needle"], "estimate"])
    na = {"NA4900": (14, 10, 22, 13, 8.6, 9.2), "NA4901": (16, 12, 24, 13, 9.5, 10.8),
          "NA4902": (20, 15, 28, 13, 10.5, 12.8), "NA4903": (22, 17, 30, 13, 11.0, 14.0),
          "NA4904": (25, 20, 37, 17, 21.0, 25.0), "NA4905": (30, 25, 42, 17, 23.8, 30.5),
          "NA4906": (35, 30, 47, 17, 25.0, 34.0)}
    for des, (Fw, d, D, B, C, C0) in na.items():
        rows.append([des, "machined_with_inner_ring_NA49", Fw, d, D, B, C, C0,
                     "dimensions per ISO 1206 series 49; ratings estimated", SRC["ina_needle"], "estimate"])
    write_csv("bearings_needle.csv", hdr, rows)


def linear_bearings():
    hdr = ["designation", "shaft_d_mm", "D_mm", "L_mm", "ring_groove_spacing_B_mm", "groove_width_W_mm",
           "groove_dia_D1_mm", "C_N", "C0_N", "mass_kg", "recommended_shaft_tolerance", "housing_bore_tolerance",
           "source_url", "value_type"]
    data = {  # d, D, L, B, W, D1, C, C0, mass_g
        "LM3UU": (3, 7, 10, None, None, None, 69, 105, 1.5), "LM4UU": (4, 8, 12, None, None, None, 88, 127, 2),
        "LM5UU": (5, 10, 15, 10.2, 1.1, 9.6, 167, 206, 4.5), "LM6UU": (6, 12, 19, 13.5, 1.1, 11.5, 206, 265, 8),
        "LM8UU": (8, 15, 24, 17.5, 1.1, 14.3, 265, 402, 16), "LM10UU": (10, 19, 29, 22.0, 1.3, 18.0, 373, 549, 30),
        "LM12UU": (12, 21, 30, 23.0, 1.3, 20.0, 412, 598, 31.5), "LM13UU": (13, 23, 32, 23.0, 1.3, 22.0, 510, 775, 43),
        "LM16UU": (16, 28, 37, 26.5, 1.6, 27.0, 775, 1180, 69), "LM20UU": (20, 32, 42, 30.5, 1.6, 30.5, 863, 1370, 87),
        "LM25UU": (25, 40, 59, 41.0, 1.85, 38.0, 980, 1570, 220), "LM30UU": (30, 45, 64, 44.5, 1.85, 43.0, 1570, 2750, 250),
        "LM35UU": (35, 52, 70, 49.5, 2.1, 49.0, 1670, 3140, 390), "LM40UU": (40, 60, 80, 60.5, 2.1, 57.0, 2160, 4020, 585),
        "LM50UU": (50, 80, 100, 74.0, 2.6, 76.5, 3820, 7940, 1580), "LM60UU": (60, 90, 110, 85.0, 3.15, 86.5, 4710, 10000, 2000),
    }
    rows = [[k, d, D, L, B, W, D1, C, C0, m / 1000, "g6 (hardened, HRC58+)", "H7 (or J7 for less play)",
             SRC["lmuu"], "handbook_typical"] for k, (d, D, L, B, W, D1, C, C0, m) in data.items()]
    write_csv("linear_bearings_LMUU.csv", hdr, rows)


def linear_rails():
    hdr = ["designation", "rail_width_mm", "rail_height_mm", "assembly_height_H_mm", "block_width_mm",
           "block_length_mm", "rail_hole_pitch_mm", "rail_bolt", "C_kN", "C0_kN", "block_mass_kg",
           "rail_mass_kg_per_m", "notes", "source_url", "value_type"]
    mg = {  # rail W, HR, H, block W, L, P, bolt, C, C0, block kg, rail kg/m
        "MGN7C": (7, 4.8, 8, 17, 22.5, 15, "M2", 0.98, 1.24, 0.010, 0.22),
        "MGN7H": (7, 4.8, 8, 17, 30.8, 15, "M2", 1.37, 1.96, 0.015, 0.22),
        "MGN9C": (9, 6.5, 10, 20, 28.9, 20, "M3", 1.86, 2.84, 0.016, 0.38),
        "MGN9H": (9, 6.5, 10, 20, 39.9, 20, "M3", 2.55, 4.27, 0.026, 0.38),
        "MGN12C": (12, 8, 13, 27, 34.7, 25, "M3", 2.84, 3.92, 0.034, 0.65),
        "MGN12H": (12, 8, 13, 27, 45.4, 25, "M3", 3.72, 5.88, 0.050, 0.65),
        "MGN15C": (15, 10, 16, 32, 42.1, 40, "M3", 4.61, 5.59, 0.059, 1.06),
        "MGN15H": (15, 10, 16, 32, 58.8, 40, "M3", 6.37, 9.11, 0.092, 1.06),
    }
    rows = []
    for k, v in mg.items():
        vt = "datasheet" if k == "MGN12H" else "handbook_typical"
        rows.append([k, *v, "HIWIN miniature; C at 50 km rated life; clones often lower accuracy",
                     SRC["hiwin_mg"], vt])
    hg = {
        "HGH15CA": (15, 15, 28, 34, 61.4, 60, "M4", 11.38, 16.97, 0.18, 1.45),
        "HGH20CA": (20, 17.5, 30, 44, 77.5, 60, "M5", 17.75, 27.76, 0.30, 2.21),
        "HGH25CA": (23, 22, 40, 48, 84.0, 60, "M6", 26.48, 36.49, 0.51, 3.21),
        "HGH30CA": (28, 26, 45, 60, 97.4, 80, "M8", 38.74, 52.19, 0.88, 4.47),
        "HGH35CA": (34, 29, 55, 70, 112.4, 80, "M8", 49.52, 69.16, 1.45, 6.30),
        "HGH45CA": (45, 38, 70, 86, 139.4, 105, "M12", 77.57, 102.71, 2.73, 10.41),
    }
    for k, v in hg.items():
        vt = "datasheet" if k in ("HGH15CA", "HGH20CA", "HGH25CA") else "handbook_typical"
        rows.append([k, *v, "HIWIN HG square block on HGR rail; C at 50 km", SRC["hiwin_hg"], vt])
    write_csv("linear_rails.csv", hdr, rows)


def bushings():
    hdr = ["material", "maker", "max_static_pressure_MPa", "max_surface_speed_rotating_m_s", "max_pv_MPa_m_s",
           "temp_min_C", "temp_max_C", "friction_coeff_dry_min", "friction_coeff_dry_max",
           "recommended_housing_tolerance", "recommended_shaft_tolerance", "notes", "source_url", "value_type"]
    rows = [
        ["iglidur G", "igus", 80, 1.0, None, -40, 130, 0.08, 0.15, "H7", "h9", "all-rounder", SRC["igus"], "handbook_typical"],
        ["iglidur J", "igus", 35, 1.5, None, -50, 90, 0.06, 0.18, "H7", "h9", "low friction, soft shafts OK", SRC["igus"], "handbook_typical"],
        ["iglidur W300", "igus", 60, 1.0, None, -40, 90, 0.08, 0.23, "H7", "h9", "high wear resistance", SRC["igus"], "handbook_typical"],
        ["iglidur X", "igus", 150, 1.5, None, -100, 250, 0.09, 0.27, "H7", "h9", "high temp/chemical", SRC["igus"], "handbook_typical"],
        ["sintered bronze (oil-impregnated)", "generic (Oilite)", 14, 6.0, 1.75, -20, 90, 0.05, 0.10, "H7", "f7/g6", "needs PV check; relube", "https://www.oilite.com/ (typical)", "handbook_typical"],
        ["PTFE-lined steel (DU type)", "GGB", 250, 2.5, 3.6, -200, 280, 0.02, 0.25, "H7", "f7", "dynamic p max ~140 MPa", SRC["ggb_du"], "handbook_typical"],
    ]
    write_csv("bushings_plain_materials.csv", hdr, rows)
    hdr2 = ["part", "type", "bore_d1_mm", "outer_d2_mm", "flange_d3_mm", "flange_thickness_mm",
            "available_lengths_mm", "notes", "source_url", "value_type"]
    sizes = {3: (4.5, None, "3;4;5;6"), 4: (5.5, None, "3;4;6"), 5: (7, None, "4;5;8"), 6: (8, 12, "6;8;10"),
             8: (10, 15, "8;10;12"), 10: (12, 18, "10;12;15"), 12: (14, 20, "10;12;15;20"),
             16: (18, 24, "12;15;20;25"), 20: (23, 30, "15;20;25;30"), 25: (28, 35, "20;25;30"),
             30: (34, None, "20;30;40")}
    rows2 = []
    for d, (d2, d3, Ls) in sizes.items():
        rows2.append([f"GSM-{d:02d}{int(d2):02d}", "sleeve", d, d2, None, None, Ls,
                      "igus iglidur G sleeve; press into H7 bore, bore closes to ~E10 after press-in",
                      SRC["igus"], "handbook_typical"])
        if d3:
            ft = 1.5 if d >= 20 else 1.0
            rows2.append([f"GFM-{d:02d}{int(d2):02d}", "flanged", d, d2, d3, ft, Ls,
                          "igus iglidur G flange bearing", SRC["igus"], "handbook_typical"])
    write_csv("bushings_plain_sizes.csv", hdr2, rows2)


# ---------------------------------------------------------------- threads
COARSE = {1: 0.25, 1.2: 0.25, 1.4: 0.3, 1.6: 0.35, 2: 0.4, 2.5: 0.45, 3: 0.5, 3.5: 0.6, 4: 0.7, 5: 0.8, 6: 1.0,
          7: 1.0, 8: 1.25, 10: 1.5, 12: 1.75, 14: 2.0, 16: 2.0, 18: 2.5, 20: 2.5, 22: 2.5, 24: 3.0, 27: 3.0,
          30: 3.5, 33: 3.5, 36: 4.0, 42: 4.5, 48: 5.0}
FINE = [(3, 0.35), (4, 0.5), (5, 0.5), (6, 0.75), (8, 1.0), (10, 1.0), (10, 1.25), (12, 1.25), (12, 1.5),
        (14, 1.5), (16, 1.5), (18, 1.5), (20, 1.5), (20, 2.0), (22, 1.5), (24, 1.5), (24, 2.0), (30, 2.0), (36, 3.0)]
TAP_COARSE = {1: 0.75, 1.2: 0.95, 1.4: 1.1, 1.6: 1.25, 2: 1.6, 2.5: 2.05, 3: 2.5, 3.5: 2.9, 4: 3.3, 5: 4.2,
              6: 5.0, 7: 6.0, 8: 6.8, 10: 8.5, 12: 10.2, 14: 12.0, 16: 14.0, 18: 15.5, 20: 17.5, 22: 19.5,
              24: 21.0, 27: 24.0, 30: 26.5, 33: 29.5, 36: 32.0, 42: 37.5, 48: 43.0}


def fmt(d):
    return f"{d:g}"


def thread_geom(d, P):
    d2 = d - 0.649519 * P
    d1 = d - 1.082532 * P
    d3 = d - 1.226869 * P
    As = math.pi / 4 * ((d2 + d3) / 2) ** 2
    return d2, d1, d3, As


def threads():
    hdr = ["designation", "series", "d_mm", "pitch_mm", "pitch_dia_d2_mm", "nut_minor_dia_D1_mm",
           "bolt_minor_dia_d3_mm", "stress_area_mm2", "tap_drill_mm", "source_url", "value_type"]
    rows = []
    for d, P in COARSE.items():
        d2, d1, d3, As = thread_geom(d, P)
        rows.append([f"M{fmt(d)}", "coarse", d, P, round(d2, 3), round(d1, 3), round(d3, 3), round(As, 2),
                     TAP_COARSE[d], SRC["iso_thread"], "standard"])
    for d, P in FINE:
        d2, d1, d3, As = thread_geom(d, P)
        tap = round(round((d - P) / 0.05) * 0.05, 2)
        rows.append([f"M{fmt(d)}x{fmt(P)}", "fine", d, P, round(d2, 3), round(d1, 3), round(d3, 3), round(As, 2),
                     tap, SRC["iso_thread"], "standard"])
    write_csv("threads_iso_metric.csv", hdr, rows)


CLEAR = {1.6: (1.7, 1.8, 2.0), 2: (2.2, 2.4, 2.6), 2.5: (2.7, 2.9, 3.1), 3: (3.2, 3.4, 3.6), 4: (4.3, 4.5, 4.8),
         5: (5.3, 5.5, 5.8), 6: (6.4, 6.6, 7.0), 8: (8.4, 9.0, 10.0), 10: (10.5, 11.0, 12.0), 12: (13.0, 13.5, 14.5),
         14: (15.0, 15.5, 16.5), 16: (17.0, 17.5, 18.5), 20: (21.0, 22.0, 24.0), 24: (25.0, 26.0, 28.0)}

CLASSES = [  # class, Rm_min, Rp02_or_ReL_min, proof_stress, note
    ("4.6", 400, 240, 225, ""), ("4.8", 420, 340, 310, ""), ("5.6", 500, 300, 280, ""),
    ("5.8", 520, 420, 380, ""), ("6.8", 600, 480, 440, ""), ("8.8", 800, 640, 580, "d<=16"),
    ("8.8", 830, 660, 600, "d>16"), ("9.8", 900, 720, 650, "d<=16"), ("10.9", 1040, 940, 830, ""),
    ("12.9", 1220, 1100, 970, ""), ("A2-70", 700, 450, None, "ISO 3506 stainless; proof ~ Rp0.2"),
    ("A4-80", 800, 600, None, "ISO 3506 stainless; proof ~ Rp0.2"),
]


def yield_for(cls, d):
    for c, Rm, Rp, Sp, note in CLASSES:
        if c != cls:
            continue
        if note == "d<=16" and d > 16:
            continue
        if note == "d>16" and d <= 16:
            continue
        return Rm, Rp, (Sp if Sp else Rp)
    raise KeyError(cls)


def fasteners():
    write_csv("fastener_property_classes.csv",
              ["property_class", "tensile_strength_min_MPa", "yield_strength_min_MPa", "proof_stress_MPa",
               "notes", "source_url", "value_type"],
              [[c, Rm, Rp, Sp, n, SRC["iso3506"] if c.startswith("A") else SRC["iso898"], "standard"]
               for c, Rm, Rp, Sp, n in CLASSES])

    # ISO 4762 SHCS: dk, k, s(key), t_min, b_ref, counterbore dia, counterbore depth, lengths
    shcs = {1.6: (3.0, 1.6, 1.5, 0.7, 15, 3.5, 1.8, "3;4;5;6;8;10;12;16"),
            2: (3.8, 2, 1.5, 1.0, 16, 4.4, 2.3, "3;4;5;6;8;10;12;16;20"),
            2.5: (4.5, 2.5, 2, 1.1, 17, 5.5, 2.8, "4;5;6;8;10;12;16;20;25"),
            3: (5.5, 3, 2.5, 1.3, 18, 6.5, 3.3, "4;5;6;8;10;12;16;20;25;30;35;40"),
            4: (7.0, 4, 3, 2.0, 20, 8.0, 4.4, "5;6;8;10;12;16;20;25;30;35;40;45;50"),
            5: (8.5, 5, 4, 2.5, 22, 9.5, 5.4, "6;8;10;12;16;20;25;30;35;40;45;50;60"),
            6: (10.0, 6, 5, 3.0, 24, 11.0, 6.5, "8;10;12;16;20;25;30;35;40;45;50;60;70;80"),
            8: (13.0, 8, 6, 4.0, 28, 14.0, 8.6, "10;12;16;20;25;30;35;40;45;50;60;70;80;100"),
            10: (16.0, 10, 8, 5.0, 32, 17.5, 10.8, "12;16;20;25;30;35;40;45;50;60;70;80;100"),
            12: (18.0, 12, 10, 6.0, 36, 20.0, 13.0, "16;20;25;30;35;40;45;50;60;70;80;100;120"),
            14: (21.0, 14, 12, 7.0, 40, 23.0, 15.2, "20;25;30;40;50;60;80;100"),
            16: (24.0, 16, 14, 8.0, 44, 26.0, 17.5, "20;25;30;35;40;50;60;70;80;100;120"),
            20: (30.0, 20, 17, 10.0, 52, 32.0, 21.5, "30;40;50;60;70;80;100;120"),
            24: (36.0, 24, 19, 12.0, 60, 39.0, 25.5, "40;50;60;80;100;120")}
    hdr = ["thread", "pitch_mm", "head_dia_dk_mm", "head_height_k_mm", "hex_key_s_mm", "key_engagement_t_min_mm",
           "thread_length_b_ref_mm", "counterbore_dia_mm", "counterbore_depth_mm", "clearance_close_mm",
           "clearance_normal_mm", "clearance_loose_mm", "tap_drill_mm", "stress_area_mm2",
           "proof_load_8_8_kN", "proof_load_10_9_kN", "proof_load_12_9_kN", "common_lengths_mm",
           "source_url", "value_type"]
    rows = []
    for d, (dk, k, s, t, b, cbd, cbh, Ls) in shcs.items():
        P = COARSE[d]
        As = thread_geom(d, P)[3]
        pl = [round(As * yield_for(c, d)[2] / 1000, 2) for c in ("8.8", "10.9", "12.9")]
        rows.append([f"M{fmt(d)}", P, dk, k, s, t, b, cbd, cbh, *CLEAR[d], TAP_COARSE[d], round(As, 2), *pl, Ls,
                     SRC["iso4762"], "standard"])
    write_csv("fasteners_iso4762_shcs.csv", hdr, rows)

    btn = {3: (5.7, 1.65, 2), 4: (7.6, 2.2, 2.5), 5: (9.5, 2.75, 3), 6: (10.5, 3.3, 4), 8: (14.0, 4.4, 5),
           10: (17.5, 5.5, 6), 12: (21.0, 6.6, 8), 16: (28.0, 8.8, 10)}
    write_csv("fasteners_iso7380_button.csv",
              ["thread", "pitch_mm", "head_dia_dk_mm", "head_height_k_mm", "hex_key_s_mm", "clearance_normal_mm",
               "notes", "source_url", "value_type"],
              [[f"M{d}", COARSE[d], dk, k, s, CLEAR[d][1], "usually class 10.9 / A2; lower key torque than SHCS",
                SRC["iso7380"], "standard"] for d, (dk, k, s) in btn.items()])

    csk = {3: (6.72, 5.54, 1.86, 2), 4: (8.96, 7.53, 2.48, 2.5), 5: (11.2, 9.43, 3.1, 3), 6: (13.44, 11.34, 3.72, 4),
           8: (17.92, 15.24, 4.96, 5), 10: (22.4, 19.22, 6.2, 6), 12: (26.88, 23.12, 7.44, 8),
           16: (33.6, 29.01, 8.8, 10), 20: (40.32, 36.05, 10.16, 12)}
    write_csv("fasteners_iso10642_countersunk.csv",
              ["thread", "pitch_mm", "head_dia_theoretical_max_mm", "head_dia_actual_min_mm", "head_height_k_mm",
               "hex_key_s_mm", "countersink_angle_deg", "countersink_dia_recommended_mm", "clearance_normal_mm",
               "source_url", "value_type"],
              [[f"M{d}", COARSE[d], dkt, dka, k, s, 90, round(dkt + 0.4, 2), CLEAR[d][1], SRC["iso10642"], "standard"]
               for d, (dkt, dka, k, s) in csk.items()])

    nut = {2: (4, 4.32, 1.6, None, 1.2), 2.5: (5, 5.45, 2.0, None, 1.6), 3: (5.5, 6.01, 2.4, 4.0, 1.8),
           4: (7, 7.66, 3.2, 5.0, 2.2), 5: (8, 8.79, 4.7, 5.0, 2.7), 6: (10, 11.05, 5.2, 6.0, 3.2),
           8: (13, 14.38, 6.8, 8.0, 4.0), 10: (16, 17.77, 8.4, 10.0, 5.0), 12: (18, 20.03, 10.8, 12.0, 6.0),
           14: (21, 23.36, 12.8, 14.0, 7.0), 16: (24, 26.75, 14.8, 16.0, 8.0), 20: (30, 32.95, 18.0, 20.0, 10.0),
           24: (36, 39.55, 21.5, 24.0, 12.0)}
    write_csv("fasteners_hex_nuts.csv",
              ["thread", "pitch_mm", "width_across_flats_s_mm", "width_across_corners_e_min_mm",
               "height_iso4032_mm", "height_nyloc_iso7040_mm", "height_thin_iso4035_mm", "source_url", "value_type"],
              [[f"M{fmt(d)}", COARSE[d], *v, SRC["iso4032"], "standard"] for d, v in nut.items()])

    wsh = {2: (2.2, 5, 0.3), 2.5: (2.7, 6, 0.5), 3: (3.2, 7, 0.5), 4: (4.3, 9, 0.8), 5: (5.3, 10, 1.0),
           6: (6.4, 12, 1.6), 8: (8.4, 16, 1.6), 10: (10.5, 20, 2.0), 12: (13.0, 24, 2.5), 16: (17.0, 30, 3.0),
           20: (21.0, 37, 3.0), 24: (25.0, 44, 4.0)}
    big = {3: (3.2, 9, 0.8), 4: (4.3, 12, 1.0), 5: (5.3, 15, 1.2), 6: (6.4, 18, 1.6), 8: (8.4, 24, 2.0),
           10: (10.5, 30, 2.5), 12: (13.0, 37, 3.0), 16: (17.0, 50, 3.0)}
    rows = [[f"M{fmt(d)}", "ISO 7089 normal", *v, SRC["iso7089"], "standard"] for d, v in wsh.items()]
    rows += [[f"M{d}", "ISO 7093 large", *v, "https://www.iso.org/standard/38895.html", "standard"] for d, v in big.items()]
    write_csv("fasteners_washers.csv",
              ["thread", "type", "inner_dia_d1_mm", "outer_dia_d2_mm", "thickness_h_mm", "source_url", "value_type"], rows)

    ins = [("M2", 4.0, 3.6, 3.2, 1.6), ("M2.5", 5.7, 4.6, 4.0, 2.0), ("M3", 5.7, 4.6, 4.0, 2.0),
           ("M3 short", 3.0, 4.6, 4.0, 1.6), ("M4", 8.1, 6.3, 5.6, 2.5), ("M5", 9.5, 7.1, 6.4, 3.0),
           ("M6", 12.7, 8.7, 8.0, 3.5), ("M8", 12.7, 10.1, 9.7, 4.0)]
    write_csv("fasteners_heat_set_inserts.csv",
              ["thread", "length_mm", "outer_dia_mm", "recommended_hole_dia_mm", "min_wall_around_hole_mm",
               "notes", "source_url", "value_type"],
              [[t, L, od, h, w, "brass knurled insert for FDM; hole depth >= length + 1 mm; vendors differ +-0.2 mm",
                SRC["inserts"], "handbook_typical"] for t, L, od, h, w in ins])

    # tightening torques (VDI 2230 simplified, nu = 0.9 utilisation, SHCS head bearing)
    rows = []
    for d in shcs:
        P = COARSE[d]
        d2, _, d3, As = thread_geom(d, P)
        d0 = (d2 + d3) / 2
        A0 = math.pi / 4 * d0 * d0
        dkm = (shcs[d][0] + CLEAR[d][1]) / 2
        for cls in ("8.8", "10.9", "12.9", "A2-70"):
            Rm, Rp, _ = yield_for(cls, d)
            for mu in (0.10, 0.12, 0.14):
                FM = A0 * 0.9 * Rp / math.sqrt(1 + 3 * (1.5 * d2 / d0 * (P / (math.pi * d2) + 1.155 * mu)) ** 2)
                MA = FM * (0.16 * P + 0.58 * d2 * mu + dkm / 2 * mu) / 1000
                rows.append([f"M{fmt(d)}", cls, mu, round(FM / 1000, 3), round(MA, 3), SRC["vdi2230"], "estimate"])
    write_csv("fastener_tightening_torque.csv",
              ["thread", "property_class", "friction_coeff", "assembly_preload_kN", "tightening_torque_Nm",
               "source_url", "value_type"], rows)


# ---------------------------------------------------------------- belts and pulleys
BELTS = {  # pitch, tooth height, thickness, PLD, widths, min teeth, working tension N/mm width (estimate)
    "GT2": (2.0, 0.75, 1.38, 0.254, "3;6;9;10;12;15", 12, 8),
    "GT3": (3.0, 1.14, 2.41, 0.381, "6;9;12;15", 12, 15),
    "HTD3M": (3.0, 1.17, 2.40, 0.381, "6;9;15", 10, 13),
    "HTD5M": (5.0, 2.06, 3.80, 0.5715, "9;15;25", 14, 25),
    "MXL": (2.032, 0.51, 1.14, 0.254, "3.2;4.8;6.4", 10, 4),
    "XL": (5.08, 1.27, 2.30, 0.254, "6.4;7.9;9.5", 10, 8),
    "T5": (5.0, 1.2, 2.2, None, "6;10;16;25", 10, 10),
}
LENGTHS = {
    "GT2": [100, 110, 112, 120, 122, 140, 158, 160, 180, 188, 200, 202, 210, 220, 232, 236, 240, 250, 252, 256,
            262, 280, 300, 302, 320, 340, 350, 360, 380, 400, 410, 420, 440, 456, 480, 500, 520, 560, 600, 610,
            640, 700, 752, 760, 800, 852, 1000, 1164],
    "GT3": [99, 111, 120, 129, 141, 150, 159, 168, 174, 180, 189, 201, 210, 225, 240, 252, 264, 276, 300, 315,
            339, 357, 384, 402, 420, 447, 474, 501, 549, 600, 651, 699, 750, 801],
    "HTD3M": [141, 153, 159, 177, 189, 201, 210, 225, 240, 252, 255, 264, 282, 300, 312, 339, 357, 375, 390, 420,
              447, 474, 501, 537, 564, 600, 633, 669, 711, 750, 804, 843, 882, 945, 1062, 1200],
    "HTD5M": [200, 225, 255, 265, 280, 300, 325, 350, 375, 400, 425, 450, 475, 500, 535, 565, 600, 635, 670, 710,
              750, 800, 850, 890, 950, 1000, 1050, 1125, 1200, 1270, 1420],
}
TEETH = {
    "GT2": [12, 16, 20, 24, 30, 32, 36, 40, 48, 60, 72, 80, 100],
    "GT3": [12, 14, 16, 18, 20, 24, 28, 30, 32, 36, 40, 44, 48, 60, 72],
    "HTD3M": [10, 12, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 44, 48, 60, 72],
    "HTD5M": [12, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30, 32, 36, 40, 44, 48, 60, 72],
    "MXL": [10, 12, 14, 16, 18, 20, 24, 28, 30, 32, 36, 40, 48, 60],
    "XL": [10, 11, 12, 14, 15, 16, 18, 20, 22, 24, 26, 28, 30, 36, 40, 48, 60],
}


def belts():
    rows = []
    for k, (p, th, t, pld, ws, zmin, ten) in BELTS.items():
        rows.append([k, p, th, t, pld, ws, zmin, ten, round(t * 1.25e-3 * 0.8, 5),
                     "fibreglass cord; working tension and mass are rough estimates, size drives with maker manual",
                     SRC["gates"], "estimate"])
    write_csv("timing_belt_profiles.csv",
              ["profile", "pitch_mm", "tooth_height_mm", "belt_thickness_mm", "pitch_line_differential_mm",
               "standard_widths_mm", "min_recommended_pulley_teeth", "max_working_tension_N_per_mm_width",
               "mass_kg_per_m_per_mm_width", "notes", "source_url", "value_type"], rows)
    rows = []
    for k, Ls in LENGTHS.items():
        p = BELTS[k][0]
        for L in Ls:
            rows.append([f"{k}-{L}", k, L, p, round(L / p), SRC["gates"], "handbook_typical"])
    write_csv("timing_belt_closed_loops.csv",
              ["designation", "profile", "pitch_length_mm", "pitch_mm", "teeth", "source_url", "value_type"], rows)
    rows = []
    for k, zs in TEETH.items():
        p, pld = BELTS[k][0], BELTS[k][3]
        for z in zs:
            pd = z * p / math.pi
            rows.append([f"{k}-{z}T", k, z, p, round(pd, 3), round(pd - 2 * pld, 3), SRC["gates"], "standard"])
    write_csv("timing_pulleys.csv",
              ["designation", "profile", "teeth", "pitch_mm", "pitch_dia_mm", "outside_dia_mm", "source_url",
               "value_type"], rows)


# ---------------------------------------------------------------- extrusions
def extrusions():
    hdr = ["profile", "family", "width_mm", "height_mm", "slot_width_mm", "area_mm2", "mass_kg_per_m",
           "Ixx_mm4", "Iyy_mm4", "Wxx_mm3", "Wyy_mm3", "E_GPa", "yield_MPa", "alloy", "notes",
           "source_url", "value_type"]
    data = [  # name, family, w, h(bending depth for Ixx), slot, area, Ixx, Iyy
        ("2020 V-slot", "OpenBuilds V-slot", 20, 20, 6.2, 165, 7.0e3, 7.0e3),
        ("2040 V-slot", "OpenBuilds V-slot", 20, 40, 6.2, 300, 4.7e4, 1.3e4),
        ("2020 T-slot", "B-type slot 6 (Misumi HFS5)", 20, 20, 6.2, 160, 6.9e3, 6.9e3),
        ("2040 T-slot", "B-type slot 6 (Misumi HFS5)", 20, 40, 6.2, 290, 4.6e4, 1.3e4),
        ("3030 T-slot", "B-type slot 8 (Misumi HFS6)", 30, 30, 8.2, 340, 3.0e4, 3.0e4),
        ("4040 T-slot", "B-type slot 8 (Misumi HFS8)", 40, 40, 8.2, 560, 9.0e4, 9.0e4),
    ]
    rows = []
    for n, fam, w, h, s, A, Ix, Iy in data:
        rows.append([n, fam, w, h, s, A, round(A * 2.70e-3, 3), Ix, Iy, round(Ix / (h / 2), 1), round(Iy / (w / 2), 1),
                     69, 160, "6063-T5/T6", "Ixx bends about the axis giving depth=height; vendor values vary +-15%",
                     SRC["openbuilds"], "handbook_typical"])
    write_csv("extrusions_aluminium.csv", hdr, rows)


# ---------------------------------------------------------------- ISO 286
RANGES = [(0, 3), (3, 6), (6, 10), (10, 18), (18, 30), (30, 50), (50, 65), (65, 80), (80, 100), (100, 120)]
IT = {  # per range, um (50-80 and 80-120 split)
    5: [4, 5, 6, 8, 9, 11, 13, 13, 15, 15], 6: [6, 8, 9, 11, 13, 16, 19, 19, 22, 22],
    7: [10, 12, 15, 18, 21, 25, 30, 30, 35, 35], 8: [14, 18, 22, 27, 33, 39, 46, 46, 54, 54],
    9: [25, 30, 36, 43, 52, 62, 74, 74, 87, 87], 10: [40, 48, 58, 70, 84, 100, 120, 120, 140, 140],
    11: [60, 75, 90, 110, 130, 160, 190, 190, 220, 220],
}
UPPER = {"f": [-6, -10, -13, -16, -20, -25, -30, -30, -36, -36], "g": [-2, -4, -5, -6, -7, -9, -10, -10, -12, -12],
         "h": [0] * 10}
LOWER = {"k": [0, 1, 1, 1, 2, 2, 2, 2, 3, 3], "m": [2, 4, 6, 7, 8, 9, 11, 11, 13, 13],
         "n": [4, 8, 10, 12, 15, 17, 20, 20, 23, 23], "p": [6, 12, 15, 18, 22, 26, 32, 32, 37, 37],
         "s": [14, 19, 23, 28, 35, 43, 53, 59, 71, 79]}
SHAFTS = ["f6", "f7", "g5", "g6", "h5", "h6", "h7", "h8", "h9", "h10", "h11", "js5", "js6", "js7", "k5", "k6",
          "m5", "m6", "n5", "n6", "p6", "s6", "s7"]


def lim_shaft(code, i):
    letter, g = code.rstrip("0123456789"), int(code.lstrip("abcdefghijklmnopqrstuvwxyz"))
    t = IT[g][i]
    if letter == "js":
        return [t / 2, -t / 2]
    if letter in UPPER:
        es = UPPER[letter][i]
        return [es, es - t]
    ei = LOWER[letter][i]
    return [ei + t, ei]


def iso286():
    out = {
        "description": "ISO 286-2 limit deviations, micrometres. Range [a,b] means over a up to and including b. "
                       "Each entry is [upper_deviation_um, lower_deviation_um] per size range, same order as size_ranges_mm.",
        "units": "um",
        "source_url": SRC["iso286"],
        "value_type": "standard",
        "notes": "js = +-IT/2 (not rounded to even); k ei given for grades 4-7.",
        "size_ranges_mm": [list(r) for r in RANGES],
        "IT_grades_um": {f"IT{g}": v for g, v in IT.items()},
        "holes": {f"H{g}": [[IT[g][i], 0] for i in range(len(RANGES))] for g in range(6, 12)},
        "shafts": {c: [lim_shaft(c, i) for i in range(len(RANGES))] for c in SHAFTS},
        "common_fits": {
            "H11/h11": "loose running, cheap", "H9/f8": "free running", "H8/f7": "close running (plain bearings)",
            "H7/g6": "sliding, accurate location", "H7/h6": "locational clearance", "H7/js6": "light transition",
            "H7/k6": "locational transition (bearing inner rings, light)", "H7/n6": "locational transition, firm",
            "H7/p6": "locational interference (press)", "H7/s6": "medium drive / shrink fit",
        },
    }
    with open(os.path.join(HERE, "iso286_fits.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("iso286_fits.json: %d holes, %d shafts, %d ranges" % (len(out["holes"]), len(out["shafts"]), len(RANGES)))


def range_index(d):
    for i, (a, b) in enumerate(RANGES):
        if a < d <= b:
            return i
    raise ValueError(d)


# ---------------------------------------------------------------- shafts, keys, rings, pins
def shafts():
    rows = []
    for d in [3, 4, 5, 6, 8, 10, 12, 13, 15, 16, 20, 25, 30, 35, 40, 50]:
        i = range_index(d)
        g6, h6 = lim_shaft("g6", i), lim_shaft("h6", i)
        rows.append([f"shaft-{d}", d, round(math.pi / 4 * d * d * 1000 * STEEL_KG_MM3, 4), g6[0], g6[1], h6[0], h6[1],
                     "CF53/SUJ2 induction hardened HRC58-62, ground", 200, SRC["shaft"], "standard"])
    write_csv("shafts_linear_precision.csv",
              ["designation", "d_mm", "mass_kg_per_m", "g6_upper_um", "g6_lower_um", "h6_upper_um", "h6_lower_um",
               "material", "E_GPa", "source_url", "value_type"], rows)

    keys = [(6, 8, 2, 2, 1.2, 1.0, 6, 20), (8, 10, 3, 3, 1.8, 1.4, 6, 36), (10, 12, 4, 4, 2.5, 1.8, 8, 45),
            (12, 17, 5, 5, 3.0, 2.3, 10, 56), (17, 22, 6, 6, 3.5, 2.8, 14, 70), (22, 30, 8, 7, 4.0, 3.3, 18, 90),
            (30, 38, 10, 8, 5.0, 3.3, 22, 110), (38, 44, 12, 8, 5.0, 3.3, 28, 140), (44, 50, 14, 9, 5.5, 3.8, 36, 160),
            (50, 58, 16, 10, 6.0, 4.3, 45, 180), (58, 65, 18, 11, 7.0, 4.4, 50, 200), (65, 75, 20, 12, 7.5, 4.9, 56, 220),
            (75, 85, 22, 14, 9.0, 5.4, 63, 250), (85, 95, 25, 14, 9.0, 5.4, 70, 280), (95, 110, 28, 16, 10.0, 6.4, 80, 320),
            (110, 130, 32, 18, 11.0, 7.4, 90, 360)]
    write_csv("keys_din6885.csv",
              ["shaft_dia_over_mm", "shaft_dia_upto_mm", "key_width_b_mm", "key_height_h_mm", "shaft_keyway_depth_t1_mm",
               "hub_keyway_depth_t2_mm", "length_min_mm", "length_max_mm", "notes", "source_url", "value_type"],
              [[*k, "parallel key form A; width tol h9, shaft groove N9/P9, hub JS9/P9; key material C45 (Rm~600 MPa)",
                SRC["din6885"], "standard"] for k in keys])

    ext = [(3, 0.4, 2.8, 0.5), (4, 0.4, 3.8, 0.5), (5, 0.6, 4.8, 0.7), (6, 0.7, 5.7, 0.8), (7, 0.8, 6.7, 0.9),
           (8, 0.8, 7.6, 0.9), (9, 1.0, 8.6, 1.1), (10, 1.0, 9.6, 1.1), (12, 1.0, 11.5, 1.1), (14, 1.0, 13.4, 1.1),
           (15, 1.0, 14.3, 1.1), (16, 1.0, 15.2, 1.1), (17, 1.0, 16.2, 1.1), (18, 1.2, 17.0, 1.3), (20, 1.2, 19.0, 1.3),
           (22, 1.2, 21.0, 1.3), (25, 1.2, 23.9, 1.3), (28, 1.5, 26.6, 1.6), (30, 1.5, 28.6, 1.6), (32, 1.5, 30.3, 1.6),
           (35, 1.5, 33.0, 1.6), (40, 1.75, 37.5, 1.85), (45, 1.75, 42.5, 1.85), (50, 2.0, 47.0, 2.15)]
    intr = [(8, 0.8, 8.4, 0.9), (9, 0.8, 9.4, 0.9), (10, 1.0, 10.4, 1.1), (12, 1.0, 12.5, 1.1), (13, 1.0, 13.6, 1.1),
            (14, 1.0, 14.6, 1.1), (15, 1.0, 15.7, 1.1), (16, 1.0, 16.8, 1.1), (17, 1.0, 17.8, 1.1), (18, 1.0, 19.0, 1.1),
            (19, 1.0, 20.0, 1.1), (20, 1.0, 21.0, 1.1), (22, 1.0, 23.0, 1.1), (24, 1.2, 25.2, 1.3), (25, 1.2, 26.2, 1.3),
            (26, 1.2, 27.2, 1.3), (28, 1.2, 29.4, 1.3), (30, 1.2, 31.4, 1.3), (32, 1.2, 33.7, 1.3), (35, 1.5, 37.0, 1.6),
            (37, 1.5, 39.0, 1.6), (40, 1.75, 42.5, 1.85), (42, 1.75, 44.5, 1.85), (47, 1.75, 49.5, 1.85),
            (52, 2.0, 55.0, 2.15), (55, 2.0, 58.0, 2.15), (62, 2.0, 65.0, 2.15)]
    rows = [["DIN 471", "external (shaft)", *r, SRC["din471"], "standard"] for r in ext]
    rows += [["DIN 472", "internal (bore)", *r, SRC["din471"], "standard"] for r in intr]
    write_csv("retaining_rings_din471_472.csv",
              ["standard", "type", "nominal_dia_d1_mm", "ring_thickness_s_mm", "groove_dia_d2_mm",
               "groove_width_m_mm", "source_url", "value_type"], rows)

    rows = []
    for d, Lmin, Lmax in [(1.5, 4, 16), (2, 5, 20), (2.5, 6, 24), (3, 6, 30), (4, 8, 40), (5, 10, 50), (6, 12, 60),
                          (8, 16, 80), (10, 20, 100), (12, 25, 100), (16, 40, 100), (20, 50, 100)]:
        i = range_index(d)
        m6 = lim_shaft("m6", i)
        shear = round(2 * math.pi / 4 * d * d * 900 / 1000, 2)
        rows.append([f"ISO 8734 {fmt(d)}", "hardened (HRC 60 core ~550HV)", d, "m6", m6[0], m6[1], Lmin, Lmax, shear,
                     "press into H7 (interference); slip into G7/F7 side; double shear est. 2*A*900 MPa",
                     SRC["iso8734"], "estimate"])
    write_csv("dowel_pins.csv",
              ["designation", "type", "d_mm", "tolerance", "upper_dev_um", "lower_dev_um", "length_min_mm",
               "length_max_mm", "double_shear_min_kN", "notes", "source_url", "value_type"], rows)


# ---------------------------------------------------------------- springs
def springs():
    mats = [  # name, ASTM, A MPa*mm^m, m, E GPa, G GPa, d range, max temp
        ("music wire", "A228", 2211, 0.145, 203.4, 82.7, "0.10-6.5", 120),
        ("oil-tempered", "A229", 1855, 0.187, 196.5, 77.2, "0.5-12", 180),
        ("hard-drawn", "A227", 1783, 0.190, 196.5, 80.0, "0.7-12", 120),
        ("chrome-vanadium", "A231", 2005, 0.168, 203.4, 77.2, "0.8-11", 220),
        ("chrome-silicon", "A401", 1974, 0.108, 203.4, 77.2, "1.6-9.5", 245),
        ("stainless 302", "A313", 1867, 0.146, 193.0, 69.0, "0.3-2.5", 260),
        ("phosphor bronze", "B159", 1000, 0.0, 103.4, 41.4, "0.1-0.6", 90),
    ]
    write_csv("spring_wire_materials.csv",
              ["material", "astm", "A_MPa_mm_m", "m_exponent", "E_GPa", "G_GPa", "wire_dia_range_mm", "max_temp_C",
               "notes", "source_url", "value_type"],
              [[*m, "Sut = A / d^m (d in mm); torsional yield ~0.45 Sut (set removed)", SRC["shigley"], "handbook_typical"]
               for m in mats])
    rows = []
    G = 81.7e3  # music wire, MPa (A228 nominal; Shigley lists 82.7)
    for d, D, Na in [(0.3, 3, 8), (0.5, 4, 8), (0.5, 5, 10), (0.6, 6, 8), (0.8, 6, 8), (0.8, 8, 8), (1.0, 8, 8),
                     (1.0, 10, 8), (1.2, 10, 8), (1.5, 12, 8), (2.0, 16, 8), (2.5, 20, 8)]:
        Dm = D - d
        k = G * d ** 4 / (8 * Dm ** 3 * Na)
        Sut = 2211 / d ** 0.145
        C = Dm / d
        Kb = (4 * C + 2) / (4 * C - 3)
        F_max = 0.45 * Sut * math.pi * d ** 3 / (8 * Kb * Dm)
        Ls = d * (Na + 2)
        L0 = round(Ls + 1.15 * F_max / k, 1)
        rows.append([f"CS-{d}x{D}x{L0}", "compression, closed & ground ends", d, D, round(Dm, 2), Na, L0, round(Ls, 2),
                     round(k, 3), round(F_max, 2), "music wire A228", "computed from k=Gd^4/(8D^3Na)",
                     SRC["shigley"], "estimate"])
    write_csv("springs_compression_typical.csv",
              ["designation", "type", "wire_dia_mm", "outer_dia_mm", "mean_dia_mm", "active_coils", "free_length_mm",
               "solid_length_mm", "rate_N_per_mm", "max_working_load_N", "material", "notes", "source_url",
               "value_type"], rows)


# ---------------------------------------------------------------- couplings
def couplings():
    inlb = 0.112985
    rows = []
    for n, od, bmax, t in [("L035", 16.0, 9.5, 3.5), ("L050", 27.4, 15.9, 26.3), ("L070", 35.0, 19.0, 43.2),
                           ("L075", 44.5, 22.2, 90), ("L090", 53.6, 25.4, 144), ("L095", 53.6, 28.6, 194),
                           ("L100", 64.3, 34.9, 414)]:
        vt = "datasheet" if n in ("L035", "L050") else "handbook_typical"
        rows.append([n, "jaw (NBR spider)", od, None, None, bmax, round(t * inlb, 2), None, None,
                     "Lovejoy L-type; parallel misalign ~0.38 mm, angular 1 deg", SRC["lovejoy"], vt])
    hobby = [("D19L25 helical", "aluminium helical beam", 19, 25, 3, 10, 1.0, 0.25, 5),
             ("D20L25 jaw", "aluminium jaw/plum (TPU spider)", 20, 25, 3, 10, 1.2, 0.2, 1),
             ("D25L30 jaw", "aluminium jaw/plum (TPU spider)", 25, 30, 4, 14, 2.5, 0.2, 1),
             ("D25L30 oldham", "aluminium oldham (POM disc)", 25, 30, 4, 14, 2.0, 1.0, 3),
             ("D14L25 rigid", "aluminium rigid clamp", 14, 25, 3, 8, 1.5, 0.0, 0),
             ("D20L25 bellows", "aluminium bellows", 20, 25, 4, 10, 1.0, 0.15, 2),
             ("D16L23 bellows", "stainless bellows", 16, 23, 3, 8, 0.6, 0.1, 1.5)]
    for n, t, od, L, bmin, bmax, T, par, ang in hobby:
        rows.append([n, t, od, L, bmin, bmax, T, par, ang, "common hobby/CNC sizes; torque rough", SRC["hobby_coupling"],
                     "estimate"])
    write_csv("couplings.csv",
              ["designation", "type", "outer_dia_mm", "length_mm", "bore_min_mm", "bore_max_mm", "rated_torque_Nm",
               "max_parallel_misalign_mm", "max_angular_misalign_deg", "notes", "source_url", "value_type"], rows)


# ---------------------------------------------------------------- screws
def lead_screws():
    rows = []
    for n, d, P, starts in [("Tr8x1.5", 8, 1.5, 1), ("Tr8x2 (T8 P2 L2)", 8, 2, 1), ("Tr8x4 (T8 L4)", 8, 2, 2),
                            ("Tr8x8 (T8 L8)", 8, 2, 4), ("Tr10x2", 10, 2, 1), ("Tr10x3", 10, 3, 1),
                            ("Tr12x3", 12, 3, 1), ("Tr16x4", 16, 4, 1), ("Tr20x4", 20, 4, 1), ("Tr24x5", 24, 5, 1)]:
        ac = 0.15 if P <= 1.5 else 0.25
        d2 = d - 0.5 * P
        d3 = d - (P + 2 * ac)
        lead = P * starts
        lam = math.atan(lead / (math.pi * d2))
        out = [n, d, P, starts, lead, round(d2, 3), round(d3, 3), round(math.degrees(lam), 2)]
        for mu in (0.1, 0.2):
            ph = math.atan(mu / math.cos(math.radians(15)))
            eta = math.tan(lam) / math.tan(lam + ph)
            out += [round(eta, 3), round(d2 / 2 * math.tan(lam + ph) / 1000, 6)]
        ph = math.atan(0.1 / math.cos(math.radians(15)))
        out += ["yes" if lam < ph else "no", round(math.pi / 4 * d3 * d3 * 1000 * STEEL_KG_MM3 * 1.15, 3)]
        note = "ISO 2904" if n in ("Tr8x1.5", "Tr10x2", "Tr10x3", "Tr12x3", "Tr16x4", "Tr20x4", "Tr24x5") else \
            "hobby T8 (not ISO): brass flange nut flange 22, body 10.2, len 15, 4x3.5 holes on PCD 16"
        rows.append(out + [note, SRC["iso2904"], "standard" if note == "ISO 2904" else "handbook_typical"])
    write_csv("lead_screws_trapezoidal.csv",
              ["designation", "d_mm", "pitch_mm", "starts", "lead_mm", "pitch_dia_d2_mm", "minor_dia_d3_mm",
               "lead_angle_deg", "efficiency_mu0_1", "torque_per_N_load_mu0_1_Nm", "efficiency_mu0_2",
               "torque_per_N_load_mu0_2_Nm", "self_locking_mu0_1", "mass_kg_per_m", "notes", "source_url",
               "value_type"], rows)

    kgf = 9.80665e-3
    rows = []
    for n, d, L, ball, Ca, C0a, D, D1, Ln, flt, bcd, hole in [
        ("SFU1204-4", 12, 4, 2.5, 902, 1884, 24, 40, 40, 10, 32, 4.5),
        ("SFU1605-4", 16, 5, 3.175, 1380, 3052, 28, 48, 42, 10, 38, 5.5),
        ("SFU1610-3", 16, 10, 3.175, 1068, 2276, 28, 48, 57, 10, 38, 5.5),
        ("SFU2005-4", 20, 5, 3.175, 1543, 3953, 36, 58, 51, 10, 47, 6.6),
        ("SFU2505-4", 25, 5, 3.175, 1722, 5014, 40, 62, 51, 10, 51, 6.6),
    ]:
        rows.append([n, d, L, ball, round(d - ball, 2), round(Ca * kgf, 2), round(C0a * kgf, 2), D, D1, Ln, flt, bcd,
                     hole, 0.9, "C7 (0.05 mm/300 mm)", round(math.pi / 4 * (d - ball / 2) ** 2 * 1000 * STEEL_KG_MM3, 3),
                     "TBI-style SFU single flange nut; ratings from TBI tables (1605 cross-checked vs TBI SFI 1605), "
                     "clones may be lower; root dia ~ d - ball", SRC["tbi"],
                     "handbook_typical" if n == "SFU1605-4" else "estimate"])
    write_csv("ball_screws_SFU.csv",
              ["designation", "d_mm", "lead_mm", "ball_dia_mm", "root_dia_approx_mm", "Ca_kN", "C0a_kN",
               "nut_dia_D_mm", "flange_dia_D1_mm", "nut_length_mm", "flange_thickness_mm", "bolt_circle_mm",
               "bolt_hole_dia_mm", "efficiency_typical", "lead_accuracy_grade", "mass_kg_per_m", "notes",
               "source_url", "value_type"], rows)


if __name__ == "__main__":
    deep_groove(); thrust(); angular(); needle(); linear_bearings(); linear_rails(); bushings()
    threads(); fasteners(); belts(); extrusions(); iso286(); shafts(); springs(); couplings(); lead_screws()
