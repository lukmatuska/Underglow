"""TreeGlow master PCB: 72 x 52 mm, 2 layers.

Top centre: ESP32-C3-WROOM-02, antenna on the board edge.
Bottom left: CH572Q radio with its own inverted-F antenna, ~40 mm from the Wi-Fi antenna.
Right edge: USB-C and the expansion header. Bottom edge: 12 V and LED-out screw terminals.
"""
import os
import sys

import pcbnew

from pcbgen import Board, drc

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, '..', 'Underglow-master')
PCB = os.path.join(PRJ, 'Underglow-master.kicad_pcb')
W, H = 72.0, 52.0
F, B = pcbnew.F_Cu, pcbnew.B_Cu
route = '--no-route' not in sys.argv

b = Board(PCB, os.path.join(PRJ, 'Underglow-master.kicad_sch'))
b.defaults(track=0.25, clearance=0.2)
b.netclass('Power', ['VIN_RAW', 'VIN_F', 'V12', 'SW', '+5V', 'VBUS'], 0.6, clearance=0.2, via=0.8, drill=0.4)
b.netclass('Supply', ['+3V3'], 0.4, clearance=0.2)
b.netclass('Ground', ['GND'], 0.5, clearance=0.2)
b.netclass('RF', ['CH_RF', 'CH_RF2', 'RF_PCB', 'RF_UFL'], 0.4, clearance=0.2)
b.outline(w=W, h=H, r=2.0)

# ---------------------------------------------------------------- ESP32-C3
b.place('U4', 36.0, 13.1)                     # module body x 27..45, y 0..20; pads x 27.25 / 44.75
b.place('C11', 23.4, 8.4, 90)                 # 3V3 10u
b.place('C12', 24.6, 8.4, 90)                 # 3V3 100n
b.place('R9', 23.4, 11.4, 90)                 # EN pull-up
b.place('C10', 24.6, 11.4, 90)                # EN RC
b.place('R12', 24.6, 17.6, 0)                 # IO8 pull-up
b.place('R10', 24.6, 19.0, 0)                 # IO9/BOOT pull-up
b.place('R11', 47.6, 10.1, 0)                 # IO2 pull-up
b.place('SW1', 12.0, 13.0, 0)                 # RESET
b.place('SW2', 12.0, 21.0, 0)                 # BOOT
b.place('R13', 47.6, 19.1, 0)                 # status LED resistor (IO10)
b.place('D3', 50.6, 19.1, 0)
b.place('R14', 47.6, 21.6, 0)                 # power LED resistor
b.place('D4', 50.6, 21.6, 0)

# ---------------------------------------------------------------- 3.3 V
b.place('U3', 16.0, 8.0, 0)                   # ME6211 SOT-23-5
b.place('C7', 13.4, 8.0, 90)                  # 5V in 1u
b.place('C8', 19.4, 5.2, 0)                   # 3V3 10u (0603)
b.place('C9', 16.0, 5.2, 0)                   # 3V3 100n

# ---------------------------------------------------------------- USB-C (right edge)
b.place('J2', 68.9, 12.5, 90)                 # mouth faces +x
b.place('U2', 60.0, 12.5, 90)                 # USBLC6
b.place('R5', 63.4, 18.6, 0)                  # CC1
b.place('R6', 63.4, 6.4, 0)                   # CC2
b.place('Q1', 60.0, 18.4, 0)                  # USB -> +5V switch
b.place('R7', 56.6, 18.0, 90)
b.place('R8', 56.6, 21.0, 90)
b.place('J3', 69.6, 21.0, 0)                  # EXP 1x08 vertical, y 21..38.8

# ---------------------------------------------------------------- 12 V in + buck (bottom right)
b.place('J1', 52.0, 47.4, 0)                  # 12 V screw terminal, wires exit downward
b.place('F1', 52.0, 38.6, 90)                 # PTC
b.place('D1', 46.0, 39.6, 180)                # TVS, cathode (VIN_F) on the right
b.place('D2', 56.6, 37.4, 180)                # series Schottky, anode (VIN_F) on the left
b.place('C1', 60.6, 37.4, 90)                 # V12 10u
b.place('C2', 62.6, 37.4, 90)
b.place('C3', 64.4, 36.4, 90)                 # V12 100n
b.place('U1', 61.0, 32.6, 90)                 # TPS54202: bottom row GND SW VIN, top row BOOT EN FB
b.place('C4', 59.0, 29.6, 0)                  # bootstrap
b.place('R1', 63.6, 30.0, 90)                 # EN divider top (V12)
b.place('R2', 64.8, 30.0, 90)                 # EN divider bottom
b.place('R3', 60.0, 27.8, 0)                  # FB top (+5V)
b.place('R4', 62.6, 27.8, 0)                  # FB bottom
b.place('L1', 53.5, 31.0, 180)                # SW (pad 1) on the right, +5V on the left
b.place('C5', 47.6, 31.0, 90)                 # +5V 22u
b.place('C6', 45.6, 31.0, 90)

# ---------------------------------------------------------------- LED out (bottom middle)
b.place('J4', 34.0, 47.4, 0)                  # LED OUT terminal
b.place('U5', 36.6, 38.0, 0)                  # 74AHCT1G125
b.place('C13', 40.0, 35.6, 0)
b.place('R16', 33.4, 38.0, 90)                # pull-down on the input
b.place('R15', 40.0, 38.6, 90)                # 33R series

# ---------------------------------------------------------------- CH572 radio (bottom left)
# U6 rotated 180: left column PA2 PA3 XO XI ANT (top->bottom), right column PA7 PA1 PA0 V5 VDD33.
AX = 15.54                                    # x of the ANT pin = straight RF line down to the feed
b.place('AE1', AX, 46.4, 180)                 # feed; copper spans x 3.7..18.1, y 46.15..51.55
b.keepout([(3.0, 46.9), (19.0, 46.9), (19.0, H), (3.0, H)], name='CH572 antenna keep-out')
b.place('U6', 17.0, 36.0, 180)
b.place('Y1', 11.9, 36.0, 90)                 # XI pad bottom-right, XO pad top-left
b.place('R18', AX, 39.9, 270)                 # pi series 0R
b.place('C17', 14.0, 39.42, 180)              # pi shunt, chip side (DNP)
b.place('C18', 14.0, 41.2, 180)               # pi shunt, antenna side (DNP)
b.place('R19', AX, 42.4, 270)                 # 0R to the PCB antenna
b.place('R20', 17.2, 41.2, 0)                 # DNP 0R to U.FL
b.place('J5', 20.6, 43.4, 0)                  # U.FL (DNP)
b.place('C15', 19.5, 38.6, 270)               # VDD33 2u2
b.place('C16', 20.55, 38.6, 270)               # VDD33 100n
b.place('R17', 22.15, 37.6, 180)               # V5 -> VDD33 1k5
b.place('C14', 22.9, 39.6, 270)               # V5 1u
b.place('J6', 25.5, 38.6, 180)                # SWD header: pins up from y 38.6 = 5V, SWDIO, SWCLK, GND

for i, (x, y) in enumerate([(3.5, 3.5), (68.5, 3.5), (3.5, 40.0), (65.5, 48.0)]):
    b.place(f'H{i + 1}', x, y)
b.check_placed()

# ESP module: its built-in 0.2 mm thermal vias -> plain pads; add 0.3 mm vias of our own.
for p_ in b.fps['U4'].Pads():
    if p_.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and pcbnew.ToMM(p_.GetDrillSize().x) < 0.3:
        p_.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        p_.SetDrillSize(pcbnew.VECTOR2I(0, 0))
        ls_ = pcbnew.LSET(); ls_.AddLayer(pcbnew.F_Cu); p_.SetLayerSet(ls_)
b.ref_at('U4', 0, -9.5)
b.ref_at('U5', 0, 2.2)
if '--pads' in sys.argv:
    for r in sys.argv[sys.argv.index('--pads') + 1:]:
        fp = b.fps[r]
        print(r, [(p.GetNumber(), b.pad_xy(r, p.GetNumber())) for p in fp.Pads() if p.GetNumber()])
    raise SystemExit

# ---------------------------------------------------------------- CH572 hand routes
pad = b.pad_xy
ant, xi, xo = pad('U6', '10'), pad('U6', '9'), pad('U6', '8')
r18a, r18b, r19a, r19b = pad('R18', '1'), pad('R18', '2'), pad('R19', '1'), pad('R19', '2')
b.track('CH_RF', [ant, r18a], 0.3)
b.track('CH_RF', [r18a, pad('C17', '1')], 0.4)
b.track('CH_RF2', [r18b, r19a], 0.4)
b.track('CH_RF2', [(AX, pad('C18', '1')[1]), pad('C18', '1')], 0.4)
b.track('CH_RF2', [(AX, pad('R20', '1')[1]), pad('R20', '1')], 0.4)
b.track('RF_PCB', [r19b, pad('AE1', '1')], 0.4)
b.track('RF_UFL', [pad('R20', '2'), (pad('J5', '1')[0], pad('R20', '2')[1]), pad('J5', '1')], 0.4)
yxi, yxo = pad('Y1', '1'), pad('Y1', '3')
b.track('CH_XI', [xi, (14.5, xi[1]), (14.5, yxi[1]), yxi], 0.2)
b.track('CH_XO', [xo, (yxo[0], xo[1]), yxo], 0.2)         # threads between the crystal's pads
pa2, pa3 = pad('U6', '6'), pad('U6', '7')
b.track('UART_E2C', [pa2, (14.6, pa2[1]), (14.6, 33.4)], 0.2)
b.track('UART_C2E', [pa3, (14.0, pa3[1]), (14.0, 33.4)], 0.2)
pa7, pa1, pa0, v5, vdd = (pad('U6', n) for n in ('5', '4', '3', '2', '1'))
b.track('CH_CTRL', [pa7, (19.4, pa7[1]), (19.4, 33.4)], 0.2)
j6 = {n: pad('J6', n) for n in '1234'}
b.track('CH_SWCLK', [pa1, (20.0, pa1[1]), (20.0, j6['3'][1]), j6['3']], 0.2)
b.track('CH_SWDIO', [pa0, (j6['2'][0], pa0[1])], 0.2)
r17a, r17b = pad('R17', '1'), pad('R17', '2')
b.track('CH_VDD33', [vdd, (r17b[0], vdd[1]), r17b], 0.25)
b.track('CH_VDD33', [(pad('C15', '1')[0], vdd[1]), pad('C15', '1')], 0.25)
b.track('CH_VDD33', [(pad('C16', '1')[0], vdd[1]), pad('C16', '1')], 0.25)
c14 = pad('C14', '1')
b.track('+5V', [v5, (c14[0], v5[1]), c14], 0.3)
b.track('+5V', [(c14[0], r17a[1]), r17a], 0.3)
b.track('+5V', [(c14[0], j6['1'][1]), j6['1']], 0.3)
for x, y in [(16.5, 36.0), (17.5, 36.0)]:                 # U6 exposed pad
    b.via('GND', x, y)
for x, y in [(35.6, 12.8), (36.7, 12.8), (35.6, 13.9), (36.7, 13.9)]:   # U4 ground pad
    b.via('GND', x, y)
b.via('GND', pad('AE1', '2')[0], pad('AE1', '2')[1] - 1.0)

# ---------------------------------------------------------------- silkscreen
b.text('TreeGlow master v1.0', 36, 24.0, 1.0)
b.text('+12V  GND', 54.5, 41.35, 0.6)
b.text('DATA  GND', 36.5, 41.35, 0.6)
b.text('RESET', 12.0, 16.9, 0.7)
b.text('STAT/PWR', 50.0, 23.3, 0.6)
b.text('BOOT', 12.0, 24.6, 0.7)
b.text('CH572 SWD', 25.5, 28.6, 0.6)

if route:
    b.autoroute(passes=40, ignore_classes=('Ground',))
b.zone('GND', [(0, 0), (W, 0), (W, H), (19.0, H), (19.0, 46.9), (3.0, 46.9), (3.0, H), (0, H)], clearance=0.25)
b.save()
b.refill()
if route:
    for v in drc(PCB):
        print(v)
print('saved', PCB)
