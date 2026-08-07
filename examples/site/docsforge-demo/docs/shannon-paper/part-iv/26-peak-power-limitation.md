---
tags:
  - information-theory
  - peak-power
  - constrained-optimization
---

# 26. The Channel Capacity with a Peak Power Limitation

## Average vs. Peak Power

Section 25 assumed average power was limited to $P$. Many systems also have **peak power** constraints — the instantaneous signal amplitude cannot exceed $A$.

This changes the optimal input distribution and the capacity formula.

---

## The Constraint

$$|x(t)| \leq A \quad \text{for all } t$$

Under this constraint, the signal cannot be Gaussian (Gaussian has infinite support). The maximum entropy distribution on $[-A, A]$ with given variance is more complex.

---

## Capacity Formula

For additive white Gaussian noise with peak amplitude constraint $A$ and noise variance $\sigma^2$:

$$
C = W \log_2 \left(\frac{A + \sigma}{\sigma}\right)
$$

(approximate form; exact requires numerical optimization).

More precisely, capacity is found by optimizing over input distributions on $[-A, A]$:

$$
C = \max_{p(x): |x| \leq A} I(x; x+n)
$$

---

## Comparison: Peak vs. Average

| Constraint | Optimal Input | Capacity Trend |
|-----------|---------------|----------------|
| Average power $P$ | Gaussian | $\sim W \log(P/N)$ |
| Peak amplitude $A$ | Non-Gaussian (often uniform-like) | $\sim W \log(A/\sigma)$ |
| Both | Truncated/constrained Gaussian | Complex optimization |

For the same numerical power ($P = A^2$), peak-limited capacity is lower because the Gaussian input is forbidden.

---

## Optical Communication

Fiber optic channels are fundamentally peak-power limited:
- Laser intensity cannot be negative
- High peak intensity causes nonlinear effects in the fiber
- The "linear regime" requires peak power constraints

Capacity is lower than the Shannon–Hartley formula would suggest, and modern research focuses on nonlinear channel capacity.

---

## Modern Wireless Systems

Cellular and WiFi have both constraints:
- Average: limited by regulations and battery
- Peak: limited by amplifier linearity (PAPR — Peak-to-Average Power Ratio)

High PAPR signals (like OFDM) are problematic. Techniques to reduce PAPR include:
- Clipping (deliberate distortion)
- Tone reservation
- Active constellation extension

These are all attempts to stay near the Shannon limit while respecting peak constraints.

---

*End of Part IV. Next: [Part V — The Rate for a Continuous Source](../part-v/27-fidelity-evaluation.md)*
