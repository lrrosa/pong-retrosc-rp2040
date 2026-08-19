# Lista de Materiais (BOM)

Componentes para **uma unidade** do RetroSC Pong. As referências (R1, C2, J4…)
são as mesmas do esquemático, da serigrafia da placa e dos arquivos KiCad —
use-as para conferir cada peça no lugar certo.

## 1. Componentes da placa

Tudo aqui vai **soldado na PCB** ([kicad/README.md](../kicad/README.md)).

| Ref | Qtd | Componente | Valor / especificação | Função |
| --- | --: | ---------- | --------------------- | ------ |
| R1 | 1 | Resistor 1/4 W | **470 Ω** | DAC de vídeo — sync |
| R2 | 1 | Resistor 1/4 W | **270 Ω** | DAC de vídeo — vídeo |
| R3 | 1 | Resistor 1/4 W | **1 kΩ** | filtro RC do áudio (com C1) |
| R4 | 1 | Resistor 1/4 W | **10 kΩ** | divisor de linha — série |
| R5 | 1 | Resistor 1/4 W | **1 kΩ** | divisor de linha — para GND |
| R6, R7 | 2 | Resistor 1/4 W | **1 kΩ** | entradas L e R do amplificador |
| C1 | 1 | Capacitor cerâmico | **100 nF** | filtro RC do áudio (com R3) |
| C2 | 1 | Capacitor **eletrolítico** | **1 µF** | acoplamento DC — **polarizado, + para o lado do GP18** |
| C3, C4 | 2 | Capacitor cerâmico | **100 nF** | filtro dos ADCs (um por potenciômetro) |
| U1 | 1 | Módulo RP2040 | Pico, YD de 3 botões ou "roxa" de 1 botão | **a variante da PCB depende do módulo** — ver [pinout.md](pinout.md) |
| U2 | 1 | Módulo amplificador | **PAM8403 (HW-012)**, 2×3 W, 5 V | com potenciômetro de volume embutido |
| J1 | 1 | Jack RCA fêmea | de painel, ângulo reto, THT | vídeo composto |
| J8, J9 | 2 | Jack RCA fêmea | de painel, ângulo reto, THT | áudio L e R |
| J4 | 1 | Barra de pinos 1×6 | passo 2,54 mm | chave de áudio A/B |
| J5, J6 | 2 | Barra de pinos 1×3 | passo 2,54 mm | potenciômetros P1 e P2 |
| J7 | 1 | Barra de pinos 1×2 | passo 2,54 mm | botão START |

> Somando por valor, para a compra: **4 × 1 kΩ** (R3, R5, R6, R7),
> **3 × 100 nF** (C1, C3, C4), 1 × 470 Ω, 1 × 270 Ω, 1 × 10 kΩ e 1 × 1 µF.
>
> **Os jacks RCA e o módulo do amp usam footprints feitos à mão** a partir de
> medidas das peças reais — confira o encaixe antes de mandar fabricar
> (imprima o **desenho de fabricação** em 1:1 e sobreponha as peças).

## 2. Peças de painel

Não vão na placa: ficam no gabinete e chegam à PCB por **fio**, nos headers
J4–J7. A função de cada pino está na serigrafia.

| Ref | Qtd | Componente | Especificação | Liga em |
| --- | --: | ---------- | ------------- | ------- |
| RV1, RV2 | 2 | Potenciômetro | **10 kΩ linear (tipo B), com batente** — ver seção abaixo | J5 e J6 |
| SW1 | 1 | Botão push NA | momentâneo, 12 mm | J7 |
| SW2 | 1 | Chave **DPDT** ON-ON | 2 polos / 6 pinos (serve uma seletora de tensão) | J4 |
| — | 2 | Manopla (knob) | Ø ~32 mm × ~20 mm, furo 6 mm | eixo dos pots |
| — | 1 | Alto-falante | 4–8 Ω, 3 W | plugado num RCA de áudio no modo B |

> A chave **SW2 seleciona o que sai pelos RCAs de áudio**: posição A = nível de
> linha para a TV; posição B = saídas do amplificador para caixa passiva. Ver
> [schematic.md](schematic.md#chave-ab--rcas-de-áudio-linha-p-tv-ou-saídas-do-amp)
> — inclusive os **cuidados obrigatórios** do modo B.

## 3. Montagem e cabos

| Qtd | Item | Especificação | Observação |
| --: | ---- | ------------- | ---------- |
| 1 | **PCB** | 2 camadas, 55 × 88 mm, HASL | envie o ZIP de gerbers da variante certa |
| 4 | Parafuso M3 + espaçador | furos H1–H4 | H2/H3 e H1/H4 têm 45 mm entre centros |
| 1 | Conector fêmea 1×6 | passo 2,54 mm | cabo da chave A/B (J4) |
| 1 | Conector fêmea 1×7 | passo 2,54 mm | **serve os dois pots de uma vez** (J5+J6, com o contato do meio vago) |
| 1 | Conector fêmea 1×2 | passo 2,54 mm | cabo do botão (J7) |
| 1 | Cabo USB | micro-USB (Pico) ou **USB-C** (clones) | alimentação e gravação |
| — | Fio AWG 24–26 flexível | | painel → headers |

> Sem PCB dá para montar tudo em placa universal de 2,54 mm, como foi o
> protótipo — a pinagem é a mesma.

## Opcional / arcade

| Qtd | Componente | Observações |
| --: | ---------- | ----------- |
| 1 | TV CRT pequena (5–14") | visual autêntico; precisa de entrada AV |
| 1 | Fonte USB 5 V / 1 A | alimenta o conjunto sem PC |
| — | Madeira / MDF p/ gabinete | caixa compatível com a TV |
| — | Adesivos / artes | logo RetroSC nas laterais |

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

- **Resistores DAC**: 220 Ω no lugar do 270 Ω também funciona (branco ~1,1 V,
  um pouco "quente" — o 270 Ω foi validado na TV real com imagem melhor).
  Evite 1 kΩ + 470 Ω: branco despenca para ~0,6 V (imagem escura).
- **Amplificador**: LM386 com 8 componentes externos, TDA2030, ou módulos
  prontos baseados em PAM8302/PAM8403.
- **Módulo RP2040 (U1)**: além do Pico oficial, o projeto tem placa para a
  YD-RP2040 de 3 botões e para a "roxa" de 1 botão. Outros clones funcionam se
  expuserem GP16–18, GP22, GP26 e GP27 — mas confira a **posição física** de
  cada um em [pinout.md](pinout.md): elas variam entre clones, e é isso que
  decide qual variante de PCB fabricar.

## Custo estimado (Brasil, 2026)

- RP2040 board: R$ 35–60
- Pots + manoplas: R$ 15
- Amp + alto-falante: R$ 25
- Resistores / capacitores / botão / RCA / headers: R$ 15
- PCB (5 un. em fábrica china, sem frete): ~R$ 10/un.
- **Total eletrônico: ~R$ 100–125** (sem TV e gabinete)
