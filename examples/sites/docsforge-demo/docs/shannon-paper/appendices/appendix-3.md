---
tags:
  - information-theory
  - ergodic-theory
  - asymptotic-equitpartition
---

# Appendix 3: Ergodic Theorems and AEP

## Rigorous Foundation for Typical Sequences

This appendix proves that for ergodic sources, almost all long sequences have probability $\approx 2^{-nH}$.

---

## The Asymptotic Equipartition Property (AEP)

**Theorem:** Let $\{X_i\}$ be a stationary ergodic process with entropy rate $H$. Then:

$$-\frac{1}{n} \log p(X_1, X_2, \ldots, X_n) \to H \quad \text{(almost surely)}$$

---

## Proof Sketch (Shannon-McMillan-Breiman)

For $n$-th order Markov processes, decompose:

$$-\frac{1}{n}\log p(X_1^n) = -\frac{1}{n}\sum_{i=1}^n \log p(X_i | X_{i-n+1}^{i-1})$$

By ergodicity, the time average converges to the ensemble average:

$$\to \mathbb{E}[-\log p(X_n | X_1^{n-1})] = H_n$$

Taking $n \to \infty$, $H_n \to H_{\infty} = H$.

---

## Consequences

### 1. Typical Set

Define the **typical set**:

$$A_\epsilon^{(n)} = \left\{(x_1^n) : 2^{-n(H+\epsilon)} \leq p(x_1^n) \leq 2^{-n(H-\epsilon)}\right\}$$

Properties:
- $P(A_\epsilon^{(n)}) \to 1$ as $n \to \infty$
- $|A_\epsilon^{(n)}| \approx 2^{nH}$
- Non-typical sequences have total probability $< \epsilon$

### 2. Source Coding

Only $\approx 2^{nH}$ sequences need unique codewords. Others can share a single "escape" code.

### 3. Data Compression

The entropy rate is both necessary and sufficient for lossless compression of ergodic sources.

---

## The Law of Large Numbers for Information

The AEP is the analog of the law of large numbers for the random variable $-\log p(X_i | \text{past})$.

Just as sample means converge to expectations, sample information rates converge to entropy rates.

---

*Next: [Appendix 4 — Proof of the Noisy Channel Theorem](appendix-4.md)*
