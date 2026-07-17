// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 RetroSC Pong contributors
#ifndef PONG_INPUT_H
#define PONG_INPUT_H

#include <stdint.h>
#include <stdbool.h>

void input_init(void);

// Le os dois potenciometros uma vez. Resultado em 0..4095, com low-pass simples.
void input_poll(void);

// Posicao do paddle 0..(FB_HEIGHT - PADDLE_H), filtrada.
int input_paddle_y(int player);

// Valor cru filtrado do pot 0..4095 (para entrada de iniciais).
int input_pot_raw(int player);

// Botao START pressionado neste frame (rising edge).
bool input_start_pressed(void);

// True se algum dos dois pots se mexeu nos ultimos N samples (para sair do attract).
bool input_movement_detected(void);

// Reseta o detector de movimento (chamar ao entrar em attract).
void input_reset_movement(void);

#endif // PONG_INPUT_H
