"""Footprints and JLCPCB/LCSC part numbers shared by both TreeGlow boards.

Prices (USD, JLCPCB parts API, 2026-10-03) are noted for the cost estimate in
docs/COST.md. "basic" parts carry no per-order JLC setup fee.
"""
R0402 = 'Resistor_SMD:R_0402_1005Metric'
C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0603 = 'Capacitor_SMD:C_0603_1005Metric'.replace('1005', '1608')
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
LED0603 = 'LED_SMD:LED_0603_1608Metric'
SOD123 = 'Diode_SMD:D_SOD-123'
SMA = 'Diode_SMD:D_SMA'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
SOT23_5 = 'Package_TO_SOT_SMD:SOT-23-5'
SOT23_6 = 'Package_TO_SOT_SMD:SOT-23-6'
SOT89 = 'Package_TO_SOT_SMD:SOT-89-3'
DFN10 = 'Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.7x2.5mm'
XTAL3225 = 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'
WS2815_FP = 'LED_SMD:LED_WS2812_PLCC6_5.0x5.0mm_P1.6mm'
ANT_FP = 'RF_Antenna:Texas_SWRA117D_2.4GHz_Right'
UFL = 'Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical'
PROG = 'TreeGlow:ProgPads_1x05_P2.54mm'

# (value, LCSC, unit price @ ~100-1k qty)
P = {
    'C_100n': ('100nF', 'C1525', 0.003),
    'C_10n': ('10nF', 'C15195', 0.003),
    'C_1u': ('1uF', 'C52923', 0.005),
    'C_2u2': ('2.2uF', 'C12530', 0.004),
    'C_10u_0603': ('10uF 10V', 'C19702', 0.02),
    'C_10u_0805': ('10uF 25V', 'C15850', 0.03),
    'C_22u_1206': ('22uF 25V', 'C12891', 0.09),
    'R_0': ('0R', 'C17168', 0.002),
    'R_33': ('33R', 'C25105', 0.001),
    'R_1k': ('1k', 'C11702', 0.001),
    'R_1k5': ('1.5k', 'C25867', 0.002),
    'R_5k1': ('5.1k', 'C25905', 0.002),
    'R_10k': ('10k', 'C25744', 0.002),
    'R_75k': ('75k', 'C25798', 0.003),
    'R_100k': ('100k', 'C25741', 0.002),
    'CH572Q': ('CH572Q', 'C46772607', 0.25),
    'WS2815B': ('WS2815B-V1', 'C5446699', 0.07),
    'XTAL32M': ('32MHz', 'C9009', 0.06),
    'HT7550': ('HT7550-1', 'C347189', 0.03),
    'B5819W': ('B5819W', 'C8598', 0.02),
    'ESP32C3': ('ESP32-C3-WROOM-02-N4', 'C2934560', 2.45),
    'TPS54202': ('TPS54202DDCR', 'C191884', 0.13),
    'L_10u': ('10uH', 'C167223', 0.06),
    'ME6211': ('ME6211C33M5G-N', 'C82942', 0.05),
    'AO3401': ('AO3401A', 'C15127', 0.07),
    'USBC': ('TYPE-C-31-M-12', 'C165948', 0.13),
    'USBLC6': ('USBLC6-2SC6', 'C2687116', 0.03),
    'SMAJ15A': ('SMAJ15A', 'C86819', 0.04),
    'AHCT125': ('74AHCT1G125GV', 'C52140417', 0.05),
    'BTN': ('TS-1187A-B-A-B', 'C318884', 0.015),
    'LED_G': ('green', 'C12624', 0.01),
    'PTC500': ('SMD1206P050TF', 'C20799', 0.05),
    'R_22k': ('22k', 'C25768', 0.002),
    'C_22u_0805': ('22uF 25V', 'C45783', 0.12),
    'HDR4': ('PZ254V-11-04P', 'C2691448', 0.02),
    'TERM2': ('KF128-5.08-2P', 'C474952', 0.12),
    'UFL': ('U.FL-R-SMT-1', 'C88373', 0.16),
}


def part(key):
    v, lcsc, _ = P[key]
    return v, lcsc
