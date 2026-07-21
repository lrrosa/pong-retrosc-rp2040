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
# Jack RCA de painel, angulo reto (medido pelo usuario)
# ============================================================
# Geometria das pernas, vista de cima, com o barril apontando para -Y
# (para fora da borda da placa):
#     pino 1 = sinal, no centro (0,0)
#     pino 2 = terra, 3 abas: esquerda, direita e frontal
# Medidas: 10 mm entre as abas esquerda/direita; 5 mm do pino central
# ate a aba frontal. Ou seja, as 3 abas ficam a 5 mm do centro.
RCA_GND_SPAN = 10.0          # entre a aba esquerda e a direita
RCA_GND_FRONT = 5.0          # do pino central ate a aba da frente
# Abas sao lâminas chatas -> furo oblongo. Pino central e mais fino.
RCA_SIG_DRILL, RCA_SIG_PAD = 1.5, 2.6
RCA_GND_DRILL_L, RCA_GND_DRILL_W = 2.4, 1.3   # furo oblongo (compr. x larg.)
RCA_GND_PAD_L, RCA_GND_PAD_W = 3.4, 2.3
# Corpo (datasheet do anuncio): barril 8.4 mm, corpo 18 x 12 x 15 mm.
RCA_BODY_W, RCA_BODY_D = 12.0, 18.0
RCA_BARREL_D = 8.4

# ============================================================
# Modulo PAM8403 HW-012 (medidas do anuncio + silk das fotos)
# ============================================================
# PCB 29.5 x 20.2 mm; o potenciometro avanca ~15.8 mm para fora de um
# dos lados e tem 15 mm de altura -> deixar espaco livre nesse lado.
HW012_PCB_W, HW012_PCB_H = 29.5, 20.2
HW012_POT_CLEAR = 15.8       # avanco do pot (so vira keep-out no silk)
HW012_PAD_PITCH = G          # 2.54 mm entre pads
HW012_DRILL, HW012_PAD = 1.1, 1.9
# Fileira unica na borda inferior, na ordem que aparece no silk do modulo:
HW012_PADS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
HW012_NAMES = {"1": "ROUT-", "2": "ROUT+", "3": "LOUT+", "4": "LOUT-",
               "5": "PWR-", "6": "PWR+", "7": "IN_L", "8": "IN_G",
               "9": "IN_R"}


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


def _pad(num, x, y, drill, size, shape="circle", rot=0):
    """drill/size escalares = furo redondo; tuplas (l, w) = oblongo."""
    if isinstance(size, tuple):
        sz = f"{size[0]} {size[1]}"
    else:
        sz = f"{size} {size}"
    if isinstance(drill, tuple):
        dr = f"oval {drill[0]} {drill[1]}"
    else:
        dr = f"{drill}"
    at = f"{round(x,3)} {round(y,3)}" + (f" {rot}" if rot else "")
    return (f'\t(pad "{num}" thru_hole {shape}\n'
            f"\t\t(at {at})\n"
            f"\t\t(size {sz})\n"
            f"\t\t(drill {dr})\n"
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
    """Pino 1 = sinal (centro); pino 2 = terra (3 abas: esq., dir. e frente).

    Origem = pino de sinal. O barril aponta para -Y, ou seja, para fora da
    borda da placa -- posicione o footprint com -Y virado para a borda.
    """
    n = "RCA_Jack_THT_Panel"
    s = _hdr(n, "Jack RCA de painel, angulo reto, THT. Sinal ao centro e 3 "
                "abas de terra a 5 mm (esquerda, direita e frontal). Barril "
                "8.4 mm; corpo 18 x 12 x 15 mm.",
             "RCA phono connector THT right-angle audio video")
    half = RCA_GND_SPAN / 2
    s += _pad("1", 0, 0, RCA_SIG_DRILL, RCA_SIG_PAD, "circle")
    # abas laterais: lamina no eixo Y -> furo oblongo girado 90 graus
    for x in (-half, half):
        s += _pad("2", x, 0,
                  (RCA_GND_DRILL_L, RCA_GND_DRILL_W),
                  (RCA_GND_PAD_L, RCA_GND_PAD_W), "oval", 90)
    # aba frontal: lamina no eixo X
    s += _pad("2", 0, -RCA_GND_FRONT,
              (RCA_GND_DRILL_L, RCA_GND_DRILL_W),
              (RCA_GND_PAD_L, RCA_GND_PAD_W), "oval")
    # contorno do corpo (barril para -Y, alem da borda da placa)
    bw, bd = RCA_BODY_W / 2, RCA_BODY_D
    s += _rect(-bw, -RCA_GND_FRONT - 2.0, bw, -RCA_GND_FRONT + 8.0)
    s += _line(-RCA_BARREL_D / 2, -RCA_GND_FRONT - 2.0,
               -RCA_BARREL_D / 2, -bd + 2)
    s += _line(RCA_BARREL_D / 2, -RCA_GND_FRONT - 2.0,
               RCA_BARREL_D / 2, -bd + 2)
    s += _rect(-bw - 0.3, -bd - 0.3, bw + 0.3, 2.6, "F.CrtYd", 0.05)
    s += _text("SIG", bw + 1.0, 0, "F.Fab")
    s += _text("GND", bw + 1.0, -RCA_GND_FRONT, "F.Fab")
    return n, s + ")\n"


def pam8403():
    """Modulo HW-012 montado EM PE (vertical), como no prototipo.

    Fica na placa apenas a fileira de 9 pads; o PCB do modulo (29.5 x
    20.2 mm) sobe perpendicular e o potenciometro fica no alto, fora do
    plano da placa. Footprint estilo SIP: faixa fina de silk.
    Origem = pad 1.
    """
    n = "PAM8403_HW-012"
    s = _hdr(n, "Modulo amplificador classe-D PAM8403 (HW-012) montado em pe "
                "(vertical) pela fileira de 9 pads. PCB do modulo 29.5 x "
                "20.2 mm sobe perpendicular; pot de volume no topo. Deixar "
                "~21 mm livres acima da placa.",
             "PAM8403 HW-012 amplifier module class-D audio SIP vertical")
    span = (len(HW012_PADS) - 1) * HW012_PAD_PITCH
    for i, num in enumerate(HW012_PADS):
        x = i * HW012_PAD_PITCH
        s += _pad(num, x, 0, HW012_DRILL, HW012_PAD,
                  "rect" if num == "1" else "circle")
        s += _text(HW012_NAMES[num], x, 2.4, "F.Fab", 0.55)
    # faixa SIP: modulo em pe, PCB dele e mais largo que a fileira de pads
    x0 = span / 2 - HW012_PCB_W / 2
    s += _rect(x0, -1.8, x0 + HW012_PCB_W, 1.8)
    s += _rect(x0 - 0.3, -2.1, x0 + HW012_PCB_W + 0.3, 3.4, "F.CrtYd", 0.05)
    s += _text("PAM8403 (em pe)", span / 2, -3.2)
    return n, s + ")\n"


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, body in (rca_jack(), pam8403()):
        (OUT / f"{name}.kicad_mod").write_text(body, encoding="utf-8")
        print(f"OK: {name}.kicad_mod")
    print(f"-> {OUT}")
