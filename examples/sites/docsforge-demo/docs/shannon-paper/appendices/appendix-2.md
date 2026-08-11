---
tags:
  - information-theory
  - maximum-entropy
  - variational-calculus
---

# Appendix 2: Maximum Entropy Derivations

## Proving the Maximum Entropy Distributions

This appendix derives the distributions that maximize entropy subject to constraints, using the calculus of variations.

---

## Method: Lagrange Multipliers

Maximize:
$$H = -\int p(x) \log p(x) \, dx$$

Subject to:
1. $\int p(x) \, dx = 1$ (normalization)
2. $\int p(x) g_k(x) \, dx = c_k$ for $k = 1, \ldots, m$ (constraints)

Form the Lagrangian:

$$\mathcal{L} = -\int p \log p \, dx + \lambda_0 \left(\int p \, dx - 1\right) + \sum_k \lambda_k \left(\int p g_k \, dx - c_k\right)$$

---

## Variation

Vary $p \to p + \delta p$:

$$\delta \mathcal{L} = -\int (\log p + 1) \delta p \, dx + \lambda_0 \int \delta p \, dx + \sum_k \lambda_k \int g_k \delta p \, dx = 0$$

For arbitrary $\delta p$:

$$-\log p - 1 + \lambda_0 + \sum_k \lambda_k g_k(x) = 0$$

Solving:

$$p(x) = \exp\left(\lambda_0 - 1 + \sum_k \lambda_k g_k(x)\right)$$

---

## Case 1: Uniform Distribution (Fixed Support)

Constraint: $p(x) = 0$ outside $[0, a]$; $\int_0^a p(x) \, dx = 1$.

No $g_k$ constraints. Then:

$$p(x) = e^{\lambda_0 - 1} = \text{constant} = \frac{1}{a}$$

---

## Case 2: Gaussian (Fixed Mean and Variance)

Constraints: $\int x p(x) \, dx = \mu$, $\int (x-\mu)^2 p(x) \, dx = \sigma^2$.

$$p(x) = \exp\left(\lambda_0 - 1 + \lambda_1 x + \lambda_2 (x-\mu)^2\right)$$

After matching constraints:

$$p(x) = \frac{1}{\sqrt{2\pi\sigma^2}} \exp\left(-\frac{(x-\mu)^2}{2\sigma^2}\right)$$

---

## Case 3: Exponential (Fixed Mean, Positive Support)

Constraints: $\int_0^\infty p(x) \, dx = 1$, $\int_0^\infty x p(x) \, dx = \mu$.

$$p(x) = \frac{1}{\mu} \exp\left(-\frac{x}{\mu}\right), \quad x \geq 0$$

---

## Maximum Entropy Values

| Distribution | Constraints | Max Entropy |
|-------------|-------------|-------------|
| Uniform $[a,b]$ | Support | $\log(b-a)$ |
| Gaussian | Mean, Variance | $\frac{1}{2}\log(2\pi e \sigma^2)$ |
| Exponential | Mean, $x \geq 0$ | $1 + \log \mu$ |

---

*Next: [Appendix 3 — Ergodic Theorems](appendix-3.md)*
