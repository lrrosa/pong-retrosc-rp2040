#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 RetroSC Pong contributors
"""
Gera kicad/pong-retrosc.kicad_pcb a partir da netlist do esquematico.

Requer o Python DO KICAD (modulo pcbnew):
  1. kicad-cli sch export netlist -o kicad/pong-retrosc.net kicad/pong-retrosc.kicad_sch
  2. "C:/Program Files/KiCad/10.0/bin/python.exe" tools/gen_kicad_pcb.py

Placement (borda de tras = y0, frente = y=BOARD_H):
  - RCAs na borda de tras (corpo para fora da placa);
  - DAC de video colado entre o Pico (GP16/17) e o RCA de video;
  - PAM8403 em pe + cadeia de audio no bloco da direita;
  - headers de painel (pots, START, chave A/B) na borda da frente;
  - zonas de GND nas duas faces (o roteamento fica para o freerouting).
"""

import re
import sys
from pathlib import Path

import pcbnew

REPO = Path(__file__).resolve().parent.parent
NETLIST = REPO / "kicad" / "pong-retrosc.net"
OUT = REPO / "kicad" / "pong-retrosc.kicad_pcb"
FP_LOCAL = REPO / "kicad" / "pong-retrosc.pretty"
FP_SYS = Path(sys.executable).parent.parent / "share" / "kicad" / "footprints"

BOARD_W, BOARD_H = 100.0, 60.0
BX, BY = 20.0, 20.0                       # canto da placa na folha

mm = pcbnew.FromMM


def V(x, y):
    """Coordenada de placa (mm, relativa ao canto) -> VECTOR2I."""
    return pcbnew.VECTOR2I(mm(BX + x), mm(BY + y))


# ---------------------------------------------------------------- netlist
def parse_sexpr(text):
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+', text)
    it = iter(tokens)

    def build():
        out = []
        for t in it:
            if t == "(":
                out.append(build())
            elif t == ")":
                return out
            else:
                out.append(t[1:-1] if t.startswith('"') else t)
        return out

    assert next(it) == "("
    return build()


def find_all(tree, key):
    for node in tree:
        if isinstance(node, list) and node and node[0] == key:
            yield node


def load_netlist():
    tree = parse_sexpr(NETLIST.read_text(encoding="utf-8"))
    comps = {}
    for section in find_all(tree, "components"):
        for c in find_all(section, "comp"):
            ref = fp = val = ""
            for f in c:
                if isinstance(f, list):
                    if f[0] == "ref":
                        ref = f[1]
                    elif f[0] == "footprint" and len(f) > 1:
                        fp = f[1]
                    elif f[0] == "value" and len(f) > 1:
                        val = f[1]
            comps[ref] = (fp, val)
    nets = {}
    for section in find_all(tree, "nets"):
        for n in find_all(section, "net"):
            name = ""
            nodes = []
            for f in n:
                if isinstance(f, list):
                    if f[0] == "name":
                        name = f[1]
                    elif f[0] == "node":
                        d = {g[0]: g[1] for g in f if isinstance(g, list)}
                        nodes.append((d.get("ref"), d.get("pin")))
            name = name.lstrip("/")         # netlist prefixa a folha raiz
            if name and not name.startswith("unconnected-"):
                nets[name] = nodes
    return comps, nets


# ---------------------------------------------------------------- board
def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    for root in (FP_SYS, FP_LOCAL.parent):
        d = root / f"{lib}.pretty"
        if d.exists():
            fp = pcbnew.FootprintLoad(str(d), name)
            if fp:
                return fp
    raise SystemExit(f"ERRO: footprint nao encontrado: {fpid}")


def main():
    comps, nets = load_netlist()
    board = pcbnew.CreateEmptyBoard() if hasattr(pcbnew, "CreateEmptyBoard") \
        else pcbnew.BOARD()

    # ----- placement: ref -> (pad_ancora, x, y, rot) -----
    # pad_ancora = pad que cai exatamente em (x, y). rot em graus.
    #
    # Floorplan (100 x 60, borda de tras = y0):
    #   AUDIO a esquerda | VIDEO a direita -> retornos separados no cobre.
    #   Pico com rot 90: a fileira usada (GP16..VBUS, pinos 21..40) vira
    #   para tras em y=12, pino 21 A DIREITA (x=56) -> GP16/17 colados no
    #   bloco de video; +5V/GND (40/38) a esquerda, colados no amp.
    #   A fileira GP0..15 (nao usada) fica na frente, y=29.78.
    # ATENCAO: o retangulo do Pico (x5..59, y10..32) e corpo de modulo --
    # nada pode ser colocado dentro dele (trilhas por baixo podem).
    # Headers 1xN sao verticais por padrao: rot 270 poe os pinos ao longo
    # de +X.
    PLACE = {
        # ---- borda de tras ----
        "J8": ("1", 12.0, 7.0, 0),          # RCA audio L
        "J9": ("1", 28.0, 7.0, 0),          # RCA audio R
        "C3": ("1", 44.0, 6.0, 0),          # filtro ADC POT1 (perto pino 31)
        "C4": ("1", 52.0, 6.0, 0),          # filtro ADC POT2
        "J1": ("1", 84.0, 7.0, 0),          # RCA video
        # ---- Pico (GP16..VBUS virados p/ tras, pino 21 a direita) ----
        # Corpo ocupa ~x5..59, y11.1..32.6 (courtyard) -- nada dentro.
        "U1": ("21", 56.0, 13.0, 90),
        # ---- video (direita, colado em GP16/17) ----
        "R1": ("1", 62.0, 10.0, 0),         # SYNC -> COMPOSITE
        "R2": ("1", 62.0, 14.0, 0),         # VIDEO -> COMPOSITE
        # ---- cadeia de audio (faixa y34..42, entre o Pico e o amp) ----
        "R3": ("1", 52.0, 37.0, 180),       # AUDIO_PWM -> AUD_F
        "C1": ("1", 38.0, 37.0, 270),       # AUD_F -> GND (shunt desce)
        "C2": ("1", 34.0, 37.0, 180),       # AUD_F -> AUD_C
        "R6": ("1", 26.0, 41.0, 180),       # AUD_C -> AMP_L
        "R7": ("1", 57.0, 40.5, 180),       # AUD_C -> AMP_R
        "R4": ("1", 42.0, 40.5, 270),       # AUD_C -> LINHA (desce)
        "R5": ("1", 46.0, 45.0, 270),       # LINHA -> GND (desce)
        # ---- amp em pe na frente-esquerda, perto de J4 ----
        "U2": ("1", 10.0, 45.0, 0),         # pads x 10..30.3
        # ---- headers de painel na frente (rot 90: pinos p/ +X) ----
        "J4": ("1", 10.0, 55.0, 90),        # chave A/B (6 vias)
        "J5": ("1", 34.0, 55.0, 90),        # pot P1
        "J7": ("1", 51.0, 55.0, 90),        # START
        "J6": ("1", 60.0, 55.0, 90),        # pot P2
    }

    footprints = {}
    for ref, (fpid, val) in sorted(comps.items()):
        if not fpid:
            continue                        # pecas de painel (RV/SW)
        if ref not in PLACE:
            raise SystemExit(f"ERRO: sem posicao para {ref} ({fpid})")
        fp = load_fp(fpid)
        fp.SetReference(ref)
        fp.SetValue(val)
        board.Add(fp)
        pad_anchor, x, y, rot = PLACE[ref]
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(V(0, 0))
        pad = None
        for p in fp.Pads():
            if p.GetNumber() == pad_anchor:
                pad = p
                break
        if pad is None:
            raise SystemExit(f"ERRO: {ref} nao tem pad '{pad_anchor}'")
        fp.Move(V(x, y) - pad.GetPosition())
        footprints[ref] = fp

    # ----- debug de orientacao (para calibrar as rotacoes no fonte) -----
    def show(ref, nums):
        fp = footprints[ref]
        for num in nums:
            for p in fp.Pads():
                if p.GetNumber() == num:
                    pos = p.GetPosition()
                    print(f"{ref} pad {num}: ({pcbnew.ToMM(pos.x)-BX:.2f}, "
                          f"{pcbnew.ToMM(pos.y)-BY:.2f})", flush=True)
                    break

    show("U1", ("1", "21", "22", "24", "31", "32", "33", "36", "38", "40"))
    show("U2", ("1", "9"))
    show("C1", ("2",))
    show("R4", ("2",))
    show("R5", ("2",))
    show("J4", ("1", "6"))
    show("J5", ("1", "3"))

    # ----- nets -----
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    for name, nodes in nets.items():
        for ref, pin in nodes:
            fp = footprints.get(ref)
            if not fp:
                continue                    # peca de painel
            for p in fp.Pads():
                if p.GetNumber() == pin:
                    p.SetNet(netinfo[name])

    # ----- contorno -----
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(V(*pts[i]))
        seg.SetEnd(V(*pts[(i + 1) % 4]))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(mm(0.1))
        board.Add(seg)

    # ----- furos de montagem M3 (cantos livres do floorplan atual) -----
    print("stage: furos", flush=True)
    for i, (hx, hy) in enumerate([(74, 5), (4, 56), (92, 28), (92, 50)]):
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(f"H{i+1}")
        board.Add(fp)
        fp.SetPosition(V(hx, hy))

    # ----- regras (JLCPCB 2 camadas) -----
    bds = board.GetDesignSettings()
    try:
        bds.m_TrackMinWidth = mm(0.2)
        bds.m_ViasMinSize = mm(0.6)
        bds.m_MinClearance = mm(0.2)
    except Exception as e:                  # API varia entre versoes
        print("aviso: regras minimas nao aplicadas:", e)
    try:
        ns = bds.GetNetSettings() if hasattr(bds, "GetNetSettings") \
            else bds.m_NetSettings
        dc = ns.GetDefaultNetclass()
        dc.SetClearance(mm(0.2))
        dc.SetTrackWidth(mm(0.3))
        dc.SetViaDiameter(mm(0.7))
        dc.SetViaDrill(mm(0.35))
        print("netclass Default: 0.3mm/0.2mm, via 0.7/0.35")
    except Exception as e:
        print("aviso: netclass nao aplicada:", e)

    # ----- zonas de GND nas duas faces -----
    print("stage: zonas", flush=True)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(netinfo["GND"])
        outline = z.Outline()
        outline.NewOutline()
        # 0,5 mm para dentro da borda (isolamento cobre-borda)
        for (zx, zy) in [(0.5, 0.5), (BOARD_W - 0.5, 0.5),
                         (BOARD_W - 0.5, BOARD_H - 0.5), (0.5, BOARD_H - 0.5)]:
            outline.Append(mm(BX + zx), mm(BY + zy))
        z.SetMinThickness(mm(0.25))
        for setter, arg in (("SetLocalClearance", mm(0.3)),
                            ("SetPadConnection",
                             getattr(pcbnew, "ZONE_CONNECTION_THERMAL", None))):
            try:
                if arg is not None:
                    getattr(z, setter)(arg)
            except Exception as e:          # API varia entre versoes
                print(f"aviso: zona.{setter}: {e}", flush=True)
        board.Add(z)

    # ----- textos de silk -----
    print("stage: texto", flush=True)
    try:
        t = pcbnew.PCB_TEXT(board)
        t.SetText("RetroSC Pong v1.0")
        t.SetPosition(V(74, 50))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.5), mm(1.5)))
        board.Add(t)
    except Exception as e:
        print("aviso: texto de silk:", e, flush=True)

    # NAO chamar ZONE_FILLER aqui: fora do processo do pcbnew ele crasha
    # (access violation). As zonas ficam sem preencher; o kicad-cli pcb drc
    # e o proprio KiCad ("B") refazem o fill automaticamente.

    print("stage: save", flush=True)
    board.SetFileName(str(OUT))
    pcbnew.SaveBoard(str(OUT), board)
    print(f"OK: {OUT}", flush=True)

    # ----- DSN para o freerouting -----
    dsn = OUT.with_suffix(".dsn")
    ok = False
    try:
        ok = pcbnew.ExportSpecctraDSN(board, str(dsn))
    except TypeError:
        try:
            ok = pcbnew.ExportSpecctraDSN(str(dsn))
        except Exception as e:
            print("aviso: export DSN falhou:", e)
    print(f"DSN: {dsn} -> {'OK' if ok else 'FALHOU'}")


if __name__ == "__main__":
    main()
