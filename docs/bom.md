# Lista de Materiais (BOM)

Componentes para uma unidade do RetroSC Pong.

| Qtd | Componente                       | Especificação                | Observações                                |
| --: | -------------------------------- | ---------------------------- | ------------------------------------------ |
| 1   | Raspberry Pi Pico (ou clone)     | RP2040, 2 MB flash           | Modelo base; também serve Pico W           |
| 2   | Potenciômetro                    | 10 kΩ linear (tipo B)        | **CR22E c/ stopper** (preferencial) — veja "Potenciômetros" abaixo |
| 2   | Manopla / knob                    | Ø~32 mm × ~20 mm alt., furo 6 mm c/ flat/set screw | Veja "Knobs" abaixo     |
| 1   | Botão tátil (push button NA)     | 12 mm momentâneo             | START                                      |
| 1   | Resistor 470 Ω                   | 1/4 W, 5%                    | DAC vídeo (sync)                           |
| 1   | Resistor 220 Ω                   | 1/4 W, 5%                    | DAC vídeo (video)                          |
| 3   | Resistor 1 kΩ                    | 1/4 W                        | Filtro RC (1) + entradas L/R do amp (2)    |
| 1   | Capacitor 100 nF                 | cerâmico                     | Filtro RC                                  |
| 1   | Capacitor 1 µF                   | eletrolítico ou tântalo       | Acoplamento DC do áudio (obrigatório c/ chave no volume) |
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

## Potenciômetros — escolha por durabilidade

**Tier 1 — PREFERENCIAL (melhor custo × durabilidade):**
- **CR22E, 10 kΩ Linear, com Stopper** — plástico condutivo, vida útil
  **5×10⁶ ciclos**, linearidade ±1,5% (±1% versão precisão), ângulo elétrico
  320°, eixo **6 mm com flat (D)**, bushing **M9 × P0,75**, furo de painel
  Φ10,32 mm, corpo Φ22 mm, IP40, escova de liga de 6 elementos. Disponível em
  marketplaces (AliExpress etc.) por uma fração do preço do Sakae, com
  qualidade de plástico condutivo equivalente. **Atenção:** a versão padrão é
  360° (rotação contínua / sem fim) — peça obrigatoriamente a variante **"com
  stopper" (com batente)**; sem ela o eixo gira sem fim e o jogador sente uma
  zona morta de 40° acima/abaixo do curso elétrico.

**Tier 1 — premium (máxima durabilidade):**
- **Sakae FCP22E, 10 kΩ Linear (L), com Stopper** — plástico condutivo,
  vida útil ~10⁷ ciclos (2× o CR22E), eixo 6,35 mm, bushing M10. Mesmo cuidado
  com o stopper: sem ele há a mesma zona morta de 40°. Datasheet:
  [folheto Sakae FCP22E](https://www.sakae-tsushin.co.jp/) (ou via
  distribuidores Mouser/Digi-Key).

**Tier 2 (médio prazo):**
- Bourns 3852A-282-103AL ou similar conductive plastic com stopper.
- Vishay/Spectrol 248 series.

**Tier 3 (protótipo / hobby):**
- Qualquer pot 10 kΩ linear tipo B, eixo 6 mm, ~300° de rotação com
  batente. Funciona bem mas dura bem menos em uso intensivo de evento.
  Modelos comuns: Alpha RV16, WH148, ou os 10kΩ genéricos chineses.

### Como achar o modelo certo (termos de busca)

A variante "com stopper" aparece com **vários nomes** nos marketplaces. Procure
por qualquer um destes:

- **"with stopper" / "com batente"**
- **"end stop"** (ou "with end stop")
- **"single turn"** — single-turn = uma volta limitada (~270–320°) com batente,
  que é exatamente o que queremos.

E **evite** os termos que indicam o oposto (gira sem fim, com a zona morta):

- "endless" / "continuous rotation" / "360°" / "无限" (sem fim, em chinês)
- "multi-turn" / "multiturn" — são pots de várias voltas (ex.: 10-turn), de
  ajuste fino; lentos demais para controlar a raquete.

> Dica: em muitos anúncios do CR22E/equivalentes há um seletor "with stopper /
> without stopper" — confira que o escolhido é o **com** stopper antes de fechar.

> A linearidade (±15% é normal em pots baratos) NÃO é crítica — o software
> só mapeia ADC → posição vertical. O usuário não percebe não-linearidade
> abaixo de uns 10%. O que IMPORTA é: **vida útil** (arcade = muitos giros)
> e **suavidade** (sem "saltos" no sinal).

> **10 kΩ ou 5 kΩ?** Tanto faz para o ADC do RP2040 — o datasheet diz que a
> entrada tem impedância > 100 kΩ e dispensa buffer para sinais DC, então a
> impedância do pot (≤ 2,5 kΩ) é irrelevante. Ficamos com 10 kΩ por convenção
> e menor consumo. Detalhes em [docs/schematic.md](schematic.md#potenciômetros).

## Knobs / manoplas

**Recomendado: ~32 mm de diâmetro** (faixa útil 30–38 mm). Como os 320°
elétricos do pot mapeiam a tela inteira, esse diâmetro dá o percurso de dedo
ideal (~85–105 mm) para varrer toda a raquete numa pegada só — rápido o
suficiente para reagir e fino o suficiente para mirar.

| Diâmetro | Percurso do dedo (320°) | Sensação |
| -------: | ----------------------: | ----------------------------- |
| 20 mm    | ~56 mm                  | Nervoso, ajuste fino difícil  |
| **32 mm**| **~89 mm**              | **Ideal**                     |
| 38 mm    | ~106 mm                 | Confortável, leve folga       |
| 50 mm+   | ~140 mm                 | Lento, exige muito punho      |

**Altura recomendada: ~20 mm** (faixa útil 15–22 mm). Com Ø32 mm dá uma
proporção confortável para girar com polegar + 1–2 dedos. Abaixo de ~15 mm
falta superfície de pega; acima de ~25–30 mm o knob vira "alavanca" e força a
bucha do pot (folga/desgaste). O furo (bore) deve assentar em boa parte do
eixo (~14–15 mm dos ~15–17 mm úteis do CR22E) — não pode encostar só na ponta,
senão balança.

Especificação sugerida:

- **Ø ~32 mm × ~20 mm de altura** — ver tabelas acima.
- **Furo 6 mm com flat (D) ou parafuso de fixação (set screw)** — casa com o
  eixo do CR22E. Evite push-on de plástico genérico (solta no uso intenso).
- **Pegada serrilhada (knurled) ou canelada (fluted)** — dedo suado escorrega
  no acabamento liso.
- **Alumínio** dá peso e cara de arcade ("skirted knob"); ABS sólido serve e
  é mais barato.
- **Sem ponteiro/seta** — o controle é por feedback visual da raquete, não por
  posição absoluta.

> **Espaçamento no painel:** o corpo do pot é Φ22 mm. Com knobs de 32–38 mm,
> deixe ≥ ~45–50 mm entre centros se os dois ficarem lado a lado. Em Pong de
> 2 jogadores eles normalmente ficam em lados opostos, então raramente é
> problema.

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
