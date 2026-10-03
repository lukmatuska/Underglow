"""Tiny KiCad 10 schematic generator.

Every pin is connected by a short wire stub ending in a net label (signals) or a
power symbol (power nets), so a design is described purely as a netlist plus
placement, and ERC verifies that the generated sheet is connected as intended.
"""
import copy
import math
import os
import uuid as _uuid

from sexp import Sym as S, dump, find, findall, parse

HERE = os.path.dirname(os.path.abspath(__file__))
SYSLIB = '/usr/share/kicad/symbols'
LOCAL_LIBS = {'TreeGlow': os.path.join(HERE, '..', 'lib', 'TreeGlow.kicad_sym')}

# net name -> (power lib symbol, True if the symbol body points "up" from its pin)
POWER = {
    'GND': ('power:GND', False),
    '+5V': ('power:+5V', True),
    '+3V3': ('power:+3V3', True),
    '+12V': ('power:+12V', True),
    'VBUS': ('power:VBUS', True),
}
STUB = 2.54


def uid():
    return str(_uuid.uuid4())


def font(size=1.27, justify=None, hide=False, bold=False):
    f = [S('font'), [S('size'), size, size]]
    if bold:
        f.append([S('bold'), S('yes')])
    e = [S('effects'), f]
    if justify:
        e.append([S('justify'), *[S(j) for j in justify.split()]])
    if hide:
        e.append([S('hide'), S('yes')])
    return e


class SymbolLib:
    def __init__(self):
        self._files = {}

    def _lib(self, lib):
        if lib not in self._files:
            path = LOCAL_LIBS.get(lib, os.path.join(SYSLIB, f'{lib}.kicad_sym'))
            tree = parse(open(path).read())
            self._files[lib] = {s[1]: s for s in findall(tree, 'symbol')}
        return self._files[lib]

    def _flat(self, lib, name):
        syms = self._lib(lib)
        node = copy.deepcopy(syms[name])
        ext = find(node, 'extends')
        if not ext:
            return node
        parent = self._flat(lib, ext[1])
        pname = parent[1]
        out = [S('symbol'), name]
        child_props = {p[1]: p for p in findall(node, 'property')}
        for c in parent[2:]:
            if isinstance(c, list) and c[0] == 'property':
                out.append(child_props.pop(c[1], c))
            elif isinstance(c, list) and c[0] == 'symbol':
                c = copy.deepcopy(c)
                c[1] = name + c[1][len(pname):]
                out.append(c)
            else:
                out.append(c)
        # Insert child-only properties before the first sub-symbol.
        idx = next(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == 'symbol')
        out[idx:idx] = list(child_props.values())
        return out

    def get(self, lib_id):
        lib, name = lib_id.split(':', 1)
        node = self._flat(lib, name)
        node[1] = lib_id
        pins, pts = [], []
        for sub in findall(node, 'symbol'):
            unit, style = (int(v) for v in sub[1].rsplit('_', 2)[1:])
            if unit not in (0, 1) or style not in (0, 1):
                continue
            for item in sub[2:]:
                if not isinstance(item, list):
                    continue
                if item[0] == 'pin':
                    at = find(item, 'at')
                    x, y, a = float(at[1]), float(at[2]), float(at[3])
                    pins.append(dict(num=find(item, 'number')[1], name=find(item, 'name')[1],
                                     kind=str(item[1]), x=x, y=y, a=a))
                    pts.append((x, y))
                for key in ('start', 'end', 'xy', 'center'):
                    for sub2 in _walk(item):
                        if sub2[0] == key and len(sub2) >= 3:
                            pts.append((float(sub2[1]), float(sub2[2])))
        xs = [p[0] for p in pts] or [0]
        ys = [p[1] for p in pts] or [0]
        return node, pins, (min(xs), max(xs), min(ys), max(ys))


def _walk(n):
    for c in n:
        if isinstance(c, list):
            yield c
            yield from _walk(c)


def xform(x, y, X, Y, rot):
    """Library coords (y up) -> sheet coords (y down), symbol rotated CCW by rot."""
    r = math.radians(rot)
    yd = -y
    return (X + x * math.cos(r) + yd * math.sin(r), Y - x * math.sin(r) + yd * math.cos(r))


def vec(dx, dy, rot):
    return xform(dx, dy, 0, 0, rot)


def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


class Schematic:
    def __init__(self, project, title, paper='A4', rev='1.0', date='2026-10-03', comments=()):
        self.project = project
        self.uuid = uid()
        self.paper = paper
        self.title = title
        self.rev = rev
        self.date = date
        self.comments = comments
        self.libs = SymbolLib()
        self.lib_symbols = {}
        self.items = []
        self.pwr_n = 0
        self.flg_n = 0
        self.refs = set()

    # ---------------------------------------------------------------- helpers
    def _use(self, lib_id):
        if lib_id not in self.lib_symbols:
            self.lib_symbols[lib_id] = self.libs.get(lib_id)
        return self.lib_symbols[lib_id]

    def _instance(self, lib_id, ref, value, X, Y, rot, props, pins, dnp=False, in_bom=True,
                  ref_at=None, val_at=None, hide_ref=False, hide_val=False, on_board=True):
        node = [S('symbol'), [S('lib_id'), lib_id], [S('at'), X, Y, rot], [S('unit'), 1],
                [S('body_style'), 1], [S('exclude_from_sim'), S('no')],
                [S('in_bom'), S('yes' if in_bom else 'no')], [S('on_board'), S('yes' if on_board else 'no')],
                [S('in_pos_files'), S('yes' if on_board else 'no')], [S('dnp'), S('yes' if dnp else 'no')],
                [S('uuid'), uid()]]
        rx, ry = ref_at or (X, Y - 5)
        vx, vy = val_at or (X, Y + 5)
        node.append([S('property'), 'Reference', ref, [S('at'), rx, ry, 0],
                     font(justify=None, hide=hide_ref)])
        node.append([S('property'), 'Value', value, [S('at'), vx, vy, 0], font(hide=hide_val)])
        for k, v in props.items():
            node.append([S('property'), k, v, [S('at'), X, Y, 0], font(hide=True)])
        for p in sorted({p['num'] for p in pins}):
            node.append([S('pin'), p, [S('uuid'), uid()]])
        node.append([S('instances'), [S('project'), self.project,
                                      [S('path'), '/' + self.uuid, [S('reference'), ref], [S('unit'), 1]]]])
        self.items.append(node)

    def _wire(self, x1, y1, x2, y2):
        self.items.append([S('wire'), [S('pts'), [S('xy'), x1, y1], [S('xy'), x2, y2]],
                           [S('stroke'), [S('width'), 0], [S('type'), S('default')]], [S('uuid'), uid()]])

    def _label(self, net, x, y, ang):
        just = {0: 'left bottom', 90: 'left bottom', 180: 'right bottom', 270: 'right bottom'}[ang]
        self.items.append([S('label'), net, [S('at'), x, y, ang], font(justify=just), [S('uuid'), uid()]])

    def _power(self, net, x, y, out_dir):
        lib_id, up = POWER[net]
        node, pins, _ = self._use(lib_id)
        # out_dir: unit vector (sheet coords) pointing away from the pin.
        dirs = {(0, 1): 'down', (0, -1): 'up', (1, 0): 'right', (-1, 0): 'left'}
        d = dirs[(round(out_dir[0]), round(out_dir[1]))]
        rot = ({'up': 0, 'down': 180, 'left': 90, 'right': 270} if up else
               {'down': 0, 'up': 180, 'right': 90, 'left': 270})[d]
        self.pwr_n += 1
        ref = f'#PWR{self.pwr_n:03d}'
        ty = y - 3.2 if (d == 'up') else y + 3.6
        tx = x
        if d in ('left', 'right'):
            tx, ty = x + (3.5 if d == 'right' else -3.5), y - 1.5
        self._instance(lib_id, ref, net, x, y, rot, {'Footprint': '', 'Datasheet': '', 'Description': ''},
                       pins, in_bom=False, on_board=False, ref_at=(x, y), val_at=(tx, ty), hide_ref=True)

    def _noconnect(self, x, y):
        self.items.append([S('no_connect'), [S('at'), x, y], [S('uuid'), uid()]])

    # -------------------------------------------------------------- public API
    def add(self, lib_id, ref, value, at, nets, footprint='', lcsc='', mpn='', rot=0, dnp=False,
            datasheet='', descr=None, extra=None, in_bom=True, stub=STUB, val_below=True):
        """Place a symbol. nets maps pin number -> net name (None = no-connect)."""
        assert ref not in self.refs, ref
        self.refs.add(ref)
        X, Y = snap(at[0]), snap(at[1])
        node, pins, bbox = self._use(lib_id)
        props = {'Footprint': footprint, 'Datasheet': datasheet or _prop(node, 'Datasheet'),
                 'Description': descr if descr is not None else _prop(node, 'Description')}
        if lcsc:
            props['LCSC'] = lcsc
        if mpn:
            props['MPN'] = mpn
        props.update(extra or {})
        # Field placement around the transformed body bbox.
        corners = [xform(x, y, X, Y, rot) for x in bbox[:2] for y in bbox[2:]]
        top = min(c[1] for c in corners)
        bot = max(c[1] for c in corners)
        right = max(c[0] for c in corners)
        w, h = abs(corners[0][0] - corners[3][0]), abs(corners[0][1] - corners[3][1])
        small = w < 6 and h >= w
        if small:
            ref_at, val_at = (right + 0.6, Y - 0.6), (right + 0.6, Y + 1.6)
        else:
            ref_at, val_at = (X, top - 1.6), (X + 1.8, bot + 1.2)
        self._instance(lib_id, ref, value, X, Y, rot, props, pins, dnp=dnp, in_bom=in_bom,
                       ref_at=ref_at, val_at=val_at)
        fields = findall(self.items[-1], 'property')[:2]
        for p in (fields if small else fields[1:]):  # left-justify so text clears the pin stubs
            p[4].append([S('justify'), S('left')])
        seen = set()
        ends = {}
        for p in pins:
            px, py = xform(p['x'], p['y'], X, Y, rot)
            a = math.radians(p['a'])
            ox, oy = (round(v) for v in vec(-math.cos(a), -math.sin(a), rot))
            ends[(round(px + ox * stub, 4), round(py + oy * stub, 4))] = nets.get(p['num'])
        missing = {p['num'] for p in pins} - set(nets)
        assert not missing, f'{ref}: unassigned pins {sorted(missing)}'
        for p in pins:
            net = nets[p['num']]
            px, py = xform(p['x'], p['y'], X, Y, rot)
            px, py = round(px, 4), round(py, 4)
            if (px, py) in seen:
                continue
            seen.add((px, py))
            if net is None:
                self._noconnect(px, py)
                continue
            a = math.radians(p['a'])
            ox, oy = vec(-math.cos(a), -math.sin(a), rot)
            ox, oy = round(ox), round(oy)
            ex, ey = round(px + ox * stub, 4), round(py + oy * stub, 4)
            self._wire(px, py, ex, ey)
            if net in POWER and ox != 0:
                # Horizontal pin: drop vertically so the power symbol stands upright.
                up = POWER[net][1]
                dy = -stub if up else stub
                hit = ends.get((ex, round(ey + dy, 4)), net)
                if hit != net:  # would land on another net's stub: go further out first
                    nx = round(ex + ox * stub, 4)
                    self._wire(ex, ey, nx, ey)
                    ex = nx
                self._wire(ex, ey, ex, round(ey + dy, 4))
                if ends.get((ex, round(ey + dy, 4))) != net:
                    self._power(net, ex, round(ey + dy, 4), (0, -1 if up else 1))
            elif net in POWER:
                self._power(net, ex, ey, (ox, oy))
            else:
                ang = {(1, 0): 0, (0, -1): 90, (-1, 0): 180, (0, 1): 270}[(ox, oy)]
                self._label(net, ex, ey, ang)

    def flag(self, net, at):
        """PWR_FLAG on a net (tells ERC the net is driven by a connector/diode)."""
        self.flg_n += 1
        ref = f'#FLG{self.flg_n:02d}'
        X, Y = snap(at[0]), snap(at[1])
        node, pins, _ = self._use('power:PWR_FLAG')
        self._instance('power:PWR_FLAG', ref, 'PWR_FLAG', X, Y, 0,
                       {'Footprint': '', 'Datasheet': '', 'Description': ''}, pins,
                       in_bom=False, on_board=False, ref_at=(X, Y - 5), val_at=(X, Y - 4), hide_ref=True)
        self.refs.add(ref)
        self._wire(X, Y, X, Y + STUB)
        if net in POWER:
            self._power(net, X, Y + STUB, (0, 1))
        else:
            self._label(net, X, Y + STUB, 270)

    def text(self, s, at, size=1.27, bold=False):
        self.items.append([S('text'), s, [S('exclude_from_sim'), S('no')], [S('at'), at[0], at[1], 0],
                           font(size, 'left top', bold=bold), [S('uuid'), uid()]])

    def box(self, x1, y1, x2, y2, title=None):
        self.items.append([S('rectangle'), [S('start'), x1, y1], [S('end'), x2, y2],
                           [S('stroke'), [S('width'), 0.2], [S('type'), S('dash')]],
                           [S('fill'), [S('type'), S('none')]], [S('uuid'), uid()]])
        if title:
            self.text(title, (x1 + 1.5, y1 + 1.5), 2.0, bold=True)

    def save(self, path):
        tb = [S('title_block'), [S('title'), self.title], [S('date'), self.date], [S('rev'), self.rev]]
        for i, c in enumerate(self.comments, 1):
            tb.append([S('comment'), i, c])
        root = [S('kicad_sch'), [S('version'), 20260306], [S('generator'), 'eeschema'],
                [S('generator_version'), '10.0'], [S('uuid'), self.uuid], [S('paper'), self.paper], tb,
                [S('lib_symbols'), *[v[0] for v in self.lib_symbols.values()]],
                *self.items,
                [S('sheet_instances'), [S('path'), '/', [S('page'), '1']]],
                [S('embedded_fonts'), S('no')]]
        with open(path, 'w') as f:
            f.write(dump(root) + '\n')


def _prop(node, name):
    for p in findall(node, 'property'):
        if p[1] == name:
            return p[2]
    return ''


def write_lib_tables(project_dir):
    with open(os.path.join(project_dir, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n\t(version 7)\n\t(lib (name "TreeGlow") (type "KiCad") '
                '(uri "${KIPRJMOD}/../lib/TreeGlow.kicad_sym") (options "") (descr "TreeGlow project symbols"))\n)\n')
    with open(os.path.join(project_dir, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n\t(version 7)\n\t(lib (name "TreeGlow") (type "KiCad") '
                '(uri "${KIPRJMOD}/../lib/TreeGlow.pretty") (options "") (descr "TreeGlow project footprints"))\n)\n')
