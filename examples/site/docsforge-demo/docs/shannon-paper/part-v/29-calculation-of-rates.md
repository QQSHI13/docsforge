---
tags:
  - information-theory
  - rate-distortion
  - optimization
---

# 29. The Calculation of Rates

## Computing $R(D)$ in Practice

The rate-distortion function is defined by a constrained optimization:

$$
R(D) = \min_{p(y|x): \mathbb{E}[d] \leq D} \sum_{x,y} p(x) p(y|x) \log \frac{p(y|x)}{p(y)}
$$

This is a convex optimization problem in the transition probabilities $p(y|x)$.

---

## The Blahut–Arimoto Algorithm

An iterative algorithm to compute $R(D)$ numerically:

1. Initialize $p(y|x)$ (e.g., uniform)
2. Compute output distribution $p(y) = \sum_x p(x) p(y|x)$
3. Update:
   $$
   p(y|x) \propto p(y) \exp(-\lambda d(x,y))
   $$
   normalized so $\sum_y p(y|x) = 1$
4. Repeat until convergence

The parameter $\lambda$ controls the trade-off (like a Lagrange multiplier). Varying $\lambda$ traces out the entire $R(D)$ curve.

---

## Bounds on $R(D)$

### Lower Bounds

- **Shannon lower bound** for squared error: $R(D) \geq H(x) - \frac{1}{2}\log(2\pi e D)$
- Tight for Gaussian sources, loose for others

### Upper Bounds

- **Vector quantization**: quantize blocks of source symbols
- Performance of practical schemes gives achievable upper bounds

---

## Asymptotic Behavior

### High Rate ($D \to 0$)

$$
R(D) \approx H(x) - \frac{1}{2}\log(2\pi e D)
$$

Rate approaches entropy plus a correction depending on distortion.

### Low Rate ($D \to D_{\max}$)

$$
R(D) \approx \alpha (D_{\max} - D)^2
$$

Near zero rate, the curve is quadratic.

---

## Extension to Continuous Sources

For continuous sources with differential entropy $h(x)$ and MSE distortion:

$$
R(D) = h(x) - \frac{1}{2}\log(2\pi e D)
$$

For Gaussian sources, this is exact. For non-Gaussian, it's a lower bound (Gaussian has maximum entropy for given variance, so needs highest rate).

---

## Summary

| Source | Distortion | $R(D)$ |
|--------|-----------|--------|
| Gaussian ($\sigma^2$) | MSE | $\frac{1}{2}\log(\sigma^2/D)$ |
| Bernoulli($p$) | Hamming | $H_2(p) - H_2(D)$ |
| Uniform $[0,a]$ | MSE | $\log(a/\sqrt{12D})$ for $D \leq a^2/12$ |
| Laplace ($b$) | MSE | $\log(b^2/(2eD))$ for small $D$ |

---

*End of Part V. Next: [Appendices](../appendices/appendix-1.md)*
