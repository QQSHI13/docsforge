---
tags:
  - information-theory
  - noisy-channel-theorem
  - proof
---

# Appendix 4: Proof of the Noisy Channel Coding Theorem

## Detailed Proof of Theorem 13

This appendix provides the full mathematical proof that reliable communication is possible at rates $R < C$.

---

## Setup

- Input alphabet $\mathcal{X}$, output alphabet $\mathcal{Y}$
- Channel transition probabilities $P(y|x)$
- Capacity $C = \max_{p(x)} I(X;Y)$
- Desired rate $R < C$
- Block length $n$

---

## Random Codebook Construction

1. Fix input distribution $p(x)$ achieving capacity (or near-capacity)
2. Generate $M = 2^{nR}$ codewords independently:
   $$X^n(i) = (X_{i1}, X_{i2}, \ldots, X_{in}), \quad i = 1, \ldots, M$$
   Each $X_{ij} \sim p(x)$ i.i.d.
3. Reveal the codebook to encoder and decoder

---

## Encoding

To send message $i \in \{1, \ldots, M\}$:
- Transmit codeword $X^n(i)$

---

## Decoding (Typical Set Decoding)

Received $Y^n$. Decoder finds the **unique** codeword $X^n(i)$ such that $(X^n(i), Y^n)$ is **jointly typical**:

$$2^{-n(H(X)+\epsilon)} \leq p(X^n) \leq 2^{-n(H(X)-\epsilon)}$$
$$2^{-n(H(Y)+\epsilon)} \leq p(Y^n) \leq 2^{-n(H(Y)-\epsilon)}$$
$$2^{-n(H(X,Y)+\epsilon)} \leq p(X^n, Y^n) \leq 2^{-n(H(X,Y)-\epsilon)}$$

Equivalently:

$$\left|-\frac{1}{n}\log p(X^n, Y^n) - H(X,Y)\right| < \epsilon$$

---

## Error Analysis

### Error Type 1: Transmitted codeword not jointly typical with received sequence

By the AEP:

$$P(\text{not typical}) \to 0 \quad \text{as } n \to \infty$$

### Error Type 2: Wrong codeword is jointly typical

For any wrong codeword $X^n(j)$ ($j \neq i$), since it is independent of $Y^n$:

$$P((X^n(j), Y^n) \text{ typical}) \approx 2^{-n I(X;Y)}$$

There are $M - 1 \approx 2^{nR}$ wrong codewords. Union bound:

$$P(\text{any wrong typical}) \leq 2^{nR} \cdot 2^{-n I(X;Y)} = 2^{-n(I(X;Y) - R)}$$

If $R < I(X;Y) \leq C$, this $\to 0$ exponentially fast.

---

## Total Error Probability

$$P_e \leq P(\text{type 1}) + P(\text{type 2}) \to 0$$

Since $R < C$ and $I(X;Y)$ can be made arbitrarily close to $C$, any rate $R < C$ is achievable.

---

## The Converse (Outline)

If $R > C$, by Fano's inequality:

$$H(W | Y^n) \leq 1 + n R P_e$$

But also:

$$H(W | Y^n) = H(W) - I(W; Y^n) = nR - I(X^n(W); Y^n)$$

$$
\geq nR - nC$$

Combining:

$$nR - nC \leq 1 + nRP_e$$

$$P_e \geq \frac{R - C - 1/n}{R} \to \frac{R - C}{R} > 0$$

Error probability is bounded away from zero. Reliable communication is impossible.

---

## Key Insights
n
1. **Random coding**: The proof uses random codebooks, not deterministic construction
2. **Typicality**: Decoding succeeds because typical sequences are rare enough to avoid collisions
3. **Exponential convergence**: Error probability decays as $2^{-nE(R)}$ for some exponent $E(R) > 0$
4. **Converse is universal**: No code can beat the limit, regardless of complexity

---

## Error Exponent

The rate at which error probability decays is characterized by the **error exponent** (or reliability function):

$$E(R) = \lim_{n \to \infty} -\frac{1}{n} \log P_e^{(n)}(R)$$

For $0 \leq R < C$:

$$E(R) > 0$$

At $R = C$, $E(R) = 0$ (error probability does not decay exponentially).

The random coding exponent gives a lower bound; the sphere packing bound gives an upper bound.

---

*Next: [Appendix 5 — Function Spaces and Measure Theory](appendix-5.md)*
