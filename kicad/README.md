# PCB — RetroSC Pong

Placa de 2 camadas com plano de terra, gerada por scripts (reprodutível) e
roteada com o Freerouting. Hardware sob **CERN-OHL-S-2.0** (ver
[`../LICENSE-HARDWARE.txt`](../LICENSE-HARDWARE.txt)).

## Arquivos versionados

| Arquivo | O quê |
| --- | --- |
| `pong-retrosc.kicad_sch` / `.kicad_pro` | esquemático e projeto |
| `pong-retrosc.kicad_pcb` | **placa roteada** (DRC 0 erros) |
| `pong-retrosc.pretty/` | footprints próprios (RCA de painel, PAM8403 HW-012) |
| `fp-lib-table` | registra a lib de footprints do projeto |
| `gerbers/` | Gerbers + furação (Excellon) prontos para fábrica |

Intermediários (`*-decoy.*`, `*.dsn`, `*.ses`, `*.net`) são **gitignored** —
regeráveis pelo pipeline abaixo.

## Pipeline (do zero à placa roteada)

Requer o **Python do KiCad** (`.../KiCad/10.0/bin/python.exe`, módulo `pcbnew`),
`kicad-cli` e o **Freerouting** instalado.

```sh
KPY="/c/Program Files/KiCad/10.0/bin/python.exe"
CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
FR="$LOCALAPPDATA/freerouting/freerouting.exe"

# 1. esquemático -> netlist  (roda no Python normal)
python tools/gen_kicad_sch.py
python tools/gen_kicad_fp.py
"$CLI" sch export netlist -o kicad/pong-retrosc.net kicad/pong-retrosc.kicad_sch

# 2. placa (placement, contorno, zonas, regras)   [Python do KiCad]
"$KPY" tools/gen_kicad_pcb.py

# 3. ISCA sem zonas + DSN                          [Python do KiCad]
"$KPY" tools/make_decoy.py

# 4. roteamento automatico  (caminhos relativos: sem espacos)
"$FR" -de kicad/pong-retrosc-decoy.dsn -do kicad/pong-retrosc-decoy.ses -mp 100 -da

# 5. importar SES na placa real + remover trilhas de GND  [Python do KiCad]
"$KPY" tools/import_ses.py

# 6. preencher o plano e validar
"$CLI" pcb drc --refill-zones --save-board --severity-error \
       --exit-code-violations kicad/pong-retrosc.kicad_pcb

# 7. gerbers + furacao
"$CLI" pcb export gerbers --layers "F.Cu,B.Cu,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts" \
       --subtract-soldermask -o kicad/gerbers/ kicad/pong-retrosc.kicad_pcb
"$CLI" pcb export drill --format excellon --drill-origin absolute \
       --excellon-units mm --generate-map --map-format gerberx2 \
       -o kicad/gerbers/ kicad/pong-retrosc.kicad_pcb
```

**Por que a isca (passo 3):** com as zonas presentes, o DSN as exporta como
*planes* que o Freerouting trata como obstáculo — ele vira quase mono-camada e
abandona os nets longos. Sem zonas, roteia livre nas 2 faces; o plano de GND
volta na placa real e absorve todo o GND (passo 5 remove as trilhas de GND
redundantes).

## Estado

- **DRC: 0 erros.** Restam avisos de silk (referências sobre cobre/borda) —
  cosméticos, não bloqueiam a fabricação.
- Regras: trilha de sinal 0,3 mm, isolamento 0,2 mm, via 0,7/0,35 mm (JLCPCB
  2 camadas).

## ATENÇÃO antes de fabricar

- **Footprints do RCA e do PAM8403 foram feitos à mão** a partir de medidas das
  peças. Confira o encaixe (imprima o PDF de fabricação em 1:1 e sobreponha as
  peças) antes de enviar para produção.
- Peças de **painel** (pots, botão, chave A/B) saem por headers (J4–J7); os RCAs
  e o amp ficam **na placa**, como no protótipo.
