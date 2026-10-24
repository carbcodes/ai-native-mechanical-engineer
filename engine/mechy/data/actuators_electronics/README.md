# actuators_electronics

Lookup tables for motors, drivers, MCUs, sensors, power and wiring, for Mechy's agents. All CSVs have a header row, SI units in column names, one row per item, and `source_url` + `value_type` (datasheet | standard | handbook_typical | estimate). Validate with `python3 -I check.py`. It prints PASS/FAIL.

## The `verification` column (read this first)
- `fetched`: the number was checked against the cited page (manufacturer or retailer) when this dataset was compiled (2026-10).
- `recalled`: the number comes from the compiler's knowledge of the public datasheet and was **not** re-checked against the source. Treat it as a good first guess and confirm it before a design depends on it. A `recalled` row marked `estimate` is less certain than one marked `datasheet`.
- The wire tables have no verification column. Their values are standard or handbook tables, and their geometry is computed.

## Files
| file | rows | contents / key columns |
|---|---|---|
| stepper_motors.csv | 38 | NEMA 6–34 hybrid steppers (Pololu, StepperOnline, LDO, Moons', Oriental). Columns: holding_torque_Nm, rated_current_A, phase_resistance_ohm, phase_inductance_mH, rotor_inertia_gcm2, mass_kg, body_length_mm, shaft_diameter_mm. Pololu R = rated V / I. |
| stepper_torque_speed_estimates.csv | 216 | Modelled pull-out torque versus speed at 12, 24 and 48 V for 9 motors. The model is in the `method` column. Every row is `estimate`, not a published curve. |
| closed_loop_steppers.csv | 9 | MKS SERVO42D/57D, BTT S42C, JMC IHSS integrated motors, StepperOnline encoder kits, Moons' TSM. |
| bldc_gimbal_motors.csv | 20 | Gimbal and outrunner motors: kv_rpm_per_V, kt_Nm_per_A (≈8.27/Kv), resistance_ohm (+ basis), pole_config, mass_kg, peak_current_A. |
| qdd_actuators.csv | 10 | CubeMars AK60-6/70-10/80-9/10-9, the MIT Mini Cheetah actuator, mjbots qdd100 and mj5208, Unitree, SteadyWin. Columns: gear ratio, rated and peak torque, Kv, Kt, currents, mass. |
| servos.csv | 28 | One row per servo per voltage. SG90, MG90S, MG996R, DS3218, Dynamixel XL330/XL430/XM430/XH430/XM540, Feetech STS3215/SCS0009, Hiwonder LX-16A/HTD-45H. Columns: stall_torque_Nm, no_load_speed_rpm, stall_current_A, interface. |
| brushed_gearmotors.csv | 97 | Pololu micro metal (N20-size), 25D and 37D gearmotors at every listed ratio, plus 3 generic N20 rows. Stall torque is Pololu's extrapolation. |
| linear_actuators.csv | 12 | Actuonix PQ12/L12/L16, Progressive Automations PA-14, a generic 1000 N actuator, and a stepper with a lead screw. |
| solenoids.csv | 6 | Adafruit lock and push-pull solenoids, JF-0530B/0826B, and a sizing rule. |
| motor_drivers.csv | 26 | A4988, DRV8825, TMC2208/2209/2226/2130/2240/5160, DM542T, TB6600, ODrive S1/Pro/v3.6, moteus r4.11/n1/c1, SimpleFOC Mini/Shield, B-G431B-ESC1, and brushed H-bridges. Columns: supply_min/max_V, abs_max_V, continuous/peak current, interface. |
| mcu_boards.csv | 17 | ESP32 / S3 / C3 / C6, Pico / Pico W / Pico 2, STM32 boards, Teensy 4.0/4.1, Arduino Uno R3/R4, Nano and Mega. Columns: clock, RAM, flash, ADC, PWM, CAN, logic voltage, pin current. |
| encoders.csv | 10 | AS5600, AS5048A, AS5047P, MT6701, MA730, TLE5012B, AMT103, Omron E6B2, LPD3806, Pololu Hall encoder. |
| imus.csv | 7 | MPU-6050, ICM-20948, ICM-42688-P, BMI088, LSM6DSOX, BNO055, BNO085. |
| sensors_other.csv | 22 | Load-cell ADCs (HX711, ADS1220, ADS1115), load cells, current sensors (INA219/226/260, ACS712/723), ToF, lidar and ultrasonic sensors, and endstops. `range_unit` gives the unit of `range_min`/`range_max`. |
| power_supplies.csv | 13 | Mean Well LRS / RSP / UHP / HDR / GST models, plus the USB-PD SPR and EPR limits. |
| dc_dc_converters.csv | 10 | LM2596, MP1584, XL4015 and XL6009 modules, Pololu D24V22F5/D36V28F5/S13V10F5, and the AMS1117, LM7805 and AP2112 regulators. Columns: rated versus practical current. |
| battery_cells.csv | 12 | 18650 and 21700 Li-ion cells (Samsung, LG, Murata, Molicel), A123 LiFePO4, Eneloop, and a generic LiPo cell. |
| wire_ampacity_awg.csv | 14 | AWG 30–4: diameter, area, copper resistance at 20 °C, chassis-wiring and power-transmission ampacity, and NEC 310.16 60/75/90 °C ampacity. |
| wire_ampacity_metric.csv | 10 | 0.25–16 mm²: resistance, flexible-cord ampacity, and fixed-wiring PVC (method C) ampacity. |
| connectors.csv | 22 | JST SH/GH/PH/XH/VH, Dupont, Molex KK / Micro-Fit / Mini-Fit, Phoenix, WAGO 221, XT30/60/90, MR30, Powerpole, barrel jack, USB-C, M8/M12, GX16. Columns: current per contact, voltage rating, AWG range. |

## Sources and licences
- **Manufacturer pages:** Pololu, ROBOTIS e-Manual, mjbots, ODrive docs, CubeMars, Oriental Motor catalog, Mean Well, TI, ST, ADI/Trinamic, Espressif, Raspberry Pi, PJRC, Arduino, ams OSRAM, JST, Molex and Amass. Only individual factual specs were taken; no pages were bulk-copied.
- **SimpleFOC docs:** the BLDC motor table (MIT licence).
- **Retailer listings, used where manufacturer pages were blocked or had no specs:** BIQU (LDO and Moons'), RobotShop (CubeMars), eBay, Tindie and maritex (StepperOnline). StepperOnline's own site returned HTTP 403.
- **Wire tables:** the PowerStream wire table, NFPA 70 (NEC) Table 310.16, IEC 60364-5-52 and BS 7671 Appendix 4, summarised as typical values. AWG geometry is computed from the ASTM B258 formula, and resistance uses ρ = 1.724e-8 Ω·m.
- Nothing was downloaded into `raw/`.

## Gaps / not verified
- **StepperOnline, LDO, JMC and Moons' TSM:** many values are `recalled`. Rotor inertia and mass are often missing or recalled. 17HS19-2004S1 resistance is 1.4 Ω on the listing and 1.6 Ω in the PDF. No manufacturer torque-speed curves were captured. The curve file is a model and should be checked against a real curve.
- **NEMA 8/11 StepperOnline rows** and the 34HS31/34HS59 rows are estimates.
- **CubeMars sources conflict:**
  - AK70-10 mass: 521 g or 621 g.
  - AK10-9 mass: 820 g or 960 g. Its Kt is 0.095 or 0.114.
  - AK60-6 rated current: 3.8 A or 4.5 A.
  - Whether Kt is motor-side or output-side is not always stated.
  - AK80-9 is `recalled` only.
- **Unitree, SteadyWin, qdd100 and the Mini Cheetah mass** are recalled estimates.
- **T-Motor MN5212:** resistance and mass come from a garbled reseller page. The U8 Lite and MN4006 rows are recalled. Kv-derived Kt ignores the phase versus line definition (±15 %).
- **Hobby servos (MG996R, DS3218, Feetech, Hiwonder):** values are vendor claims. Clones vary widely.
- **Motor drivers:** all chip ratings except ODrive S1 and moteus r4.11 are recalled. Check the abs-max values of TMC2208/2209 and the ODrive Pro limits before high-voltage use.
- **Battery cells:** continuous ratings mix manufacturer and independent-test figures, as noted per row.
- **Connectors:** ratings are per contact at 20–30 °C and must be derated for circuit count and temperature.
- **Wire ampacity:** values assume copper with PVC or similar insulation. Silicone (200 °C) hobby wire can carry more and is not tabulated.
- **Not covered:** manufacturer torque-speed curves for steppers and gearmotors, Hall/optical endstop timing, Feetech SCS15/STS3032, and Dynamixel P/PRO series.
