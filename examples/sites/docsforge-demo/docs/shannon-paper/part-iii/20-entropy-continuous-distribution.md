---
tags:
  - information-theory
  - differential-entropy
  - continuous
---

# 20. Entropy of a Continuous Distribution

## Differential Entropy

For a continuous random variable $X$ with probability density $p(x)$, the **differential entropy** is:

$$
\boxed{H(X) = -\int_{-\infty}^{\infty} p(x) \log p(x) \, dx}
$$

This looks like the discrete formula with sums replaced by integrals, but there's a critical subtlety: differential entropy can be **negative**, and it changes under coordinate transformations.

---

## Why Differential Entropy Is Different

### 1. It Can Be Negative

For a uniform distribution on $[0, a]$:

$$
H = -\int_0^a \frac{1}{a} \log \frac{1}{a} \, dx = \log a
$$

If $a < 1$, then $H < 0$. This is impossible for discrete entropy.

**Resolution**: Differential entropy measures entropy *relative to a uniform reference* (the "coordinate system"). The absolute entropy of a continuous variable is actually infinite (infinitely many points), but differences in differential entropy are meaningful.

### 2. It Changes Under Coordinate Transformations

If $Y = g(X)$ with invertible $g$:

$$
H(Y) = H(X) + \int p(x) \log \left|\frac{dg}{dx}\right| \, dx
$$

Or more compactly:

$$
H(Y) = H(X) + \mathbb{E}\left[\log \left|\frac{dg}{dx}\right|\right]
$$

For linear $Y = aX$:

$$
H(Y) = H(X) + \log |a|
$$

Entropy is not invariant under scaling — unlike discrete entropy.

---

## Maximum Entropy Distributions

Given constraints, what distribution maximizes entropy? These are the "most uncertain" or "least informative" distributions consistent with known information.

### Constraint: Support on $[0, a]$

Maximum entropy: **Uniform distribution**

$$
p(x) = \frac{1}{a}, \quad H = \log a
$$

### Constraint: Fixed Variance $\sigma^2$

Maximum entropy: **Gaussian distribution**

$$
p(x) = \frac{1}{\sqrt{2\pi\sigma^2}} e^{-x^2/(2\sigma^2)}, \quad H = \frac{1}{2}\log(2\pi e \sigma^2)
$$

### Constraint: Fixed Mean $\mu$, Support $[0, \infty)$

Maximum entropy: **Exponential distribution**

$$
p(x) = \frac{1}{\mu} e^{-x/\mu}, \quad H = \log(e\mu) = 1 + \log \mu
$$

### Constraint: Support $(-\infty, \infty)$, Fixed Mean and Variance

Again **Gaussian** — this is why the Gaussian appears ubiquitously in nature (maximum entropy principle).

---

## The Maximum Entropy Principle

Jaynes (1957) later formalized this: when you have incomplete information, the distribution that makes the fewest additional assumptions is the one with maximum entropy subject to your known constraints.

This principle connects information theory to statistical mechanics, Bayesian inference, and machine learning.

---

## Joint and Conditional Differential Entropy

For joint density $p(x,y)$:

$$
H(x,y) = -\iint p(x,y) \log p(x,y) \, dx \, dy
$$

$$
H_x(y) = -\iint p(x,y) \log \frac{p(x,y)}{p(x)} \, dx \, dy
$$

$$
H(y) = H(x,y) - H_x(y) + \text{(coordinate terms)}
$$

The chain rule and mutual information properties carry over from the discrete case, but with care for the coordinate-dependent terms.

---

## Relative Entropy (Kullback-Leibler Divergence)

A coordinate-invariant quantity for comparing distributions:

$$
D_{KL}(p \| q) = \int p(x) \log \frac{p(x)}{q(x)} \, dx
$$

Always non-negative, zero iff $p = q$ almost everywhere. This is the "information gain" from learning that the true distribution is $p$ rather than $q$.

---

*Next: [§21 — Entropy of an Ensemble of Functions](21-entropy-ensemble-functions.md)*
