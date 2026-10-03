"""TreeGlow master board schematic -> HW/Underglow-master/Underglow-master.kicad_sch"""
import os

from kigen import Schematic, write_lib_tables
from parts import *

OUT = os.path.join(os.path.dirname(__file__), '..', 'Underglow-master')
os.makedirs(OUT, exist_ok=True)

s = Schematic('Underglow-master', 'TreeGlow master (ESP32-C3 + CH572Q 2.4 GHz bridge)', paper='A3', rev='1.0',
              comments=('Wi-Fi/USB controller that broadcasts frames to all TreeGlow nodes',
                        'ESP32-C3 <-UART-> CH572Q radio; 12 V or USB-C powered; local WS281x output'))


def passive(kind, ref, key, at, n1, n2, fp=C0402, dnp=False):
    val, lcsc = part(key) if key else ('DNP', '')
    lib = {'R': 'Device:R_Small', 'C': 'Device:C_Small', 'L': 'Device:L_Small'}[kind]
    s.add(lib, ref, val, at, {'1': n1, '2': n2}, footprint=fp, lcsc=lcsc, dnp=dnp)


# ================================================================ 12 V in + buck
s.box(12, 18, 205, 108, 'POWER IN: 12 V, protection, 5 V buck (TPS54202)')
v, l = part('TERM2')
s.add('Connector_Generic:Conn_01x02', 'J1', '12V IN', (30, 55), {'1': 'VIN_RAW', '2': 'GND'},
      footprint='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', lcsc=l,
      mpn=v, descr='Screw terminal, 12 V from the tree power supply')
s.flag('VIN_RAW', (36, 32))
s.flag('GND', (36, 85))
s.flag('V12', (100, 32))
s.flag('+5V', (190, 32))
v, l = part('PTC500')
s.add('Device:Polyfuse_Small', 'F1', v, (48, 45), {'1': 'VIN_RAW', '2': 'VIN_F'}, footprint='Fuse:Fuse_1206_3216Metric',
      lcsc=l, descr='500 mA resettable fuse; trips if the input is reversed (TVS conducts)')
v, l = part('SMAJ15A')
s.add('Device:D_Zener_Small', 'D1', v, (60, 60), {'1': 'VIN_F', '2': 'GND'}, footprint=SMA, lcsc=l,
      descr='15 V TVS on the input')
v, l = part('B5819W')
s.add('Device:D_Schottky_Small', 'D2', v, (74, 45), {'1': 'V12', '2': 'VIN_F'}, rot=180, footprint=SOD123, lcsc=l)
passive('C', 'C1', 'C_10u_0805', (84, 60), 'V12', 'GND', fp=C0805)
passive('C', 'C2', 'C_10u_0805', (96, 60), 'V12', 'GND', fp=C0805)
passive('C', 'C3', 'C_100n', (108, 60), 'V12', 'GND')
passive('R', 'R1', 'R_100k', (118, 70), 'V12', 'EN_BUCK')
passive('R', 'R2', 'R_22k', (118, 96), 'EN_BUCK', 'GND')
v, l = part('TPS54202')
s.add('Regulator_Switching:TPS54202DDC', 'U1', v, (140, 60),
      {'1': 'GND', '2': 'SW', '3': 'V12', '4': 'FB', '5': 'EN_BUCK', '6': 'BUCK_BST'}, footprint=SOT23_6, lcsc=l)
passive('C', 'C4', 'C_100n', (162, 40), 'BUCK_BST', 'SW')
v, l = part('L_10u')
s.add('Device:L_Small', 'L1', v, (170, 60), {'1': 'SW', '2': '+5V'}, footprint='Inductor_SMD:L_Changjiang_FXL0630',
      lcsc=l)
passive('R', 'R3', 'R_75k', (178, 70), '+5V', 'FB')
passive('R', 'R4', 'R_10k', (178, 88), 'FB', 'GND')
passive('C', 'C5', 'C_22u_0805', (185, 60), '+5V', 'GND', fp=C0805)
passive('C', 'C6', 'C_22u_0805', (199, 60), '+5V', 'GND', fp=C0805)
s.text('Vout = 0.596 V x (1 + 75k/10k) = 5.07 V\n'
       'EN divider: starts above ~6.8 V input\n'
       'Load: ESP32-C3 peaks ~350 mA @3.3 V + CH572', (126, 92))

# ================================================================ USB-C + power path
s.box(209, 18, 330, 108, 'USB-C (power + ESP32 native USB), power path')
v, l = part('USBC')
s.add('Connector:USB_C_Receptacle_USB2.0_16P', 'J2', 'USB-C', (232, 60),
      {'A1': 'GND', 'A12': 'GND', 'B1': 'GND', 'B12': 'GND', 'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS',
       'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_DP', 'B6': 'USB_DP', 'A7': 'USB_DN', 'B7': 'USB_DN',
       'A8': None, 'B8': None, 'SH': 'GND'},
      footprint='Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12', lcsc=l, mpn=v)
s.flag('VBUS', (262, 32))
passive('R', 'R5', 'R_5k1', (262, 88), 'CC1', 'GND')
passive('R', 'R6', 'R_5k1', (270, 88), 'CC2', 'GND')
v, l = part('USBLC6')
s.add('Power_Protection:USBLC6-2SC6', 'U2', v, (292, 60),
      {'1': 'USB_DP', '6': 'USB_DP', '3': 'USB_DN', '4': 'USB_DN', '2': 'GND', '5': 'VBUS'}, footprint=SOT23_6,
      lcsc=l)
v, l = part('AO3401')
s.add('Transistor_FET:AO3401A', 'Q1', v, (312, 84), {'1': 'USB_GATE', '2': '+5V', '3': 'VBUS'}, footprint=SOT23,
      lcsc=l, descr='USB -> +5V switch; turned off by the 12 V input so the buck has priority')
passive('R', 'R7', 'R_10k', (286, 82), 'VIN_F', 'USB_GATE')
passive('R', 'R8', 'R_100k', (286, 98), 'USB_GATE', 'GND')
s.text('12 V present: gate ~11 V > source 5 V -> Q1 off.\n'
       '12 V absent: gate 0 V -> Q1 on, USB feeds +5V\n'
       '(~50 mV drop instead of a diode\'s 0.35 V; the\n'
       'CH572Q needs at least 4.5 V).', (212, 96))

# ================================================================ 3.3 V
s.box(334, 18, 408, 108, '3.3 V LDO')
v, l = part('ME6211')
s.add('Regulator_Linear:AP2112K-3.3', 'U3', v, (366, 56), {'1': '+5V', '2': 'GND', '3': '+5V', '4': None, '5': '+3V3'},
      footprint=SOT23_5, lcsc=l, descr='ME6211C33 500 mA LDO (AP2112K-compatible pinout)')
passive('C', 'C7', 'C_1u', (346, 72), '+5V', 'GND')
passive('C', 'C8', 'C_10u_0603', (380, 72), '+3V3', 'GND', fp=C0603)
passive('C', 'C9', 'C_100n', (394, 72), '+3V3', 'GND')

# ================================================================ ESP32-C3
s.box(12, 112, 205, 206, 'ESP32-C3 controller (Wi-Fi / USB / app)')
v, l = part('ESP32C3')
s.add('RF_Module:ESP32-C3-WROOM-02', 'U4', v, (100, 158),
      {'1': '+3V3', '2': 'ESP_EN', '3': 'UART_E2C', '4': 'UART_C2E', '5': 'CH_CTRL', '6': 'LED_OUT_3V3',
       '7': 'IO8', '8': 'BOOT', '9': 'GND', '10': 'STATUS_LED', '11': 'U0RXD', '12': 'U0TXD',
       '13': 'USB_DN', '14': 'USB_DP', '15': 'EXP_IO3', '16': 'IO2', '17': 'EXP_IO1', '18': 'EXP_IO0', '19': 'GND'},
      footprint='RF_Module:ESP32-C3-WROOM-02', lcsc=l, mpn=v)
passive('R', 'R9', 'R_10k', (24, 128), '+3V3', 'ESP_EN')
passive('C', 'C10', 'C_1u', (24, 146), 'ESP_EN', 'GND')
v, l = part('BTN')
s.add('Switch:SW_Push', 'SW1', 'RESET', (40, 160), {'1': 'ESP_EN', '2': 'GND'},
      footprint='Button_Switch_SMD:SW_SPST_TL3342', lcsc=l)
s.add('Switch:SW_Push', 'SW2', 'BOOT', (40, 180), {'1': 'BOOT', '2': 'GND'},
      footprint='Button_Switch_SMD:SW_SPST_TL3342', lcsc=l)
passive('R', 'R10', 'R_10k', (32, 128), '+3V3', 'BOOT')
passive('R', 'R11', 'R_10k', (40, 128), '+3V3', 'IO2')
passive('R', 'R12', 'R_10k', (48, 128), '+3V3', 'IO8')
passive('C', 'C11', 'C_10u_0603', (130, 126), '+3V3', 'GND', fp=C0603)
passive('C', 'C12', 'C_100n', (144, 126), '+3V3', 'GND')
passive('R', 'R13', 'R_1k', (150, 176), 'STATUS_LED', 'LED_A')
v, l = part('LED_G')
s.add('Device:LED_Small', 'D3', 'STATUS ' + v, (156, 192), {'1': 'GND', '2': 'LED_A'}, rot=0, footprint=LED0603,
      lcsc=l)
passive('R', 'R14', 'R_1k', (176, 176), '+3V3', 'PWR_LED_A')
s.add('Device:LED_Small', 'D4', 'POWER ' + v, (182, 192), {'1': 'GND', '2': 'PWR_LED_A'}, rot=0, footprint=LED0603,
      lcsc=l)
v, l = part('HDR4')
s.add('Connector_Generic:Conn_01x08', 'J3', 'EXP', (178, 140),
      {'1': '+3V3', '2': 'GND', '3': 'EXP_IO0', '4': 'EXP_IO1', '5': 'EXP_IO3', '6': 'U0TXD', '7': 'U0RXD', '8': '+5V'},
      footprint='Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical', in_bom=False,
      descr='Expansion: I2C display / buttons / sensors, UART0')
s.text('Strapping: IO9 (BOOT) and IO8 pulled up, IO2 pulled up.\n'
       'Programming/console over native USB (IO18/IO19).', (16, 194))

# ================================================================ CH572 radio
s.box(209, 112, 408, 206, 'CH572Q 2.4 GHz radio (broadcasts to nodes)')
v, l = part('CH572Q')
s.add('TreeGlow:CH572Q', 'U6', v, (270, 152),
      {'2': '+5V', '1': 'CH_VDD33', '3': 'CH_SWDIO', '4': 'CH_SWCLK', '5': 'CH_CTRL',
       '10': 'CH_RF', '9': 'CH_XI', '8': 'CH_XO', '7': 'UART_C2E', '6': 'UART_E2C', '11': 'GND'},
      footprint=DFN10, lcsc=l)
passive('C', 'C14', 'C_1u', (222, 128), '+5V', 'GND')
passive('R', 'R17', 'R_1k5', (230, 128), '+5V', 'CH_VDD33')
passive('C', 'C15', 'C_2u2', (238, 128), 'CH_VDD33', 'GND')
passive('C', 'C16', 'C_100n', (246, 128), 'CH_VDD33', 'GND')
v, l = part('XTAL32M')
s.add('Device:Crystal_GND24_Small', 'Y1', v, (316, 186), {'1': 'CH_XI', '3': 'CH_XO', '2': 'GND', '4': 'GND'},
      footprint=XTAL3225, lcsc=l)
passive('C', 'C17', None, (318, 136), 'CH_RF', 'GND', dnp=True)
passive('R', 'R18', 'R_0', (330, 136), 'CH_RF', 'CH_RF2')
passive('C', 'C18', None, (342, 136), 'CH_RF2', 'GND', dnp=True)
passive('R', 'R19', 'R_0', (356, 136), 'CH_RF2', 'RF_PCB')
passive('R', 'R20', None, (356, 160), 'CH_RF2', 'RF_UFL', dnp=True)
s.add('Device:Antenna_Shield', 'AE1', 'PCB IFA', (378, 132), {'1': 'RF_PCB', '2': 'GND'},
      footprint=ANT_FP, in_bom=False, descr='TI SWRA117D 2.4 GHz inverted-F PCB antenna')
v, l = part('UFL')
s.add('Connector:Conn_Coaxial', 'J5', 'U.FL', (386, 162), {'1': 'RF_UFL', '2': 'GND'}, footprint=UFL, lcsc=l,
      dnp=True, descr='Optional external antenna (fit R20 instead of R19)')
s.add('Connector_Generic:Conn_01x04', 'J6', 'CH572 SWD', (232, 186),
      {'1': '+5V', '2': 'CH_SWDIO', '3': 'CH_SWCLK', '4': 'GND'},
      footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical', in_bom=False,
      descr='WCH-LinkE (2-wire SDI) / USB-ISP (5V, D-, D+, GND)')
s.text('UART: ESP32 IO4 -> CH572 PA2 (RXD), CH572 PA3 (TXD) -> ESP32 IO5.\n'
       'CH_CTRL (ESP32 IO6 -> PA7): reset (RST_ remap) or flow control.\n'
       'Antenna: R19 fitted = PCB antenna; or R20 + J5 for an external\n'
       'whip on the top of the tree (better range through branches).', (290, 172))

# ================================================================ LED out
s.box(12, 210, 205, 270, 'Local WS281x output (tree-top star / test strip)')
v, l = part('AHCT125')
s.add('74xGxx:74AHCT1G125', 'U5', v, (80, 240),
      {'1': 'GND', '2': 'LED_OUT_3V3', '3': 'GND', '4': 'LED_OUT_5V', '5': '+5V'}, footprint=SOT23_5, lcsc=l)
passive('R', 'R16', 'R_10k', (54, 252), 'LED_OUT_3V3', 'GND')
passive('C', 'C13', 'C_100n', (100, 222), '+5V', 'GND')
passive('R', 'R15', 'R_33', (114, 246), 'LED_OUT_5V', 'LED_DATA')
v, l = part('TERM2')
s.add('Connector_Generic:Conn_01x02', 'J4', 'LED OUT', (150, 240), {'1': 'LED_DATA', '2': 'GND'},
      footprint='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal', lcsc=l,
      mpn=v)
s.text('3.3 V -> 5 V level shift. R16 keeps the strip dark while the ESP32 boots.\n'
       'Power the strip straight from the 12 V supply, only DATA/GND come from here.', (16, 260))

s.box(209, 210, 285, 240, 'Mounting')
for i in range(4):
    s.add('Mechanical:MountingHole', f'H{i + 1}', 'M3', (222 + i * 16, 226), {},
          footprint='MountingHole:MountingHole_3.2mm_M3', in_bom=False)

s.save(os.path.join(OUT, 'Underglow-master.kicad_sch'))
write_lib_tables(OUT)
print('master schematic written')
