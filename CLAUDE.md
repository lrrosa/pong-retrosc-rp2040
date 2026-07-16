# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A 2-player **Pong for the Raspberry Pi Pico (RP2040)**, built for an arcade
cabinet at the RetroSC event. The firmware generates **NTSC composite video**
(1-bit, 256×192) entirely in PIO + DMA, reads two 10 kΩ potentiometers via ADC,
and plays PWM audio. C / Pico SDK. No RTOS — a single `while` loop in `main.c`
synced to vsync.

## Build, flash, run

Toolchain is the **Pico SDK 1.5.1** Windows installer (GCC 10.3.1, CMake, Ninja).
Staying on 1.5.1 is intentional (RP2040-only); the code uses only stock SDK APIs
so it is forward-compatible with 2.x. `clk_sys` is forced to **125 MHz** in
`main.c` — the PIO `clkdiv` values depend on this; do not change one without the other.

Build (PowerShell, this machine's absolute paths):

```powershell
& "C:\Program Files\Raspberry Pi\Pico SDK v1.5.1\pico-env.ps1"
& "C:\Program Files\Raspberry Pi\Pico SDK v1.5.1\ninja\ninja.exe" -C build
```

First-time configure: `cmake -G Ninja -B build` (after dot-sourcing `pico-env.ps1`
so `PICO_SDK_PATH` and the toolchain are set). Output is `build/pong-rp2040.uf2`.

Flash: hold BOOTSEL, plug USB, copy `build/pong-rp2040.uf2` to the `RPI-RP2` drive.

There are **no unit tests**. Validation = the build must succeed (the PIO assembler
catches timing/instruction errors) plus running a simulator.

## Simulators

- **Python** (`python tools/sim.py`, needs `pygame`): re-implements the game logic
  and **parses `src/assets.c` and `src/font.c` at runtime via regex**, so bitmap/font
  changes show up without porting. Mouse-Y halves = the two pots, Space = START.
- **Wokwi** (`diagram.json` + `wokwi.toml`, "Wokwi for VS Code" extension): runs the
  real compiled `.elf` on an emulated RP2040 and shows the composite output on a
  `wokwi-tv` part. Open the `pong-rp2040` folder as the workspace root. `*.vcd`
  (logic-analyzer dumps) are gitignored.
- **CRT preview** (`python tools/crt_preview.py`, needs `pillow numpy`): applies a
  TV-tube effect to framebuffer PNGs.

## Architecture

**Video (`ntsc.{pio,c,h}`) is the subtle part.** Two PIO state machines on one PIO:
- `ntsc_sync` (`.side_set 1` on the SYNC pin) consumes a **per-scanline descriptor**
  word streamed by chained DMA. Descriptor bit0 = vsync line, bit1 = active line.
  On active lines it raises IRQ 4. **One line = 54 PIO cycles at clkdiv 147.118**
  (= 63.55 µs). The first 4 cycles (descriptor fetch, sync held low) are the
  **H-sync = 4.71 µs** — this exact width matters (see gotchas).
- `ntsc_data` waits on IRQ 4 and clocks 256 framebuffer bits onto the VIDEO pin.
- The two pins form a **2-resistor DAC** (470 Ω sync + 270 Ω video) → 3 analog
  levels (sync/black/white). On Wokwi the same two pins are read digitally by `wokwi-tv`.
- `line_descriptors[262]` is built in `ntsc_init()` from `LINES_VSYNC` / `LINES_TOP_BLANK`
  / `LINES_ACTIVE` / `LINES_BOT_BLANK` (`config.h`). DMA chains (sync descriptors and
  pixel data) re-trigger each frame and bump `ntsc_frame_count`.

**Framebuffer** `fb` is 256×192, 1-bit, MSB-first: `word = y*8 + (x>>5)`,
`bit = 31 - (x & 31)`. All drawing is in `gfx.{c,h}`; text via the 5×7 font in
`font.{c,h}` (glyphs indexed `['X' - 0x20]`).

**Game** (`game.{c,h}`) is a state machine: `GS_ATTRACT → GS_COUNTDOWN → GS_PLAY →
GS_ROUND_END → GS_GAME_OVER → GS_ENTER_INITIALS → GS_HIGH_SCORES`. Ball physics is
fixed-point Q8. `game_frame()` is called once per vsync. Winners entering the top 5
pick 3 arcade-style initials (pot cycles A–Z, START confirms).

**Input** (`input.{c,h}`): ADC poll with an IIR filter. `input_paddle_y(player)` maps
ADC→paddle position; `input_pot_raw(player)` is used for initials entry. Also forces
the Pico SMPS into PWM mode (GPIO23 high) for a cleaner ADC supply.

**High scores** (`highscores.{c,h}`): persisted in the **last flash sector**
(magic + version + checksum). Flash-touching functions are `__not_in_flash_func`
and wrap `save_and_disable_interrupts()`.

**Assets** (`assets.{c,h}`): const 1-bit bitmaps (currently just the RetroSC logo),
generated from PNG by `tools/png_to_c.py` and pasted in. Pin/dimension constants all
live in `src/config.h`.

## Project-specific gotchas

- **NTSC sync timing is non-obvious.** A standard 4.7 µs H-sync (the 54-cycle / clkdiv
  147 scheme) is required for `wokwi-tv` to lock and is also better for real CRTs. The
  delay counts in `ntsc.pio` are hand-balanced so **every code path through a line totals
  exactly 54 cycles**; with `.side_set 1` the max delay is `[15]`, so long waits are split.
- **Image centering is two separate knobs:** horizontal = the back-porch `nop [..]`
  before `irq nowait 4` in `ntsc.pio` (~7 px/cycle); vertical = `LINES_TOP_BLANK` in
  `config.h` (1 line/unit). `LINES_TOP_BLANK = 35` centers on a **real TV** (the
  project target); Wokwi's visible window is shifted up and would want ~55.
- **Vsync must be serrated.** Each of the 3 vsync lines carries 2 half-line broad
  pulses (23 cycles LOW + 4 HIGH). A whole-line LOW vsync loses the TV's H-lock:
  CRTs drop sync periodically and LED TVs never lock (real-hardware validated).
- **XIP suspends during flash writes**, so anything the running PIO/DMA dereferences must
  live in RAM, not flash/XIP. `fb_base_ptr` and `desc_base_ptr` in `ntsc.c` are
  deliberately non-`const` for this reason.
- **`<<` binds tighter than `<`/`>`** — parenthesize shift expressions in comparisons
  (a real bug fixed here: `ball_x < ((PADDLE_MARGIN + PADDLE_W) << 8)`).
- Git: files are authored LF; the LF→CRLF warnings on Windows are expected. Commit/push
  only when asked.
