#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 RetroSC Pong contributors
"""
Gera os footprints que NAO existem nas bibliotecas do KiCad:
o jack RCA de painel e o modulo amplificador PAM8403 (HW-012).

>>> AS MEDIDAS ABAIXO SAO PROVISORIAS <<<
Ajuste as constantes marcadas com [MEDIR] conferindo as pecas reais e
rode de novo. Como o prototipo foi montado em perfboard de 2,54 mm, o
jeito mais facil de medir e CONTAR FUROS entre os pinos.

Uso:
    python tools/gen_kicad_fp.py
Saida: kicad/pong-retrosc.pretty/*.kicad_mod
"""

import uuid as _uuid
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "kicad" / "pong-retrosc.pretty"
VERSION = "20260206"
G = 2.54                     # passo da perfboard (grade de 0,1")

# ============================================================
# [MEDIR] Jack RCA de painel (os dourados do prototipo)
# ============================================================
# Distancia entre o pino central (sinal) e a aba de terra.
RCA_PIN_TO_GND = 3 * G       # 7.62 mm  = 3 furos
# Distancia centro-a-centro entre dois RCAs vizinhos (usada no PCB).
RCA_PITCH = 8 * G            # 20.32 mm = 8 furos
# Furos de solda.
RCA_DRILL_SIG, RCA_PAD_SIG = 1.3, 2.4
RCA_DRILL_GND, RCA_PAD_GND = 1.8, 3.2
# Corpo (para silk/courtyard): diametro do cilindro e recuo do painel.
RCA_BODY_D = 10.0
RCA_BODY_L = 16.0

# ============================================================
# [MEDIR] Modulo PAM8403 HW-012
# ============================================================
# O modulo e soldado por duas fileiras de pads. Meca:
HW012_ROW_PITCH = 6 * G      # 15.24 mm = 6 furos entre as duas fileiras
HW012_PAD_PITCH = G          # 2.54 mm entre pads da mesma fileira
HW012_W, HW012_H = 9 * G, 8 * G   # contorno do modulo (silk)
HW012_DRILL, HW012_PAD = 1.0, 1.8
# Fileira de entrada (esquerda) e de saida (direita), de cima para baixo.
HW012_LEFT = ["1", "2", "3", "4"]     # +5V, GND, IN_L, IN_R
HW012_RIGHT = ["5", "6", "7", "8"]    # L+, L-, R+, R-
HW012_NAMES = {"1": "+5V", "2": "GND", "3": "IN_L", "4": "IN_R",
               "5": "LOUT+", "6": "LOUT-", "7": "ROUT+", "8": "ROUT-"}


def _u():
    return str(_uuid.uuid4())


def _hdr(name, descr, tags):
    return (f'(footprint "{name}"\n'
            f"\t(version {VERSION})\n"
            f'\t(generator "gen_kicad_fp.py")\n'
            f'\t(generator_version "10.0")\n'
            f'\t(layer "F.Cu")\n'
            f'\t(descr "{descr}")\n'
            f'\t(tags "{tags}")\n'
            f"\t(attr through_hole)\n"
            + _prop("Reference", "REF**", 0, -1, "F.SilkS")
            + _prop("Value", name, 0, 1, "F.Fab"))


def _prop(key, val, x, y, layer):
    hide = "\n\t\t(hide yes)" if key not in ("Reference", "Value") else ""
    return (f'\t(property "{key}" "{val}"\n'
            f"\t\t(at {x} {y} 0)\n"
            f'\t\t(layer "{layer}"){hide}\n'
            f'\t\t(uuid "{_u()}")\n'
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1 1)\n"
            f"\t\t\t\t(thickness 0.15)\n\t\t\t)\n\t\t)\n\t)\n")


def _pad(num, x, y, drill, size, shape="circle"):
    return (f'\t(pad "{num}" thru_hole {shape}\n'
            f"\t\t(at {round(x,3)} {round(y,3)})\n"
            f"\t\t(size {size} {size})\n"
            f"\t\t(drill {drill})\n"
            f'\t\t(layers "*.Cu" "*.Mask")\n'
            f'\t\t(remove_unused_layers no)\n'
            f'\t\t(uuid "{_u()}")\n\t)\n')


def _line(x1, y1, x2, y2, layer="F.SilkS", w=0.12):
    return (f"\t(fp_line\n\t\t(start {round(x1,3)} {round(y1,3)})\n"
            f"\t\t(end {round(x2,3)} {round(y2,3)})\n"
            f"\t\t(stroke\n\t\t\t(width {w})\n\t\t\t(type solid)\n\t\t)\n"
            f'\t\t(layer "{layer}")\n\t\t(uuid "{_u()}")\n\t)\n')


def _rect(x1, y1, x2, y2, layer="F.SilkS", w=0.12):
    return (_line(x1, y1, x2, y1, layer, w) + _line(x2, y1, x2, y2, layer, w)
            + _line(x2, y2, x1, y2, layer, w) + _line(x1, y2, x1, y1, layer, w))


def _text(s, x, y, layer="F.SilkS", size=0.8):
    return (f'\t(fp_text user "{s}"\n\t\t(at {round(x,3)} {round(y,3)} 0)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{_u()}")\n'
            f"\t\t(effects\n\t\t\t(font\n\t\t\t\t(size {size} {size})\n"
            f"\t\t\t\t(thickness 0.12)\n\t\t\t)\n\t\t)\n\t)\n")


def rca_jack():
    """Pino 1 = sinal (centro), pino 2 = terra (aba/carcaca)."""
    n = "RCA_Jack_THT_Panel"
    s = _hdr(n, "Jack RCA de painel, montagem THT. MEDIDAS PROVISORIAS - "
                "conferir com a peca real (ver tools/gen_kicad_fp.py).",
             "RCA phono connector THT panel audio video")
    s += _pad("1", 0, 0, RCA_DRILL_SIG, RCA_PAD_SIG, "rect")
    s += _pad("2", 0, RCA_PIN_TO_GND, RCA_DRILL_GND, RCA_PAD_GND)
    # contorno do corpo + courtyard
    half = RCA_BODY_D / 2
    s += _rect(-half, -half, half, RCA_PIN_TO_GND + half)
    s += _rect(-half - 0.3, -half - 0.3, half + 0.3,
               RCA_PIN_TO_GND + half + 0.3, "F.CrtYd", 0.05)
    s += _text("SIG", half + 0.8, 0)
    s += _text("GND", half + 0.8, RCA_PIN_TO_GND)
    return n, s + ")\n"


def pam8403():
    """Modulo HW-012: duas fileiras de pads de 2,54 mm."""
    n = "PAM8403_HW-012"
    s = _hdr(n, "Modulo amplificador PAM8403 (HW-012) com pot de volume. "
                "MEDIDAS PROVISORIAS - conferir (ver tools/gen_kicad_fp.py).",
             "PAM8403 HW-012 amplifier module class-D")
    x0 = -HW012_ROW_PITCH / 2
    for side, pads in ((x0, HW012_LEFT), (x0 + HW012_ROW_PITCH, HW012_RIGHT)):
        y0 = -(len(pads) - 1) * HW012_PAD_PITCH / 2
        for i, num in enumerate(pads):
            y = y0 + i * HW012_PAD_PITCH
            s += _pad(num, side, y, HW012_DRILL, HW012_PAD,
                      "rect" if num == "1" else "circle")
            s += _text(HW012_NAMES[num],
                       side + (-3.6 if side < 0 else 3.6), y, "F.Fab", 0.7)
    s += _rect(-HW012_W / 2, -HW012_H / 2, HW012_W / 2, HW012_H / 2)
    s += _rect(-HW012_W / 2 - 0.3, -HW012_H / 2 - 0.3,
               HW012_W / 2 + 0.3, HW012_H / 2 + 0.3, "F.CrtYd", 0.05)
    s += _text("PAM8403", 0, -HH if (HH := HW012_H / 2 + 1.2) else 0)
    return n, s + ")\n"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in (rca_jack(), pam8403()):
        (OUT / f"{name}.kicad_mod").write_text(body, encoding="utf-8")
        print(f"OK: {name}.kicad_mod")
    print(f"-> {OUT}")
