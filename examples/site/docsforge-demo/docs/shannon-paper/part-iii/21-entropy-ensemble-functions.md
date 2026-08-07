---
tags:
  - information-theory
  - entropy-rate
  - stochastic-process
---

# 21. Entropy of an Ensemble of Functions

## Entropy Rate for Continuous Time

For a continuous-time stochastic process $\{x(t)\}$, we define the **entropy rate** per unit time:

$$
h = \lim_{T \to \infty} \frac{H(x(t) : 0 \leq t \leq T)}{T}
$$

This is the continuous analog of the entropy per symbol for discrete sources.

---

## Spectral Representation

For a stationary Gaussian process with power spectral density $P(f)$:

$$
h = \int_{-W}^{W} \log P(f) \, df + \text{constant}
$$

(up to an additive constant depending on the coordinate system).

The entropy rate depends on the logarithm of the spectral density. Flat spectrum (white noise) maximizes entropy for a given power constraint.

---

## White Noise

**White noise** has constant spectral density $N_0/2$ for all frequencies:

$$
P(f) = \frac{N_0}{2}, \quad \text{for all } f
$$

It is the continuous analog of the discrete independent uniform source — maximum entropy rate for a given power spectral density.

Autocorrelation:

$$
R(\tau) = \mathbb{E}[n(t)n(t+\tau)] = \frac{N_0}{2} \delta(\tau)
$$

Uncorrelated at all non-zero time shifts (hence "white" like white light containing all frequencies).

---

## Entropy of Sampled Process

If we sample a band-limited process at rate $2W$:

$$
H_{\text{samples}} = 2W \cdot T \cdot h_{\text{per-sample}}
$$

The total entropy grows linearly with time, and the rate is:

$$
\frac{H}{T} = 2W \cdot h_{\text{per-sample}}
$$

This connects the continuous entropy rate to discrete samples.

---

*Next: [§22 — Entropy Loss in Linear Filters](22-entropy-loss-filters.md)*
