# Esquemático

Esquemático em ASCII (referência para protoboard ou PCB). Para um
diagrama gráfico, recomenda-se reconstruir em KiCad ou EasyEDA usando estas
informações.

```
                          Raspberry Pi Pico (RP2040)
                       +-----------------------------+
                       |  USB                        |
                       |                             |
                       |  GP16 (pino 21) -- SYNC --+ |
                       |  GP17 (pino 22) -- VIDEO -+-|---+---R1=470 Ω---+----- composto (RCA center)
                       |  GP18 (pino 24) -- AUDIO -|--+                 |
                       |                           |  |  R2=220 Ω <-----+ (do GP17)
                       |  GP22 (pino 29) -- START -|  |  |
                       |                           |  |  + (composto)
                       |  GP26 (pino 31) <- P1 ----|--|--|---+ (wiper P1)
                       |  GP27 (pino 32) <- P2 ----|--|--|---|----+ (wiper P2)
                       |                           |  |  |   |    |
                       |  3V3 (pino 36) ------------> |  |   |    |
                       |  GND (pino 38) ----+         |  |   |    |
                       |  VBUS(pino 40) -----------+  |  |   |    |
                       +---------------------------|--|--|---|----+
                                                   |  |  |   |
                                                   |  |  |   |
                                                   |  |  |   |
   (DAC para video composto)                       v  v  v   v
                                                                                
                                                                                
   +----------------+                                                            
   | SYNC pin GP16  |----R1 = 470 Ω-----+                                        
   +----------------+                   |                                        
                                        +----o----+---o RCA Center (composto)   
   +----------------+                   |    |    |                              
   | VIDEO pin GP17 |----R2 = 220 Ω-----+    |    +---o RCA Shield (GND)         
   +----------------+                        |                                   
                                            === 75 Ω terminacao opcional         
                                             |                                   
                                            GND                                  
```

## DAC de vídeo composto (2 resistores)

Combina os 2 pinos GPIO num sinal de 3 níveis lido pela TV:

| GP16 (SYNC) | GP17 (VIDEO) | Tensão na TV (75 Ω carga) | Significado          |
| :---------: | :----------: | :-----------------------: | -------------------- |
| 0           | 0            | 0,00 V                    | Sync tip             |
| 1           | 0            | ~0,35 V                   | Black (blanking)     |
| 1           | 1            | ~1,10 V                   | White                |
| 0           | 1            | (não usado)               | -                    |

Cálculo (Thevenin, 3,3 V, R1=470, R2=220, term=75):

```
G = 1/470 + 1/220 + 1/75 = 0,02001 S
V_black = (3.3/470) / G = 0,351 V
V_white = (3.3/470 + 3.3/220) / G = 1,103 V
```

> **Por que não 1 kΩ + 470 Ω?** Funciona, mas o nível branco fica em ~0,63 V
> (imagem escura). Os valores acima dão um Vpp próximo do ideal de 1 V.

## Áudio (PWM filtrado + amplificador)

```
                     R3=1k                                 +---- entrada IN+ do PAM8403
   GP18 -----------/\/\/\------+-----+------+--------------+
                               |     |      |
                              ===   ===    ===
                              C1    C2     (saida do filtro)
                              100n   1u
                               |     |
                              GND   GND   ----- entrada IN- do PAM8403 (= GND)
```

- **R3 = 1 kΩ + C1 = 100 nF**: filtro RC passa-baixa (fc ≈ 1,6 kHz). Remove
  componentes do PWM, deixando passar os beeps do Pong (até ~500 Hz).
- **C2 = 1 µF**: capacitor de acoplamento DC, opcional dependendo do amp.

Amplificador sugerido: **PAM8403** (módulo barato, 3 W). Saída direta para
alto-falante de 4–8 Ω (3 W). Ajustar potenciômetro de volume do módulo, ou
adicionar um trimpot de 10 kΩ entre o filtro e a entrada do amp.

Alternativa minimalista: alto-falante de PC (8 Ω) direto via capacitor de
acoplamento de 10 µF — volume baixo, mas funciona.

## Potenciômetros

```
   +3V3 ---+
           |
          [pot 10K linear]  <-- wiper -----> GPIO (26 ou 27)
           |                          |
          GND                       100nF
                                      |
                                     GND
```

- **Linear** (tipo B / "L"). Logarítmico (tipo A) também funciona mas o
  movimento fica não-uniforme.
- O capacitor de 100 nF entre wiper e GND reduz ruído do ADC.
- **Para arcade:** preferencial **CR22E 10 kΩ Linear com stopper** (plástico
  condutivo, 5×10⁶ ciclos, eixo 6 mm com flat, bushing M9). Alternativa
  premium: Sakae FCP22E (~10⁷ ciclos, eixo 6,35 mm, bushing M10). Em ambos o
  **stopper é obrigatório**: sem ele o eixo gira sem batente e o jogador
  encontra uma "zona morta" de 40° acima/abaixo do curso elétrico (que é
  320°). Veja [docs/bom.md](bom.md).
- Furação do painel: **10,5 mm** (ambos os bushings — M9 do CR22E e M10 do
  FCP22E — pedem furo de Φ10,32 mm).

## Botão START

```
   GPIO22 ---+----[ botão NA ]---- GND
             |
             (pull-up interno habilitado em software)
```

Push-button momentâneo. Quando aberto, GP22 fica em 3,3 V (via pull-up
interno). Quando pressionado, GP22 vai a GND e o software detecta o
flanco de descida.

## Alimentação

- USB do Pico (5 V): suficiente para o RP2040 e os 2 potenciômetros.
- O PAM8403 precisa de 5 V — pode ser pegado em **VBUS** (pino 40) do Pico.
- Se usar uma fonte externa, ligue em **VSYS** (pino 39) e o RP2040 regula
  para 3,3 V. NÃO ligue 5 V em 3V3 OUT.
- Aterramento comum (GND): conecte o GND da fonte/USB, do amp, dos
  potenciômetros e do RCA juntos.

## Saída para TV

- Cabo composto RCA padrão (geralmente amarelo).
- Conectar o **center** (positivo) na saída do DAC, e o **shield** no GND.
- Funciona em CRTs (com entrada AV/composto) e na maioria das TVs LCD com
  entrada AV preservada. Em PAL-M (Brasil), a maioria das TVs aceita NTSC
  monocromático sem cor sem problema.
