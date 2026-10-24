"""Controller board pin maps for 4 A4988 step/dir drivers.

Each motor slot gives the Arduino pin numbers plus the AVR port and bit of the STEP pin, so
the firmware can pulse all step pins from the timer interrupt with direct port writes
(digitalWrite takes ~4 us per call on a 16 MHz AVR, too slow inside the ISR).
Pin numbers are the shield/board makers' published assignments (sources in `source`).
"""

from __future__ import annotations

BOARDS: dict[str, dict] = {
    "uno_cnc": {
        "title": "Arduino Uno + CNC Shield V3 (4x A4988)",
        "mcu": "ATmega328P @ 16 MHz",
        "fqbn": "arduino:avr:uno",
        "define": "MECHY_BOARD_UNO_CNC",
        "source": "Protoneer CNC Shield V3.00 pinout (GRBL 0.9+ layout; A axis on D12/D13 jumpers)",
        # slot: socket label on the shield
        "slots": [
            {"socket": "X", "step": 2, "step_port": "PORTD", "step_bit": 2, "dir": 5, "enable": 8},
            {"socket": "Y", "step": 3, "step_port": "PORTD", "step_bit": 3, "dir": 6, "enable": 8},
            {"socket": "Z", "step": 4, "step_port": "PORTD", "step_bit": 4, "dir": 7, "enable": 8},
            {"socket": "A", "step": 12, "step_port": "PORTB", "step_bit": 4, "dir": 13, "enable": 8,
             "note": "set the two A-axis jumpers to D12 (step) and D13 (dir); leave SpnEn/SpnDir headers unused"},
        ],
        "switches": [
            {"pin": 9, "label": "X- / X+ limit header (D9)"},
            {"pin": 10, "label": "Y- / Y+ limit header (D10)"},
            {"pin": 11, "label": "Z- / Z+ limit header (D11)"},
            {"pin": 14, "label": "Abort header (A0 = D14)"},
        ],
        "estop": {"pin": 15, "label": "Hold header (A1 = D15), optional; leave open if unused"},
        "enable_shared": True,
        "serial_baud": 115200,
        "tick_hz": 20000,
        "ram_bytes": 2048,
        "flash_bytes": 32256,
    },
    "mega_ramps": {
        "title": "Arduino Mega 2560 + RAMPS 1.4 (4x A4988)",
        "mcu": "ATmega2560 @ 16 MHz",
        "fqbn": "arduino:avr:mega",
        "define": "MECHY_BOARD_MEGA_RAMPS",
        "source": "RepRap RAMPS 1.4 pin table (Marlin pins_RAMPS.h)",
        "slots": [
            {"socket": "X", "step": 54, "step_port": "PORTF", "step_bit": 0, "dir": 55, "enable": 38},
            {"socket": "Y", "step": 60, "step_port": "PORTF", "step_bit": 6, "dir": 61, "enable": 56},
            {"socket": "Z", "step": 46, "step_port": "PORTL", "step_bit": 3, "dir": 48, "enable": 62},
            {"socket": "E0", "step": 26, "step_port": "PORTA", "step_bit": 4, "dir": 28, "enable": 24},
        ],
        "switches": [
            {"pin": 3, "label": "X-MIN endstop (D3)"},
            {"pin": 14, "label": "Y-MIN endstop (D14)"},
            {"pin": 18, "label": "Z-MIN endstop (D18)"},
            {"pin": 2, "label": "X-MAX endstop (D2)"},
        ],
        "estop": {"pin": 15, "label": "Y-MAX endstop (D15), optional; leave open if unused"},
        "enable_shared": False,
        "serial_baud": 115200,
        "tick_hz": 20000,
        "ram_bytes": 8192,
        "flash_bytes": 253952,
    },
}

CONTROLLER_ALIASES = {
    "arduino-uno": "uno_cnc", "uno": "uno_cnc", "uno_cnc": "uno_cnc", "arduino-uno-cnc": "uno_cnc",
    "arduino-mega": "mega_ramps", "mega": "mega_ramps", "ramps": "mega_ramps", "mega_ramps": "mega_ramps",
    "arduino-mega-ramps": "mega_ramps",
}


def board_for_controller(controller: str | None) -> str:
    """Board id for hw/drivers.yaml `controller` (default uno_cnc)."""
    if not controller:
        return "uno_cnc"
    return CONTROLLER_ALIASES.get(str(controller).strip().lower(), "uno_cnc")


def get_board(board: str) -> dict:
    if board not in BOARDS:
        raise ValueError(f"unknown board {board!r}; known: {', '.join(BOARDS)}")
    return BOARDS[board]
