#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 RetroSC Pong contributors
"""
Gera kicad/pong-retrosc.kicad_pcb a partir da netlist do esquematico.

Requer o Python DO KICAD (modulo pcbnew):
  1. kicad-cli sch export netlist -o kicad/pong-retrosc.net kicad/pong-retrosc.kicad_sch
  2. "C:/Program Files/KiCad/10.0/bin/python.exe" tools/gen_kicad_pcb.py

Placement (placa retrato 55 x 88; topo = y0):
  - Pico na coluna esquerda, USB colado na borda de cima;
  - PAM8403 ao lado do Pico, corpo na placa, pot saindo pela borda de cima;
  - RCAs na borda direita (barril para fora);
  - cadeia de video/audio na faixa central entre o Pico e os RCAs;
  - headers de painel (chave A/B, pots, START) empilhados abaixo do Pico;
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

BOARD_W, BOARD_H = 55.0, 88.0             # retrato: o Pico (51 mm) corre em Y
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
    # Floorplan (placa retrato 55 x 88, topo = y0):
    #   Pico (rot 0)   -> coluna ESQUERDA, USB colado na borda de cima;
    #                     pino 1 = (3.1, 2.0); coluna direita (21..40 =
    #                     GP16..VBUS) em x20.9 e a favor da faixa central.
    #   PAM8403        -> AO LADO do Pico na borda de cima: corpo na placa
    #                     (rot 0, pads y22), pot protrai pela borda superior.
    #   RCAs (A/V)     -> borda DIREITA, rot 270; sinal a 7.5 mm da borda
    #                     para o barril protrair ~8.5 mm para FORA da placa.
    #   coluna central -> x35: 1 coluna (DAC video, filtros, audio).
    #   headers        -> empilhados abaixo do Pico (rot 90: pinos +X).
    # Pico: corpo x1.5..22.5 / y0.6..51.7, keepout de cobre na base
    # (x~5..19 / y~45..52). Resistores VERTICAIS (~2.5 mm).
    PLACE = {
        # ---- topo: Pico (USB p/ fora) + PAM ao lado (pot p/ fora) ----
        "U1": ("1", 3.1, 2.0, 0),           # PCB x1.5..22.5 / y0.6..51.7
        "U2": ("1", 26.3, 22.0, 0),         # corpo x24.5..53.5 / y0.2..20.2
        # ---- RCAs na borda direita (rot 270: barril para +X) ----
        # Sinal a 7.5 mm da borda: a frente do corpo fica rente a borda
        # (x54.5) e o BARRIL protrai ~8.5 mm PARA FORA (ate x63.5), onde o
        # cabo e plugado. Abas frontais em x52.5 (folga cobre-borda 0.8).
        "J1": ("1", 47.5, 31.5, 270),       # video
        "J8": ("1", 47.5, 47.5, 270),       # audio L
        "J9": ("1", 47.5, 63.5, 270),       # audio R
        # ---- coluna central (x35, entre o furo H1 e a traseira dos RCAs) --
        "C3": ("1", 35.0, 28.0, 0),         # filtro ADC
        "C4": ("1", 35.0, 35.0, 0),         # filtro ADC
        "R1": ("1", 35.0, 42.0, 0),         # SYNC -> COMPOSITE
        "R2": ("1", 35.0, 48.0, 0),         # VIDEO -> COMPOSITE
        "R3": ("1", 35.0, 54.0, 0),         # AUDIO_PWM -> AUD_F
        "C1": ("1", 35.0, 61.0, 0),         # AUD_F -> GND (shunt)
        "C2": ("1", 32.5, 69.0, 0),         # AUD_F -> AUD_C (eletrolitico)
        "R6": ("1", 35.0, 76.0, 0),         # AUD_C -> AMP_L
        "R7": ("1", 35.0, 82.0, 0),         # AUD_C -> AMP_R
        # ---- abaixo do RCA de baixo ----
        "R4": ("1", 41.0, 76.0, 0),         # AUD_C -> LINHA
        "R5": ("1", 47.0, 76.0, 0),         # LINHA -> GND (shunt)
        # ---- headers EMPILHADOS abaixo do Pico (rot 90: pinos para +X) ----
        # J5/J6 na mesma fileira com UMA posicao vaga entre eles (x11.62):
        # um unico conector femea 1x7 serve os dois. Linha centrada entre
        # J4 (y58) e J7 (y82).
        "J4": ("1", 4.0, 58.0, 90),         # chave de audio A/B (6 vias)
        "J5": ("1", 4.0, 70.0, 90),         # pot P1 (pads x4..9.08)
        "J6": ("1", 14.16, 70.0, 90),       # pot P2 (pads x14.16..19.24)
        "J7": ("1", 13.5, 82.0, 90),        # START
    }
    # rotulos gerais (conectores de 2 pinos e o amp): 1 texto perto de cada
    # RCA: centro=sinal, corpo=GND (convencao universal) -> so o nome da funcao
    SILK = {
        "J1": ("VIDEO", 46.0, 39.4),
        "J8": ("AUDIO L", 46.0, 55.4),
        "J9": ("AUDIO R", 46.0, 71.4),
        "U2": ("PAM8403", 30.0, 25.0),
    }
    # NOME de cada header (o que o conector faz), abaixo dos pads
    HDR_NAME = {
        "J4": ("CHAVE AUDIO A/B", 12.0, 61.5),
        "J5": ("POT P1", 6.5, 73.5),
        "J6": ("POT P2", 16.7, 73.5),
        "J7": ("START", 15.0, 85.5),
    }
    # rotulo de FUNCAO por pino nos headers de painel (vertical, acima do pad)
    PIN_SILK = {
        "J4": ["RCA_C", "RCA_S", "LINHA", "GND", "LOUT+", "LOUT-"],  # chave A/B
        "J5": ["3V3", "P1", "AGND"],                                 # pot P1
        "J6": ["3V3", "P2", "AGND"],                                 # pot P2
        "J7": ["START", "GND"],                                      # botao
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

    show("U1", ("1", "40", "20", "21", "22", "24", "31", "32", "36", "38"))
    show("U2", ("1", "9"))
    show("J1", ("1", "2"))

    # ----- rotulos gerais de funcao na serigrafia -----
    for ref, (txt, tx, ty) in SILK.items():
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(V(tx, ty))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
        t.SetTextThickness(mm(0.12))
        board.Add(t)

    # ----- NOME de cada header (funcao do conector) -----
    for ref, (txt, tx, ty) in HDR_NAME.items():
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(V(tx, ty))
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(0.9), mm(0.9)))
        t.SetTextThickness(mm(0.15))
        board.Add(t)

    # ----- rotulo de funcao POR PINO nos headers de painel -----
    # texto vertical (90 graus) logo acima de cada pad, lido a partir da
    # posicao real do pad -> robusto a rotacao/direcao do footprint.
    for ref, names in PIN_SILK.items():
        fp = footprints[ref]
        for i, name in enumerate(names):
            pad = next((p for p in fp.Pads()
                        if p.GetNumber() == str(i + 1)), None)
            if pad is None:
                continue
            px = pcbnew.ToMM(pad.GetPosition().x) - BX
            py = pcbnew.ToMM(pad.GetPosition().y) - BY
            t = pcbnew.PCB_TEXT(board)
            t.SetText(name)
            t.SetPosition(V(px, py - 3.4))     # acima do pad (lado interno)
            t.SetLayer(pcbnew.F_SilkS)
            t.SetTextAngle(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T))
            t.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
            t.SetTextThickness(mm(0.15))
            board.Add(t)

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

    # ----- furos de montagem M3: losango com passo de 45 mm -----
    # Regra: base em y84 com H2/H3 a 45 mm entre centros (simetricos no eixo
    # X) e H4 no centro; H1 no eixo X, 45 mm acima da base -> H1-H4 = 45 mm.
    # Retangulo de 4 furos nos cantos nao fecha nesta placa: os cantos de
    # cima sao do Pico (esq.) e do RCA de video (dir.).
    print("stage: furos", flush=True)
    for i, (hx, hy) in enumerate([(BOARD_W / 2, 39.0),
                                  (BOARD_W / 2 - 22.5, 84.0),
                                  (BOARD_W / 2 + 22.5, 84.0),
                                  (BOARD_W / 2, 84.0)]):
        fp = load_fp("MountingHole:MountingHole_3.2mm_M3")
        fp.SetReference(f"H{i+1}")
        board.Add(fp)
        fp.SetPosition(V(hx, hy))

    # ----- regras (JLCPCB 2 camadas) -----
    bds = board.GetDesignSettings()
    try:
        bds.m_TrackMinWidth = mm(0.2)
        bds.m_ViasMinSize = mm(0.6)
        bds.m_MinClearance = mm(0.15)
        # 1 raio termico ja conecta o pad de GND (baixa corrente): evita
        # 'starved_thermal' onde trilhas vizinhas bloqueiam parte dos raios.
        bds.m_MinResolvedSpokes = 1
    except Exception as e:                  # API varia entre versoes
        print("aviso: regras minimas nao aplicadas:", e)
    try:
        ns = bds.GetNetSettings() if hasattr(bds, "GetNetSettings") \
            else bds.m_NetSettings
        dc = ns.GetDefaultNetclass()
        dc.SetClearance(mm(0.15))
        dc.SetTrackWidth(mm(0.3))
        dc.SetViaDiameter(mm(0.7))
        dc.SetViaDrill(mm(0.35))
        print("netclass Default: 0.3mm/0.15mm, via 0.7/0.35")
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
        # raios termicos finos e proximos: o plano preenche mais junto das
        # trilhas (menos ilhas isoladas) e ainda cabem raios em espacos apertados
        for m, v in (("SetThermalReliefGap", mm(0.3)),
                     ("SetThermalReliefSpokeWidth", mm(0.4)),
                     ("SetMinIslandArea", mm(0.2) * mm(0.2))):
            try:
                getattr(z, m)(v)
            except Exception as e:
                print(f"aviso: zona.{m}: {e}", flush=True)
        for setter, arg in (("SetLocalClearance", mm(0.2)),
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
        t.SetPosition(V(41, 87))            # rodape, entre H4 e H3
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        board.Add(t)
    except Exception as e:
        print("aviso: texto de silk:", e, flush=True)

    # ----- logo RetroSC no silk da frente, DENTRO do espaco do Pico -----
    # O logo (docs/images/logo_retrosc_1bit.png, 220x69, branco sobre preto)
    # vira tinta de silk onde os pixels sao BRANCOS (preto/branco invertidos:
    # o traco e que e impresso). Ocupa a janela entre as duas fileiras de
    # pinos do Pico (x4.0..20.0 / y0.6..51.7, sem nenhum pad), rotacionado
    # 90 graus. A 0.22 mm/px (traco de 1 px = 0.22 >= 0.15 minimo de
    # fabrica) fica com 48.4 x 15.2 mm, centrado sob o modulo.
    print("stage: logo", flush=True)
    try:
        from PIL import Image
        img = Image.open(str(REPO / "docs" / "images" /
                             "logo_retrosc_1bit.png")).convert("1")
        LW, LH = img.size
        lpx = img.load()
        S = 0.22                            # mm por pixel do logo
        BLEED = 0.01                        # funde runs vizinhos na tinta
        LX, LY = 4.4, 1.8                   # canto do logo (rel, na placa)
        # um PCB_SHAPE poly do arquivo so guarda 1 contorno -> um RECT
        # preenchido por run de pixels
        nruns = 0
        for j in range(LH):                 # linha da imagem -> X da placa
            i = 0
            while i < LW:                   # coluna da imagem -> Y da placa
                if lpx[i, j]:
                    i0 = i
                    while i < LW and lpx[i, j]:
                        i += 1
                    # frente (sem espelho): linhas j crescem para -X
                    xa = LX + (LH - 1 - j) * S - BLEED
                    xb = xa + S + 2 * BLEED
                    ya = LY + i0 * S - BLEED
                    yb = LY + i * S + BLEED
                    sh = pcbnew.PCB_SHAPE(board)
                    sh.SetShape(pcbnew.SHAPE_T_RECT)
                    sh.SetStart(V(xa, ya))
                    sh.SetEnd(V(xb, yb))
                    sh.SetFilled(True)
                    sh.SetWidth(0)
                    sh.SetLayer(pcbnew.F_SilkS)
                    board.Add(sh)
                    nruns += 1
                else:
                    i += 1
        print(f"logo: {nruns} runs em F.SilkS "
              f"({LH*S:.1f} x {LW*S:.1f} mm)", flush=True)
    except ImportError:
        print("aviso: PIL ausente no Python do KiCad - logo nao desenhado")
    except Exception as e:
        print("aviso: logo nao desenhado:", e, flush=True)

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
