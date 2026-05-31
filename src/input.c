#include "input.h"
#include "config.h"

#include "pico/stdlib.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"

#define FILTER_ALPHA  3                 // suaviza: novo = (3*ant + novo)/4
#define MOVE_THRESH   40                // delta minimo (em unidades ADC) p/ "moveu"
#define MOVE_HISTORY  20                // janela de frames para detectar movimento

static uint16_t raw[2]      = { 2048, 2048 };
static uint16_t filtered[2] = { 2048, 2048 };
static uint16_t baseline[2] = { 2048, 2048 };
static int moved_frames = 0;
static bool last_button = false;
static bool button_edge = false;

void input_init(void) {
    // Forca o SMPS da placa Pico em modo PWM (GPIO23 alto) para reduzir o
    // ripple no supply do ADC -> leituras dos pots mais limpas. Inofensivo em
    // clones onde esse pino nao tem essa funcao. (Datasheet do Pico, sec. 4.3.)
    gpio_init(PICO_SMPS_PS_PIN);
    gpio_set_dir(PICO_SMPS_PS_PIN, GPIO_OUT);
    gpio_put(PICO_SMPS_PS_PIN, 1);

    adc_init();
    adc_gpio_init(POT_P1_GPIO);
    adc_gpio_init(POT_P2_GPIO);

    gpio_init(START_BUTTON_PIN);
    gpio_set_dir(START_BUTTON_PIN, GPIO_IN);
    gpio_pull_up(START_BUTTON_PIN);

    // primeira leitura para "armar" baseline
    adc_select_input(POT_P1_ADC); raw[0] = filtered[0] = baseline[0] = adc_read();
    adc_select_input(POT_P2_ADC); raw[1] = filtered[1] = baseline[1] = adc_read();
}

void input_poll(void) {
    adc_select_input(POT_P1_ADC); raw[0] = adc_read();
    adc_select_input(POT_P2_ADC); raw[1] = adc_read();

    for (int i = 0; i < 2; i++) {
        filtered[i] = (filtered[i] * FILTER_ALPHA + raw[i]) / (FILTER_ALPHA + 1);
        int delta = (int)filtered[i] - (int)baseline[i];
        if (delta < 0) delta = -delta;
        if (delta > MOVE_THRESH) {
            moved_frames = MOVE_HISTORY;
            baseline[i] = filtered[i];
        }
    }
    if (moved_frames > 0) moved_frames--;

    bool now = !gpio_get(START_BUTTON_PIN);   // pull-up: pressed = LOW
    button_edge = (now && !last_button);
    last_button = now;
}

int input_pot_raw(int player) {
    return filtered[player & 1];
}

int input_paddle_y(int player) {
    uint16_t v = filtered[player & 1];
    int range = FB_HEIGHT - PADDLE_H;
    int y = (v * range) / 4095;
    if (y < 0) y = 0;
    if (y > range) y = range;
    return y;
}

bool input_start_pressed(void) {
    return button_edge;
}

bool input_movement_detected(void) {
    return moved_frames > 0;
}

void input_reset_movement(void) {
    moved_frames = 0;
    baseline[0] = filtered[0];
    baseline[1] = filtered[1];
}
