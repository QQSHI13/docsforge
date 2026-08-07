---
tags:
  - information-theory
  - continuous-channel
  - channel-capacity
---

# 24. The Capacity of a Continuous Channel

## Extending to Continuous Signals

A continuous channel transmits functions of time rather than discrete symbols. The same fundamental question applies: what is the maximum rate of reliable information transmission?

---

## Definition

For a continuous channel with input ensemble $x(t)$, output ensemble $y(t)$, and transition probability measure $P_x(y)$:

$$
C = \max_{p(x)} I(x; y) = \max_{p(x)} [H(y) - H_x(y)]
$$

Where:
- $H(y)$ = differential entropy of the output
- $H_x(y)$ = conditional entropy of output given input (= entropy of the noise, if noise is independent)

---

## Additive Noise Channel

For the most important case — **additive noise** where $y(t) = x(t) + n(t)$ with signal $x$ and noise $n$ independent:

$$
H_x(y) = H(n)
$$

The equivocation equals the noise entropy regardless of the signal. Therefore:

$$
C = \max_{p(x)} [H(x + n) - H(n)]
$$

Maximizing over input distributions.

---

## The Band-Limited Gaussian Channel

For a band-limited channel (bandwidth $W$) with additive white Gaussian noise of power spectral density $N_0/2$:

- Noise power in band: $N = N_0 W$
- Signal power constraint: $P$
- The input that maximizes entropy for a given power is **Gaussian**
- Output $x + n$ is then also Gaussian with power $P + N$

---

*Next: [§25 — Channel Capacity with an Average Power Limitation](25-average-power-limitation.md)*
