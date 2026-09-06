// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 RetroSC Pong contributors
//
// Fases do RetroSC Pong.
//
// Cada fase e so um "cenario": muda o formato/orientacao da raquete, poe
// obstaculos na quadra ou solta um bicho no meio do jogo. As regras
// (PHASE_WIN_SCORE pontos por fase, cada ponto somando no total geral) sao
// iguais em todas e ficam em game.c, valendo tanto para o modo arcade quanto
// para o versus.
//
// O que uma fase pode ter:
//   - tijolos: colunas verticais de BRICK_W x BRICK_H que SOMEM quando a bola
//     bate. Cada coluna guarda suas BRICK_ROWS (24) linhas num bitmask de 32
//     bits -- barato de testar e de copiar quando a fase rearma os tijolos.
//   - solidos: retangulos que so rebatem. Ficam parados (bumpers do pinball,
//     rede do Rebound) ou andam (a coluna da fase COLUNA).
//   - bichos: o fantasma (fase propria) e a nave-bonus, que nao e fase nenhuma:
//     ela aparece de tempos em tempos nas fases marcadas com PF_TEM_NAVE.
//
// Para acrescentar uma fase: um item no enum phase_id_t, o nome/dica nas
// tabelas abaixo e o que ela tem de especial. O resto do jogo -- pontuacao,
// menu, telas -- nao muda.
//
// Ideias que ainda nao viraram fase (ver "ideias de fases.txt", uma pasta
// acima do repo): variacoes de outros pongs, tipo o Telejogo 10 e a colecao
// "Pongs" do Pippin Barr.

#include "phases.h"

#include "gfx.h"
#include "font.h"
#include "assets.h"

#include "pico/rand.h"

// =============================================================
// Estado
// =============================================================
#define BRICK_COLS_MAX 4
#define SOLID_MAX      9

static int      cur_phase;
static uint32_t cur_flags;
static uint32_t frame_ctr;                      // so para piscar textos

// tijolos
static int      brick_cols;                     // colunas em uso (0 = sem tijolos)
static int      brick_col_x[BRICK_COLS_MAX];    // x da esquerda de cada coluna
static uint32_t brick_alive[BRICK_COLS_MAX];    // linhas ainda de pe
static uint32_t brick_start[BRICK_COLS_MAX];    // padrao original da fase
static bool     brick_rebuild_round;            // rearma os tijolos a cada ponto

// solidos (parados ou moveis)
static rect_t   solids[SOLID_MAX];
static int      solid_count;
static int      col_y, col_dir;                 // deslocamento da coluna movel

// nave-bonus (qualquer fase com PF_TEM_NAVE)
static bool     ship_on;
static int32_t  ship_x_q, ship_y_q, ship_vx_q, ship_vy_q;
static int      ship_wait;
static int      ship_left;                      // passagens que ainda restam

// fantasma + tiros (PHASE_FANTASMA)
static int      ghost_y, ghost_dir, ghost_cool;
static struct { int x, y, vx; bool on; } shots[GHOST_SHOT_MAX];
static int      shrink[2];                      // frames de raquete encolhida

// =============================================================
// Tabela das fases
// =============================================================
static const char *const names[PHASE_COUNT] = {
    [PHASE_CLASSICO]  = "PONG CLASSICO",
    [PHASE_FANTASMA]  = "FANTASMA",
    [PHASE_TRIPLO]    = "TRIPLO",
    [PHASE_BARREIRA1] = "BARREIRA I",
    [PHASE_PINBALL]   = "PINBALL",
    [PHASE_BARREIRA2] = "BARREIRA II",
    [PHASE_COLUNA]    = "COLUNA",
    [PHASE_MURALHA]   = "MURALHA",
    [PHASE_REBOUND]   = "REBOUND",
    [PHASE_BARREIRA3] = "BARREIRA III",
};

static const char *const hints[PHASE_COUNT] = {
    [PHASE_CLASSICO]  = "O PONG DE SEMPRE",
    [PHASE_FANTASMA]  = "OS TIROS ENCOLHEM A RAQUETE",
    [PHASE_TRIPLO]    = "TRES RAQUETES COM VAOS",
    [PHASE_BARREIRA1] = "DOIS MUROS NO MEIO",
    [PHASE_PINBALL]   = "OBSTACULOS NO MEIO",
    [PHASE_BARREIRA2] = "TRES MUROS COM VAOS",
    [PHASE_COLUNA]    = "OBSTACULOS SOBEM E DESCEM",
    [PHASE_MURALHA]   = "OS TIJOLOS GUARDAM O GOL",
    [PHASE_REBOUND]   = "VOLEI: NAO DEIXE A BOLA CAIR",
    [PHASE_BARREIRA3] = "QUATRO MUROS: ABRA CAMINHO",
};

const char *phase_name(int idx) {
    if ((unsigned)idx >= PHASE_COUNT) return "";
    return names[idx];
}

const char *phase_hint(int idx) {
    if ((unsigned)idx >= PHASE_COUNT) return "";
    return hints[idx];
}

int      phase_current(void) { return cur_phase; }
uint32_t phase_flags(void)   { return cur_flags; }

// =============================================================
// Montagem dos cenarios
// =============================================================
// BARREIRA III: blocos de tijolo separados por um corredor de uma linha,
// grossos nas pontas e fino no meio. Sao 24 linhas ao todo (FB_HEIGHT/BRICK_H):
// 5+4+2+4+5 = 20 de tijolo mais os 4 corredores fecham exatamente 24. O padrao
// 5-4-3-4-5 pedido daria 21+4 = 25 linhas, uma a mais do que cabe na tela.
static const uint8_t barreira3_blocos[] = { 5, 4, 2, 4, 5 };

// Muros no meio da quadra: 'cols' colunas com 'gap' px entre elas. Com
// 'blocos' != NULL, a coluna nasce dividida nesses blocos, separados por uma
// linha vazia -- corredores prontos que tiram o pior da barreira mais grossa.
// O estrago fica ate o fim da fase -- quando abre um vao de ponta a ponta, a
// fase volta a ser um pong normal, que e a graca dela. Por isso a progressao
// de 2 -> 3 -> 4 muros ao longo do jogo.
static void build_barreira(int cols, int gap,
                           const uint8_t *blocos, int n_blocos) {
    brick_cols = cols;
    int step  = BRICK_W + gap;
    int total = cols * BRICK_W + (cols - 1) * gap;
    int x0    = FB_WIDTH / 2 - total / 2;

    uint32_t mask = 0;
    if (blocos == NULL) {
        for (int r = 0; r < BRICK_ROWS; r++) mask |= (1u << r);
    } else {
        int r = 0;
        for (int b = 0; b < n_blocos && r < BRICK_ROWS; b++) {
            for (int i = 0; i < blocos[b] && r < BRICK_ROWS; i++, r++)
                mask |= (1u << r);
            r++;                       // corredor entre um bloco e o proximo
        }
    }
    for (int c = 0; c < cols; c++) {
        brick_col_x[c] = x0 + c * step;
        brick_start[c] = mask;
    }
    brick_rebuild_round = false;
    cur_flags |= PF_NO_CENTER_LINE;
}

// MURALHA: uma coluna atras de cada raquete, com vaos grandes ja abertos.
// A bola sempre rebate nos tijolos: so da ponto quem enfia a bola num vao.
// Aqui os tijolos voltam a cada ponto, senao o gol ficaria escancarado.
static void build_muralha(void) {
    brick_cols = 2;
    brick_col_x[0] = 0;
    brick_col_x[1] = FB_WIDTH - BRICK_W;
    uint32_t mask = 0;
    for (int r = 0; r < BRICK_ROWS; r++) {
        // 3 tijolos, 3 vazios: com vao de 24 px a bola (3 px) passa sem ser
        // sorte grossa. Vaos menores travam a fase (medido no simulador:
        // vao de 8 px = 34 s por ponto; de 24 px = 16 s por ponto).
        if ((r % 6) < 2 || (r % 6) > 4) mask |= (1u << r);
    }
    brick_start[0] = brick_start[1] = mask;
    brick_rebuild_round = true;
    cur_flags |= PF_TEM_NAVE;
}

// PINBALL: obstaculos fixos espalhados pelo meio da quadra em losango. As
// raquetes continuam nos lugares de sempre; o que muda e o caminho da bola.
// Nada acima de y=40: ali em cima estao o placar da fase e o total.
static void build_pinball(void) {
    #define BX(dx) (FB_WIDTH  / 2 + (dx) - BUMPER_W / 2)
    #define BY(dy) (FB_HEIGHT / 2 + (dy) - BUMPER_H / 2)
    // Sem postes no eixo central entre o centro e as pontas: eles fechavam
    // fileiras de tres e tampavam a passagem pelo meio.
    static const int pos[9][2] = {
        { BX(  0), BY(  0) },                       // centro
        { BX(  0), BY(-72) }, { BX(  0), BY(+72) }, // pontas do eixo vertical
        { BX(-32), BY(-30) }, { BX(+32), BY(-30) }, // diagonais
        { BX(-32), BY(+30) }, { BX(+32), BY(+30) },
        { BX(-64), BY(  0) }, { BX(+64), BY(  0) }, // laterais
    };
    #undef BX
    #undef BY
    solid_count = 9;
    for (int i = 0; i < solid_count; i++) {
        solids[i].x = pos[i][0];
        solids[i].y = pos[i][1];
        solids[i].w = BUMPER_W;
        solids[i].h = BUMPER_H;
    }
}

// Altura ocupada pela coluna movel inteira.
static int coluna_span(void) {
    return COL_BUMPERS * BUMPER_H + (COL_BUMPERS - 1) * COL_GAP;
}

static void coluna_place(void) {
    for (int i = 0; i < COL_BUMPERS; i++)
        solids[i].y = col_y + i * (BUMPER_H + COL_GAP);
}

// COLUNA: os mesmos obstaculos do pinball, empilhados no meio e subindo e
// descendo juntos. Quem manda na jogada e o instante em que a bola chega.
static void build_coluna(void) {
    solid_count = COL_BUMPERS;
    int x = FB_WIDTH / 2 - BUMPER_W / 2;
    for (int i = 0; i < COL_BUMPERS; i++) {
        solids[i].x = x;
        solids[i].w = BUMPER_W;
        solids[i].h = BUMPER_H;
    }
    col_y   = (FB_HEIGHT - coluna_span()) / 2;
    col_dir = +1;
    coluna_place();
    cur_flags |= PF_NO_CENTER_LINE;
}

// REBOUND: volei. As raquetes deitam no chao e andam na horizontal dentro da
// propria meia-quadra; a bola tem gravidade e o ponto sai quando ela toca o
// chao. A rede no meio e um solido que vai do chao ate NET_TOP.
static void build_rebound(void) {
    solid_count = 1;
    solids[0].x = FB_WIDTH / 2 - NET_W / 2;
    solids[0].y = NET_TOP;
    solids[0].w = NET_W;
    solids[0].h = FB_HEIGHT - NET_TOP;
    cur_flags |= PF_NO_CENTER_LINE | PF_GRAVITY | PF_FLOOR_SCORES |
                 PF_SIDE_WALLS | PF_PADDLE_HORIZ;
}

static void ship_sleep(void) {
    ship_on   = false;
    ship_wait = SHIP_WAIT_MIN + (int)(get_rand_32() % SHIP_WAIT_RANGE);
}

static void ghost_reset(void) {
    // Pode nascer no meio da quadra: a contagem regressiva agora e desenhada
    // com um fundo preto e nao some mais atras dele.
    ghost_y    = (FB_HEIGHT - RETROSC_MASCOTE_H) / 2;
    ghost_dir  = +1;
    ghost_cool = GHOST_SHOT_PERIOD;
}

void phase_begin(int idx) {
    if ((unsigned)idx >= PHASE_COUNT) idx = 0;
    cur_phase   = idx;
    cur_flags   = 0;
    frame_ctr   = 0;
    brick_cols  = 0;
    solid_count = 0;
    brick_rebuild_round = false;
    ghost_reset();
    shrink[0] = shrink[1] = 0;
    for (int i = 0; i < GHOST_SHOT_MAX; i++) shots[i].on = false;
    ship_left = SHIP_PASSES_MAX;
    ship_sleep();

    switch (idx) {
        case PHASE_CLASSICO:  cur_flags |= PF_TEM_NAVE;    break;
        case PHASE_TRIPLO:    cur_flags |= PF_TEM_NAVE;    break;
        case PHASE_FANTASMA:                               break;
        case PHASE_BARREIRA1: build_barreira(2, 1, NULL, 0);
                              cur_flags |= PF_TEM_NAVE;    break;
        case PHASE_BARREIRA2: build_barreira(3, 16, NULL, 0); break;
        // Sem os corredores, a barreira cheia de 4 muros vira uma partida do
        // jogador contra a propria parede.
        case PHASE_BARREIRA3:
            build_barreira(4, 1, barreira3_blocos,
                           (int)(sizeof(barreira3_blocos))); break;
        case PHASE_MURALHA:   build_muralha();             break;
        case PHASE_PINBALL:   build_pinball();             break;
        case PHASE_COLUNA:    build_coluna();              break;
        case PHASE_REBOUND:   build_rebound();             break;
        default: break;
    }
    for (int c = 0; c < brick_cols; c++) brick_alive[c] = brick_start[c];
}

void phase_round_reset(void) {
    shrink[0] = shrink[1] = 0;
    for (int i = 0; i < GHOST_SHOT_MAX; i++) shots[i].on = false;
    ghost_reset();
    ship_sleep();
    if (!brick_rebuild_round) return;
    for (int c = 0; c < brick_cols; c++) brick_alive[c] = brick_start[c];
}

// =============================================================
// Raquetes
// =============================================================
// Na MURALHA a raquete anda um pouco mais para dentro, senao fica colada nos
// tijolos e o olho nao separa as duas coisas.
static int paddle_margin(void) {
    return (cur_phase == PHASE_MURALHA) ? (PADDLE_MARGIN + 6) : PADDLE_MARGIN;
}

int phase_paddle_range(void) {
    if (cur_flags & PF_PADDLE_HORIZ)
        return FB_WIDTH / 2 - 2 * VOLLEY_MARGIN - VOLLEY_PADDLE_W;
    if (cur_phase == PHASE_TRIPLO)
        return FB_HEIGHT - (3 * TRIPLE_SEG_H + 2 * TRIPLE_GAP);
    return FB_HEIGHT - PADDLE_H;
}

int phase_paddle_segments(int player, int pos, rect_t *out) {
    if (cur_flags & PF_PADDLE_HORIZ) {
        int base = (player == 0) ? VOLLEY_MARGIN
                                 : (FB_WIDTH / 2 + VOLLEY_MARGIN);
        out[0].x = base + pos;
        out[0].y = FB_HEIGHT - VOLLEY_PADDLE_Y;
        out[0].w = VOLLEY_PADDLE_W;
        out[0].h = VOLLEY_PADDLE_H;
        return 1;
    }

    int margin = paddle_margin();
    int x = (player == 0) ? margin : (FB_WIDTH - margin - PADDLE_W);

    if (cur_phase == PHASE_TRIPLO) {
        for (int i = 0; i < 3; i++) {
            out[i].x = x;
            out[i].y = pos + i * (TRIPLE_SEG_H + TRIPLE_GAP);
            out[i].w = PADDLE_W;
            out[i].h = TRIPLE_SEG_H;
        }
        return 3;
    }

    out[0].x = x;
    out[0].y = pos;
    out[0].w = PADDLE_W;
    out[0].h = PADDLE_H;
    // Tiro do fantasma: a raquete fica pela metade, centrada na mesma posicao,
    // para o curso do pot nao mudar debaixo da mao do jogador.
    if (shrink[player & 1] > 0) {
        out[0].y = pos + PADDLE_H / 4;
        out[0].h = PADDLE_H / 2;
    }
    return 1;
}

// =============================================================
// Saque
// =============================================================
int phase_serve_x(int dir) {
    if (brick_cols > 0 && !brick_rebuild_round) {
        // Sair do centro colocaria a bola dentro da barreira: saca do lado de
        // quem vai RECEBER (dir aponta para ele), colado na barreira, para a
        // bola ter a quadra inteira dele pela frente antes de virar gol.
        int left  = brick_col_x[0] - 8 - BALL_SIZE;
        int right = brick_col_x[brick_cols - 1] + BRICK_W + 8;
        return (dir < 0) ? left : right;
    }
    if (cur_flags & PF_PADDLE_HORIZ) {
        // Volei: a bola cai na meia-quadra de quem vai sacar.
        return (dir < 0) ? (FB_WIDTH / 4) : (3 * FB_WIDTH / 4);
    }
    if (cur_phase == PHASE_COLUNA || cur_phase == PHASE_PINBALL) {
        // Sair do centro seria sair de dentro de um obstaculo.
        return (dir < 0) ? (FB_WIDTH / 2 - 34) : (FB_WIDTH / 2 + 34);
    }
    return FB_WIDTH / 2;
}

int phase_serve_y(void) {
    if (cur_flags & PF_GRAVITY) return 24;      // solta a bola do alto
    return FB_HEIGHT / 2;
}

// =============================================================
// Colisao da bola com o cenario
// =============================================================
// Rebate a bola num retangulo em que ela ja entrou. A face de saida sai da
// DIRECAO em que a bola vinha (a face que ela atravessou), e nao da menor
// penetracao: escolher pela penetracao devolvia a bola pela lateral quando ela
// tinha entrado por cima perto do canto e, como a velocidade ja apontava para
// fora naquele eixo, nada era invertido -- a bola seguia reto, "atravessando"
// o obstaculo. Vale para tijolo, bumper, coluna movel, rede e fantasma.
// Devolve true se quem inverteu foi o eixo X.
static bool bounce_off(int rx0, int ry0, int rx1, int ry1,
                       int32_t *bx, int32_t *by,
                       int32_t *vx, int32_t *vy) {
    int x0 = *bx >> 8, x1 = x0 + BALL_SIZE - 1;
    int y0 = *by >> 8, y1 = y0 + BALL_SIZE - 1;

    // Penetracao contra a face oposta ao movimento; eixo parado nao concorre.
    const int LONGE = 0x7FFF;
    int p_x = (*vx > 0) ? (x1 - rx0 + 1) : ((*vx < 0) ? (rx1 - x0 + 1) : LONGE);
    int p_y = (*vy > 0) ? (y1 - ry0 + 1) : ((*vy < 0) ? (ry1 - y0 + 1) : LONGE);

    if (p_x <= p_y) {
        *bx = (*vx > 0) ? ((int32_t)(rx0 - BALL_SIZE) << 8)
                        : ((int32_t)(rx1 + 1) << 8);
        *vx = -*vx;
        return true;
    }
    *by = (*vy > 0) ? ((int32_t)(ry0 - BALL_SIZE) << 8)
                    : ((int32_t)(ry1 + 1) << 8);
    *vy = -*vy;
    return false;
}

bool phase_ball_collide(int32_t prev_x, int32_t prev_y,
                        int32_t *bx, int32_t *by,
                        int32_t *vx, int32_t *vy) {
    (void)prev_x; (void)prev_y;      // a face de saida vem da velocidade
    int x0 = *bx >> 8, x1 = x0 + BALL_SIZE - 1;
    int y0 = *by >> 8, y1 = y0 + BALL_SIZE - 1;

    // --- tijolos (somem ao serem atingidos) ---
    for (int c = 0; c < brick_cols; c++) {
        if (brick_alive[c] == 0) continue;
        int cx0 = brick_col_x[c];
        int cx1 = cx0 + BRICK_W - 1;
        if (x1 < cx0 || x0 > cx1) continue;

        int r0 = y0 / BRICK_H;
        int r1 = y1 / BRICK_H;
        if (r0 < 0) r0 = 0;
        if (r1 > BRICK_ROWS - 1) r1 = BRICK_ROWS - 1;

        for (int r = r0; r <= r1; r++) {
            if (!(brick_alive[c] & (1u << r))) continue;
            brick_alive[c] &= ~(1u << r);
            bounce_off(cx0, r * BRICK_H, cx1, (r + 1) * BRICK_H - 1,
                       bx, by, vx, vy);
            return true;
        }
    }

    // --- solidos (bumpers, coluna movel, rede) ---
    for (int i = 0; i < solid_count; i++) {
        const rect_t *s = &solids[i];
        if (x1 < s->x || x0 > s->x + s->w - 1) continue;
        if (y1 < s->y || y0 > s->y + s->h - 1) continue;
        bool eixo_x = bounce_off(s->x, s->y, s->x + s->w - 1, s->y + s->h - 1,
                                 bx, by, vx, vy);
        (void)eixo_x;
        if (cur_phase == PHASE_PINBALL || cur_phase == PHASE_COLUNA) {
            // Gira o vetor alguns graus para um lado ou para o outro: duas
            // faces paralelas devolvendo a bola sempre no mesmo angulo a
            // deixavam presa entre dois postes.
            int32_t s   = (get_rand_32() & 1) ? +1 : -1;
            int32_t nvx = *vx - s * (*vy >> BUMPER_SPIN_SHIFT);
            int32_t nvy = *vy + s * (*vx >> BUMPER_SPIN_SHIFT);
            *vx = nvx;
            *vy = nvy;
            if (*vx > -BALL_VX_MIN_Q && *vx < BALL_VX_MIN_Q)
                *vx = (*vx < 0) ? -BALL_VX_MIN_Q : BALL_VX_MIN_Q;
        }
        return true;
    }

    // --- o proprio fantasma rebate a bola ---
    if (cur_phase == PHASE_FANTASMA) {
        int gx1 = GHOST_X + RETROSC_MASCOTE_W - 1;
        int gy1 = ghost_y + RETROSC_MASCOTE_H - 1;
        if (!(x1 < GHOST_X || x0 > gx1 || y1 < ghost_y || y0 > gy1)) {
            bounce_off(GHOST_X, ghost_y, gx1, gy1, bx, by, vx, vy);
            return true;
        }
    }
    return false;
}

// =============================================================
// Partes moveis
// =============================================================
static bool overlap(int ax, int ay, int aw, int ah,
                    int bx, int by, int bw, int bh) {
    return !(ax >= bx + bw || ax + aw <= bx || ay >= by + bh || ay + ah <= by);
}

// A nave entra por cima ou por baixo e atravessa na diagonal. Fica presa a
// faixa SHIP_X_MIN..SHIP_X_MAX para nao passear em cima das raquetes.
static void ship_spawn(void) {
    uint32_t r = get_rand_32();
    bool de_cima = (r & 1) != 0;
    int  faixa   = SHIP_X_MAX - SHIP_X_MIN + 1;
    int32_t vx   = SHIP_VX_MIN_Q +
                   (int32_t)((r >> 8) % (SHIP_VX_MAX_Q - SHIP_VX_MIN_Q + 1));

    ship_x_q  = (int32_t)(SHIP_X_MIN + (int)((r >> 1) % faixa)) << 8;
    ship_y_q  = de_cima ? -((int32_t)SHIP_H << 8)
                        :  ((int32_t)FB_HEIGHT << 8);
    ship_vy_q = de_cima ? +SHIP_VY_Q : -SHIP_VY_Q;
    ship_vx_q = ((r >> 20) & 1) ? -vx : +vx;
    ship_on   = true;
}

static void update_nave(int32_t ball_x, int32_t ball_y,
                        int last_hitter, int bonus[2]) {
    if (!ship_on) {
        if (ship_left <= 0) return;             // ja passou o limite da fase
        if (--ship_wait <= 0) { ship_left--; ship_spawn(); }
        return;
    }
    ship_x_q += ship_vx_q;
    ship_y_q += ship_vy_q;

    int sx = ship_x_q >> 8;
    int sy = ship_y_q >> 8;
    if (sx < SHIP_X_MIN) { ship_x_q = (int32_t)SHIP_X_MIN << 8; ship_vx_q = -ship_vx_q; }
    if (sx > SHIP_X_MAX) { ship_x_q = (int32_t)SHIP_X_MAX << 8; ship_vx_q = -ship_vx_q; }
    if (sy > FB_HEIGHT || sy < -SHIP_H) { ship_sleep(); return; }

    sx = ship_x_q >> 8;
    if (overlap(ball_x >> 8, ball_y >> 8, BALL_SIZE, BALL_SIZE,
                sx, sy, SHIP_W, SHIP_H)) {
        // A bola atravessa a nave (nao desvia a jogada); quem rebateu por
        // ultimo leva o bonus.
        if (last_hitter == 0 || last_hitter == 1) bonus[last_hitter] += SHIP_BONUS;
        ship_sleep();
    }
}

static void update_coluna(void) {
    int max = FB_HEIGHT - coluna_span();
    col_y += col_dir * COL_SPEED;
    if (col_y >= max) { col_y = max; col_dir = -1; }
    if (col_y <= 0)   { col_y = 0;   col_dir = +1; }
    coluna_place();
}

static void update_fantasma(const int paddle_pos[2]) {
    ghost_y += ghost_dir * GHOST_SPEED;
    if (ghost_y > FB_HEIGHT - RETROSC_MASCOTE_H) {
        ghost_y = FB_HEIGHT - RETROSC_MASCOTE_H; ghost_dir = -1;
    }
    if (ghost_y < 0) { ghost_y = 0; ghost_dir = +1; }

    if (--ghost_cool <= 0) {
        ghost_cool = GHOST_SHOT_PERIOD;
        for (int i = 0; i < GHOST_SHOT_MAX; i++) {
            if (shots[i].on) continue;
            bool para_esquerda = (get_rand_32() & 1) != 0;
            shots[i].on = true;
            shots[i].y  = ghost_y + RETROSC_MASCOTE_H / 2;
            shots[i].x  = para_esquerda ? (GHOST_X - SHOT_W)
                                        : (GHOST_X + RETROSC_MASCOTE_W);
            shots[i].vx = para_esquerda ? -SHOT_SPEED : +SHOT_SPEED;
            break;
        }
    }

    rect_t seg[PADDLE_SEG_MAX];
    for (int i = 0; i < GHOST_SHOT_MAX; i++) {
        if (!shots[i].on) continue;
        shots[i].x += shots[i].vx;
        if (shots[i].x < -SHOT_W || shots[i].x > FB_WIDTH) {
            shots[i].on = false;
            continue;
        }
        int p = (shots[i].vx < 0) ? 0 : 1;
        int n = phase_paddle_segments(p, paddle_pos[p], seg);
        for (int k = 0; k < n; k++) {
            if (overlap(shots[i].x, shots[i].y, SHOT_W, SHOT_H,
                        seg[k].x, seg[k].y, seg[k].w, seg[k].h)) {
                shots[i].on = false;
                shrink[p] = SHRINK_FRAMES;
                break;
            }
        }
    }
}

void phase_update(int32_t ball_x, int32_t ball_y, const int paddle_pos[2],
                  int last_hitter, int bonus[2]) {
    bonus[0] = bonus[1] = 0;
    frame_ctr++;
    for (int p = 0; p < 2; p++) if (shrink[p] > 0) shrink[p]--;

    if (cur_flags & PF_TEM_NAVE) update_nave(ball_x, ball_y, last_hitter, bonus);
    if (cur_phase == PHASE_COLUNA)   update_coluna();
    if (cur_phase == PHASE_FANTASMA) update_fantasma(paddle_pos);
}

// =============================================================
// Desenho
// =============================================================
static void draw_nave(void) {
    if (!ship_on) return;
    int x = ship_x_q >> 8, y = ship_y_q >> 8;
    gfx_fill_rect(x + 5, y + 0, 3, 1, 1);
    gfx_fill_rect(x + 4, y + 1, 5, 1, 1);
    gfx_fill_rect(x + 3, y + 2, 7, 1, 1);
    gfx_fill_rect(x + 2, y + 3, 9, 1, 1);
    gfx_fill_rect(x + 0, y + 4, 13, 2, 1);
    gfx_fill_rect(x + 1, y + 6, 2, 2, 1);
    gfx_fill_rect(x + 5, y + 6, 3, 2, 1);
    gfx_fill_rect(x + 10, y + 6, 2, 2, 1);

    // "BONUS" piscando junto da nave (acima ou abaixo, o que couber na tela).
    if ((frame_ctr >> 4) & 1) return;
    const char *msg = "BONUS";
    int tw = gfx_text_width(msg, 1);
    int tx = x + SHIP_W / 2 - tw / 2;
    if (tx < 2) tx = 2;
    if (tx > FB_WIDTH - tw - 2) tx = FB_WIDTH - tw - 2;
    int ty = (y > FB_HEIGHT / 2) ? (y - FONT_CELL_H - 1) : (y + SHIP_H + 2);
    if (ty < 0) ty = 0;
    if (ty > FB_HEIGHT - FONT_CELL_H) ty = FB_HEIGHT - FONT_CELL_H;
    gfx_fill_rect(tx - 2, ty - 1, tw + 4, FONT_H + 2, 0);   // fundo preto
    gfx_text(tx, ty, msg, 1, 1);
}

void phase_draw(void) {
    for (int c = 0; c < brick_cols; c++) {
        for (int r = 0; r < BRICK_ROWS; r++) {
            if (!(brick_alive[c] & (1u << r))) continue;
            // 1 px de folga embaixo so para o olho separar os tijolos; a
            // colisao continua usando a linha inteira (BRICK_H).
            gfx_fill_rect(brick_col_x[c], r * BRICK_H, BRICK_W, BRICK_H - 1, 1);
        }
    }
    for (int i = 0; i < solid_count; i++)
        gfx_fill_rect(solids[i].x, solids[i].y, solids[i].w, solids[i].h, 1);

    if (cur_phase == PHASE_FANTASMA) {
        gfx_blit(retrosc_mascote_data, RETROSC_MASCOTE_W, RETROSC_MASCOTE_H,
                 GHOST_X, ghost_y, 1);
        for (int i = 0; i < GHOST_SHOT_MAX; i++)
            if (shots[i].on)
                gfx_fill_rect(shots[i].x, shots[i].y, SHOT_W, SHOT_H, 1);
    }

    if (cur_flags & PF_TEM_NAVE) draw_nave();
}
