---
tags:
  - information-theory
  - channel-capacity
  - special-cases
---

# 16. The Channel Capacity in Certain Special Cases

## Simplified Capacity Formulas

Shannon derives closed-form capacity expressions for several important channel classes.

---

## 1. Noiseless Channel

If the channel is noiseless with $n$ input symbols and no output constraints:

$$
C = \log_2 n
$$

Achieved with uniform input distribution.

---

## 2. Independent Noise Per Symbol

If each symbol has independent noise (memoryless channel):

$$
C = \max_{p(x)} \sum_i p(x_i) \sum_j P_{x_i}(y_j) \log \frac{P_{x_i}(y_j)}{p(y_j)}
$$

This is the standard discrete memoryless channel (DMC) formula. Optimization is convex in $p(x)$.

---

## 3. Gaussian Approximation to Discrete Channels

For channels with many output levels, the noise can be approximated as Gaussian. Capacity approaches:

$$
C \approx \frac{1}{2} \log_2\left(1 + \frac{S}{N}\right)
$$

per channel use, where $S$ is signal power and $N$ is noise power. This foreshadows the continuous Gaussian channel result in Part IV.

---

## 4. Channel with Symbol Costs

If different input symbols have different transmission costs $c_i$ and total cost is constrained:

$$
C(\beta) = \max_{p: \sum p_i c_i \leq \beta} I(X;Y)
$$

This is a constrained optimization problem solvable with Lagrange multipliers.

---

## 5. Sum Channel

If the channel is a mixture of subchannels used with probabilities $q_i$:

$$
C = \max_{q_i} \sum_i q_i C_i
$$

subject to resource constraints on the subchannels.

---

## Summary Table

| Channel Type | Capacity Formula | Optimal Input |
|-------------|------------------|---------------|
| Noiseless | $\log n$ | Uniform |
| BSC(p) | $1 - H_2(p)$ | Uniform |
| BEC($\alpha$) | $1 - \alpha$ | Uniform |
| Z-channel | $\log(1 + (1-p)p^{p/(1-p)})$ | Non-uniform |
| Gaussian (preview) | $\frac{1}{2}\log(1 + S/N)$ | Gaussian |

---

*Next: [§17 — An Example of Efficient Coding](17-efficient-coding-example.md)*
