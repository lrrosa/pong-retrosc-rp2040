# Peças do gabinete — como escolher e comprar

Detalhamento das peças **mecânicas e de painel** do RetroSC Pong: quais
potenciômetros duram num arcade, que manopla dá a melhor pegada e o que mais
entra na caixa. As quantidades e as referências estão na
[lista de materiais](bom.md) — aqui é sobre **qual modelo comprar**.

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

## Opcional / arcade

| Qtd | Componente | Observações |
| --: | ---------- | ----------- |
| 1 | TV CRT pequena (5–14") | visual autêntico; precisa de entrada AV |
| 1 | Fonte USB 5 V / 1 A | alimenta o conjunto sem PC |
| — | Madeira / MDF p/ gabinete | caixa compatível com a TV |
| — | Adesivos / artes | logo RetroSC nas laterais |
