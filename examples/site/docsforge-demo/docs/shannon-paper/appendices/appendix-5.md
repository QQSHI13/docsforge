---
tags:
  - information-theory
  - measure-theory
  - functional-analysis
---

# Appendix 5: Function Spaces and Measure Theory

## Mathematical Preliminaries for Continuous Ensembles

This appendix provides the rigorous measure-theoretic foundations used in Parts III–V.

---

## Measurable Spaces

A **measurable space** $(\Omega, \mathcal{F})$ consists of:
- $\Omega$: sample space (set of all possible outcomes)
- $\mathcal{F}$: $\sigma$-algebra (collection of measurable subsets)

For function spaces, $\Omega$ is typically a space of functions $f: [0,T] \to \mathbb{R}$.

---

## Probability Measure

A **probability measure** $P: \mathcal{F} \to [0,1]$ satisfies:
1. $P(\Omega) = 1$
2. Countable additivity: $P(\bigcup_i A_i) = \sum_i P(A_i)$ for disjoint $A_i$

---

## Kolmogorov Extension Theorem

Given consistent finite-dimensional distributions, there exists a unique probability measure on the infinite-dimensional space.

**Consistent means:** If you marginalize the joint distribution of $(f(t_1), \ldots, f(t_n))$ to any subset of time points, you get the corresponding lower-dimensional distribution.

---

## Important Function Spaces

### $L^2$ Space

$$L^2[0,T] = \left\{f: \int_0^T |f(t)|^2 \, dt < \infty\right\}$$

Hilbert space with inner product $\langle f, g \rangle = \int f(t) g(t) \, dt$.

Most physical signals belong to $L^2$ (finite energy).

### $L^\infty$ Space

$$L^\infty[0,T] = \left\{f: \text{ess sup}_{t \in [0,T]} |f(t)| < \infty\right\}$$

Bounded functions. Important for peak power constraints.

### Sobolev Spaces

Functions with derivatives in $L^2$. Used when smoothness matters.

---

## Stochastic Processes as Random Functions

A stochastic process $\{X_t\}_{t \in T}$ is a collection of random variables indexed by time. Equivalently, it is a single random function:

$$X: \Omega \to \mathbb{R}^T$$

where $\mathbb{R}^T$ is the space of all functions $T \to \mathbb{R}$.

The **law** of the process is the probability measure induced on $\mathbb{R}^T$.

---

## Stationarity and Ergodicity

### Strict Stationarity

For all $n$, all $t_1, \ldots, t_n$, all $\tau$:

$$(X_{t_1}, \ldots, X_{t_n}) \stackrel{d}{=} (X_{t_1+\tau}, \ldots, X_{t_n+\tau})$$

### Wide-Sense Stationarity

Weaker: $\mathbb{E}[X_t] = \mu$ (constant) and $\mathbb{E}[X_t X_{t+\tau}] = R(\tau)$ (depends only on lag).

### Ergodicity

Time averages = ensemble averages (almost surely).

For Gaussian processes: ergodicity can be checked from the spectral density.

---

## Wiener Measure

The **Wiener measure** is the probability measure on continuous functions corresponding to Brownian motion:

- $W(0) = 0$
- Independent increments
- $W(t) - W(s) \sim \mathcal{N}(0, t-s)$

This measure is concentrated on nowhere-differentiable functions — almost all Brownian paths are rough!

---

## Application to Information Theory

For continuous-time Gaussian channels, the rigorous formulation uses:
- Cameron-Martin space (functions in the support of the Wiener measure)
- Radon-Nikodym derivative (likelihood ratio)
- Mutual information defined via Kullback-Leibler divergence of path measures

---

*Next: [Appendix 6 — Continuous Entropy Properties](appendix-6.md)*
