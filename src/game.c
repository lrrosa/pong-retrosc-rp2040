#include "game.h"

#include <stdio.h>

#include "config.h"
#include "gfx.h"
#include "font.h"
#include "input.h"
#include "audio.h"
#include "highscores.h"
#include "assets.h"

#include "pico/stdlib.h"
#include "pico/rand.h"

// =============================================================
// Estado do jogo
// =============================================================
static game_state_t state;
static int          state_timer;  // contador de frames dentro do estado

static int score[2];              // pontos P1, P2
static int paddle_y[2];           // y atual de cada raquete
static int last_winner;           // 0 = ninguem, 1 ou 2 ao terminar partida

// Bola em ponto fixo Q8 (1 unidade = 1/256 pixel)
static int32_t ball_x, ball_y;
static int32_t ball_vx, ball_vy;
static int32_t ball_speed_q;    // |v| atual

// =============================================================
// Helpers
// =============================================================
static int sign(int v) { return v < 0 ? -1 : (v > 0 ? 1 : 0); }

static int abs_i(int v) { return v < 0 ? -v : v; }

static void set_state(game_state_t s) {
    state = s;
    state_timer = 0;
}

static void serve_ball(int direction /* -1 ou +1 */) {
    ball_x = (FB_WIDTH / 2) << 8;
    ball_y = (FB_HEIGHT / 2) << 8;
    ball_speed_q = BALL_SPEED_INIT_Q;
    // angulo aleatorio: vy entre -0.6 e +0.6 da velocidade
    int32_t r = (int32_t)(get_rand_32() & 0xFF) - 128;     // -128..127
    int32_t vy_frac = (r * ball_speed_q) / 256;            // ~ +/- 0.5 * speed
    int32_t vx_frac;
    // vx tal que |v|^2 = vx^2 + vy^2 ~ speed^2
    int32_t s2 = ball_speed_q * ball_speed_q;
    int32_t vy2 = vy_frac * vy_frac;
    int32_t vx2 = s2 - vy2;
    int32_t vx_abs = 0;
    // sqrt inteira
    for (int32_t g = (ball_speed_q >> 1); g <= ball_speed_q; g++) {
        if (g * g >= vx2) { vx_abs = g; break; }
    }
    if (vx_abs == 0) vx_abs = ball_speed_q;
    vx_frac = direction * vx_abs;
    ball_vx = vx_frac;
    ball_vy = vy_frac;
}

static void reset_round(int last_scorer) {
    paddle_y[0] = (FB_HEIGHT - PADDLE_H) / 2;
    paddle_y[1] = (FB_HEIGHT - PADDLE_H) / 2;
    // bola sai em direcao a quem perdeu o ponto
    int dir = (last_scorer == 1) ? -1 : +1;
    serve_ball(dir);
}

// =============================================================
// Fisica e colisoes (chamado em GS_PLAY)
// =============================================================
static void update_paddles_human(void) {
    int p0 = input_paddle_y(0);
    int p1 = input_paddle_y(1);
    paddle_y[0] = p0;
    paddle_y[1] = p1;
}

static void update_paddles_demo(void) {
    // AI simples: cada raquete persegue a bola lentamente
    for (int i = 0; i < 2; i++) {
        int target = (ball_y >> 8) - PADDLE_H / 2;
        int diff = target - paddle_y[i];
        int speed = 2;
        if (abs_i(diff) > speed) diff = (diff > 0) ? speed : -speed;
        paddle_y[i] += diff;
        if (paddle_y[i] < 0) paddle_y[i] = 0;
        if (paddle_y[i] > FB_HEIGHT - PADDLE_H) paddle_y[i] = FB_HEIGHT - PADDLE_H;
    }
}

static void on_paddle_hit(int paddle_idx) {
    // Inverte vx, ajusta vy de acordo com a posicao do contato.
    int pad_top = paddle_y[paddle_idx];
    int pad_center = pad_top + PADDLE_H / 2;
    int by = ball_y >> 8;
    int offset = by - pad_center;          // -PADDLE_H/2..+PADDLE_H/2

    // aumenta velocidade
    if (ball_speed_q < BALL_SPEED_MAX_Q) ball_speed_q += BALL_SPEED_STEP_Q;

    // novo vetor: angulo a partir do offset
    int32_t vy_frac = (offset * ball_speed_q) / (PADDLE_H);
    int32_t s2 = ball_speed_q * ball_speed_q;
    int32_t vx2 = s2 - vy_frac * vy_frac;
    if (vx2 < 0) vx2 = 0;
    int32_t vx_abs = 0;
    for (int32_t g = (ball_speed_q >> 2); g <= ball_speed_q; g++) {
        if (g * g >= vx2) { vx_abs = g; break; }
    }
    if (vx_abs == 0) vx_abs = ball_speed_q >> 1;
    ball_vx = (paddle_idx == 0) ? +vx_abs : -vx_abs;
    ball_vy = vy_frac;
    audio_paddle_hit();
}

static void physics(void) {
    ball_x += ball_vx;
    ball_y += ball_vy;

    // Topo / fundo
    if (ball_y < 0) { ball_y = 0; ball_vy = -ball_vy; audio_wall_hit(); }
    int max_y = (FB_HEIGHT - BALL_SIZE) << 8;
    if (ball_y > max_y) { ball_y = max_y; ball_vy = -ball_vy; audio_wall_hit(); }

    // Raquetes
    int bx = ball_x >> 8;
    int by = ball_y >> 8;

    // Paddle 0 (esquerda) em x = PADDLE_MARGIN
    int p0_x = PADDLE_MARGIN;
    if (ball_vx < 0 && bx <= p0_x + PADDLE_W && bx + BALL_SIZE > p0_x) {
        if (by + BALL_SIZE > paddle_y[0] && by < paddle_y[0] + PADDLE_H) {
            ball_x = (p0_x + PADDLE_W) << 8;
            on_paddle_hit(0);
        }
    }
    // Paddle 1 (direita)
    int p1_x = FB_WIDTH - PADDLE_MARGIN - PADDLE_W;
    if (ball_vx > 0 && bx + BALL_SIZE >= p1_x && bx < p1_x + PADDLE_W) {
        if (by + BALL_SIZE > paddle_y[1] && by < paddle_y[1] + PADDLE_H) {
            ball_x = (p1_x - BALL_SIZE) << 8;
            on_paddle_hit(1);
        }
    }

    // Score: saida pelas laterais
    if (bx + BALL_SIZE < 0) {
        score[1]++;
        last_winner = (score[1] >= WIN_SCORE) ? 2 : 0;
        audio_score();
        set_state(GS_ROUND_END);
    } else if (bx > FB_WIDTH) {
        score[0]++;
        last_winner = (score[0] >= WIN_SCORE) ? 1 : 0;
        audio_score();
        set_state(GS_ROUND_END);
    }
}

// =============================================================
// Desenho
// =============================================================
static void draw_field(void) {
    // separador central pontilhado
    gfx_dotted_vline(FB_WIDTH / 2, 0, FB_HEIGHT, 4, 4);
}

static void draw_paddles(void) {
    gfx_fill_rect(PADDLE_MARGIN, paddle_y[0], PADDLE_W, PADDLE_H, 1);
    gfx_fill_rect(FB_WIDTH - PADDLE_MARGIN - PADDLE_W, paddle_y[1], PADDLE_W, PADDLE_H, 1);
}

static void draw_ball(void) {
    int bx = ball_x >> 8;
    int by = ball_y >> 8;
    gfx_fill_rect(bx, by, BALL_SIZE, BALL_SIZE, 1);
}

static void draw_scores(void) {
    char buf[4];
    buf[0] = '0' + score[0]; buf[1] = 0;
    gfx_text(FB_WIDTH/2 - 30 - gfx_text_width(buf, 3), 8, buf, 3, 1);
    buf[0] = '0' + score[1]; buf[1] = 0;
    gfx_text(FB_WIDTH/2 + 30, 8, buf, 3, 1);
}

static void center_text(int y, const char *s, int scale) {
    int w = gfx_text_width(s, scale);
    gfx_text((FB_WIDTH - w) / 2, y, s, scale, 1);
}

// =============================================================
// Telas
// =============================================================
static void draw_attract(void) {
    gfx_clear(0);

    // Logo RetroSC centralizado horizontalmente, perto do topo
    int lx = (FB_WIDTH - RETROSC_LOGO_W) / 2;
    gfx_blit(retrosc_logo_data, RETROSC_LOGO_W, RETROSC_LOGO_H, lx, 8, 1);

    // Titulo
    center_text(8 + RETROSC_LOGO_H + 10, "PONG", 3);

    // Demo do jogo no fundo (campo + bola e raquetes pequenas no centro inferior)
    // Tracejado central
    gfx_dotted_vline(FB_WIDTH / 2, FB_HEIGHT - 70, FB_HEIGHT - 6, 4, 4);
    // raquetes demo
    gfx_fill_rect(PADDLE_MARGIN, paddle_y[0], PADDLE_W, PADDLE_H, 1);
    gfx_fill_rect(FB_WIDTH - PADDLE_MARGIN - PADDLE_W, paddle_y[1], PADDLE_W, PADDLE_H, 1);
    draw_ball();

    // Texto de chamada (pisca a cada ~32 frames)
    if (((state_timer >> 5) & 1) == 0) {
        center_text(FB_HEIGHT - 18, "MOVA UM POTENCIOMETRO", 1);
    }
    center_text(FB_HEIGHT - 8, "RETROSC.ORG", 1);
}

static void draw_countdown(void) {
    gfx_clear(0);
    draw_field();
    draw_scores();
    draw_paddles();

    int sec_left = 3 - state_timer / 60;
    if (sec_left > 0) {
        char buf[2] = { (char)('0' + sec_left), 0 };
        center_text(FB_HEIGHT / 2 - 10, buf, 3);
    } else {
        center_text(FB_HEIGHT / 2 - 10, "GO", 3);
    }
}

static void draw_play(void) {
    gfx_clear(0);
    draw_field();
    draw_scores();
    draw_paddles();
    draw_ball();
}

static void draw_round_end(void) {
    draw_play();   // congelado
}

static void draw_game_over(void) {
    gfx_clear(0);
    draw_scores();
    char buf[24];
    if (last_winner == 1) {
        snprintf(buf, sizeof(buf), "JOGADOR 1 VENCE");
    } else {
        snprintf(buf, sizeof(buf), "JOGADOR 2 VENCE");
    }
    center_text(FB_HEIGHT/2 - 8, buf, 1);
    if ((state_timer >> 4) & 1) {
        center_text(FB_HEIGHT/2 + 8, "GAME OVER", 2);
    }
}

static void draw_highscores(void) {
    gfx_clear(0);
    center_text(8, "HIGH SCORES", 2);
    const hi_table_t *t = hi_get();
    int y = 36;
    for (int i = 0; i < HISCORE_COUNT; i++) {
        char buf[24];
        if (t->entries[i].score > 0) {
            snprintf(buf, sizeof(buf), "%d.  %2d  P%d",
                     i + 1, t->entries[i].score, t->entries[i].player);
        } else {
            snprintf(buf, sizeof(buf), "%d.   -      ", i + 1);
        }
        gfx_text(80, y, buf, 1, 1);
        y += 14;
    }
    center_text(FB_HEIGHT - 12, "RETROSC PONG", 1);
}

// =============================================================
// Frame de cada estado
// =============================================================
static void frame_attract(void) {
    update_paddles_demo();
    // bola animada no espaco da demo (parte inferior)
    if (ball_x < ((PADDLE_MARGIN + PADDLE_W) << 8)) {
        ball_vx = abs_i(ball_vx);
    }
    if (ball_x > ((FB_WIDTH - PADDLE_MARGIN - PADDLE_W - BALL_SIZE) << 8)) {
        ball_vx = -abs_i(ball_vx);
    }
    int min_y = (FB_HEIGHT - 70) << 8;
    int max_y = (FB_HEIGHT - 6 - BALL_SIZE) << 8;
    if (ball_y < min_y) { ball_y = min_y; ball_vy = abs_i(ball_vy); }
    if (ball_y > max_y) { ball_y = max_y; ball_vy = -abs_i(ball_vy); }
    ball_x += ball_vx;
    ball_y += ball_vy;

    if (input_movement_detected() || input_start_pressed()) {
        score[0] = score[1] = 0;
        last_winner = 0;
        reset_round(0);
        set_state(GS_COUNTDOWN);
        return;
    }
    draw_attract();
}

static void frame_countdown(void) {
    update_paddles_human();
    draw_countdown();
    if (state_timer >= 3 * 60 + 30) {       // 3s + meio segundo "GO"
        set_state(GS_PLAY);
    }
}

static void frame_play(void) {
    update_paddles_human();
    physics();
    draw_play();
}

static void frame_round_end(void) {
    update_paddles_human();
    draw_round_end();
    if (state_timer >= 60) {
        if (score[0] >= WIN_SCORE || score[1] >= WIN_SCORE) {
            last_winner = (score[0] > score[1]) ? 1 : 2;
            hi_consider((uint16_t)(score[0] > score[1] ? score[0] : score[1]),
                        (uint8_t)last_winner);
            hi_save();
            set_state(GS_GAME_OVER);
        } else {
            reset_round(score[0] > score[1] ? 1 : 2);
            set_state(GS_COUNTDOWN);
        }
    }
}

static void frame_game_over(void) {
    draw_game_over();
    if (state_timer >= 4 * 60) {
        set_state(GS_HIGH_SCORES);
    }
}

static void frame_high_scores(void) {
    draw_highscores();
    if (state_timer >= 10 * 60 || input_start_pressed()) {
        input_reset_movement();
        set_state(GS_ATTRACT);
        // posicao inicial da bola no espaco do demo
        ball_x = (FB_WIDTH / 2) << 8;
        ball_y = ((FB_HEIGHT - 40)) << 8;
        ball_vx = BALL_SPEED_INIT_Q;
        ball_vy = BALL_SPEED_INIT_Q / 2;
    }
}

// =============================================================
// API
// =============================================================
void game_init(void) {
    score[0] = score[1] = 0;
    last_winner = 0;
    paddle_y[0] = paddle_y[1] = (FB_HEIGHT - PADDLE_H) / 2;
    ball_x = (FB_WIDTH / 2) << 8;
    ball_y = ((FB_HEIGHT - 40)) << 8;
    ball_vx = BALL_SPEED_INIT_Q;
    ball_vy = BALL_SPEED_INIT_Q / 2;
    set_state(GS_ATTRACT);
}

void game_frame(void) {
    switch (state) {
        case GS_ATTRACT:     frame_attract();     break;
        case GS_COUNTDOWN:   frame_countdown();   break;
        case GS_PLAY:        frame_play();        break;
        case GS_ROUND_END:   frame_round_end();   break;
        case GS_GAME_OVER:   frame_game_over();   break;
        case GS_HIGH_SCORES: frame_high_scores(); break;
    }
    state_timer++;
}

game_state_t game_get_state(void) { return state; }
