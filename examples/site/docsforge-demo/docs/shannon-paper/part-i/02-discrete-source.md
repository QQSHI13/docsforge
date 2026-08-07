---
tags:
  - information-theory
  - entropy
  - stochastic-process
---

# 2. The Discrete Source of Information

## From Channels to Sources

Section 1 asked: *how fast can a channel carry information?* Now we ask the complementary question: *how fast does a source produce information?*

The answer depends critically on the **statistical structure** of the source. English text is not random — "E" appears far more often than "Z", "TH" is common while "XP" is rare. This structure means English carries **less than maximum** information per symbol, and we can exploit that for compression.

---

## Stochastic Process Model

A **discrete source** is modeled as a **stochastic process** that generates a sequence of symbols from a finite alphabet. At each step, the next symbol is chosen according to probabilities that may depend on previous choices.

Formally, a discrete source is any stochastic process producing a sequence:

$$
X_1, X_2, X_3, \ldots
$$

where each $X_i \in \{s_1, s_2, \ldots, s_n\}$.

!!! info "Types of Sources Covered"
    1. **Natural languages** — English, German, Chinese
    2. **Quantized continuous signals** — PCM speech, digital video
    3. **Abstract mathematical processes** — purely defined by probability rules

---

## Independence vs. Dependence

### Case A: Independent, Equiprobable Symbols

Five letters A, B, C, D, E each with probability $0.2$, independent choices:

```
B D C B C E C C A D C B D D A A E C E E A
A B B D A E E C A C E E B A E E C B C E A D
```

This is **maximum entropy** — every symbol carries $\log_2 5 \approx 2.32$ bits.

### Case B: Independent, Non-Uniform

Probabilities: A=0.4, B=0.1, C=0.2, D=0.2, E=0.1:

```
A A A C D C B D C E A A D A D A C E D A
E A D C A B E D A D D C E C A A A A A D
```

"A" dominates. The entropy is lower because some outcomes are predictable.

### Case C: Markov Dependence

The probability of the next symbol depends on the **previous symbol** (first-order Markov). Define **transition probabilities** $p_i(j)$ = probability that letter $i$ is followed by letter $j$.

Also define **digram probabilities** $p(i,j)$ = relative frequency of the pair $ij$.

The relations:

$$
p(i) = \sum_j p(i,j) = \sum_j p(j,i) = \sum_j p(j) p_j(i)
$$

$$
p(i,j) = p(i) \, p_i(j)
$$

$$
\sum_j p_i(j) = \sum_i p(i) = \sum_{i,j} p(i,j) = 1
$$

!!! example "Three-Letter Example"
    Letters A, B, C with transition matrix:
    
    | $p_i(j)$ | A | B | C |
    |----------|---|---|---|
    | **A**    | 0 | 4/5 | 1/5 |
    | **B**    | 1/2 | 1/2 | 0 |
    | **C**    | 1/2 | 1/10 | 2/5 |
    
    Stationary distribution: $p(A) = 9/27$, $p(B) = 16/27$, $p(C) = 2/27$
    
    A typical sequence: A B A C A B C A B C A C B C B A B C A B A...
    
    Notice: after A, almost always B; after B, about half A and half C.

---

## Higher-Order Structure

**$n$-gram structure**: the probability of a symbol depends on the previous $n-1$ symbols.

| Order | Model | Description |
|-------|-------|-------------|
| 0 | Independent, uniform | No structure |
| 1 | Independent, with frequencies | Letter probabilities only |
| 2 | Digram | $P(x_k \mid x_{k-1})$ |
| 3 | Trigram | $P(x_k \mid x_{k-1}, x_{k-2})$ |
| Word-1 | Word frequencies | Independent words |
| Word-2 | Word transitions | $P(w_k \mid w_{k-1})$ |

Higher order = more structure = more predictability = lower entropy rate = more compressible.

---

## The Source Entropy Rate

For a source with states (as in Section 1's channel model), each state $i$ has its own entropy $H_i$ based on the probabilities $p_i(j)$ of symbols it can emit.

The **source entropy** (per symbol) is the weighted average:

$$
H = \sum_i P_i H_i = -\sum_{i,j} P_i \, p_i(j) \log p_i(j)
$$

where $P_i$ is the stationary probability of being in state $i$.

For an independent source with probabilities $p_1, \ldots, p_n$:

$$
H = -\sum_{i=1}^{n} p_i \log p_i
$$

This is the famous **Shannon entropy formula** — the average information produced per symbol.

---

## Why This Matters for Coding

If a source produces information at rate $H$ bits per symbol, and a channel has capacity $C$ bits per second, then:

- **If $H \leq C$**: We can encode the source and transmit it (perhaps with delay)
- **If $H > C$**: We must either compress (loseless if $H$ can be reduced by better modeling) or accept information loss

Morse code already exploits this informally: "E" (most common) gets the shortest symbol (dot), while "Q, X, Z" get longer sequences. Shannon will prove this intuition is optimal.

---

*Next: [§3 — The Series of Approximations to English](03-approximations-to-english.md)*
