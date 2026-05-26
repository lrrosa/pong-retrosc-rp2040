#ifndef PONG_CONFIG_H
#define PONG_CONFIG_H

// ===== Pinos =====
// Video composto: DAC resistivo de 2 bits.
//   SYNC_PIN  --[470 ohm]--+
//   VIDEO_PIN --[220 ohm]--+---- RCA center (composite out)
//                          +---- 75 ohm  ---- GND (terminacao da TV)
#define NTSC_SYNC_PIN     16
#define NTSC_VIDEO_PIN    17

// Audio: PWM em um GPIO, filtro RC, depois amplificador
//   AUDIO_PIN --[1k]--+---- entrada do amp
//                     |
//                    100nF
//                     |
//                    GND
#define AUDIO_PIN         18

// Botao de START (push-button para GND, pull-up interno habilitado)
#define START_BUTTON_PIN  22

// Potenciometros 10K (ADC). Wiper para o GPIO, extremos para 3V3 e GND.
//   GPIO 26 = ADC0 = P1
//   GPIO 27 = ADC1 = P2
#define POT_P1_GPIO       26
#define POT_P2_GPIO       27
#define POT_P1_ADC        0
#define POT_P2_ADC        1

// ===== Video =====
#define FB_WIDTH          256
#define FB_HEIGHT         192
#define FB_STRIDE_WORDS   (FB_WIDTH / 32)   // 8 words por linha
#define FB_WORDS          (FB_STRIDE_WORDS * FB_HEIGHT)

#define LINES_PER_FRAME   262
#define LINES_VSYNC       3
#define LINES_TOP_BLANK   22
#define LINES_ACTIVE      FB_HEIGHT          // 192
#define LINES_BOT_BLANK   (LINES_PER_FRAME - LINES_VSYNC - LINES_TOP_BLANK - LINES_ACTIVE)

// ===== Audio =====
#define AUDIO_SAMPLE_RATE 22050
#define PWM_TOP           1023               // 10-bit PWM

// ===== Jogo =====
#define WIN_SCORE         7                  // pontos para vencer
#define PADDLE_W          3
#define PADDLE_H          24
#define BALL_SIZE         3
#define PADDLE_MARGIN     6                  // distancia das raquetes ate as bordas
#define BALL_SPEED_INIT_Q 0x180              // velocidade inicial (1.5 px/frame em Q8)
#define BALL_SPEED_MAX_Q  0x500              // velocidade max (5 px/frame em Q8)
#define BALL_SPEED_STEP_Q 0x020              // incremento por rebatida
#define ATTRACT_TIMEOUT_S 20                 // segundos antes de voltar a attract

// ===== Highscores =====
#define HISCORE_COUNT     5
#define HISCORE_MAGIC     0x50524F4Bu        // 'PROK'
#define HISCORE_VERSION   2                  // v2: adicionou iniciais de 3 chars
#define INITIALS_LEN      3                  // letras por entrada

#endif // PONG_CONFIG_H
