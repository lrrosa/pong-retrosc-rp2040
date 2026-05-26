#ifndef PONG_GAME_H
#define PONG_GAME_H

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    GS_ATTRACT,
    GS_COUNTDOWN,
    GS_PLAY,
    GS_ROUND_END,
    GS_GAME_OVER,
    GS_ENTER_INITIALS,
    GS_HIGH_SCORES,
} game_state_t;

void game_init(void);

// Avanca um frame de logica e desenha no framebuffer. Chamar a 60 fps.
void game_frame(void);

game_state_t game_get_state(void);

#endif // PONG_GAME_H
