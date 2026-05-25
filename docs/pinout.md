# Pinout do RP2040 (Raspberry Pi Pico)

| Pino físico | GPIO   | Função          | Direção | Observações                                 |
| ----------- | ------ | --------------- | ------- | ------------------------------------------- |
| 21          | GP16   | NTSC SYNC       | OUT     | Vai para resistor 470 Ω → composto          |
| 22          | GP17   | NTSC VIDEO      | OUT     | Vai para resistor 220 Ω → composto          |
| 24          | GP18   | AUDIO PWM       | OUT     | Filtro RC + amp                             |
| 29          | GP22   | START BUTTON    | IN      | Pull-up interno, push-button para GND       |
| 31          | GP26 / ADC0 | POT P1     | AIN     | Wiper do pot esquerdo                       |
| 32          | GP27 / ADC1 | POT P2     | AIN     | Wiper do pot direito                        |
| 36          | 3V3 OUT | 3,3 V          | -       | Alimenta os extremos dos potenciômetros    |
| 38          | GND     | GND            | -       | Massa comum                                 |
| 40          | VBUS    | +5 V do USB    | -       | (ou VSYS pino 39 com fonte externa)         |

> **Pinos físicos** seguem a numeração padrão do módulo Raspberry Pi Pico
> (1–40), pino 1 no canto superior esquerdo do BOOTSEL.

> Os GPIOs estão fixados em [src/config.h](../src/config.h) — altere lá se
> precisar realocar.

## Por que estes GPIOs?

- **GP16/17** ficam adjacentes e permitem usar 2 pinos consecutivos como
  saída do PIO (sync + dados), o que simplifica o programa PIO.
- **GP26/27** são os únicos ADC com baixo ruído (GP28 também serve mas
  costuma ser usado para outros fins). Os capacitores de 100 nF entre wiper
  e GND filtram ruído de comutação do conversor.
- **GP18** está livre de DMA crítico e é PWM canal A do slice 1.
- **GP22** é o pino físico imediatamente após GP21 (não usado), boa
  ergonomia de cabeamento.
