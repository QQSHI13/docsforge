---
tags:
  - information-theory
  - filters
  - signal-processing
---

# 22. Entropy Loss in Linear Filters

## Filtering Reduces Information

A linear filter is a deterministic operation. Intuitively, it cannot create new information, but can it preserve all existing information? Shannon shows: **unless the filter is perfectly invertible, entropy is lost**.

---

## The Filter Equation

Input ensemble $\{x(t)\}$ with spectral density $S_x(f)$ passes through a linear filter with transfer function $Y(f)$:

$$
S_y(f) = |Y(f)|^2 S_x(f)
$$

Output spectral density = input spectral density × squared magnitude response.

---

## Entropy Change

The entropy rate changes by:

$$
H_y = H_x + \frac{1}{W} \int_0^W \log |Y(f)|^2 \, df
$$

For an ideal bandpass filter that passes frequencies in $[f_1, f_2]$ and rejects others:

$$
|Y(f)|^2 = \begin{cases} 1 & f_1 \leq f \leq f_2 \\ 0 & \text{otherwise} \end{cases}
$$

The integral becomes $\log 1 = 0$ in the passband, but the output is now band-limited, so its maximum entropy is reduced.

---

## The Ideal Low-Pass Filter

Passing white noise through an ideal low-pass filter with cutoff $W$:

$$
H_{\text{out}} = H_{\text{in}} + \int_0^W \log(1) \, df = H_{\text{in}}
$$

But the output has finite bandwidth, so its entropy per degree of freedom is higher than the input's. The total entropy is preserved, but concentrated into fewer degrees of freedom.

For a non-ideal filter with roll-off, some information is irretrievably lost in the transition band.

---

## Recoverability

If $|Y(f)| > 0$ for all $f$ in the signal band, the filter is **invertible** (at least in principle). The original signal can be recovered by inverse filtering:

$$
\hat{X}(f) = \frac{Y(f)}{|Y(f)|^2 + \epsilon}
$$

(with regularization $\epsilon$ for numerical stability).

If $|Y(f)| = 0$ for some frequencies, those frequency components are **permanently lost**.

---

*Next: [§23 — Entropy of a Sum of Two Ensembles](23-entropy-sum-two-ensembles.md)*
