# Electronics for Mechatronics: Reference for Mechy Agents

Scope: the electrical side of small to medium mechatronic builds (desktop robot arms, gantries, rovers,
grippers). Typical system: 12 to 48 V DC bus, stepper or BLDC/servo drivers, an MCU, a few sensors,
cables that run through moving joints. It is not a mains-wiring guide. Anything touching mains goes to
a certified, enclosed power supply (see Section 20).

Conventions:
- SI units. V = volts, A = amps, Ω = ohms, W = watts, F = farads, H = henries, s = seconds.
- "Typical" means a common design value, not a guarantee. "Estimate" means a rule of thumb. Always
  check the datasheet of the exact part.
- Source tags in [brackets] refer to "Canonical references" at the end.

---

## 0. Quick checklist (run this on every design)

1. Power budget: sum each load's worst-case current. Size the supply to 1.25 to 1.5x the realistic
   peak, not the sum of every motor's nameplate current (Section 3).
2. Choose bus voltage: 12 V for small/low-speed, 24 V default for steppers, 48 V for speed or power
   (Section 4).
3. A fuse sits right at the source on every supply rail. Rate the wire for at least the fuse current (Section 9).
4. Reverse-polarity protection on any connector a human plugs in (Section 9).
5. Every inductive load (relay, solenoid, brushed motor, brake) has a flyback path (Section 10).
6. Motor drivers have bulk capacitance near their supply pins, plus a plan for regen voltage (Section 11).
7. Logic levels match. No 5 V signals into 3.3 V-only pins (Section 13).
8. Buses fit their distance: I2C stays on the board or within about 1 m. Anything that leaves the box
   uses differential signalling (CAN, RS485) (Section 15).
9. Star ground or a solid ground plane. Motor return currents do not flow through sensor grounds (Section 17).
10. Cables through moving joints are flex-rated, strain-relieved, and bent no tighter than their
    minimum bend radius (Section 18).
11. A hardware e-stop cuts motor power directly, not through firmware (Section 20).
12. LiPo/Li-ion: a BMS or protected pack, a fuse, a charger matched to the chemistry, and never
    charged unattended (Section 6).

---

## 1. Fundamentals

### 1.1 Ohm's law and power
- V = I·R. V in volts, I in amps, R in ohms.
- P = V·I = I²·R = V²/R. P in watts.
- Energy: E = P·t (joules = W·s). Battery energy in Wh = V_nominal × Ah.

Mini-example: a 0.1 Ω shunt carrying 5 A drops V = 0.5 V and dissipates P = 5²×0.1 = 2.5 W. That
needs a 5 W resistor. A 10 mΩ shunt drops 50 mV and dissipates 0.25 W, which is why current shunts are
milliohms.

### 1.2 Kirchhoff's laws
- KCL (current law): currents into a node sum to zero. Whatever flows in to a driver's V+ pin flows out
  its GND pin. The ground wire carries the full load current, so size it the same as V+.
- KVL (voltage law): voltages around any closed loop sum to zero. Wire drops count. If a 24 V supply
  feeds a 3 A load through 2 m of wire (out and back = 4 m) at 0.0133 Ω/m (16 AWG), the loss is
  3 × 4 × 0.0133 ≈ 0.16 V. Negligible. With 26 AWG (0.134 Ω/m) it is ≈ 1.6 V. That is a problem.

### 1.3 Series and parallel
- Series resistors add: R = R1 + R2.
- Parallel: 1/R = 1/R1 + 1/R2. For two resistors, R = R1·R2/(R1+R2).
- Capacitors are the opposite: parallel C adds, series C combines like parallel resistors.

### 1.4 Voltage divider
- Vout = Vin · R2/(R1+R2), with R2 being the bottom resistor (to ground).
- Use it for: sensing a battery or bus voltage with an ADC, or setting a regulator's feedback.
- Do not use it to power anything. The output sags as soon as current is drawn. Use a regulator.
- Load rule (estimate): the divider current should be at least 10x the load current at its tap. For
  an MCU ADC input, keep the source impedance below the ADC's limit. STM32 and RP2040 like
  about 10 kΩ or less unless you sample slowly. Otherwise add 10 to 100 nF from the tap to ground.

Mini-example (battery monitor, 4S LiPo max 16.8 V into a 3.3 V ADC): pick R1 = 100 kΩ, R2 = 22 kΩ.
Vout = 16.8 × 22/122 = 3.03 V. That leaves headroom. The standing drain is 16.8/122k ≈ 0.14 mA. Add
100 nF across R2 to steady the reading.

### 1.5 RC and RL circuits
- RC time constant τ = R·C (s). A capacitor charges to 63% in 1τ, 95% in 3τ, and 99% in 5τ.
- RC low-pass cutoff: f_c = 1/(2π·R·C).
  Example: 10 kΩ and 100 nF give f_c ≈ 159 Hz. That is a good debounce or anti-alias filter on a
  slow sensor line.
- RL time constant τ = L/R. Current in an inductor cannot change instantly. Interrupt it and the
  voltage spikes, V = L·di/dt. This is the root of flyback (Section 10).
- Motor windings are RL loads. A stepper coil with L = 3 mH and R = 1.5 Ω has τ = 2 ms. At high step
  rates the current cannot rise in time, so torque falls off. A higher bus voltage forces di/dt
  = V/L faster. This is the main reason to use 24 to 48 V for steppers (Section 4).

### 1.6 Capacitor basics for power rails
- Ceramic (MLCC, X7R/X5R): low ESR, for high-frequency decoupling. Use 100 nF at every IC power pin,
  as close as possible. Real capacitance drops a lot under DC bias. A 10 µF 0805 at its rated
  voltage may deliver only 3 to 5 µF (typical behaviour, check the manufacturer's DC-bias curve).
- Electrolytic (aluminium): cheap bulk capacitance. Use 100 to 1000 µF at motor driver inputs. Rate the
  voltage at least 1.5x the bus, and higher if regen is possible. Ripple current rating matters.
- Rule of thumb: derate ceramic voltage by 2x and electrolytic by 1.25 to 1.5x.

---

## 2. Power: what everything consumes

| Load | Typical draw (estimate) | Notes |
|---|---|---|
| NEMA17 stepper, 1.5 to 2 A/phase rating | 0.5 to 1.5 A from a 24 V supply | A chopper driver draws far less supply current than phase current at low speed (it acts like a buck converter) |
| NEMA23 stepper, 3 to 4 A/phase | 1 to 3 A from 24 to 48 V | |
| Hobby servo (SG90) | 0.1 to 0.25 A running, about 0.7 A stall at 5 V | Stall current is what browns out an MCU |
| Hobby servo (MG996R) | 0.5 to 1 A running, 2.5 A stall at 6 V | Use a dedicated 5 to 6 V BEC per few servos |
| Small brushed DC gearmotor | 0.1 to 0.5 A running, 1 to 3 A stall | Stall is 5 to 10x running current |
| BLDC gimbal / robot actuator | 1 to 10 A or more peak | Check the driver's limit |
| ESP32 (Wi-Fi active) | 80 to 260 mA, peaks around 400 to 500 mA | Wi-Fi TX bursts need bulk capacitance near the module |
| RP2040 / STM32 board | 20 to 100 mA | |
| Arduino Uno | about 50 mA | |
| Raspberry Pi 4/5 | 0.6 to 3 A at 5 V (Pi 5 PSU spec is 5 A) | Needs a solid 5 V buck |
| Fan 40 mm, 12/24 V | 0.05 to 0.15 A | |

Sources: manufacturer datasheets (Espressif ESP32, Raspberry Pi docs, TowerPro); stepper supply
current behaviour from TI and Trinamic app notes [TI-SLVA, ADI-TMC].

Key insight: a stepper driver is a switching current regulator. Supply current ≈ (motor electrical
power + losses)/V_bus, not the phase current. For two coils at I_phase through R_coil, the low-speed
floor is P ≈ 2·I²·R. Example: a NEMA17 at 1.5 A and 1.8 Ω gives 2 × 2.25 × 1.8 ≈ 8 W. From 24 V
that is about 0.35 A, plus losses. At speed, mechanical power adds.

---

## 3. Sizing a power supply

### 3.1 Procedure
1. List every load with continuous and peak current at its own voltage.
2. Convert to supply-side power: P_in = P_load/η. Use η ≈ 0.85 to 0.9 for a buck converter (estimate)
   and η = V_out/V_in for a linear regulator.
3. Sum the realistic simultaneous continuous power. Steppers on a gantry rarely all peak together, but
   assume they do if a homing or e-stop recovery moves everything at once.
4. PSU rating ≥ 1.25 to 1.5 × that sum (estimate). Run supplies at 50 to 80% of rating for life and
   thermal margin.
5. Check peak and inrush. Motors starting or reversing can exceed a PSU's overcurrent trip.
   Constant-current (CC) or hiccup-mode protection makes the PSU cycle on and off. Bulk caps on the
   bus cover short peaks.

Mini-example (3-axis arm, 24 V):
- 3 × NEMA17 at about 15 W each worst case = 45 W
- ESP32 plus sensors at 5 V, 0.5 A = 2.5 W, about 3 W input through a buck
- Gripper servo at 6 V, 2 A stall = 12 W, about 14 W input
- Total ≈ 62 W. × 1.5 ≈ 93 W. Pick a 24 V 100 to 150 W supply (4 to 6 A).

### 3.2 Supply types
| Type | Use when | Watch out for |
|---|---|---|
| Enclosed SMPS (Mean Well LRS/RSP style) | Bench or fixed machines, 12/24/48 V | Mains terminals are exposed. Cover them, earth the chassis (Section 20) |
| Laptop-style brick (USB-C PD, barrel jack) | Small portable builds, under about 100 W | Barrel jacks are rated only about 2 to 5 A. USB-C PD needs a trigger IC for 9/12/15/20 V |
| Bench supply | Development, current limiting while testing | Set the current limit low on first power-up |
| Battery | Mobile robots | See Section 6 |

---

## 4. Choosing bus voltage: 12, 24 or 48 V

| Bus | Use when | Pros | Cons |
|---|---|---|---|
| 12 V | Small, slow, low-power (under about 60 W). Lots of off-the-shelf 12 V parts (fans, LED strips, pumps) | Cheap parts, safe | High current for a given power, so thicker wire. Steppers lose torque at speed (Section 1.5) |
| 24 V | Default for desktop CNC, 3D printers, arms with NEMA17/23 | Good stepper speed, half the current of 12 V, industrial-standard sensors and relays (24 V PLC world) | Some 12 V parts need a buck |
| 48 V | NEMA23/34 at speed, BLDC robot actuators, more than about 300 W | Quarter the current of 12 V, best high-speed torque | Close to the 60 V DC SELV limit (Section 20). Regen spikes can exceed driver ratings. Fewer cheap drivers (TMC2209 max is 29 V) |

Rules:
- Check the driver's absolute-max voltage first. TMC2209: 4.75 to 29 V. TMC5160: up to 60 V (36 V
  for some variants). A4988: 8 to 35 V. DRV8825: 8.2 to 45 V. Leave at least 20% headroom for regen
  and ringing (Trinamic and TI datasheets).
- Stepper top speed scales roughly with V_bus/L. Doubling voltage roughly doubles the speed at which
  torque collapses (estimate, depends on driver and current).
- SELV (Safety Extra-Low Voltage) is ≤ 60 V DC ripple-free in dry conditions under IEC 61140 and
  IEC 62368-1 limits. Staying at 48 V keeps you comfortably below it.

---

## 5. Converters and regulators

### 5.1 Decision table
| Need | Use | Typical η |
|---|---|---|
| Step down, small current (under 100 mA), small drop (under 2 V), low noise (analog, sensors) | LDO linear regulator (AP2112, MCP1700, AMS1117) | V_out/V_in |
| Step down, anything else | Buck (synchronous buck module, MP1584, LM2596 (old, about 80%), TPS54xxx) | 85 to 95% |
| Step up | Boost (MT3608, TPS61xxx) | 80 to 93% |
| Output between a varying input (battery 3.0 to 4.2 V into 3.3 V) | Buck-boost (TPS63020) | 85 to 95% |
| Isolated | Isolated DC-DC module (B0505S, RECOM) | 70 to 85% |

### 5.2 Linear regulator heat (common mistake)
P_loss = (V_in − V_out) × I.
Example: 12 V into a 5 V LDO at 0.5 A gives 3.5 W. A SOT-223 package (θJA about 60 to 90 °C/W)
would run roughly 200 °C over ambient. It will shut down or fail. Use a buck.
Rule (estimate): a linear regulator is fine when (V_in − V_out) × I < 0.5 W for SOT-23/SOT-223 without
heatsinking.

### 5.3 Buck/boost practicalities
- Input cap close to the IC. Keep the switching loop (input cap, switch, diode/low FET) tiny (Section 19).
- Ratings on cheap modules are optimistic. A "3 A" LM2596 module manages about 1.5 to 2 A continuous
  without a heatsink (community-tested estimate). Derate by about 50%.
- Boost converters cannot limit output current at short circuit. Input flows straight through the
  inductor and diode. Fuse them.
- Switching noise: 100 kHz to 2 MHz plus harmonics. Keep analog sensors on an LDO after the buck, or
  add an LC filter (ferrite bead and 10 µF).

### 5.4 Inrush current
- On power-up, discharged bulk capacitors look like a short circuit. I_peak ≈ V/(R_source + ESR +
  wire). With a battery and 1000 µF that can be hundreds of amps for microseconds. That causes the
  spark when an XT60 mates, pitting the contacts.
- Fixes: an NTC inrush thermistor (mains side), a precharge resistor that a switch or relay then bypasses,
  an anti-spark connector (XT90-S or AS150 have a built-in resistor), or a hot-swap/soft-start
  controller (TI TPS2490 family, eFuse ICs like TPS2595).
- For battery robots above about 6S with more than about 500 µF, use an anti-spark connector or a
  precharge circuit (common RC/drone practice).

---

## 6. Batteries (Li-ion, LiPo, LiFePO4)

### 6.1 Cell numbers (typical, from manufacturer datasheets and Battery University [BU])
| Chemistry | Nominal | Full charge | Min discharge (cutoff) | Storage | Notes |
|---|---|---|---|---|---|
| Li-ion (NMC/NCA, 18650/21700) | 3.6 to 3.7 V | 4.20 V | 2.5 to 3.0 V (use 3.0 V for life) | about 3.7 to 3.85 V (40 to 60%) | Cylindrical, robust can |
| LiPo (pouch) | 3.7 V | 4.20 V (4.35 V for LiHV) | 3.0 V (3.3 V under load for life) | 3.80 to 3.85 V | Highest C-rates, swells when abused |
| LiFePO4 | 3.2 V | 3.60 to 3.65 V | 2.5 V | about 3.3 V | Safest, long cycle life, flat curve (hard to gauge state of charge by voltage) |

Pack naming: "4S2P" means 4 cells in series (4 × 3.7 = 14.8 V nominal) and 2 in parallel (2 × the capacity).

### 6.2 C-rate
- C-rate = current/capacity. A 2200 mAh pack at 1 C = 2.2 A. At 25 C it is 55 A.
- Max continuous current = capacity (Ah) × C_continuous. Treat hobby LiPo C ratings as inflated. Plan
  on about 50 to 70% of the label for continuous use (community testing, estimate).
- 18650 cells: about 2 C (energy cells, 3000 to 3500 mAh) up to about 10 A or more (power cells like the
  Samsung 30Q at 15 A, Molicel P28A at 35 A). Use datasheet continuous ratings from independent testers
  (Mooch's tests) rather than wrapper labels.
- Charge rate: 0.5 to 1 C standard. Above 1 C only if the datasheet allows.
- Runtime estimate: t (h) ≈ Ah × 0.8/I_avg. The 0.8 accounts for not discharging to 0% and for
  voltage sag.

### 6.3 BMS (Battery Management System)
A BMS protects the pack. It is not optional for Li-ion packs built from bare cells.
Functions:
- Overvoltage per cell (about 4.25 to 4.30 V) and undervoltage per cell (about 2.5 to 3.0 V) cutoff
- Overcurrent and short-circuit cutoff (usually back-to-back MOSFETs on the negative side)
- Cell balancing (passive bleed resistors, typically 30 to 100 mA) so series cells stay matched
- Optional: temperature (NTC), state-of-charge estimation (fuel gauge ICs like BQ series, MAX17xxx)

Sizing: BMS continuous current ≥ peak continuous load × 1.2. Check whether its short-circuit trip
interrupts motor startup surges.
RC LiPo packs usually have no BMS. They rely on a balance charger and an ESC/controller low-voltage
cutoff. For a robot left unattended or used by others, use a pack with a BMS or add one.

Note: a "common-port" BMS charges and discharges through the same terminals. A "split-port" BMS uses
separate ones. With a split-port BMS the overcharge protection does not cover the discharge port, so
regen from motors can bypass it.

### 6.4 Safety rules
1. Charge with a charger set to the right chemistry and cell count. Use balance-charging for series
   LiPo packs.
2. Never charge unattended, and do it on or in a fire-resistant surface (LiPo bag, metal box).
3. Do not charge below 0 °C (lithium plating).
4. A swollen ("puffed") LiPo is retired. Do not puncture it, do not charge it.
5. Fuse the pack positive as close to the cells as possible.
6. Store at storage voltage. Never leave a pack deeply discharged for long.
7. Use a physical disconnect (anti-spark connector or switch) for transport.
8. Shipping lithium batteries is regulated (UN38.3, IATA). Consider this when specifying a product.

---

## 7. Wire gauge versus current

### 7.1 Reference table (copper)
Resistance and area are physical constants from the AWG definition (ASTM B258). The "chassis" column
is a free-air single-wire rating and the "power transmission" column is the very conservative
historical 700 circular-mil-per-amp rating. Both are widely republished (PowerStream, Engineering
Toolbox) [PS-AWG]. The "Practical design" column is the recommended value for agents. It assumes
bundled wire, inside an enclosure, at about 40 °C ambient, with a 105 °C PVC or 150 to 200 °C silicone
insulation. It is an estimate made by cross-checking the chassis data with EN 60204-1 values
(Section 7.2).

| AWG | Diameter (mm) | Area (mm²) | Resistance (mΩ/m, 20 °C) | Chassis, free air (A) | Power-transmission, conservative (A) | **Practical design, bundled (A, estimate)** | Typical use |
|---|---|---|---|---|---|---|---|
| 30 | 0.255 | 0.051 | 339 | 0.86 | 0.14 | 0.5 | Wire-wrap, sensor signals only |
| 28 | 0.321 | 0.081 | 213 | 1.4 | 0.23 | 0.8 to 1 | Ribbon cable, signal |
| 26 | 0.405 | 0.129 | 134 | 2.2 | 0.36 | 1 to 1.5 | Encoder, I2C, sensor, JST-SH/GH |
| 24 | 0.511 | 0.205 | 84.2 | 3.5 | 0.58 | 2 | Small steppers (under 1 A), JST-PH/XH |
| 22 | 0.644 | 0.326 | 52.9 | 7 | 0.92 | 3 | NEMA17 coils (up to 2 A), servos |
| 20 | 0.812 | 0.518 | 33.3 | 11 | 1.5 | 5 | NEMA23 coils, 24 V distribution to one driver |
| 18 | 1.024 | 0.823 | 20.9 | 16 | 2.3 | 7 to 8 | Small PSU outputs, NEMA23 at 4 A |
| 16 | 1.291 | 1.31 | 13.2 | 22 | 3.7 | 10 | Main 24 V bus for a small machine |
| 14 | 1.628 | 2.08 | 8.28 | 32 | 5.9 | 15 | Main bus, battery leads under about 15 A |
| 12 | 2.053 | 3.31 | 5.21 | 41 | 9.3 | 20 | Battery leads, XT60 |
| 10 | 2.588 | 5.26 | 3.28 | 55 | 15 | 30 | Large battery leads, XT90 |
| 8 | 3.264 | 8.37 | 2.06 | 73 | 24 | 40 to 50 | Rover main bus |

Notes:
- The chassis column is the upper bound for short, well-ventilated, single runs. Do not exceed it.
- Silicone-jacketed "RC" wire tolerates higher temperatures and so can carry somewhat more. RC sellers
  quote about 1.5 to 2x the "practical" column. That is only for short, cooled, intermittent use.
- Size also for voltage drop: keep it under about 3% on power runs and under 1% on sensor supply. ΔV
  = I × R_per_m × (2 × length).
- Fine-stranded wire (for example 0.08 mm strands) flexes better (Section 18). Solid core wire breaks
  when it moves. Use it only on breadboards.

### 7.2 Metric (IEC/EN 60204-1 style, PVC, 40 °C ambient, approximate)
EN 60204-1 (Safety of machinery, electrical equipment) Table 6 gives current-carrying capacities by
installation method. The values below are approximate for multi-core cable on a surface/wall (method
B2/C range). Treat them as estimates and check the standard for the method you actually use.

| mm² | ≈ AWG | Approx. capacity (A) | Notes |
|---|---|---|---|
| 0.14 | 26 | about 1 | Signal |
| 0.25 | 24 | about 2 to 3 | Signal, small power |
| 0.5 | 20 | about 5 to 7 | |
| 0.75 | 18 | about 7.5 to 9 | Lowest size EN 60204-1 allows for power circuits outside enclosures (0.75 mm² for multicore, check edition) |
| 1.0 | 17 | about 10 to 12 | |
| 1.5 | 16 | about 13 to 16 | Common machine power wiring |
| 2.5 | 14 | about 18 to 22 | |
| 4 | 12 | about 24 to 30 | |
| 6 | 10 | about 31 to 38 | |

Derating (estimate, from IEC 60364-5-52 style correction factors): about 0.8 for 3 to 4 loaded
circuits bundled together, about 0.7 for 6 or more, and about 0.87 at 50 °C ambient versus 30 °C.

### 7.3 Common mistakes
- Using ground wire thinner than V+. Ground carries the same current (KCL).
- Using the gauge on a stepper motor's own pigtail (often 26 AWG) as the extension's gauge for long
  runs. That is fine for 1 to 2 A over 1 m but not over 3 m.
- Dupont jumper wire (28 to 30 AWG) for motor power.

---

## 8. Connectors and crimping

### 8.1 Connector selection (ratings are manufacturer "per contact" values. Derate when all positions
carry current)
| Family | Pitch | Rated current per contact (manufacturer) | Use for | Notes |
|---|---|---|---|---|
| JST SH | 1.0 mm | 1 A | Qwiic/STEMMA QT I2C, small sensors | Fragile, 28 to 32 AWG |
| JST GH | 1.25 mm | 1 A | Pixhawk/drone peripherals, CAN, encoders | Has a latch, good vibration resistance |
| JST PH | 2.0 mm | 2 A | Small batteries (1S), sensors, fans | No positive latch, friction only |
| JST XH | 2.5 mm | 3 A | Stepper motors (common on 3D printers), LiPo balance leads | Friction lock. The most common hobby stepper connector |
| JST VH | 3.96 mm | 10 A | Power on appliance PCBs | |
| Molex Micro-Fit 3.0 | 3.0 mm | 5 to 8.5 A (depending on wire and position count) | PSU, driver power, PC-style | Positive latch, industry standard |
| Molex KK 254 / Dupont | 2.54 mm | about 2 to 3 A (KK), Dupont about 1 to 3 A | Header jumpers, debug | See pitfalls |
| Phoenix/screw terminal 5.0/5.08 mm | 5 mm | 10 to 16 A | Driver boards, PSU | Use ferrules on stranded wire |
| XT30 | — | about 15 A continuous, 30 A burst (AMASS marketing) | Batteries under about 15 A, 2 to 4S packs | Polarised |
| XT60 | — | about 30 A continuous, 60 A burst (AMASS) | Most robot batteries | Polarised, solder cup, 12 AWG |
| XT90 (-S anti-spark) | — | about 40 to 45 A continuous, 90 A burst | Large packs, 6S and above | -S version has a precharge resistor |
| Anderson Powerpole PP15/30/45 | — | 15/30/45 A | Modular power distribution, ham radio, field robots | Genderless, crimp, stackable |
| M8/M12 circular | — | 2 to 4 A (M8), up to 16 A (M12 power codes) | Industrial sensors, outdoor, IP67 | Pricier, robust |

Sources: JST, Molex, AMASS and Anderson datasheets [JST, MOLEX, AMASS].
XT connector "burst" numbers are marketing. Treat the continuous number as the limit and 50% of the
"name" (XT60 is about 30 A) as the design value.

### 8.2 Dupont (2.54 mm jumper) pitfalls
- Weak retention: they vibrate loose, especially on moving parts.
- Cheap crimps have high, variable contact resistance (tens to hundreds of mΩ). They cause intermittent
  faults that look like firmware bugs.
- No polarisation or keying. Plugged in one pin off, they will feed 12 V into a 3.3 V pin.
- Rule: Dupont is for prototyping and debug headers only. Production or moving parts need latching,
  keyed connectors (JST GH, Micro-Fit, JST XH with hot-glue only as a last resort).

### 8.3 Crimping rules
1. Use the tool designed for that terminal family. Pliers or generic "Dupont" crimpers deform JST and
   Molex terminals. Engineer PA-09 and IWISS SN-28B are common hobby choices. Molex/JST make official tools.
2. Two crimps per terminal: the conductor crimp (on bare strands) and the insulation crimp (on the jacket,
   for strain relief).
3. Strip length per the terminal datasheet (typically 1.5 to 3 mm for small terminals). No strands
   outside the barrel, insulation not inside the conductor barrel.
4. Pull test: a good small crimp holds well past what you can pull by hand. UL 486A-486B and IEC 60352-2
   define pull-force values by gauge (for example about 30 N or more for 26 AWG, estimate).
5. Do not solder and then crimp. Solder wicks, makes the wire stiff, and creates a fatigue break point
   at the crimp edge. Crimped joints are preferred in vibration and flex (NASA-STD-8739.4 workmanship
   standard).
6. Ferrules on stranded wire going into screw terminals. Bare tinned (soldered) wire in a screw terminal
   cold-flows and loosens over time.
7. Wire gauge must fall inside the terminal's rated range.

---

## 9. Fuses and reverse-polarity protection

### 9.1 Fusing rules
- The fuse protects the wire, not the load. Fuse rating ≤ the ampacity of the smallest wire it protects.
- Put it as close to the source (battery or PSU output) as possible. Any wire before the fuse is unprotected.
- Rating: about 1.25 to 1.5 × the normal maximum continuous current (estimate), and below the wire limit.
- Choose slow-blow (time-delay) for motor loads with inrush and fast-blow for electronics.
- The DC voltage rating must exceed the bus voltage. Automotive blade fuses (ATO/ATC, mini) are rated
  32 V DC. That suits 12 to 24 V, but not 48 V. Use 58 V or higher rated fuses (some ATO/MIDI) or
  specified DC fuses.
- PTC resettable fuses (polyfuses) are good for small branch protection (USB, sensor rails). They are slow,
  they have resistance, and they leak "hold" current. Not for battery mains.
- Fuse each branch to each driver separately, or fuse the main and use a driver with its own
  overcurrent protection.

Mini-example: a 24 V bus on 16 AWG (practical 10 A) feeding 4 A of load. Use a 5 to 7.5 A slow-blow
fuse. The 22 AWG branch to the 1 A servo board gets a 2 A fuse or a PTC.

### 9.2 Reverse-polarity protection
| Method | Loss | Use when |
|---|---|---|
| Series Schottky diode | 0.3 to 0.5 V × I (at 3 A that is about 1.2 W) | Under about 1 A, logic power |
| P-channel MOSFET in the high side (gate to GND through resistor, Zener to protect V_GS) | I² × R_DS(on) (at 5 A and 10 mΩ, 0.25 W) | Up to about 10 A, simple and cheap. Standard approach |
| N-channel MOSFET in the low side | Low | Fine but splits ground, which complicates shared grounds with other boards |
| Ideal-diode controller IC (LM74700, LTC4359) with N-FET | Very low | Higher current, also blocks back-feed |
| Diode across the input plus fuse ("crowbar") | None in normal operation | Cheap. Blows the fuse when reversed |
| Keyed, polarised connectors | None | Always. This prevents the mistake in the first place |

P-FET circuit notes: the FET's body diode points from drain to source. Mount it so the body diode
conducts in the correct polarity at startup. Add a 10 to 15 V Zener from gate to source when V_in
exceeds the FET's V_GS max (often ±20 V) [TI-SLVA139].

---

## 10. Flyback diodes (inductive kickback)

Breaking current in an inductor gives V = −L·di/dt. A relay coil switched by a transistor can spike to
hundreds of volts and kill the transistor or reset the MCU.

Rules:
- Put a diode across every DC inductive load switched by a transistor: relay coil, solenoid, small
  brushed motor, electromagnetic brake. Cathode to the positive supply, anode to the switching node.
- Diode choice: 1N4148 for small relay coils (under 100 mA), 1N4007 for slow loads, Schottky (SS34,
  1N5819) for PWM motors (fast recovery, low drop).
- A plain diode slows relay release (current decays slowly). For faster release, add a Zener or TVS in
  series with the diode. The kickback clamps at V_supply + V_Z and decays faster.
- H-bridges and motor-driver ICs already have body diodes or internal clamps. Do not add an external
  diode across a motor driven by an H-bridge, it shorts during reversal. Add capacitance on the supply
  and possibly a TVS instead.
- AC loads use an RC snubber or varistor, not a diode.

---

## 11. Back-EMF and regenerative protection

A spinning motor is a generator. Back-EMF V_bemf = k_e × ω (k_e in V·s/rad, ω in rad/s).
When a motor decelerates fast or is back-driven (arm falls under gravity, someone pushes an axis by hand),
the driver's body diodes rectify that energy back onto the supply bus.

Consequences:
- A bench PSU or SMPS cannot absorb current. The bus voltage rises. If it exceeds the driver's absolute
  maximum (for example 29 V for TMC2209 on a 24 V bus), the driver dies. This is a common cause of dead
  stepper drivers when someone spins an unpowered motor by hand: the motor charges the bus and can
  even power the electronics.
- Batteries absorb regen if their BMS allows charge current. A tripped BMS ends this.

Protection, in order of escalation:
1. Bulk capacitance on the bus: E = ½·C·(V_max² − V_nom²). 1000 µF from 24 to 29 V absorbs only
   about 0.13 J. That is enough for small steppers but not for a falling arm.
2. TVS diode across the bus (for example SMBJ/SMCJ with standoff above V_nom and clamp below the
   driver maximum. For a 24 V bus, SMCJ26A or SMCJ28A, clamp about 42 to 45 V. Check this is below
   the driver limit). TVS units clamp transients but cannot dissipate continuous regen.
3. Brake chopper / shunt regulator: a comparator switches a power resistor across the bus when it
   exceeds a threshold (for example V_nom + 10 to 15%). Standard on servo drives. Size the resistor for
   the energy of the worst-case stop.
4. Software: limit deceleration, avoid back-driving.
5. Ideal-diode on the PSU output stops regen from back-feeding the PSU (but then regen has nowhere to
   go. You still need 2 or 3).

Mini-example: 1 kg arm link with centre of mass at 0.3 m falls 90°. Energy ≈ m·g·h = 1 × 9.81 × 0.3
≈ 2.9 J. Capacitor-only absorption from 24 V to a 28 V limit needs C = 2E/(V_max² − V_nom²) = 5.8/
(784 − 576) ≈ 28 mF. That is impractical. You need a brake resistor or a mechanical brake/non-backdrivable
gearing (worm, high-ratio). Section on gravity compensation belongs to the controls agent.

---

## 12. MOSFET switching basics

### 12.1 Low-side N-channel switch (the default)
Load between V+ and drain, source to GND, MCU pin drives the gate through a 100 Ω (limits ringing)
with a 10 to 100 kΩ pull-down from gate to source (keeps the FET off at boot while the pin is floating).

### 12.2 Choosing the FET
1. V_DS(max) ≥ 1.5 to 2 × bus voltage (spikes).
2. Logic level: check R_DS(on) is specified at V_GS = 2.5 V (for 3.3 V MCUs) or 4.5 V (for 5 V). V_GS(th)
   is the voltage where it just starts conducting (about 250 µA). It is not "on". The classic mistake is
   IRF540/IRFZ44N driven from 3.3 V: they need about 10 V for full enhancement.
   Logic-level examples: IRLZ44N (5 V), AO3400 (SOT-23, about 2.5 V), IRLB8721, Si2302.
3. Conduction loss: P = I² × R_DS(on) (hot. R_DS(on) rises about 1.5x at 100 °C).
4. Switching loss at PWM: P_sw ≈ ½ × V × I × (t_rise + t_fall) × f_PWM. A GPIO (about 10 to 20 mA)
   charges a large gate slowly. Above about 20 kHz or 5 A, use a gate driver IC (TC4427, UCC27517)
   or a driver with built-in bridges.
5. Thermal: T_j = T_a + P × θ_JA. Keep T_j under about 100 to 125 °C.

Mini-example: 12 V, 4 A heater from an ESP32 (3.3 V). AO3400 has R_DS(on) about 50 mΩ at V_GS = 2.5 V:
P = 16 × 0.05 = 0.8 W in a SOT-23 (θ_JA ~ 100+ °C/W) is too hot. Use IRLB8721 (TO-220, about 12 mΩ at
4.5 V, still OK-ish at 3.3 V, check curves) → about 0.2 W. Fine with no heatsink.

### 12.3 High-side switching
P-channel FET with an NPN/N-FET level shifter to pull its gate down, or a dedicated high-side switch
(load switch ICs, smart high-side switches like the Infineon PROFET or TI TPS1H). Use when the load
must keep its ground (for example a sensor sharing ground with signals).

### 12.4 H-bridges and motor drivers
Do not build discrete H-bridges for a typical project. Use integrated drivers:
| Motor | Driver examples (typical) |
|---|---|
| Brushed DC under 2 A | DRV8833, TB6612FNG (1.2 A continuous) |
| Brushed DC 2 to 10 A | DRV8871 (3.6 A peak), VNH5019, BTS7960 modules (about 15 to 20 A real) |
| Stepper, quiet | TMC2209 (about 2 A RMS max, 1.2 to 1.5 A realistic without forced air), TMC2240, TMC5160 (with external FETs, high current) |
| Stepper, cheap | A4988 (about 1 A without heatsink), DRV8825 (about 1.5 A) |
| BLDC/FOC | DRV8302/8305 boards, SimpleFOC Mini, ODrive, MKS ESC, moteus |
| Hobby servo | Direct PWM from MCU, or PCA9685 I2C PWM board for many |

Avoid L298N for new designs: bipolar, about 2 to 4 V drop, so it wastes heat (ST datasheet).

---

## 13. Logic levels: 3.3 V vs 5 V

| Family | V_OH typ | V_IH min | 5 V tolerant inputs? |
|---|---|---|---|
| 5 V AVR (Uno, Nano, Mega) | about 4.7 V | about 3.0 V (0.6 × V_CC) | N/A |
| ESP32 | about 3.3 V | about 2.5 V (0.75 × VDD) | No. Absolute max 3.6 V |
| RP2040 | 3.3 V | about 2.0 V | No. 3.6 V max (RP2350 has some 5 V tolerant pins, check datasheet) |
| STM32 | 3.3 V | about 2.0 V (0.7 × V_DD on some) | Many pins marked "FT" are 5 V tolerant when configured as inputs, not when ADC/analog |

Key facts:
- 3.3 V out to 5 V CMOS (V_IH = 3.5 V for HC series at 5 V) can fail. 74HCT parts accept TTL levels
  (V_IH 2.0 V) and solve this cleanly.
- 5 V into 3.3 V is the dangerous direction. It may "work" for a while through the protection diodes
  and then kill the pin or the part.

Level-shifting options:
| Method | Speed | Direction | Use for |
|---|---|---|---|
| Resistor divider (for example 1 kΩ/2 kΩ) | Up to about 1 MHz (RC limited) | 5 V to 3.3 V only | UART RX, slow signals |
| BSS138 MOSFET shifter (Adafruit/SparkFun board) | Up to about 400 kHz to 2 MHz | Bidirectional | I2C |
| 74LVC1T45/TXB0108 | 10 to 100 MHz | Auto or fixed | SPI, fast signals (TXB is for push-pull. Not for I2C) |
| 74AHCT125 / 74HCT245 | Fast | 3.3 V to 5 V | WS2812 LEDs, 5 V step/dir inputs |
| Optocoupler (PC817, 6N137) | PC817: about 10 kHz. 6N137: about 10 Mbit/s | One way, isolated | Isolation from noisy or different-ground systems (Section 20) |

Note: I2C pull-ups go to the lower voltage on the low side and the higher voltage on the high side when
using a BSS138 shifter.

---

## 14. Microcontrollers: which one, when

| MCU | Core and clock | Strengths | Weaknesses | Pick when |
|---|---|---|---|---|
| Arduino Uno/Nano (ATmega328P) | 8-bit AVR, 16 MHz, 2 KB RAM | 5 V I/O, huge community, simple, robust | Slow, little RAM, no floating point hardware, 1 UART | Teaching, simple single-motor jobs, 5 V shield ecosystem |
| ESP32 (classic, S3, C3, C6) | Xtensa/RISC-V, up to 240 MHz, about 320 to 512 KB RAM | Wi-Fi + Bluetooth, dual core (classic/S3), cheap, MCPWM and PCNT (pulse counter for encoders) | ADC is nonlinear and noisy (calibrate or use external), boot-strapping pins (GPIO0, 2, 12, 15) have startup constraints, Wi-Fi current spikes, a few pins input-only (34 to 39 on classic) | Anything that needs wireless: web UI, telemetry, phone control. Has a CAN (TWAI) controller (needs transceiver) |
| RP2040 / RP2350 (Raspberry Pi Pico) | Dual Cortex-M0+ 133 MHz (RP2350: M33 150 MHz) | PIO state machines (custom protocols, precise step pulse generation, quadrature decoding), cheap, good docs, USB | No native CAN, no Wi-Fi (except Pico W), ADC is basic (12-bit with about 9 ENOB on RP2040) | Precise timing, many step/dir outputs, custom protocols, low cost |
| STM32 (F1/F4/G4/H7) | Cortex-M0 to M7, 48 to 550 MHz | Hardware timers with encoder mode, advanced motor-control PWM (dead-time, complementary), CAN/FD, good ADCs, industrial temperature range, long-term availability | Steeper learning curve (CubeMX/HAL), more setup | Motor control (FOC), CAN networks, real-time loops, products. G4 is designed for motor control |
| Teensy 4.x | Cortex-M7, 600 MHz | Very fast, Arduino-compatible, 3 CAN buses (one FD) | Pricier, supply/availability | Heavy compute (kinematics, filtering) in an Arduino environment |
| Raspberry Pi (SBC, Linux) | Cortex-A, GHz | Linux, camera, ROS 2, Python | Not real-time, slow boot, SD card corruption on power loss | High-level planning, vision, UI. Pair with an MCU for real-time I/O |

Decision rules:
1. Need wireless? ESP32.
2. Need CAN, FOC, or hard real-time motor loops? STM32 (G4/F4) or Teensy.
3. Need precise pulse timing on many channels and low cost? RP2040 with PIO.
4. Need to talk to 5 V shields directly, or teaching? Arduino Uno/Nano.
5. Need vision/ROS? Raspberry Pi or Jetson plus one of the above over UART/USB/CAN.
6. Real-time loops (motor current, step generation) never run on Linux SBCs without an MCU co-processor
   or a real-time patch.

---

## 15. Communication buses

### 15.1 Summary table (typical values)
| Bus | Wires | Topology | Typical speed | Practical distance | Noise immunity | Use for |
|---|---|---|---|---|---|---|
| UART (TTL) | TX, RX, GND | Point-to-point | 9600 to 1 Mbit/s (115200 common) | Under about 1 to 2 m at TTL level | Low (single-ended) | MCU to MCU in a box, GPS, debug, TMC2209 config (single-wire UART) |
| RS232 | TX, RX, GND (±3 to 15 V) | Point-to-point | Up to about 115 kbit/s | about 15 m (spec) | Medium | Legacy instruments |
| I2C | SDA, SCL, GND (+V) | Multi-drop, addressed, open-drain | 100 kHz (Standard), 400 kHz (Fast), 1 MHz (Fast-mode Plus) | On-board, under about 0.5 to 1 m. Bus capacitance ≤ 400 pF (spec) | Low | On-board sensors (IMU, AS5600, displays) |
| SPI | SCK, MOSI, MISO, CS per device, GND | Single master, chip-select per slave | 1 to 50 MHz | On-board, under about 0.3 m at high speed | Low to medium | Fast sensors (AS5048A, IMUs), displays, SD cards, TMC5160 |
| CAN (ISO 11898-2) | CANH, CANL, GND (twisted pair), 120 Ω at each end | Multi-drop bus, multi-master, prioritised arbitration | 125 kbit/s to 1 Mbit/s (CAN FD data up to 5 to 8 Mbit/s) | 1 Mbit/s: about 20 to 25 m. 500 kbit/s: about 100 m. 250 kbit/s: about 250 m. 125 kbit/s: about 500 m | High (differential, error handling, retransmission) | Motor controllers in an arm (each joint on the bus), vehicles, robots |
| RS485 (TIA-485) | A, B, (GND), twisted pair, 120 Ω termination | Multi-drop half duplex (32 unit loads standard, more with 1/8 UL transceivers) | Up to 10 Mbit/s short, about 100 kbit/s at 1200 m | Up to about 1200 m at low speed | High (differential) | Long cables, Modbus RTU, Dynamixel servos (RS485 versions), industrial sensors |
| USB | D+, D−, V, GND | Host-device | 12 Mbit/s (FS) to 480 Mbit/s (HS) | 5 m max for HS cable (USB 2.0 spec) | Medium | PC link, firmware updates |
| Ethernet | 2 or 4 twisted pairs | Star via switch | 10/100/1000 Mbit/s | 100 m (Cat5e/6) | High (magnetics isolation) | High-level networks, EtherCAT for industrial |

CAN distances: Schneider Electric and CiA tables give 1 Mbit/s at 20 to 25 m and 125 kbit/s at about
500 m. A rough rule is bit rate × length ≤ about 50 to 60 Mbit·m/s, driven by propagation delay of
about 5 ns/m [CIA, SE-CAN]. RS485 distance from TI's RS-485 design guide (SLLA272) [TI-485].

### 15.2 Rules and pitfalls
- I2C:
  - Pull-ups required on SDA and SCL. TI's SLVA689 gives the method: the minimum resistor is set by
    sink current (3 mA standard) and the maximum by rise time (1000 ns Standard, 300 ns Fast) and bus
    capacitance. Typical choices: 4.7 kΩ at 100 kHz, 2.2 kΩ at 400 kHz for 3.3 V and short buses
    (estimate, TI app note SLVA689) [TI-I2C].
  - Breakout boards often already have 10 kΩ pull-ups. Several in parallel reduce the total. Check.
  - Fixed-address parts: the AS5600 is fixed at 0x36. Two on one bus need an I2C mux (TCA9548A) or
    separate buses. The AS5600L variant has a programmable address.
  - Long I2C runs or through slip rings: use a differential extender (PCA9615, or LTC4331) or switch to
    SPI/CAN.
  - I2C lockup: a slave can hold SDA low after an interrupted transfer. Firmware should clock SCL 9 times
    to recover.
- SPI: each device needs its own CS. MISO must be tri-stated by non-selected devices (most are, some
  cheap SD modules are not). Keep it short. Use a series resistor (22 to 33 Ω) at the source for fast edges.
- UART: TX goes to RX (cross over). Share ground. Check logic levels.
- CAN:
  - Exactly two 120 Ω termination resistors, at the physical ends. Measure about 60 Ω between CANH
    and CANL with power off.
  - Stubs short: under about 0.3 m at 1 Mbit/s (CiA) [CIA].
  - Need a transceiver: 3.3 V devices use the SN65HVD230/TCAN334/TJA1051T/3 (3.3 V I/O variant).
  - All nodes need the same bit rate.
  - Twisted pair (about 120 Ω characteristic impedance), with a ground reference wire.
- RS485: two 120 Ω terminations at the ends, fail-safe biasing resistors (about 560 Ω to 1 kΩ pull-up
  on A and pull-down on B) so the bus idles in a defined state, and a direction (DE/RE) pin controlled
  by firmware for half duplex. Daisy-chain, do not star.
- Rule for robot arms: inside the controller box, I2C/SPI/UART. Between box and moving joints over
  about 0.5 m, CAN (or RS485). The cable passes through motors with PWM noise, and differential
  signalling with error checking survives it.

---

## 16. Sensors

### 16.1 Encoders
| Type | Resolution (typical) | Absolute? | Interface | Notes |
|---|---|---|---|---|
| Optical incremental (quadrature A/B, plus Z index) | 100 to 10000 CPR (×4 with quadrature decoding) | No, needs homing | Push-pull or differential (RS422) | Use hardware timer encoder mode (STM32), PCNT (ESP32), PIO (RP2040). Software interrupts miss counts at speed |
| Magnetic incremental (in motor encoders) | 12 to 64 CPR on motor shaft (× gear ratio) | No | Hall A/B | Common on gearmotors (N20 etc.) |
| AS5600 (ams/OSRAM) | 12-bit (4096 positions/rev, about 0.088°/LSB) | Yes, single turn | I2C (fixed 0x36, up to 1 MHz), analog, or PWM output | Cheap, easy. Accuracy is worse than resolution (about ±1° or worse with typical magnet alignment, estimate). Short I2C runs only. Datasheet I2C max SCL 1 MHz [AMS-5600] |
| AS5048A/B (ams) | 14-bit (16384/rev, about 0.022°/LSB) | Yes, single turn | AS5048A: SPI. AS5048B: I2C. Also PWM | Better resolution, SPI is faster and more robust [AMS-5048] |
| AS5047P, MT6701, TLE5012B | 12 to 15 bit plus ABI incremental | Yes | SPI/SSI/ABI | Common in FOC (SimpleFOC, ODrive) |
| Capacitive (AMT10x/AMT22) | Up to 4096 PPR, absolute versions | Some | Quadrature or SPI | Resistant to dust and magnets |
| Multi-turn absolute | — | Yes, multi-turn | SSI, BiSS, EnDat | Industrial, expensive. Alternatively single-turn plus counting in non-volatile memory |

Magnetic encoder rules:
1. Use a diametrically magnetised magnet (not axial), typically 6 mm diameter × 2.5 to 3 mm thick,
   neodymium N35 to N52. Check the datasheet for exact size.
2. Air gap: AS5600 about 0.5 to 3 mm. AS5048 about 0.5 to 2.5 mm (datasheet ranges, typical). Too close
   saturates, too far loses signal. Most chips report magnet strength status ("MD/ML/MH" on AS5600).
   Check it.
3. Centre the magnet on the axis within about 0.25 to 0.5 mm. Off-axis error causes a sinusoidal error
   once per rev. Calibrate with a lookup table if accuracy matters.
4. Keep steel and motor magnets (stepper rotors leak flux) away, or shield with a mu-metal or steel cup.
   Stepper stray field can disturb sensors at the back of the shaft. Leave space or test.
5. Mount the magnet on the output shaft to read joint position directly (absorbs belt and gear backlash
   in the measurement).

Gear ratio note: an encoder on the motor shaft multiplies resolution by the gear ratio but loses
absolute position across the ratio (one motor rev ≠ one joint rev). An encoder on the output gives
absolute joint angle but lower resolution per joint radian.

### 16.2 Limit switches and homing
- Mechanical microswitches (Omron SS/D2F style): cheap, repeatable to about 0.01 to 0.05 mm
  with slow approach (estimate). Wire normally-closed (NC) to ground: a broken wire reads as "triggered",
  which fails safe.
- Optical endstops (slotted interrupter): no contact wear, good repeatability, sensitive to ambient light
  and dust.
- Inductive proximity (12 to 24 V NPN/PNP, LJ12A3 etc.): industrial, sense metal targets, robust. Outputs
  are at supply voltage. Shift to 3.3 V with an optocoupler or divider.
- Hall effect with a small magnet: sealed, no contact.
- Sensorless homing (Trinamic StallGuard): uses motor back-EMF to detect a hard stop. No switch needed, but
  lower repeatability and needs tuning. Fine for 3D printers, less ideal for precision arms.
- Homing routine: fast approach, back off, slow second approach. Repeatability comes from the slow approach.
- Hardware RC filter (for example 10 kΩ/100 nF) plus software debounce. Motor cables induce glitches on
  switch wires running alongside.

### 16.3 Hall-effect sensors
- Digital switch/latch (A3144 (obsolete), DRV5032, SS441): on/off with a magnet. Open-drain outputs need a pull-up.
- Linear (DRV5053, SS49E): analog output proportional to field. For position over short travel.
- Unipolar (responds to one pole), bipolar (switches on one pole and off on the other), latch (holds state).
  BLDC commutation uses latches.

### 16.4 IMUs
| Part | Type | Interface | Notes (typical) |
|---|---|---|---|
| MPU-6050 | 6-axis accel+gyro | I2C | Old, end-of-life, very common clone parts. OK for learning |
| ICM-20948 | 9-axis (with magnetometer) | I2C/SPI | |
| BNO055 / BNO085 (Bosch/CEVA) | 9-axis with on-chip sensor fusion | I2C/UART/SPI | Outputs quaternions directly. Easiest for orientation. BNO055 has I2C clock-stretching issues on some MCUs (ESP32, RPi) |
| LSM6DSO / ICM-42688-P | 6-axis, low noise | SPI/I2C | Good for drones and balance robots |

Rules: mount close to the centre of rotation and rigidly, isolate from vibration (motors) with foam or
gel only if the datasheet's bandwidth allows. Magnetometers are ruined by nearby motors, steel, and
currents. Calibrate after installation. Gyros drift. Fuse with accel (complementary or Kalman filter).

### 16.5 Load cells and HX711
- Strain-gauge load cells (bar, S-type, button) form a Wheatstone bridge. Output is about 1 to 2 mV/V
  at full scale (typical). With 5 V excitation and 2 mV/V, full-scale output is 10 mV.
- HX711 (Avia Semiconductor): 24-bit ADC for bridges. Channel A gain 128 (±20 mV full scale at 5 V
  AVDD) or 64. Channel B gain 32. 10 or 80 samples/s (RATE pin). Supply 2.6 to 5.5 V. Not I2C. It uses
  a two-wire clock/data protocol. Bit-banged, timing matters (an interrupt during readout can corrupt
  data) [HX711].
  - Effective resolution is far below 24 bits. Expect about 16 to 18 noise-free bits at 10 SPS (estimate,
    community measurements).
  - 10 SPS rejects 50/60 Hz mains noise better. Use 80 SPS for faster force control loops, at more noise.
  - For faster force sensing (above about 100 Hz) use ADS1220/ADS1232/NAU7802 (I2C, up to 320 SPS) or
    an instrumentation amplifier into an MCU ADC.
- Rules: shield and twist the 4 or 6 wire load-cell cable. Short leads. Calibrate with known weights
  (2 point minimum). Let it warm up (drift). Avoid side loads and overload. Mechanically protect with a hard stop.

### 16.6 Current sensing
| Method | Range | Isolation | Notes |
|---|---|---|---|
| Low-side shunt plus op-amp | mA to tens of A | No | Simple, but lifts the load's ground. Breaks for loads sharing ground with signals |
| High-side shunt plus current-sense amp (INA180/INA240, INA219/INA226 I2C power monitors) | mA to tens of A | No | INA240 handles PWM common-mode transients (motor phases). INA219/226 give V, I, P over I2C |
| Hall-effect IC (ACS712 (old, noisy), ACS723/ACS724, ACS758 for high current) | ±5 A to 200 A | Yes (galvanic) | Easy, isolated, about 1 to 2% accuracy. ACS712 has low sensitivity at 3.3 V (185 mV/A at 5 V for 5 A version) |
| Driver-integrated (TMC, DRV83xx sense resistors) | | | Often already available. Read it before adding hardware |

Shunt sizing: choose R so the full-scale drop is 50 to 100 mV (estimate). Power = I² × R. Use a
4-terminal (Kelvin) layout: route sense traces from the shunt pads separately from the high-current path.

---

## 17. Grounding, EMI and noise

### 17.1 Grounding rules
1. One ground reference. Separate high-current (motor/power) returns from logic/sensor returns and join
   them at a single point, usually at the power supply negative or the driver's ground ("star ground").
2. On PCBs, use a solid ground plane and route high-current paths so their return current does not flow
   under sensitive analog circuits.
3. Every signal must have a ground return. A signal wire between two boards needs a ground wire alongside
   it (in the same cable, ideally twisted with it).
4. Avoid ground loops: two boards connected by both a signal ground and a separate power ground form a
   loop. Motor current in one path induces voltage. Fix with isolation (optocouplers, isolated CAN/RS485
   transceivers such as ISO1050/ADM2587E) or by making sure the ground conductors are low-impedance.
5. Protective earth (PE, from mains) connects to metal chassis for safety. It is not a signal ground.
   Tie DC ground to PE at one point only (or not at all, follow the PSU's design).
6. Cable shields: ground at one end (usually the controller end) for low-frequency noise. Ground at both
   ends (with 360° clamps) for high-frequency, if there is no ground-loop issue. Industrial VFD/servo
   cables: both ends, 360° clamp (EMC practice per drive manufacturer guidelines).

### 17.2 EMI and noise sources and fixes
| Source | Symptom | Fix |
|---|---|---|
| Stepper/BLDC PWM (20 to 50 kHz, fast edges) | Glitched encoder/limit/I2C signals, ADC noise | Twisted-pair motor phases, keep motor cables away from signal cables (at least 50 to 100 mm or cross at 90°), shielded motor cable, ferrite on motor leads |
| Brushed DC motor commutator sparks | MCU resets, radio noise | Three ceramic caps (100 nF from each terminal to the case and across terminals), soldered right on the motor |
| Relays, solenoids | Resets when switching | Flyback diode, separate supply rail, bulk cap |
| Buck converter | Analog noise, ADC ripple | LC/ferrite filter, LDO after buck, tight layout |
| Wi-Fi TX bursts (ESP32) | Brownouts, ADC spikes | 100 to 470 µF bulk cap near module, good 3.3 V regulator (≥ 500 mA) |
| Long sensor cables | Picked-up noise | Lower impedance (stronger pull-up, e.g. 1 to 4.7 kΩ), RC filter at the MCU, differential signalling, shielding |

General rules:
- Decouple every IC: 100 nF ceramic per power pin, plus 1 to 10 µF per board.
- Bulk caps (100 to 1000 µF) at motor driver inputs, close to the driver.
- Keep loop areas small: a power wire and its return run together (twisted), not on opposite sides of the frame.
- Schmitt-trigger inputs or hardware filtering for slow edge signals (switches).
- Unused MCU pins: set as outputs or enable pull-ups. Floating inputs pick up noise and draw current.
- MCU brownout detector enabled. The fail-safe for supply dips.

---

## 18. Cable management for moving joints

### 18.1 Cable selection
- Use stranded wire with fine strands (class 5 or 6 per IEC 60228, e.g. 0.05 to 0.1 mm strands)
  and a flex-rated jacket (PUR or TPE for continuous flex. Silicone is very flexible but tears easily
  and abrades).
- Continuous-flex ("chain-rated") cables like igus chainflex are rated for millions of cycles at their
  stated bend radius. igus specifies minimum bend radius as a bending factor × outer diameter. Factors
  of about 5 to 15 × d are common, with 7.5 × d typical for many continuous-flex data and servo
  cables (igus product data) [IGUS].
- Ordinary PVC hookup wire and ribbon cable fail by copper fatigue in about tens of thousands of cycles
  at tight bends (estimate). Fine for fixed routing only.
- Rule of thumb when no data: bend radius ≥ 10 × cable outer diameter for continuous flex, ≥ 5 × d
  for occasional flex (estimate).

### 18.2 Routing through rotating joints
| Rotation | Solution | Notes |
|---|---|---|
| Under about ±180° to ±270° | Service loop or clock-spring (spiral) around the axis, or a hollow shaft with slack | Most hobby arms. Put a hard or soft limit on rotation so cable never twists beyond its loop |
| Continuous rotation | Slip ring (capsule slip rings, 6 to 24 circuits) | Each circuit about 2 A typical for small capsule types (12 mm). Contact noise (tens of mΩ variation) corrupts I2C and analog. Use CAN or RS485 through slip rings and add redundancy (2 rings per power line) |
| Continuous rotation, high data | Wireless link (BLE, Wi-Fi) or contactless/optical slip rings | |
| Linear axes | Cable carrier (drag chain, e.g. igus E-chain) | Bend radius of chain ≥ cable minimum. Fill no more than about 60 to 80% of the chain cross-section. Do not tie cables together inside the chain |

Routing rules:
1. Clamp (strain relief) the cable on both sides of every moving section, so the flexing is in the
   designed region and not at a connector or solder joint.
2. The flex zone must not include connectors, crimps or solder joints.
3. Torsion (twisting) through a hollow axis: spread over the longest practical length. Torsion-rated
   cables (robot cables) exist.
4. Separate motor phase cables from encoder/signal cables, or use shielded cables. In a drag chain use
   separators between them.
5. Leave service length for maintenance. Label both ends.
6. Test: cycle the joint over its full range many times before trusting the cable (e.g. leave it
   running overnight).

---

## 19. PCB design basics

### 19.1 Trace width
- IPC-2221 (older) and IPC-2152 (current) give trace width vs current and temperature rise. Rule of thumb
  (estimate, 1 oz/35 µm copper, external layer, 10 °C rise): about 0.3 mm (12 mil) per 1 A, 1 mm (40
  mil) about 2 to 2.5 A, 2.5 mm (100 mil) about 4 to 5 A. Inner layers carry roughly half. Use an
  IPC-2152 calculator (e.g. Saturn PCB Toolkit, free) for real values.
- High current (> 5 A): wider pours, 2 oz copper, multiple layers stitched with vias, or bus bars/wires.
- Vias: a standard 0.3 mm drill via carries about 1 A (estimate). Use several vias in parallel for power.

### 19.2 Clearance (IPC-2221 spacing for uncoated external conductors, typical)
- Under 30 V: 0.1 mm minimum. Use ≥ 0.2 mm (most fab defaults are 0.127 to 0.15 mm).
- 48 V: about 0.6 mm creepage good practice.
- Mains (230 V): creepage ≥ 2.5 to 3 mm functional. For reinforced isolation (safety), 6 to 8 mm
  creepage and slots, following IEC 62368-1. Do not lay out mains circuits as a beginner. Buy a
  certified module.

### 19.3 Layout rules (checklist)
1. Two layers minimum, four layers if there is a switching converter plus sensitive analog or fast buses.
   Four-layer stack: signal / GND / power / signal.
2. Unbroken ground plane under fast signals. Do not split ground planes under traces.
3. Decoupling caps within 1 to 2 mm of power pins, with vias directly to ground.
4. Switching converter: keep the hot loop (input cap, switch, diode) as small as possible. Follow the
   datasheet reference layout exactly.
5. Separate the board into zones: power input → motor drivers → logic → analog/sensors, with the
   high-current path not passing through the logic area.
6. Thermal: use copper pours and thermal vias under power ICs (TMC drivers, regulators). Check
   datasheet layout.
7. Connectors at the board edge, all with silkscreen labels and pin 1 marking, polarised/keyed.
8. Test points on every rail and on key signals (UART, I2C, step/dir).
9. Mounting holes isolated or connected to ground on purpose, not by accident.
10. Run ERC (electrical rules check) and DRC (design rules check) against the fab's rules.
11. Add TVS/ESD protection (e.g. USBLC6, PESD) on connectors that people touch (USB, sensor headers).
12. Tools: KiCad (free, open source) is the default. JLCPCB/PCBWay for cheap fab and assembly.

### 19.4 First power-up procedure
1. Visual inspection, check for shorts with a multimeter (V+ to GND resistance).
2. Bench supply with current limit set low (e.g. 100 mA). No motors connected.
3. Check each rail voltage.
4. Flash firmware, test I/O, then connect motors one at a time with current limit raised gradually.

---

## 20. Safety

### 20.1 Voltage classes
- SELV (Safety Extra-Low Voltage): ≤ 60 V DC ripple-free (and ≤ 30 V AC RMS in some standards) in dry
  conditions, isolated from mains by safety isolation (IEC 61140, IEC 62368-1). 12/24/48 V systems from
  a certified PSU are SELV. Touchable, though batteries can still deliver fire-starting currents.
- Mains (100 to 240 V AC) is lethal. Rules:
  1. Use a certified, enclosed power supply (UL/CE/IEC 62368-1 marked). Avoid open-frame "LED" supplies
     with exposed terminals, or put them in an enclosure with terminal covers.
  2. Connect protective earth (PE) to the PSU's earth terminal and to any metal chassis the mains part
     could touch.
  3. IEC C14 inlet with integrated fuse and switch, strain-relieved cord. Never a bare cord through a hole.
  4. Fuse the mains side (inside the inlet module or PSU).
  5. Keep mains wiring physically separated from low-voltage wiring, ideally in its own compartment.
  6. Never work on mains circuits powered. Capacitors in PSUs can stay charged after unplugging.
  7. Relays switching mains: use rated relay modules with proper creepage, or solid-state relays, and
     enclosed terminals.

### 20.2 Emergency stop (e-stop)
- Function: an e-stop removes energy from hazardous motion. Standards: IEC 60204-1 (stop categories) and
  ISO 13850 (e-stop design). The e-stop must override all other functions and must not depend on
  software alone.
- Stop categories (IEC 60204-1):
  - Category 0: immediate removal of power to actuators (uncontrolled stop).
  - Category 1: controlled stop with power available, then removal of power once stopped.
  - Category 2: controlled stop, power remains (not allowed for e-stop).
- Implementation for a hobby/desk machine:
  1. A red mushroom head on yellow background, latching, normally-closed (NC) contacts, twist or pull
     to release.
  2. Wire the NC contact in series with motor power (directly for small currents, or via a contactor/relay
     coil for larger) so a broken wire = stopped (fail-safe).
  3. Also wire a second contact (or the relay aux contact) to an MCU input, so firmware knows and refuses
     to resume until reset.
  4. Releasing the e-stop must not restart motion. Require an explicit reset/start action.
  5. Logic power can stay on (so the MCU keeps encoder position and can report), but motor driver power is cut.
  6. Consider gravity: cutting power to a stepper arm makes it fall. Use brakes, non-backdrivable gearing,
     or Category 1 stop.
- For products, use a safety relay (e.g. PILZ PNOZ, or similar) and assess per ISO 13849-1. Hobby
  builds: still use a hardware NC chain.
- Driver "enable" pins are not an e-stop alone (firmware or a stuck driver can fail). The hardware
  power cut is the primary path.

### 20.3 Other safety items
- Batteries: Section 6.4.
- Thermal: drivers and regulators can exceed 80 to 100 °C. Keep away from PLA (softens about 55 to
  60 °C). Mount on aluminium or with airflow. Use PETG/ABS/ASA for electronics enclosures near heat.
- Fire: fuses on every source. No plastic enclosure in contact with hot parts. Check for flame
  ratings (UL94 V-0) on enclosures for products.
- Pinch points: the mechanical design matters as much as electrical. Limit speed and force near people.
  ISO/TS 15066 covers collaborative robot force limits.
- Isolation for user-touchable I/O: if a port connects to a PC or an external system with its own ground,
  consider isolated USB (ADuM3160) or optocouplers.

---

## 21. Worked mini-example: electrical design of a 3-DOF desktop arm

Requirements: 3 × NEMA17 (1.5 A phase), 1 servo gripper (MG996R), AS5600 on each joint output, ESP32
for Wi-Fi control, desk use, mains powered.

1. Bus: 24 V (TMC2209 drivers, max 29 V). PSU: 24 V 150 W enclosed Mean Well (estimate from Section 3:
   about 62 W needed, ×1.5 → about 95 W, choose 150 W for headroom).
2. Mains: IEC C14 fused inlet, PE to PSU earth and to metal base plate. Terminal cover on PSU.
3. Distribution: 16 AWG from PSU to a fuse block. 5 A slow-blow for the driver rail, 3 A for the
   buck converters. 20 to 22 AWG to each driver.
4. Bulk: 470 µF/50 V electrolytic at each driver input plus 100 nF ceramic. A 28 V TVS (SMCJ28A) across
   the bus near the drivers. Note: TMC2209 absolute maximum 29 V, so the TVS clamp (about 45 V) is too
   high to fully protect. Mitigation: limit deceleration in firmware and add a simple brake chopper if
   the arm can back-drive, or run a 12 V bus or use TMC2240 (36 V). (Flag for controls/cad agent.)
5. Logic: 24 V → 5 V buck (3 A) for servo and ESP32 dev board. A separate 6 V buck (3 A or more) for
   the MG996R so its stall current does not brown out the ESP32.
6. Logic levels: TMC2209 accepts 3.3 V logic. ESP32 step/dir/enable directly.
7. Encoders: three AS5600s all at 0x36, so put them on a TCA9548A I2C mux, or (better) read them through
   their analog/PWM outputs, or swap for AS5048A on SPI. Cable runs through joints are about 0.3 to 0.6 m:
   I2C at 100 kHz with 2.2 kΩ pull-ups is marginal. Consider SPI with short leads or a small MCU per
   joint over CAN for a scaled-up version.
8. Homing: microswitch per joint, NC to ground, 10 kΩ/100 nF RC filter.
9. Cables: 22 AWG flex-rated 4-core (shielded) for steppers, separate 26 AWG 4-core for sensors, both
   clamped either side of each joint, ≥ 10 × d bend radius, service loop with ±170° joint limits.
10. E-stop: NC mushroom switch in series with the 24 V driver rail through a relay or contactor rated
    10 A DC, aux contact to ESP32 input. Logic stays powered.
11. Connectors: JST-XH for steppers on the board, JST-GH for sensors, Micro-Fit for 24 V input.

---

## 22. Common mistakes (things agents should flag)

1. Feeding 5 V signals into ESP32/RP2040 pins.
2. MOSFETs that are not logic-level driven from 3.3 V (IRF540N, IRFZ44N).
3. Linear regulators dropping large voltages at significant current.
4. No flyback diodes on relays, solenoids, or brakes.
5. Powering servos from the MCU board's 5 V pin.
6. Motor drivers with no bulk capacitor, or the bulk cap 30 cm away on long wires.
7. Bus voltage too close to driver absolute maximum, ignoring regen.
8. I2C through long cables, slip rings, or alongside motor cables.
9. Two devices with the same fixed I2C address on one bus (e.g. two AS5600).
10. CAN with zero, one, or three termination resistors.
11. Solid-core or plain PVC wire through moving joints.
12. Connectors or solder joints in the flex zone.
13. No fuse, or a fuse larger than the wire's capacity.
14. Ground wire thinner than the supply wire. Signal cables without ground returns.
15. Automotive 32 V fuses on a 48 V bus.
16. LiPo packs without low-voltage cutoff or BMS on unattended robots.
17. E-stop implemented only in software.
18. Mains wiring with exposed terminals and no earth.
19. Hot-plugging stepper motors while the driver is powered (destroys drivers: inductive spike on disconnect).
20. Reading magnetic encoders with an axially magnetised magnet or with steel nearby.

---

## Canonical references

Free:
- [TI-I2C] Texas Instruments, "I2C Bus Pullup Resistor Calculation", SLVA689. Free.
  https://www.ti.com/lit/an/slva689/slva689.pdf
- [TI-485] Texas Instruments, "The RS-485 Design Guide", SLLA272. Free.
  https://www.ti.com/lit/an/slla272c/slla272c.pdf
- [TI-SLVA139] Texas Instruments, "Reverse Current/Battery Protection Circuits", SLVA139. Free.
  https://www.ti.com/lit/an/slva139/slva139.pdf
- [TI-SLVA] Texas Instruments motor drive application notes and stepper "How to" guides (DRV8825 etc.). Free.
  https://www.ti.com/motor-drivers/overview.html
- [ADI-TMC] Analog Devices/Trinamic TMC2209, TMC5160, TMC2240 datasheets. Free. https://www.analog.com
- [CIA] CAN in Automation, CANopen lower layers / bit timing and network length. Free.
  https://www.can-cia.org/can-knowledge/canopen-lower-layers
- [SE-CAN] Schneider Electric FAQ FA339840, maximum CAN bus length by bit rate. Free.
  https://www.se.com/us/en/faqs/FA339840/
- [AMS-5600] ams OSRAM AS5600 datasheet; Infineon/ams AS5600L datasheet. Free. https://ams-osram.com
- [AMS-5048] ams AS5048A/B datasheet. Free. https://ams-osram.com (mirror:
  https://home.mlab.cz/Modules/Sensors/RPS01A/pdf/AS5048_Datasheet_EN_v4.pdf)
- [HX711] Avia Semiconductor HX711 datasheet (mirrored on TI E2E and SparkFun). Free.
  https://cdn.sparkfun.com/datasheets/Sensors/ForceFlex/hx711_english.pdf
- Adafruit HX711 guide. Free. https://learn.adafruit.com/adafruit-hx711-24-bit-adc
- [PS-AWG] PowerStream AWG wire gauge table. Free. https://www.powerstream.com/Wire_Size.htm
- [IGUS] igus chainflex catalogue and bend radius explanations. Free. https://www.igus.com/chainflex
  and https://blog.igus.co.uk/?p=12439
- [BU] Battery University (Cadex). Free. https://batteryuniversity.com
- [JST] JST connector catalogue. Free. https://www.jst-mfg.com
- [MOLEX] Molex Micro-Fit 3.0 product specification. Free. https://www.molex.com
- [AMASS] AMASS XT connector datasheets (via distributors). Free.
- Espressif ESP32 datasheets and hardware design guidelines. Free. https://docs.espressif.com
- Raspberry Pi RP2040 datasheet and "Hardware design with RP2040". Free. https://www.raspberrypi.com/documentation/microcontrollers/
- ST STM32 application note AN4013 (timers), AN4899 (GPIO), and STM32G4 motor control docs. Free. https://www.st.com
- MIT OCW 6.002 Circuits and Electronics; 6.101 Introductory Analog Electronics Lab. Free.
  https://ocw.mit.edu/courses/6-002-circuits-and-electronics-spring-2007/
- All About Circuits textbook (free online). https://www.allaboutcircuits.com/textbook/
- NASA-STD-8739.4 (crimping, interconnecting cables, harnesses and wiring workmanship). Free.
  https://standards.nasa.gov
- Saturn PCB Toolkit (IPC-2152 trace width calculator). Free. https://saturnpcb.com/saturn-pcb-toolkit/
- KiCad documentation. Free. https://docs.kicad.org
- SimpleFOC documentation (BLDC/encoder practice). Free. https://docs.simplefoc.com
- Henry Ott, EMC articles (free on his site). https://www.hottconsultants.com

Paid / standards:
- Horowitz & Hill, "The Art of Electronics", 3rd ed. (Cambridge UP). The standard practical reference.
- Henry W. Ott, "Electromagnetic Compatibility Engineering" (Wiley). Grounding and shielding.
- IEC 60204-1, Safety of machinery: electrical equipment of machines (stop categories, wire sizing).
- ISO 13850, Emergency stop function. ISO 13849-1, safety-related parts of control systems.
- IEC 62368-1, Audio/video, information and communication technology equipment safety (SELV, creepage).
- IEC 61140, Protection against electric shock.
- IPC-2221 and IPC-2152, PCB design and current-carrying capacity.
- ISO 11898-1/-2, CAN. TIA/EIA-485-A, RS485.
- UL 486A-486B, wire connectors (crimp pull-out values). IEC 60352-2 crimped connections.

---

## Gaps / not verified

- Practical bundled ampacity column (Section 7.1) is an estimate made by reconciling chassis-wiring tables
  with EN 60204-1. I did not have EN 60204-1 Table 6 itself. The metric table (Section 7.2) values are
  approximate recollections and should be checked against the standard for the actual installation method.
- XT30/XT60/XT90 continuous ratings come from vendor marketing and community testing, not a formal standard.
- Connector per-contact ratings vary by wire gauge, position count and terminal plating. Verify per part number.
- CAN length values differ between sources (Schneider: 1 Mbit/s at 20 m; CiA: 25 m; HMS: 40 m with
  their assumptions). I used 20 to 25 m. RS485 1200 m at about 100 kbit/s is from TI's design guide
  as commonly cited. I did not re-read it this session.
- AS5600 accuracy, air-gap ranges and AS5048 air gap are typical values from memory of the datasheets,
  not re-verified. AS5600 fixed address 0x36 confirmed from secondary sources only.
- HX711 noise-free bits (about 16 to 18) is a community estimate, not a datasheet value.
- MCU current draws, servo stall currents and cheap-module derating (LM2596) are typical/community values.
- PCB trace current rules of thumb are approximate. Always use an IPC-2152 calculator.
- Crimp pull-force example (about 30 N at 26 AWG) is an estimate. Check UL 486A-486B tables.
- Fuse DC ratings for automotive blade fuses at 48 V: some ATO variants are rated 58 V. Verify per part.
- Safety section summarises IEC 60204-1/ISO 13850 principles but is not a compliance guide. Products
  need a proper risk assessment (ISO 12100) and qualified review.
- Regen worked example is simplified (no losses, no motor/driver efficiency).
