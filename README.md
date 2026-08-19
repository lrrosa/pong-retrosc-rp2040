# RetroSC Pong — Raspberry Pi Pico (RP2040)

Pong clássico de 2 jogadores em um Raspberry Pi Pico, com saída de **vídeo
composto** (NTSC 1-bit gerado por PIO) e **áudio PWM**. Foi feito para uma
máquina arcade do evento [**RetroSC**](https://retrosc.org/).

![logo](docs/images/logo_retrosc.png)

## Recursos

- Vídeo composto NTSC 256×192, 1-bit, ~60 Hz, gerado inteiramente em PIO + DMA
  (CPU livre para o jogo).
- 2 raquetes controladas por **potenciômetros 10 kΩ** (ADC do Pico).
- **Attract screen** com logo da RetroSC + demo automático (AI vs AI).
- Pontuação para vencer configurável (`WIN_SCORE` em `src/config.h`, padrão 7).
- **High scores persistentes** na flash do RP2040 com **iniciais de 3 letras**
  estilo arcade — o vencedor usa o potenciômetro para escolher cada letra
  e o botão START para confirmar.
- Áudio com os 3 sons clássicos do Pong (raquete, parede, ponto) em PWM
  filtrado.
- Botão **START** opcional (também sai do attract jiggling qualquer
  potenciômetro).

## Estrutura do repositório

```
pong-rp2040/
├── CMakeLists.txt
├── pico_sdk_import.cmake
├── README.md
├── LICENSE
├── docs/
│   ├── schematic.md     <-- esquemático por blocos (diagramas SVG)
│   ├── pinout.md        <-- pinagem dos 3 módulos RP2040 suportados
│   ├── bom.md           <-- lista de materiais (por referência: R1, C2, J4…)
│   ├── pecas-do-gabinete.md  <-- pots, knobs e itens da caixa: qual comprar
│   └── images/          <-- diagramas, renders da placa, capturas
├── kicad/               <-- PCB: 2 variantes, gerbers prontos p/ fábrica
│   ├── README.md        <-- pipeline (esquemático -> placa -> gerbers)
│   ├── retrosc-pong*.kicad_{sch,pcb,pro}
│   ├── retrosc-pong.pretty/   <-- footprints próprios (RCA, PAM8403)
│   └── gerbers*/ + *-gerbers.zip
├── src/
│   ├── main.c
│   ├── config.h         <-- constantes do projeto (pinos, dimensões, etc.)
│   ├── ntsc.{c,h,pio}   <-- driver de vídeo composto
│   ├── gfx.{c,h}        <-- desenho no framebuffer
│   ├── font.{c,h}       <-- fonte 5x7
│   ├── input.{c,h}      <-- ADC dos pots + botão
│   ├── audio.{c,h}      <-- PWM de áudio
│   ├── highscores.{c,h} <-- persistência na flash
│   ├── game.{c,h}       <-- máquina de estados e física
│   └── assets.{c,h}     <-- bitmaps embutidos
└── tools/
    ├── png_to_c.py      <-- conversor PNG → C array
    ├── sim.py           <-- simulador do jogo (pygame)
    ├── crt_preview.py   <-- efeito de tubo nas capturas
    ├── gen_kicad_sch.py <-- gera o esquemático  (--yd p/ a variante)
    ├── gen_kicad_fp.py  <-- gera os footprints próprios
    ├── gen_kicad_pcb.py <-- gera a placa (placement, zonas, silk, logo)
    ├── make_decoy.py    <-- placa-isca p/ o Freerouting + DSN
    ├── import_ses.py    <-- traz o roteamento de volta
    └── dsn_tweak.py     <-- ajusta larguras/isolamento no DSN
```

## Hardware

Veja os arquivos em [docs/](docs/) para detalhes:

- [docs/schematic.md](docs/schematic.md) — esquemático completo
- [docs/pinout.md](docs/pinout.md) — pinagem dos **3 módulos RP2040
  suportados** (Pico oficial, YD-RP2040 de 3 botões e "roxa" de 1 botão) e
  qual variante de PCB usar com cada um
- [docs/bom.md](docs/bom.md) — lista de materiais e custo
- [docs/pecas-do-gabinete.md](docs/pecas-do-gabinete.md) — potenciômetros,
  manoplas e peças da caixa: **qual modelo comprar** e por quê
- [kicad/README.md](kicad/README.md) — as **duas variantes de PCB** prontas
  para fabricar (gerbers zipados)

Resumo do hardware:

| Bloco | GPIO | Componentes (referências do BOM) |
| ----- | ---- | -------------------------------- |
| Vídeo composto | GP16 (sync), GP17 (video) | R1 470 Ω + R2 270 Ω → jack J1 |
| Áudio | GP18 (PWM) | filtro R3 + C1, acoplamento C2, divisor R4/R5, entradas R6/R7 → amp U2 → jacks J8/J9 |
| Botão START | GP22 | SW1 (para GND) via header J7 |
| Potenciômetro P1 | GP26 (ADC0) | RV1 10 kΩ linear + C3 → header J5 |
| Potenciômetro P2 | GP27 (ADC1) | RV2 10 kΩ linear + C4 → header J6 |

Os GPIOs acima são os mesmos nos três módulos suportados; o que muda entre
eles é **em qual furo** cada GPIO aparece (ver [pinout.md](docs/pinout.md)).

## Como compilar

### 1. Instalar o Pico SDK

**Recomendado (Windows):** baixe o [Raspberry Pi Pico Windows Installer](https://github.com/raspberrypi/pico-setup-windows/releases),
que instala toolchain (ARM GCC), CMake, Ninja, Python e o Pico SDK de uma
vez.

**Manual (qualquer SO):**

```bash
git clone --depth 1 https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk
git submodule update --init
export PICO_SDK_PATH=$(pwd)
```

Instale também:

- ARM GCC (`gcc-arm-none-eabi`)
- CMake ≥ 3.13
- Ninja ou Make

### 2. Build

```bash
git clone https://github.com/lrrosa/retrosc-pong.git
cd retrosc-pong
mkdir build && cd build
cmake -G "Ninja" ..   # ou simplesmente: cmake ..
ninja                 # ou: make -j
```

Resultado: `build/pong-rp2040.uf2`.

### 3. Gravar no Pico

1. Segure o botão **BOOTSEL** do Pico enquanto conecta o USB.
2. O Pico aparece como pendrive (`RPI-RP2`).
3. Arraste `pong-rp2040.uf2` para dentro do pendrive.
4. O Pico reinicia automaticamente rodando o jogo.

## Simulador (Python, sem hardware)

Para iterar em layouts e gameplay sem flashear o Pico, há um simulador que
roda a mesma lógica em Python e carrega os MESMOS bitmaps/fonte do código C:

```bash
pip install pygame
python tools/sim.py
```

Janela 768×576 (framebuffer 256×192 × 3). Controles:

- **Mouse Y na metade esquerda** → raquete P1
- **Mouse Y na metade direita** → raquete P2
- **Espaço** → botão START
- **R** → zera high scores (só em RAM, não toca a flash do Pico)
- **Q** ou **ESC** → sair

Pré-visualizações com efeito CRT (como deve ficar numa TV de tubo —
scanlines, glow de fósforo, vignette e curvatura):

| Attract | Countdown | Play |
| :---: | :---: | :---: |
| ![](docs/images/crt_attract.png) | ![](docs/images/crt_countdown.png) | ![](docs/images/crt_play.png) |

| Game Over | Enter Initials | High Scores |
| :---: | :---: | :---: |
| ![](docs/images/crt_game_over.png) | ![](docs/images/crt_enter_initials.png) | ![](docs/images/crt_highscores.png) |

Renderizações "raw" (sem CRT, só o framebuffer escalado) ficam em
`docs/images/sim_*.png`.

> **Limitação:** o simulador não reproduz a fidelidade do sinal NTSC nem
> o timing exato do PIO/DMA. Use para validar UX e visual; o teste final
> do vídeo só com a TV real.

### CRT preview

Para aplicar o efeito CRT (scanlines + bloom + fósforo + vignette +
curvatura) em qualquer PNG do framebuffer:

```bash
pip install pillow numpy
python tools/crt_preview.py docs/images/sim_attract.png        # gera crt_sim_attract.png
python tools/crt_preview.py --all                              # regenera todos os crt_*.png
```

Os parâmetros (intensidade do bloom, dos scanlines, cor do fósforo) estão
no topo de `crt_effect()` em [tools/crt_preview.py](tools/crt_preview.py)
e são bons pontos de partida; mexa neles pra ajustar pra TV verde, âmbar,
ou ajustar o "estado" do tubo.

## Simulador Wokwi (TV de verdade no navegador)

Diferente do simulador Python (que reproduz a lógica do jogo), o **Wokwi roda
o firmware compilado de verdade** no RP2040 emulado e mostra a saída de vídeo
composto numa **TV virtual** (`wokwi-tv`), com potenciômetros, botão e buzzer.

O `wokwi-tv` não usa DAC resistivo: ele lê os 2 pinos digitais direto e segue
os pulsos de sync (funciona com NTSC e PAL). Os arquivos já estão no repo:

- [`diagram.json`](diagram.json) — fiação: `GP16→SYNC`, `GP17→IN`, 2
  potenciômetros em `GP26`/`GP27`, botão START em `GP22`, buzzer em `GP18`.
- [`wokwi.toml`](wokwi.toml) — aponta para `build/pong-rp2040.uf2`/`.elf`.

Como rodar (extensão do VS Code, mais confiável que o site):

```bash
# 1. Compile o firmware
mkdir build && cd build && cmake -G Ninja .. && ninja && cd ..
# 2. No VS Code: instale a extensão "Wokwi for VS Code" e faça login (grátis)
# 3. Abra diagram.json e rode o comando "Wokwi: Start Simulator"
```

Controles no Wokwi: gire os **potenciômetros** (mouse) para mover as raquetes;
**botão verde** = START.

> **Importante:** abra a pasta `pong-rp2040` como raiz do workspace do VS Code
> (o `wokwi.toml` precisa estar na raiz). Se clicar em "play" e nada acontecer,
> rode antes `Ctrl+Shift+P` → "Wokwi: Request a New License" (token gratuito).

> **Velocidade:** o Wokwi roda a ~30% do tempo real — é normal. Emular o vídeo
> composto ciclo-a-ciclo no navegador é pesado. O **hardware real roda a 60 fps**
> (PIO + DMA fazem o vídeo, a CPU fica livre).

> **Se o Wokwi não abre no seu navegador:** ele exige WebAssembly + isolamento
> cross-origin (`SharedArrayBuffer`); extensões ou políticas às vezes bloqueiam.
> Use a **extensão do VS Code** (roda local) ou teste numa aba anônima. Se nem
> os projetos públicos do Wokwi rodam aí, conserte isso antes — não é do nosso
> projeto.

> **Centralização Wokwi × TV real:** a "janela visível" do `wokwi-tv` é
> deslocada para cima, então `LINES_TOP_BLANK` (em `src/config.h`) está em **55**
> para centralizar no simulador. Numa **TV CRT real** o centro padrão fica em
> **~30–35** — reduza esse valor (ou use o controle de V-Position/V-Hold da TV).
> A posição horizontal sai do "back porch" em `src/ntsc.pio`.

## Como jogar

- **Liga**: conecte alimentação (USB ou fonte 5 V).
- **Sair do attract**: mexa qualquer potenciômetro **ou** aperte START.
- **Jogar**: rode os potenciômetros para mover as raquetes (esquerda = P1,
  direita = P2). Primeiro a marcar 7 pontos vence.
- **Iniciais**: se o vencedor entrar no top 5, ele insere 3 letras estilo
  arcade — girar o pot rola pelo alfabeto A–Z, apertar START confirma a
  letra atual e passa para a próxima.
- **High scores**: depois das iniciais (ou direto, se não entrou no top),
  a tabela aparece por 10 s antes de voltar ao attract.

## Customização

Tudo importante está em [`src/config.h`](src/config.h):

- `WIN_SCORE` — pontos para vencer
- `BALL_SPEED_*` — física da bola
- `PADDLE_W`, `PADDLE_H`, `BALL_SIZE` — visual
- Pinos GPIO

Para trocar o logo do attract:

```bash
python tools/png_to_c.py docs/images/seu_logo.png retrosc_logo 0 0 threshold > tools/_logo.inc
# Substituir o array correspondente em src/assets.c
```

Modo `threshold` (corte fixo em 128) é melhor para arte com contornos
definidos (logos, ícones). Modo `dither` (Floyd-Steinberg) é melhor para
fotos com gradientes — mas em 60 Hz num CRT, o padrão de dithering pode
ficar tremido. Para o evento, prefira `threshold`.

Veja `docs/images/preview_logo_1bit.png` para saber como ficou a versão
1-bit.

## Limitações conhecidas

- **NTSC monocromático**: sem cor. Em TVs PAL-M brasileiras, a maioria
  aceita o sinal sem problema (mostra em preto e branco). Se sua TV não
  aceita, talvez precise de uma TV CRT com entrada AV "real" ou um
  conversor.
- **Timing do PIO** está calculado para `clk_sys = 125 MHz`. Se você
  alterar o clock, ajuste `clkdiv` em `src/ntsc.c` proporcionalmente.
- **High scores sem iniciais**: o MVP grava apenas o número de pontos e o
  lado (P1/P2). Implementar entrada de iniciais é uma melhoria futura
  (usar o pot para selecionar letras + START para confirmar).

## Créditos e referências

- A abordagem de gerar NTSC com duas PIOs (sync + dados) + DMA é inspirada
  no trabalho de [@brucland](https://github.com/brucland/RP2040/tree/main/PIO/NTSC_1_bit).
  Este projeto é uma implementação independente (não copia o código), mas a
  análise daquele repositório foi essencial para definir o timing.
- Pong original: Allan Alcorn, Atari (1972).
- Logo da RetroSC: cortesia do evento [RetroSC](https://retrosc.org/).

## Licença

Projeto com **licença dupla** (ver [`NOTICE`](NOTICE) para o detalhamento por
arquivo):

- **Software** (firmware em `src/`, ferramentas em `tools/`, build) —
  **[GPL-3.0-or-later](LICENSE)** (`SPDX-License-Identifier: GPL-3.0-or-later`).
- **Hardware** (esquemáticos: `kicad/`, `docs/schematic.md`, `docs/bom.md`,
  `docs/pinout.md`, diagramas SVG) — **[CERN-OHL-S-2.0](LICENSE-HARDWARE.txt)**
  (`SPDX-License-Identifier: CERN-OHL-S-2.0`), a variante *Strongly Reciprocal*
  da CERN Open Hardware Licence.

As duas são **recíprocas** (copyleft): trabalhos derivados devem manter a mesma
licença e disponibilizar as fontes correspondentes (código no caso do software,
arquivos de projeto no caso do hardware).

As **marcas e arte do evento RetroSC** (logo) permanecem propriedade do evento e
**não** estão cobertas por essas licenças — ver [`NOTICE`](NOTICE).
