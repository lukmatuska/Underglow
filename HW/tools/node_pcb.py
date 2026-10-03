"""TreeGlow node PCB: 62 x 20 mm, 2 layers, LEDs on both sides.

Left end: inverted-F antenna (copper keep-out), CH572Q right below it.
Middle: 3 WS2815B on top, 3 directly behind them on the bottom.
Right end: 4 wire pads (12 V / GND in + out) and 2 x 2.2 mm holes (mini zip tie / hook).

Almost everything is routed explicitly below; Freerouting only finishes the
short MCU nets (VDD33, +5V, SWD, UART). GND is two poured planes + stitching.
"""
import os
import sys

import pcbnew

from pcbgen import Board, drc

HERE = os.path.dirname(os.path.abspath(__file__))
PRJ = os.path.join(HERE, '..', 'Underglow-slave')
PCB = os.path.join(PRJ, 'Underglow-slave.kicad_pcb')
W, H = 62.0, 20.0
F, B = pcbnew.F_Cu, pcbnew.B_Cu
route = '--no-route' not in sys.argv

b = Board(PCB, os.path.join(PRJ, 'Underglow-slave.kicad_sch'))
b.defaults(track=0.25, clearance=0.2)
b.netclass('Bus', ['VIN_12V'], 1.2, clearance=0.25, via=0.8, drill=0.4)
b.netclass('Power', ['+12V'], 0.5, clearance=0.2, via=0.6, drill=0.3)
b.netclass('Ground', ['GND'], 0.5, clearance=0.2, via=0.6, drill=0.3)
b.netclass('RF', ['RF_CHIP', 'RF_ANT'], 0.4, clearance=0.2)
b.outline(w=W, h=H, r=1.5)

# ---------------------------------------------------------------- placement
b.place('AE1', 3.5, 6.0)                      # feed; antenna copper spans x 0.95..15.35, y 0.85..6.25
b.keepout([(0, 0), (17.0, 0), (17.0, 5.5), (0, 5.5)], name='antenna keep-out')
b.place('R2', 5.2, 8.0, 180)                  # pi-match series 0R (pad2 RF_ANT left)
b.place('C9', 3.5, 8.9, 270)                  # pi-match shunt, antenna side (DNP)
b.place('C8', 6.9, 8.9, 270)                  # pi-match shunt, chip side (DNP)
b.place('U1', 9.5, 11.5, 90)                  # top row: ANT XI XO PA3 PA2 / bottom: VDD33 V5 PA0 PA1 PA7
b.place('Y1', 13.6, 8.6, 270)                 # XI pad top-left, XO pad bottom-right
b.place('C4', 6.4, 14.4, 270)                 # VDD33 2.2u
b.place('C5', 7.4, 14.4, 270)                 # VDD33 100n
b.place('R1', 7.6, 16.2, 180)                 # V5 -> VDD33 1k5
b.place('C3', 11.0, 16.8, 270)                # V5 1u
b.place('R3', 13.0, 13.7, 0)                  # PA7 -> LED data 33R
b.place('U2', 19.25, 13.4, 0)                  # HT7550-1 (SOT-89)
b.place('C2', 15.45, 17.2, 270)                # +5V 10u
b.place('C1', 22.6, 14.0, 270)                # +12V 10u
b.place('J3', 22.2, 8.4, 0, back=True)        # LED DO pad for an external strip
b.place('J1', 9.6, 18.0, 180, back=True)      # pogo pads, bottom side

LX = [27.5, 38.0, 48.5]                       # LED columns
for i, x in enumerate(LX):
    b.place(f'D{2 + i}', x, 10.0, 180)                     # front: DIN on the left, DO on the right
    b.place(f'C{10 + i}', x, 14.6, 180)
    b.place(f'D{7 - i}', x, 10.0, 180, back=True)          # back: DIN on the right, DO on the left

b.place('H1', 54.8, 3.3)
b.place('H2', 54.8, 16.7)
b.place('D1', 54.8, 10.0, 90)                 # anode (VIN_12V) up, cathode (+12V) down
b.place('J2', 59.3, 2.8, 270)                 # pads at y = 2.8 / 7.6 / 12.4 / 17.2
b.check_placed()
pad = b.pad_xy

# ---------------------------------------------------------------- RF + clock
fx, fy = pad('AE1', '1')
r2a, r2c = pad('R2', '2'), pad('R2', '1')
c9, c8, ant = pad('C9', '1'), pad('C8', '1'), pad('U1', '10')
b.track('RF_ANT', [(fx, fy), (fx, r2a[1]), r2a], 0.4)
b.track('RF_ANT', [(fx, r2a[1]), c9], 0.4)
b.track('RF_CHIP', [r2c, (ant[0], r2c[1]), ant], 0.3)
b.track('RF_CHIP', [(c8[0], r2c[1]), c8], 0.4)
xi, xo = pad('U1', '9'), pad('U1', '8')
yxi, yxo = pad('Y1', '1'), pad('Y1', '3')
b.track('XI', [xi, (xi[0], yxi[1]), yxi], 0.2)                 # up and over
ymid = (yxi[1] + yxo[1]) / 2                                      # between the crystal's left pads
b.track('XO', [xo, (xo[0], ymid), (yxo[0], ymid), yxo], 0.2)

# ---------------------------------------------------------------- MCU data out
pa7, r3a, r3b = pad('U1', '5'), pad('R3', '1'), pad('R3', '2')
b.track('LED_DATA_MCU', [pa7, (pa7[0], r3a[1]), r3a], 0.2)
din = pad('D2', '4')
b.track('LED_D1', [r3b, (14.2, r3b[1]), (14.2, 11.0), (23.0, 11.0), (23.0, din[1]), din], 0.25)

# ---------------------------------------------------------------- 5 V
v5, r1, c3, c2, u2o, j1 = (pad('U1', '2'), pad('R1', '1'), pad('C3', '1'), pad('C2', '1'),
                           pad('U2', '3'), pad('J1', '1'))
V5Y = 15.7
b.track('+5V', [v5, (v5[0], V5Y), (u2o[0], V5Y), u2o], 0.3)
b.track('+5V', [(c3[0], V5Y), c3], 0.3)
b.track('+5V', [(c2[0], V5Y), c2], 0.3)
b.track('+5V', [(v5[0], V5Y), (v5[0], 17.0), (j1[0], 17.0)], 0.3)
b.track('+5V', [(v5[0], r1[1]), r1], 0.3)
b.via('+5V', j1[0], 17.0)

# SWCLK: straight down through a via, then to its pogo pad on B.Cu.
ck, jck = pad('U1', '4'), pad('J1', '3')
b.track('SWCLK', [ck, (ck[0], 14.3), (11.0, 14.3)], 0.2)
b.via('SWCLK', 11.0, 14.3)
b.track('SWCLK', [(11.0, 14.3), (11.0, 16.3), (jck[0], 16.3), jck], 0.25, layer=B)
# SWDIO: down between the V5 and SWCLK lanes, via, then left on B.Cu.
io, jio = pad('U1', '3'), pad('J1', '2')
b.track('SWDIO', [io, (io[0], 14.6), (9.9, 15.0)], 0.2)
b.via('SWDIO', 9.9, 15.0)
b.track('SWDIO', [(9.9, 15.0), (jio[0], 15.0), jio], 0.25, layer=B)

# ---------------------------------------------------------------- LED chain
for a, z in (('D2', 'D3'), ('D3', 'D4')):                       # front, left -> right on F.Cu
    b.track(b.pinnet[(z, '4')].lstrip('/'), [pad(a, '3'), pad(z, '4')], 0.25)
do4 = pad('D4', '3')
b.track('LED_D4', [do4, (52.4, do4[1])], 0.25)
b.via('LED_D4', 52.4, do4[1])
b.track('LED_D4', [(52.4, do4[1]), pad('D5', '4')], 0.25, layer=B)
for a, z in (('D5', 'D6'), ('D6', 'D7')):                       # back, right -> left on B.Cu
    b.track(b.pinnet[(z, '4')].lstrip('/'), [pad(a, '3'), pad(z, '4')], 0.25, layer=B)
do7, ext = pad('D7', '3'), pad('J3', '1')
b.track('LED_EXT', [do7, ext], 0.25, layer=B)
for i in range(3):                                                # DIN2 -> GND stubs
    b.track('GND', [pad(f'D{2 + i}', '5'), pad(f'D{2 + i}', '6')], 0.5)
    b.track('GND', [pad(f'D{5 + i}', '5'), pad(f'D{5 + i}', '6')], 0.5, layer=B)

# ---------------------------------------------------------------- 12 V
BUS_Y = 13.3
k = pad('D1', '1')
taps = [19.25]                                                           # bus x positions with a branch
for i, x in enumerate(LX):
    v = pad(f'D{2 + i}', '2')                                            # front VDD (right side)
    b.track('+12V', [v, (x + 3.9, v[1]), (x + 3.9, BUS_Y)], 0.5)
    taps.append(x + 3.9)
    bv = pad(f'D{7 - i}', '2')                                           # back VDD (left side)
    if i == 0:   # left of D7 is busy on F.Cu: run under D7 on B.Cu and drop into the bus
        b.track('+12V', [bv, (x - 3.7, bv[1]), (x - 3.7, BUS_Y), (x - 0.5, BUS_Y)], 0.5, layer=B)
        b.via('+12V', x - 0.5, BUS_Y)
        taps.append(x - 0.5)
        c = pad(f'C{10 + i}', '1')
        b.track('+12V', [c, (c[0], BUS_Y)], 0.4)
        taps.append(c[0])
        continue
    vx = x - 4.1
    b.track('+12V', [bv, (vx, bv[1])], 0.5, layer=B)
    b.via('+12V', vx, bv[1])
    b.track('+12V', [(vx, bv[1]), (vx, BUS_Y)], 0.5)
    c = pad(f'C{10 + i}', '1')
    b.track('+12V', [c, (c[0], BUS_Y)], 0.4)
    taps += [vx, c[0]]
c1 = pad('C1', '1')
b.track('+12V', [c1, (c1[0], BUS_Y)], 0.5)
taps.append(c1[0])
b.track('+12V', [(x_, BUS_Y) for x_ in sorted(set(taps))] + [(k[0], BUS_Y), k], 0.8)
# Bus: J2 pad 1 <-> pad 4 (F.Cu, left of the pads), GND pads 2 <-> 3 (B.Cu), D1 anode tap.
p1, p4 = pad('J2', '1'), pad('J2', '4')
bx = p1[0] - 2.3
b.track('VIN_12V', [p1, (bx, p1[1]), (bx, p4[1]), p4], 1.2)
a = pad('D1', '2')
b.track('VIN_12V', [a, (a[0], 7.0), (bx, 7.0)], 0.8)
b.track('GND', [pad('J2', '2'), pad('J2', '3')], 1.5, layer=B)

# ---------------------------------------------------------------- GND stitching
for x, y in [(9.0, 11.5), (10.0, 11.5)]:                       # U1 exposed pad
    b.via('GND', x, y, 0.6, 0.3)
stitch = [(2.3, 9.6), (5.0, 10.5), (6.9, 10.2), (16.2, 9.5), (16.6, 6.5),
          (12.3, 17.2), (17.7, 18.6), (21.8, 18.4), (19.3, 4.0),
          (24.0, 3.5), (32.7, 3.5), (43.3, 3.5), (51.0, 3.5), (52.0, 6.5),
          (24.5, 17.8), (31.0, 17.8), (35.0, 17.8), (41.5, 17.8), (45.5, 17.8), (52.0, 17.8),
          (31.5, 6.2), (42.0, 6.2), (2.5, 13.0), (2.5, 16.0)]
for x, y in stitch:
    b.via('GND', x, y)

# ---------------------------------------------------------------- silkscreen
b.text('TreeGlow node v1.0', 37, 1.4, 0.8)
for y_, t_ in ((2.8, '+12V'), (7.6, 'GND'), (12.4, 'GND'), (17.2, '+12V')):
    b.text(t_, 61.3, y_, 0.6, rot=90)
b.text('DO', 22.2, 6.6, 0.7, layer=pcbnew.B_SilkS)
b.text('TreeGlow node (back)', 37, 18.6, 0.7, layer=pcbnew.B_SilkS)

if route:
    b.autoroute(passes=30, ignore_classes=('Ground',))
b.zone('GND', [(0, 5.5), (17.0, 5.5), (17.0, 0), (W, 0), (W, H), (0, H)], clearance=0.25)
b.save()
b.refill()
if route:
    for v in drc(PCB):
        print(v)
print('saved', PCB)
