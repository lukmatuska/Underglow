"""Build a KiCad board from a schematic netlist plus a placement table.

Flow: kicad-cli netlist -> footprints placed/netted with pcbnew -> optional
hand-routed tracks -> Freerouting (Specctra DSN/SES) -> zones filled -> saved.
"""
import json
import os
import shutil
import subprocess
import sys

import pcbnew

from sexp import find, findall, parse

HERE = os.path.dirname(os.path.abspath(__file__))
SYSFP = '/usr/share/kicad/footprints'
LOCALFP = {'TreeGlow': os.path.join(HERE, '..', 'lib', 'TreeGlow.pretty')}
FREEROUTING = os.environ.get('FREEROUTING_JAR', os.path.join(HERE, 'freerouting.jar'))
OX, OY = 100.0, 100.0  # board origin on the page


def mm(v):
    return pcbnew.FromMM(v)


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def read_netlist(sch):
    tmp = sch + '.net.tmp'
    subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', tmp, sch],
                   check=True, capture_output=True)
    t = parse(open(tmp).read())
    os.remove(tmp)
    comps = {}
    for c in findall(find(t, 'components'), 'comp'):
        ref = find(c, 'ref')[1]
        fields = {f[1][1] if isinstance(f[1], list) else '': f[2] if len(f) > 2 else ''
                  for f in findall(find(c, 'fields') or [], 'field')}
        props = {p_[1][1]: (p_[2][1] if len(p_) > 2 else '') for p_ in findall(c, 'property')}
        comps[ref] = dict(ref=ref, value=find(c, 'value')[1], footprint=find(c, 'footprint')[1],
                          uuid=find(c, 'tstamps')[1], fields=fields, props=props)
    pinnet = {}
    for n in findall(find(t, 'nets'), 'net'):
        name = find(n, 'name')[1]
        for node in findall(n, 'node'):
            pinnet[(find(node, 'ref')[1], find(node, 'pin')[1])] = name
    return comps, pinnet


def load_fp(fpid):
    lib, name = fpid.split(':', 1)
    path = LOCALFP.get(lib, os.path.join(SYSFP, f'{lib}.pretty'))
    fp = pcbnew.FootprintLoad(path, name)
    assert fp, fpid
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


class Board:
    def __init__(self, path, sch):
        self.path = path
        self.board = pcbnew.NewBoard(path)
        self.board.SetCopperLayerCount(2)
        self.comps, self.pinnet = read_netlist(sch)
        self.nets = {}
        self.fps = {}
        self.sheetfile = os.path.basename(sch)
        for name in sorted(set(self.pinnet.values())):
            ni = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(ni)
            self.nets[name] = ni

    def net(self, name):
        return self.nets[name] if name in self.nets else self.nets['/' + name]

    def netname(self, name):
        return self.net(name).GetNetname()

    # ------------------------------------------------------------ placement
    def place(self, ref, x, y, rot=0, back=False):
        c = self.comps[ref]
        fp = load_fp(c['footprint'])
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['uuid']))
        fp.SetSheetname('/')
        fp.SetSheetfile(self.sheetfile)
        ds_ = c['fields'].get('Datasheet', '')
        if ds_:
            fp.GetField('Datasheet').SetText(ds_)
        de = c['fields'].get('Description', '')
        if de:
            fp.GetField('Description').SetText(de)
        for k in ('LCSC', 'MPN', 'Side'):
            v = c['fields'].get(k) or c['props'].get(k)
            if v:
                fp.SetField(k, v)
                f = fp.GetField(k)
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        if 'dnp' in c['props']:
            fp.SetDNP(True)
        if 'exclude_from_bom' in c['props']:
            fp.SetExcludedFromBOM(True)
        self.board.Add(fp)
        fp.SetPosition(P(x, y))
        fp.SetOrientationDegrees(rot)
        if back:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in fp.Pads():
            net = self.pinnet.get((ref, pad.GetNumber()))
            if net:
                pad.SetNet(self.nets[net])
        # Small, uncluttered silkscreen references.
        r = fp.Reference()
        r.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
        r.SetTextThickness(mm(0.1))
        fp.Value().SetVisible(False)
        fab_ref = (any(k in c['footprint'] for k in ('0402', 'ProgPads', 'MountingHole', 'SolderWire', 'TestPoint'))
                   or ref.rstrip('0123456789') in ('R', 'C', 'F', 'H', 'SW', 'J', 'U', 'D')
                   and not c['footprint'].startswith(('Package_DFN', 'RF_Module', 'LED_SMD:LED_WS')))
        if fab_ref:
            r.SetLayer(pcbnew.B_Fab if back else pcbnew.F_Fab)
        self.fps[ref] = fp
        return fp

    def ref_at(self, ref, dx, dy, rot=None):
        """Move a footprint's silkscreen reference relative to the footprint origin."""
        fp = self.fps[ref]
        t = fp.Reference()
        t.SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(mm(dx), mm(dy)))
        if rot is not None:
            t.SetTextAngleDegrees(rot)

    def pad_xy(self, ref, num):
        for pad in self.fps[ref].Pads():
            if pad.GetNumber() == num:
                p = pad.GetPosition()
                return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY
        raise KeyError((ref, num))

    def check_placed(self):
        missing = set(self.comps) - set(self.fps)
        assert not missing, f'not placed: {sorted(missing)}'

    # -------------------------------------------------------------- copper
    def track(self, net, pts, w=0.3, layer=pcbnew.F_Cu, locked=True):
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(P(x1, y1))
            t.SetEnd(P(x2, y2))
            t.SetWidth(mm(w))
            t.SetLayer(layer)
            t.SetNet(self.net(net))
            t.SetLocked(locked)
            self.board.Add(t)

    def via(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(P(x, y))
        v.SetWidth(mm(d))
        v.SetDrill(mm(drill))
        v.SetNet(self.net(net))
        self.board.Add(v)

    def outline(self, pts=None, w=None, h=None, r=1.0):
        if pts is None:
            pts = [(0, 0), (w, 0), (w, h), (0, h)]
        if r and w is not None:
            self._rounded_rect(w, h, r)
            return
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(x1, y1))
            s.SetEnd(P(x2, y2))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            self.board.Add(s)

    def _rounded_rect(self, w, h, r):
        segs = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)), ((w - r, h), (r, h)), ((0, h - r), (0, r))]
        for a, b in segs:
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a))
            s.SetEnd(P(*b))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            self.board.Add(s)
        import math
        k = r * (1 - math.sqrt(0.5))
        for st, mid, en in [((0, r), (k, k), (r, 0)), ((w - r, 0), (w - k, k), (w, r)),
                            ((w, h - r), (w - k, h - k), (w - r, h)), ((r, h), (k, h - k), (0, h - r))]:
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetArcGeometry(P(*st), P(*mid), P(*en))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            self.board.Add(s)

    def slot_hole(self, x, y, w, h):
        """Non-plated rounded slot / cut-out (e.g. zip tie)."""
        r = min(w, h) / 2
        # drawn as a closed oval on Edge.Cuts
        if h >= w:
            pts = [((x - r, y - h / 2 + r), (x - r, y + h / 2 - r)), ((x + r, y + h / 2 - r), (x + r, y - h / 2 + r))]
            arcs = [((x, y - h / 2 + r), (x + r, y - h / 2 + r)), ((x, y + h / 2 - r), (x - r, y + h / 2 - r))]
        else:
            pts = [((x - w / 2 + r, y - r), (x + w / 2 - r, y - r)), ((x + w / 2 - r, y + r), (x - w / 2 + r, y + r))]
            arcs = [((x + w / 2 - r, y), (x + w / 2 - r, y - r)), ((x - w / 2 + r, y), (x - w / 2 + r, y + r))]
        for a, b in pts:
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(P(*a))
            s.SetEnd(P(*b))
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            self.board.Add(s)
        for c, st in arcs:
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetCenter(P(*c))
            s.SetStart(P(*st))
            s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(-180, pcbnew.DEGREES_T), True)
            s.SetLayer(pcbnew.Edge_Cuts)
            s.SetWidth(mm(0.1))
            self.board.Add(s)

    def _poly(self, pts):
        chain = pcbnew.SHAPE_LINE_CHAIN()
        for x, y in pts:
            chain.Append(P(x, y))
        chain.SetClosed(True)
        return chain

    def zone(self, net, pts, layers=(pcbnew.F_Cu, pcbnew.B_Cu), priority=0, clearance=0.25,
             min_w=0.2, thermal_gap=0.3, spoke=0.4, solid_pads=False, name=''):
        for layer in layers:
            z = pcbnew.ZONE(self.board)
            z.SetLayer(layer)
            z.SetNet(self.net(net))
            z.Outline().AddOutline(self._poly(pts))
            z.SetAssignedPriority(priority)
            z.SetLocalClearance(mm(clearance))
            z.SetMinThickness(mm(min_w))
            z.SetThermalReliefGap(mm(thermal_gap))
            z.SetThermalReliefSpokeWidth(mm(spoke))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid_pads else pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            if name:
                z.SetZoneName(name)
            self.board.Add(z)

    def keepout(self, pts, layers=(pcbnew.F_Cu, pcbnew.B_Cu), name='keepout', footprints=True):
        for layer in layers:
            z = pcbnew.ZONE(self.board)
            z.SetIsRuleArea(True)
            z.SetLayer(layer)
            z.Outline().AddOutline(self._poly(pts))
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(True)
            z.SetDoNotAllowZoneFills(True)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowFootprints(not footprints)
            z.SetZoneName(name)
            self.board.Add(z)

    def text(self, s, x, y, size=1.0, layer=pcbnew.F_SilkS, rot=0, bold=False):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(P(x, y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
        t.SetTextAngleDegrees(rot)
        if layer in (pcbnew.B_SilkS, pcbnew.B_Cu, pcbnew.B_Mask):
            t.SetMirrored(True)
        self.board.Add(t)

    # ---------------------------------------------------------- net classes
    def netclass(self, name, nets, width, clearance=0.2, via=0.6, drill=0.3):
        ns = self.board.GetDesignSettings().m_NetSettings
        nc = pcbnew.NETCLASS(name)
        nc.SetTrackWidth(mm(width))
        nc.SetClearance(mm(clearance))
        nc.SetViaDiameter(mm(via))
        nc.SetViaDrill(mm(drill))
        ns.SetNetclass(name, nc)
        nets = [self.netname(n) for n in nets]
        for n in nets:
            ns.SetNetclassPatternAssignment(n, name)
        self.classes = getattr(self, 'classes', [])
        self.classes.append((name, nets, width, clearance, via, drill))

    def defaults(self, track=0.25, clearance=0.2, via=0.6, drill=0.3):
        ds = self.board.GetDesignSettings()
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetTrackWidth(mm(track))
        nc.SetClearance(mm(clearance))
        nc.SetViaDiameter(mm(via))
        nc.SetViaDrill(mm(drill))
        ds.m_MinClearance = mm(0.15)
        ds.m_CopperEdgeClearance = mm(0.3)
        ds.m_HoleClearance = mm(0.25)
        ds.m_TrackMinWidth = mm(0.15)
        self.default_class = (track, clearance, via, drill)

    # -------------------------------------------------------------- routing
    def autoroute(self, passes=40, ignore_classes=()):
        base = os.path.splitext(self.path)[0]
        dsn, ses = base + '.dsn', base + '.ses'
        assert pcbnew.ExportSpecctraDSN(self.board, dsn), 'DSN export failed'
        cmd = ['java', '-jar', FREEROUTING, '-de', dsn, '-do', ses, '-mp', str(passes),
               '--gui.enabled=false']
        if ignore_classes:
            cmd += ['-inc', ','.join(ignore_classes)]
        print('running', ' '.join(cmd))
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        log = base + '.freerouting.log'
        open(log, 'w').write(r.stdout + r.stderr)
        for line in (r.stdout + r.stderr).splitlines():
            if 'unrouted' in line and 'completed' in line:
                last = line
        print((locals().get('last') or 'no summary')[-120:])
        assert os.path.exists(ses), 'freerouting produced no SES'
        assert pcbnew.ImportSpecctraSES(self.board, ses), 'SES import failed'
        os.remove(dsn)
        os.remove(ses)

    def fill(self):
        pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones())

    def refill(self):
        """Reload from disk so the project's rules apply, then pour zones and save."""
        board = pcbnew.LoadBoard(self.path)
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(self.path, board)
        self.board = board

    def save(self):
        self.board.BuildConnectivity()
        pcbnew.SaveBoard(self.path, self.board)
        self._write_rules()

    def _write_rules(self):
        """Mirror rules and net classes into the .kicad_pro (DRC reads them from there)."""
        pro = os.path.splitext(self.path)[0] + '.kicad_pro'
        d = json.load(open(pro)) if os.path.exists(pro) else {}
        bd = d.setdefault('board', {}).setdefault('design_settings', {})
        rules = bd.setdefault('rules', {})
        rules.update({'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.5,
                      'min_through_hole_diameter': 0.3, 'min_via_annular_width': 0.1,
                      'min_copper_edge_clearance': 0.3, 'min_hole_clearance': 0.25,
                      'min_hole_to_hole': 0.25, 'min_text_height': 0.6, 'min_text_thickness': 0.08,
                      'min_silk_clearance': 0.0, 'min_resolved_spokes': 1})
        track, clr, via, drill = self.default_class
        classes = [dict(name='Default', clearance=clr, track_width=track, via_diameter=via, via_drill=drill,
                        microvia_diameter=0.3, microvia_drill=0.1, diff_pair_width=0.2, diff_pair_gap=0.25,
                        diff_pair_via_gap=0.25, wire_width=6, bus_width=12, line_style=0,
                        pcb_color='rgba(0, 0, 0, 0.000)', schematic_color='rgba(0, 0, 0, 0.000)',
                        priority=2147483647)]
        pats = []
        for i, (name, nets, w, c, v, dr) in enumerate(getattr(self, 'classes', [])):
            classes.append(dict(classes[0], name=name, clearance=c, track_width=w, via_diameter=v,
                                via_drill=dr, priority=i))
            pats += [dict(netclass=name, pattern=n) for n in nets]
        ns = d.setdefault('net_settings', {})
        ns['classes'] = classes
        ns['netclass_patterns'] = pats
        ns.setdefault('meta', {'version': 4})
        d.setdefault('meta', {'filename': os.path.basename(pro), 'version': 3})
        json.dump(d, open(pro, 'w'), indent=2)


def drc(pcb):
    rpt = os.path.splitext(pcb)[0] + '-drc.json'
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--format', 'json', '--schematic-parity',
                    '--severity-error', '--severity-warning', '-o', rpt, pcb], capture_output=True)
    d = json.load(open(rpt))
    os.remove(rpt)
    out = []
    for key in ('violations', 'unconnected_items', 'schematic_parity'):
        for v in d.get(key, []):
            items = '; '.join(i['description'] for i in v.get('items', []))
            out.append(f"[{v['severity']}] {v['type']}: {v['description']} :: {items}")
    return out
