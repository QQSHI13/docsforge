---
tags:
  - information-theory
  - measure-theory
  - functional-analysis
---

# 18. Sets and Ensembles of Functions

## Mathematical Foundations for Continuous Signals

Parts I and II dealt with discrete symbols. Parts IV and V will extend the theory to continuous signals (radio, television, analog audio). This requires rigorous definitions of "sets of functions" and probability measures over them.

---

## What Is an Ensemble of Functions?

An **ensemble** is a set of functions $\{f(t)\}$ together with a **probability measure** — a rule that assigns probabilities to subsets of functions.

Think of it as a stochastic process in continuous time: each "outcome" is an entire function of time, not just a single value.

---

## Examples of Function Ensembles

### 1. Finite Set of Functions

$$
\{f_1(t), f_2(t), \ldots, f_k(t)\}
$$

with probabilities $p_1, p_2, \ldots, p_k$.

Simplest case: like a discrete source, but each "symbol" is a full waveform.

### 2. Band-Limited Functions

The set of all functions containing no frequencies over $W$ cycles/second:

$$
\{f(t) : \text{spectrum of } f \text{ is zero for } |f| > W\}
$$

By the sampling theorem, these are completely determined by their values at sampling points $t = n/(2W)$.

### 3. Amplitude-Limited Functions

Functions limited in band to $W$ and in amplitude to $A$:

$$
|f(t)| \leq A \quad \text{for all } t
$$

### 4. English Speech Signals

The set of all English speech waveforms with a probability measure given by the frequency of occurrence in actual conversation.

---

## Measure and Probability on Function Spaces

For a rigorous foundation, we need a **probability measure** $\mu$ on the function space such that:

1. $\mu(S) \geq 0$ for all measurable sets $S$
2. $\mu(\text{entire space}) = 1$
3. Countable additivity for disjoint sets

The **ensemble average** of a functional $F[f]$ is:

$$
\mathbb{E}[F] = \int F[f] \, d\mu(f)
$$

For **stationary ergodic** ensembles, time averages equal ensemble averages:

$$
\lim_{T \to \infty} \frac{1}{T} \int_0^T F[f(t)] \, dt = \mathbb{E}[F]
$$

with probability 1.

---

## Stationarity

An ensemble is **stationary** if its statistics are time-invariant:

$$
P(f(t_1), \ldots, f(t_n)) = P(f(t_1 + \tau), \ldots, f(t_n + \tau))
$$

for all $\tau$. The distribution doesn't depend on absolute time, only on relative time differences.

---

## Finite-Dimensional Distributions

To specify an ensemble, it's often enough to give the joint distributions of samples at finite sets of times:

$$
P(f(t_1) \leq a_1, \ldots, f(t_n) \leq a_n)
$$

for all $n$, all times $t_1, \ldots, t_n$, and all thresholds $a_1, \ldots, a_n$. By Kolmogorov's extension theorem, these finite-dimensional distributions uniquely determine the measure on the function space (under mild regularity conditions).

---

## Examples with Specific Measures

### Poisson Impulse Process

Points distributed on the $t$-axis according to a Poisson process with density $\lambda$. At each point, the function has a standard impulse shape $g(t)$:

$$
f(t) = \sum_i g(t - t_i)
$$

where $t_i$ are Poisson-distributed points. Used to model shot noise in electronic devices.

### Gaussian White Noise

The derivative (in a generalized sense) of the Wiener process. Gaussian, uncorrelated at different times, with flat spectrum:

$$
\mathbb{E}[n(t) n(t+\tau)] = \frac{N_0}{2} \delta(\tau)
$$

This is the idealized noise model for most communication channels.

---

*Next: [§19 — Band Limited Ensembles of Functions](19-band-limited-ensembles.md)*
