#ifndef PONG_HIGHSCORES_H
#define PONG_HIGHSCORES_H

#include <stdint.h>
#include <stdbool.h>

#include "config.h"

typedef struct {
    uint16_t score;
    uint8_t  player;   // 1 ou 2 (lado da raquete)
    uint8_t  pad;
} hi_entry_t;

typedef struct {
    uint32_t   magic;
    uint32_t   version;
    hi_entry_t entries[HISCORE_COUNT];
    uint32_t   checksum;
} hi_table_t;

void hi_init(void);

// Carrega da flash (ou inicializa zerado se invalida).
void hi_load(void);

// Salva a tabela atual na flash.
void hi_save(void);

// Considera um novo placar e insere se entrar no top.
//   Retorna true se entrou no top, false caso contrario.
bool hi_consider(uint16_t score, uint8_t player);

// Acesso a tabela em RAM.
const hi_table_t *hi_get(void);

#endif // PONG_HIGHSCORES_H
