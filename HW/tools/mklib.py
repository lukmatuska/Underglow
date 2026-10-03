"""Generates the project-local TreeGlow symbol and footprint library."""
import os
import uuid
from sexp import Sym as S, dump

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, '..', 'lib')
F = [S('effects'), [S('font'), [S('size'), 1.27, 1.27]]]
FH = [S('effects'), [S('font'), [S('size'), 1.27, 1.27]], [S('hide'), S('yes')]]


def prop(name, val, x=0, y=0, hide=False):
    return [S('property'), name, val, [S('at'), x, y, 0], FH if hide else F]


def pin(num, name, kind, x, y, ang, length=2.54, hidden=False):
    p = [S('pin'), S(kind), S('line'), [S('at'), x, y, ang], [S('length'), length]]
    if hidden:
        p.append([S('hide'), S('yes')])
    p += [[S('name'), name, F], [S('number'), num, F]]
    return p


def rect(x1, y1, x2, y2):
    return [S('rectangle'), [S('start'), x1, y1], [S('end'), x2, y2],
            [S('stroke'), [S('width'), 0.254], [S('type'), S('default')]],
            [S('fill'), [S('type'), S('background')]]]


def symbol(name, ref, value, fp, ds, desc, body, pins, extra=()):
    return [S('symbol'), name,
            [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
            prop('Reference', ref, 0, body[1] + 1.27), prop('Value', value, 0, body[3] - 1.27),
            prop('Footprint', fp, hide=True), prop('Datasheet', ds, hide=True),
            prop('Description', desc, hide=True), *extra,
            [S('symbol'), f'{name}_0_1', rect(*body)],
            [S('symbol'), f'{name}_1_1', *pins],
            [S('embedded_fonts'), S('no')]]


ch572q = symbol(
    'CH572Q', 'U', 'CH572Q', 'Package_DFN_QFN:DFN-10-1EP_3x3mm_P0.5mm_EP1.7x2.5mm',
    'https://www.wch-ic.com/products/CH572.html',
    'WCH CH572Q RISC-V MCU, BLE 5.0 / 2.4 GHz proprietary radio, USB FS, DFN-10 3x3. '
    'Single 5 V supply (4.5-5.3 V) on V5; internal LDO outputs 3.3 V on VDD33.',
    (-20.32, 10.16, 20.32, -10.16),
    [pin('2', 'V5', 'power_in', -22.86, 7.62, 0),
     pin('1', 'VDD33', 'power_out', -22.86, 5.08, 0),
     pin('3', 'PA0/UDM/SWDIO', 'bidirectional', -22.86, 0, 0),
     pin('4', 'PA1/UDP/SWCLK', 'bidirectional', -22.86, -2.54, 0),
     pin('5', 'PA7/PWM1/TMR', 'bidirectional', -22.86, -5.08, 0),
     pin('10', 'ANT', 'bidirectional', 22.86, 7.62, 180),
     pin('9', 'XI', 'input', 22.86, 2.54, 180),
     pin('8', 'XO', 'output', 22.86, 0, 180),
     pin('7', 'PA3/TXD/PWM3', 'bidirectional', 22.86, -2.54, 180),
     pin('6', 'PA2/RXD/PWM2', 'bidirectional', 22.86, -5.08, 180),
     pin('11', 'GND', 'power_in', 0, -12.7, 90)],
    extra=[prop('LCSC', 'C46772607', hide=True), prop('ki_keywords', 'WCH RISC-V BLE 2.4G', hide=True)])

ws2815 = symbol(
    'WS2815B', 'D', 'WS2815B-V1', 'LED_SMD:LED_WS2812_PLCC6_5.0x5.0mm_P1.6mm',
    'https://www.lcsc.com/datasheet/lcsc_datasheet_2012110135_Worldsemi-WS2815B_C965559.pdf',
    'Worldsemi WS2815B 12 V addressable RGB LED, 5050, with backup data input (DIN2)',
    (-7.62, 5.08, 7.62, -5.08),
    [pin('2', 'VDD', 'power_in', 0, 7.62, 270),
     pin('5', 'GND', 'power_in', 0, -7.62, 90),
     pin('4', 'DIN1', 'input', -10.16, 2.54, 0),
     pin('6', 'DIN2', 'input', -10.16, -2.54, 0),
     pin('3', 'DO', 'output', 10.16, 2.54, 180),
     pin('1', 'NC', 'no_connect', 10.16, -2.54, 180)],
    extra=[prop('LCSC', 'C5446699', hide=True), prop('ki_keywords', 'RGB LED addressable WS2815', hide=True)])

lib = [S('kicad_symbol_lib'), [S('version'), 20251024], [S('generator'), 'treeglow_mklib'],
       [S('generator_version'), '10.0'], ch572q, ws2815]
with open(os.path.join(LIB, 'TreeGlow.kicad_sym'), 'w') as f:
    f.write(dump(lib) + '\n')


def u():
    return [S('uuid'), str(uuid.uuid4())]


def fp_text(kind, text, x, y, layer, size=1.0, hide=False):
    t = [S('property') if kind != 'user' else S('fp_text'), *([S('user')] if kind == 'user' else [kind]), text,
         [S('at'), x, y, 0], [S('layer'), layer]]
    if hide:
        t.append([S('hide'), S('yes')])
    t += [u(), [S('effects'), [S('font'), [S('size'), size, size], [S('thickness'), size * 0.15]]]]
    return t


def line(x1, y1, x2, y2, layer, w=0.12):
    return [S('fp_line'), [S('start'), x1, y1], [S('end'), x2, y2],
            [S('stroke'), [S('width'), w], [S('type'), S('solid')]], [S('layer'), layer], u()]


# Pogo / tag pads for programming the CH572 (WCH-LinkE 2-wire SDI) and UART logging.
# Pin order 1-4 equals a USB cable (VBUS, D-, D+, GND) because PA0/PA1 are also the
# CH572 USB pins, so the same pads serve WCH-LinkE and USB-ISP.
labels = ['5V', 'IO', 'CK', 'GND', 'TX']
pitch = 2.54
pads = []
x0 = -pitch * (len(labels) - 1) / 2
for i, lab in enumerate(labels):
    x = x0 + i * pitch
    pads.append([S('pad'), str(i + 1), S('smd'), S('circle') if i else S('rect'), [S('at'), x, 0],
                 [S('size'), 1.6, 1.6], [S('layers'), 'F.Cu', 'F.Mask'], u()])
    pads.append(fp_text('user', lab, x, 2.0, 'F.SilkS', 0.7))
fp = [S('footprint'), 'ProgPads_1x05_P2.54mm',
      [S('version'), 20260206], [S('generator'), 'treeglow_mklib'], [S('generator_version'), '10.0'],
      [S('layer'), 'F.Cu'],
      [S('descr'), 'Programming pads: 5V, PA0/D-/SWDIO, PA1/D+/SWCLK, GND, PA2/TXD_1; 2.54 mm pogo pitch'],
      [S('tags'), 'pogo test pad program CH572'],
      fp_text('Reference', 'REF**', 0, -1.9, 'F.SilkS', 0.8),
      fp_text('Value', 'ProgPads', 0, 3.5, 'F.Fab'),
      [S('attr'), S('smd'), S('exclude_from_pos_files'), S('exclude_from_bom')],
      line(x0 - 1.1, -1.1, -x0 + 1.1, -1.1, 'F.CrtYd', 0.05),
      line(x0 - 1.1, 2.7, -x0 + 1.1, 2.7, 'F.CrtYd', 0.05),
      line(x0 - 1.1, -1.1, x0 - 1.1, 2.7, 'F.CrtYd', 0.05),
      line(-x0 + 1.1, -1.1, -x0 + 1.1, 2.7, 'F.CrtYd', 0.05),
      *pads, [S('embedded_fonts'), S('no')]]
with open(os.path.join(LIB, 'TreeGlow.pretty', 'ProgPads_1x05_P2.54mm.kicad_mod'), 'w') as f:
    f.write(dump(fp) + '\n')
print('ok')
