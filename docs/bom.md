# Lista de Materiais (BOM)

Componentes para uma unidade do RetroSC Pong.

| Qtd | Componente                       | Especificação                | Observações                                |
| --: | -------------------------------- | ---------------------------- | ------------------------------------------ |
| 1   | Raspberry Pi Pico (ou clone)     | RP2040, 2 MB flash           | Modelo base; também serve Pico W           |
| 2   | Potenciômetro                    | 10 kΩ linear (tipo B)        | Eixo longo para manopla externa            |
| 2   | Manopla / knob                    | Encaixe 6 mm                 | Estética arcade                            |
| 1   | Botão tátil (push button NA)     | 12 mm momentâneo             | START                                      |
| 1   | Resistor 470 Ω                   | 1/4 W, 5%                    | DAC vídeo (sync)                           |
| 1   | Resistor 220 Ω                   | 1/4 W, 5%                    | DAC vídeo (video)                          |
| 1   | Resistor 1 kΩ                    | 1/4 W                        | Filtro RC do áudio                         |
| 1   | Capacitor 100 nF                 | cerâmico                     | Filtro RC                                  |
| 1   | Capacitor 1 µF                   | eletrolítico ou tântalo       | Acoplamento DC do áudio                    |
| 2   | Capacitor 100 nF                 | cerâmico                     | Filtragem dos ADCs                         |
| 1   | Módulo amplificador              | PAM8403 (3 W) ou similar     | Alimentação 5 V                            |
| 1   | Alto-falante                     | 4–8 Ω, 1–3 W                 | Tamanho conforme caixa                     |
| 1   | Conector RCA (jack ou cabo)      | composto                     | Para saída de vídeo                        |
| 1   | Cabo USB                         | micro-USB (Pico clássico)    | Alimentação                                |
| -   | Protoboard ou placa universal    | 400+ pontos                  | Para protótipo; PCB para versão final       |
| -   | Jumpers ou fio rígido AWG 24     |                              | Cabeamento                                 |

## Opcional / arcade

| Qtd | Componente                       | Observações                                |
| --: | -------------------------------- | ------------------------------------------ |
| 1   | TV CRT pequena (5–14")           | Para visual autêntico; com entrada AV      |
| 1   | Fonte USB 5 V / 1 A              | Para alimentar o Pico sem PC               |
| -   | Madeira / MDF p/ gabinete        | Caixa arcade compatível com a TV           |
| -   | Adesivos / artes                 | Logo RetroSC nas laterais                  |

## Substituições aceitáveis

- **Resistores DAC**: 1 kΩ + 470 Ω também funciona, mas com branco em
  ~0,6 V (imagem mais escura). 560 + 270 dá resultado muito similar.
- **Amplificador**: LM386 com 8 componentes externos, TDA2030, ou módulos
  prontos baseados em PAM8302/PAM8403.
- **Pico**: qualquer placa baseada em RP2040 com pelo menos os GPIOs
  necessários expostos (GP16–18, GP22, GP26, GP27).

## Custo estimado (Brasil, 2026)

- RP2040 board: R$ 35–60
- Pots + manoplas: R$ 15
- Amp + alto-falante: R$ 25
- Resistores / capacitores / botão / RCA: R$ 10
- **Total eletrônico: ~R$ 90–110** (sem TV e gabinete)
