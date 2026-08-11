---
tags:
  - information-theory
  - examples
  - channel-capacity
---

# 15. Example of a Discrete Channel and Its Capacity

## The Binary Symmetric Channel in Detail

The BSC with crossover probability $p$ is the canonical example. Let's work through its capacity calculation completely.

---

## Setup

Input $X \in \{0, 1\}$, output $Y \in \{0, 1\}$.

Channel matrix:

$$
\begin{array}{c|cc}
P(y|x) & 0 & 1 \\
\hline
0 & 1-p & p \\
1 & p & 1-p
\end{array}
$$

Let input distribution be $P(X=0) = q$, $P(X=1) = 1-q$.

---

## Output Distribution

$$
P(Y=0) = q(1-p) + (1-q)p = p + q - 2pq
$$

$$
P(Y=1) = qp + (1-q)(1-p) = 1 - p - q + 2pq
$$

---

## Mutual Information

$$
I(X;Y) = H(Y) - H(Y|X)
$$

The conditional entropy:

$$
H(Y|X) = q H_2(p) + (1-q) H_2(p) = H_2(p)
$$

(Since noise is independent of input.)

So:

$$
I(X;Y) = H(Y) - H_2(p)
$$

To maximize: choose $q$ to maximize $H(Y)$. Since $H(Y)$ is maximized when $P(Y=0) = P(Y=1) = 0.5$, and this is achieved by $q = 0.5$:

$$
C = \max_q I(X;Y) = 1 - H_2(p)
$$

---

## Numerical Values

| $p$ | $H_2(p)$ | $C = 1 - H_2(p)$ |
|-----|----------|-----------------|
| 0.0 | 0.000 | 1.000 |
| 0.01 | 0.080 | 0.920 |
| 0.05 | 0.286 | 0.714 |
| 0.10 | 0.469 | 0.531 |
| 0.11 | 0.500 | 0.500 |
| 0.25 | 0.811 | 0.189 |
| 0.50 | 1.000 | 0.000 |

At $p = 0.11$, capacity is exactly 0.5 — you can reliably send 1 bit every 2 channel uses.

---

## The Z-Channel

Asymmetric channel where one error direction dominates:

$$
P(0|0) = 1, \quad P(1|0) = 0
$$

$$
P(0|1) = p, \quad P(1|1) = 1-p
$$

Capacity requires non-uniform input distribution. Optimization yields:

$$
C = \log_2(1 + (1-p)p^{p/(1-p)})
$$

---

*Next: [§16 — The Channel Capacity in Certain Special Cases](16-special-cases.md)*
