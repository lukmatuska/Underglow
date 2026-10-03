"""TreeGlow node (slave) board schematic -> HW/Underglow-slave/Underglow-slave.kicad_sch"""
import os

from kigen import Schematic, write_lib_tables
from parts import *

OUT = os.path.join(os.path.dirname(__file__), '..', 'Underglow-slave')

s = Schematic('Underglow-slave', 'TreeGlow node (CH572Q + 6x WS2815B)', rev='1.0',
              comments=('Wireless 12 V RGB node for the TreeGlow Christmas tree',
                        '3x WS2815B per side, CH572Q 2.4 GHz receiver, 12 V pass-through power'))


def passive(kind, ref, key, at, n1, n2, fp=C0402, dnp=False):
    val, lcsc = part(key) if key else ('DNP', '')
    lib = {'R': 'Device:R_Small', 'C': 'Device:C_Small'}[kind]
    s.add(lib, ref, val, at, {'1': n1, '2': n2}, footprint=fp, lcsc=lcsc, dnp=dnp)


# ------------------------------------------------------------------ power
s.box(12, 18, 118, 96, 'POWER: 12 V bus in/out, reverse protection, 5 V LDO')
s.add('Connector_Generic:Conn_01x04', 'J2', 'PWR 12V', (35, 50),
      {'1': 'VIN_12V', '2': 'GND', '3': 'GND', '4': 'VIN_12V'},
      footprint='Connector_Wire:SolderWire-0.75sqmm_1x04_P4.8mm_D1.25mm_OD2.3mm', in_bom=False,
      descr='Wire pads: two +12V/GND pairs, internally bridged, to daisy-chain power to the next node')
s.flag('VIN_12V', (22, 30))
s.flag('GND', (104, 26))
v, l = part('B5819W')
s.add('Device:D_Schottky_Small', 'D1', v, (55, 40), {'1': '+12V', '2': 'VIN_12V'}, rot=180,
      footprint=SOD123, lcsc=l, descr='Reverse-polarity protection for this node only (bus passes through)')
s.flag('+12V', (66, 30))
passive('C', 'C1', 'C_10u_0805', (66, 52), '+12V', 'GND', fp=C0805)
v, l = part('HT7550')
s.add('Regulator_Linear:HT75xx-1-SOT89', 'U2', v, (88, 52), {'1': 'GND', '2': '+12V', '3': '+5V'},
      footprint=SOT89, lcsc=l, descr='5 V 100 mA LDO, 30 V max input, 2.5 uA Iq')
passive('C', 'C2', 'C_10u_0603', (108, 52), '+5V', 'GND', fp=C0603)
s.text('D1 drops ~0.35 V: LEDs see ~11.6 V (WS2815B min 9.5 V).\n'
       'U2 dissipates (12-5) V x ~12 mA = ~85 mW.\n'
       'J2 pins 1/4 and 2/3 are bridged on the PCB: the\n'
       'downstream chain current flows only through J2.', (16, 75))

# ------------------------------------------------------------------ MCU
s.box(122, 18, 210, 96, 'MCU: CH572Q (5 V mode)')
v, l = part('CH572Q')
s.add('TreeGlow:CH572Q', 'U1', v, (170, 58),
      {'2': '+5V', '1': 'VDD33', '3': 'SWDIO', '4': 'SWCLK', '5': 'LED_DATA_MCU',
       '10': 'RF_CHIP', '9': 'XI', '8': 'XO', '7': None, '6': 'UART_TX', '11': 'GND'},
      footprint=DFN10, lcsc=l)
passive('C', 'C3', 'C_1u', (132, 36), '+5V', 'GND')
passive('R', 'R1', 'R_1k5', (140, 36), '+5V', 'VDD33')
passive('C', 'C4', 'C_2u2', (148, 36), 'VDD33', 'GND')
passive('C', 'C5', 'C_100n', (156, 36), 'VDD33', 'GND')
passive('R', 'R3', 'R_33', (140, 82), 'LED_DATA_MCU', 'LED_D1')
s.text('Per CH572 datasheet (5 V supply): 2.2 uF + 100 nF\n'
       'on VDD33 and 1.5 k between V5 and VDD33.\n'
       'WS2815B VIH(min) = 2.7 V, so the 3.3 V\n'
       'GPIO drives DIN directly via R3.\n'
       'Log UART: map TXD_1 to PA2. PA3 = spare.', (150, 78))

# ------------------------------------------------------------------ RF + clock
s.box(214, 18, 285, 96, 'RF + 32 MHz clock')
v, l = part('XTAL32M')
s.add('Device:Crystal_GND24_Small', 'Y1', v, (244, 74), {'1': 'XI', '3': 'XO', '2': 'GND', '4': 'GND'},
      footprint=XTAL3225, lcsc=l)
passive('C', 'C8', None, (224, 42), 'RF_CHIP', 'GND', dnp=True)
passive('R', 'R2', 'R_0', (240, 42), 'RF_CHIP', 'RF_ANT')
passive('C', 'C9', None, (256, 42), 'RF_ANT', 'GND', dnp=True)
s.add('Device:Antenna_Shield', 'AE1', 'PCB IFA', (274, 40), {'1': 'RF_ANT', '2': 'GND'},
      footprint=ANT_FP, in_bom=False, descr='TI SWRA117D 2.4 GHz inverted-F PCB antenna')
s.text('Pi match: R2 = 0R, C8/C9 not fitted.\n'
       'Tune with a VNA if range is short.\n'
       'No external load caps: CH572 has\n'
       'tunable internal ones (R8_XT32M_TUNE).', (216, 56))

# ------------------------------------------------------------------ LEDs
s.box(12, 100, 200, 168, 'LEDs: 3x WS2815B front (D2-D4), 3x back (D5-D7)')
chain = ['LED_D1', 'LED_D2', 'LED_D3', 'LED_D4', 'LED_D5', 'LED_D6', 'LED_EXT']
v, l = part('WS2815B')
for i in range(6):
    x = 40 + (i % 3) * 52
    y = 120 if i < 3 else 150
    s.add('TreeGlow:WS2815B', f'D{i + 2}', v, (x, y),
          {'2': '+12V', '5': 'GND', '4': chain[i], '6': 'GND', '3': chain[i + 1], '1': None},
          footprint=WS2815_FP, lcsc=l, extra={'Side': 'front' if i < 3 else 'back'})
for i in range(3):
    passive('C', f'C{10 + i}', 'C_100n', (176 + i * 8, 112), '+12V', 'GND')
s.text('DIN2 (backup data input) is tied to GND as Worldsemi\n'
       'specifies for a pixel without a backup source.\n'
       'Data: D2>D3>D4 (front) > via > D5>D6>D7 (back) > J3.', (118, 102.5))

# ------------------------------------------------------------------ connectors
s.box(204, 100, 285, 160, 'Programming / expansion')
s.add('Connector_Generic:Conn_01x05', 'J1', 'PROG', (240, 118),
      {'1': '+5V', '2': 'SWDIO', '3': 'SWCLK', '4': 'GND', '5': 'UART_TX'},
      footprint=PROG, in_bom=False,
      descr='Bottom-side pogo pads. 1-4 = USB order (VBUS, D-, D+, GND) for CH572 USB-ISP, or WCH-LinkE SDI')
s.add('Connector_Generic:Conn_01x01', 'J3', 'LED DO', (240, 146), {'1': 'LED_EXT'},
      footprint='TestPoint:TestPoint_Pad_D1.5mm', in_bom=False,
      descr='Optional: continue the pixel chain into an external WS2815 strip (power it from J2)')
s.add('Mechanical:MountingHole', 'H1', 'MountingHole', (258, 150), {},
      footprint='MountingHole:MountingHole_2.2mm_M2', in_bom=False)
s.add('Mechanical:MountingHole', 'H2', 'MountingHole', (258, 158), {},
      footprint='MountingHole:MountingHole_2.2mm_M2', in_bom=False)

s.save(os.path.join(OUT, 'Underglow-slave.kicad_sch'))
write_lib_tables(OUT)
print('node schematic written')
