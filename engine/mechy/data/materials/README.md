# Materials dataset

Lookup data that Mechy agents use for material selection and sizing. All CSVs have a header row, SI units in the column names, one row per item, plus `source_url` and `value_type` (`datasheet` | `standard` | `handbook_typical` | `estimate`). Run `python3 -I check.py` to validate. It currently prints PASS.

## Files

| File | Rows | Contents |
|---|---|---|
| `materials.csv` | 348 | Bulk/conventional materials: carbon, structural, alloy, tool and stainless steels with heat treatments; cast irons; Al alloys and tempers; Cu/brass/bronze; Ti; Mg; Zn; Ni and refractory metals; LPBF metals; engineering, commodity and high-performance plastics; composites, laminates and fibres; woods; elastomers; ceramics; glass |
| `am_materials.csv` | 70 | 3D-printing materials: generic FDM, Prusament, Polymaker, Bambu Lab, eSun, Formlabs resins and powder, HP MJF, EOS SLS, Markforged, Stratasys, igus. XY vs Z columns |
| `galvanic_anodic_index.csv` | 19 | MIL-STD-889 style anodic index (V) by metal group |
| `galvanic_seawater_potentials.csv` | 29 | Corrosion potential ranges in flowing seawater (V vs SCE) |
| `galvanic_rules.json` | - | Allowed anodic-index difference by environment (0.15 / 0.25 / 0.50 V), plus mitigations |
| `friction_pairs.csv` | 57 | Static/kinetic friction coefficients for material pairs, dry and lubricated |
| `bushing_pv_limits.csv` | 28 | Plain-bearing limits: static/dynamic pressure, speed, PV, mu, temperature range, shaft recommendation |

### materials.csv columns
`id, name, category, subcategory, designation, condition, density_kg_m3, youngs_modulus_GPa, shear_modulus_GPa, poisson_ratio, yield_strength_MPa, uts_MPa, elongation_pct, flexural_strength_MPa, compressive_strength_MPa, hardness_value, hardness_scale, endurance_limit_MPa, cte_um_per_m_K, thermal_conductivity_W_per_m_K, max_service_temp_C, hdt_0_45MPa_C, hdt_1_8MPa_C, tg_C, melting_point_C, cost_tier, notes, source_url, value_type`

How to read the columns:
- `hardness_scale` can be HB, HRB, HRC, HRA, HRE, HRF, HRH, HRM, HRR, HV, HK, ShoreA, ShoreD or Janka_N.
- `cost_tier` is the approximate raw stock price: 1 is under $2/kg, 2 is $2-6, 3 is $6-20, 4 is $20-100, 5 is over $100/kg (or a specialty item).
- Woods: `youngs_modulus_GPa` is the bending MOE and `flexural_strength_MPa` is the MOR (modulus of rupture). Both are measured parallel to grain on clear wood at 12% moisture. `compressive_strength_MPa` is compression parallel to grain.
- Ceramics and glass: design on `flexural_strength_MPa` (for carbides this is transverse rupture strength). `uts_MPa` is blank for most of them.
- Composites: values are in the fibre/0-degree direction. Transverse values are in `notes`.
- Elastomers: E is estimated from Shore hardness with the Gent relation, so treat it as approximate.
- `endurance_limit_MPa`: for steels without a published value it is about 0.5×UTS (rotating-beam, unnotched) and marked in notes. For Al, Mg and Zn it is the fatigue strength at 5e8 cycles, because these metals have no true endurance limit. Polymer values are at 1e7 cycles.
- Polymer `yield_strength_MPa` is the tensile yield stress. Nylons are given both dry-as-moulded and conditioned (50%RH). Design with the conditioned values.
- Hardened tool steels (above about 58 HRC) leave yield and UTS blank and give an estimated compressive strength instead.

### am_materials.csv columns
`id, brand, product, process, base_polymer, density_kg_m3, tensile_strength_XY_MPa, tensile_strength_Z_MPa, tensile_modulus_XY_GPa, tensile_modulus_Z_GPa, elongation_XY_pct, elongation_Z_pct, flexural_strength_MPa, flexural_modulus_GPa, impact_XY_kJ_m2, impact_Z_kJ_m2, hardness_value, hardness_scale, hdt_0_45MPa_C, hdt_1_8MPa_C, tg_C, nozzle_temp_min_C, nozzle_temp_max_C, bed_temp_C, cost_tier, printability_notes, source_url, value_type`

Rules of thumb for printed parts:
- FDM Z strength is typically 40-70% of XY. Generic rows include Z estimates.
- SLA/MSLA parts are near-isotropic, so leave Z blank and use XY.
- Brand values from different vendors use different test methods, so compare within one brand only.

## Sources and licences
- Wikipedia articles (CC BY-SA) for alloy, polymer and ceramic summaries. Their values are cross-checked against the standard handbook values I remember (Shigley Tables A-21/A-24 for steel and cast iron Q&T data; ASTM A240/A564/A536/A48 minimums). Values are summarised, not bulk-copied.
- USDA Forest Products Laboratory, Wood Handbook FPL-GTR-190 (US government work, public domain) for the wood rows.
- Formlabs engineering materials page, fetched 2026-10-23. Values were transcribed for the resins marked `datasheet`.
- Prusament PETG TDS v1.1 (third-party-hosted copy) for `prusa_petg`.
- Bambu PAHT-CF TDS figures as reproduced by a retailer page (`bambu_paht_cf`).
- Engineering ToolBox friction table (summarised) for the friction pairs.
- Galvanic series and anodic index: MIL-STD-889 as summarised on Wikipedia.
- No files were downloaded and there is no `raw/` folder. MatWeb and paywalled ASM handbooks were not used.

## Gaps / not verified
- Most brand filament values (Prusament other than PETG, Polymaker, Bambu other than PAHT-CF, eSun, HP, EOS, Markforged, Stratasys, igus) were recalled from vendor TDS and are labelled `estimate`. Verify against the current vendor TDS before relying on them. Vendor sites (Polymaker, Bambu, eSun) blocked automated fetches. Z-direction tensile values are mostly missing for brand rows.
- Formlabs resin densities are estimates (about 1150 kg/m3). The Formlabs page gives flexural modulus, not tensile modulus, so tensile modulus is left blank.
- Many shear moduli for non-metals are blank. Metal G values are checked against E/(2(1+nu)) within 12%.
- Stainless rows marked `standard` give ASTM minimums, and typical values are 20-40% higher. Most other metal rows are typical values, not design allowables. For safety-critical work use MMPDS/ASTM minimums.
- Endurance limits marked "est" are 0.5×UTS rules of thumb with no surface, size or reliability factors applied.
- Bushing PV, P and V limits are mostly `estimate`, compiled from typical manufacturer catalogue figures (Oilite, GGB, igus, DuPont, Vespel). They vary by grade and by the vendor's test conditions.
- Friction coefficients vary widely with surface finish, contamination and load. Treat them as ±30%.
- Composites, woods and elastomers vary a lot between batches and suppliers. Use conservative knock-downs.
- `max_service_temp_C` is an approximate continuous-use guide, not a rated value.
