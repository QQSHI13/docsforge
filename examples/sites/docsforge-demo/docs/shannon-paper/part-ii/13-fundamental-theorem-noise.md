---
tags:
  - information-theory
  - noisy-channel-coding-theorem
  - shannon-theorem
---

# 13. The Fundamental Theorem for a Discrete Channel with Noise

## Shannon's Second Theorem

This is arguably the most important result in information theory. It proves that **reliable communication over noisy channels is possible at any rate below capacity** — and impossible above it.

---

## Theorem Statement

Let a discrete channel have capacity $C$ and let a discrete source have entropy $H$ bits per second.

**Part 1 (Achievability):** If $H \leq C$, there exists a coding system such that the output of the source can be transmitted over the channel with **arbitrarily small frequency of errors** (or equivocation). This is true even if $H = C$ exactly, though the delay and complexity may grow.

**Part 2 (Converse):** If $H > C$, it is impossible to transmit with arbitrarily small error frequency. No coding scheme can overcome the noise when demanded rate exceeds capacity.

---

## The Shock and the Revolution

Before Shannon, engineers believed noise set a fundamental limit on reliability. You could reduce error by:
- Repeating messages (but this wastes bandwidth)
- Increasing power (but this is expensive)
- Better hardware (but noise is fundamental)

Shannon proved: **as long as rate < C, errors can be made arbitrarily small without infinite power or bandwidth** — just with clever enough coding and sufficiently long blocks.

This transformed communication engineering from an art into a science.

---

## Proof Sketch: Random Coding

### Step 1: The Typical Set

Consider transmitting $N$ symbols. The input sequence $x^N$ is typical with probability $\approx 2^{-NH(x)}$. The output sequence $y^N$ is typical with probability $\approx 2^{-NH(y)}$.

### Step 2: The Ambiguity Set

For a given received $y^N$, the set of inputs that could have produced it (the "ambiguity set") contains about:

$$
2^{N H_y(x)} = 2^{N(H(x) - I(x;y))}
$$

elements.

### Step 3: Random Codebook

Choose $2^{NR}$ codewords at random from the typical set. If $R < I(x;y) \leq C$, then:
- The ambiguity set size $2^{N(H(x)-I)}$ is smaller than the total typical set $2^{NH(x)}$
- The probability that two codewords fall in the same ambiguity set $\to 0$ as $N \to \infty$
- The decoder can uniquely identify the transmitted codeword with high probability

### Step 4: Error Analysis

For any $\epsilon > 0$, choose $N$ large enough that:
- Typical set captures probability $1-\epsilon$
- Random codebook has collision probability $\u003c \epsilon$
- Overall error probability $\u003c 2\epsilon$

Since $\epsilon$ is arbitrary, errors can be made arbitrarily small.

---

## Why This Is Not a Constructive Proof

The random coding proof shows codes **exist** but doesn't tell you how to find them. For 50 years after Shannon, researchers sought practical codes that approached capacity:

| Era | Code Type | Distance from Capacity |
|-----|-----------|----------------------|
| 1950s | Hamming codes | Far |
| 1960s | BCH, Reed-Solomon | Moderate |
| 1990s | Turbo codes (Berrou) | Within ~0.5 dB |
| 2000s | LDPC codes, Polar codes | Essentially at capacity |

---

## Converse Proof

If rate $R > C$, then by Fano's inequality:

$$
H(x^N | y^N) \geq N(R - C) - 1
$$

The equivocation grows linearly with $N$. No matter the code, the decoder cannot resolve $\approx 2^{N(R-C)}$ equally likely messages. Error probability $\to 1$ as $N \to \infty$.

---

## Practical Implications

| System | Typical Rate vs. Capacity |
|--------|--------------------------|
| Deep Space (Voyager) | RS + Convolutional, ~50% of C |
| Cellular (3G/4G/5G) | Turbo/LDPC, ~80-95% of C |
| WiFi | LDPC, ~90% of C |
| Fiber Optics | LDPC + soft decision, ~95% of C |
| Satellite (DVB-S2) | LDPC, ~90% of C |

Modern systems operate within 0.5 dB of the Shannon limit — essentially achieving what Shannon proved possible in 1948.

---

*Next: [§14 — Discussion](14-discussion.md)*
