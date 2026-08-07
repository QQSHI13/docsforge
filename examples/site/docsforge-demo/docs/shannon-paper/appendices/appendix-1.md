---
tags:
  - information-theory
  - channel-capacity
  - proof
---

# Appendix 1: Channel Capacity with State Constraints

## Detailed Proof of Theorem 1

This appendix proves the determinant method for computing channel capacity when symbol sequences are constrained by state transitions.

---

## The Setup

States: $a_1, a_2, \ldots, a_m$

From state $i$, symbol $s$ with duration $b_{ij}^{(s)}$ leads to state $j$.

Let $N_i(T)$ = number of allowed signals of duration $T$ starting from state $i$.

---

## The Recurrence

$$N_i(T) = \sum_{j,s} N_j(T - b_{ij}^{(s)})$$

For large $T$, assume $N_i(T) \approx A_i W^T$. Substituting:

$$A_i W^T = \sum_{j,s} A_j W^{T - b_{ij}^{(s)}}$$

Dividing by $W^T$:

$$A_i = \sum_{j,s} A_j W^{-b_{ij}^{(s)}}$$

Rearranging:

$$\sum_j \left(\sum_s W^{-b_{ij}^{(s)}} - \delta_{ij}\right) A_j = 0$$

For a non-trivial solution $(A_1, \ldots, A_m) \neq 0$, the determinant must vanish:

$$\det\left|\sum_s W^{-b_{ij}^{(s)}} - \delta_{ij}\right| = 0$$

The largest real root $W$ gives capacity $C = \log W$.

---

## Example: Telegraph Revisited

States:
- $a_1$: last symbol was not a space
- $a_2$: last symbol was a space

Transitions from $a_1$:
- dot (duration 2) → $a_1$
- dash (duration 4) → $a_1$
- letter space (duration 3) → $a_2$
- word space (duration 6) → $a_2$

Transitions from $a_2$:
- dot (duration 2) → $a_1$
- dash (duration 4) → $a_1$

Matrix:

$$
\begin{vmatrix}
W^{-2} + W^{-4} - 1 & W^{-3} + W^{-6} \\
W^{-2} + W^{-4} & -1
\end{vmatrix} = 0$$

Expanding:
$(W^{-2} + W^{-4} - 1)(-1) - (W^{-3} + W^{-6})(W^{-2} + W^{-4}) = 0$

Simplifies to:
$W^{-2} + W^{-4} + W^{-5} + W^{-7} + W^{-8} + W^{-10} = 1$

(The characteristic equation from §1!)

---

## Generalization

This method works for any regular language constraint on sequences. The state graph encodes the grammar, and the determinant equation captures the growth rate of allowed sequences.

---

*Next: [Appendix 2 — Maximum Entropy Derivations](appendix-2.md)*
