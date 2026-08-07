---
tags:
  - information-theory
  - entropy
  - convolution
---

# 23. Entropy of a Sum of Two Ensembles

## Adding Random Processes

If $x(t)$ and $y(t)$ are independent ensembles, what is the entropy of $z(t) = x(t) + y(t)$?

---

## The Convolution Rule

The probability density of a sum is the convolution of the individual densities:

$$
p_z(z) = \int p_x(x) p_y(z-x) \, dx = (p_x * p_y)(z)
$$

For entropies, there is no simple convolution formula, but bounds exist.

---

## Key Inequality

$$
H(x + y) \geq \max(H(x), H(y))
$$

Adding independent noise cannot decrease the entropy of the result (it can only add uncertainty). Equality holds only in degenerate cases.

For independent $x$ and $y$ with powers $P_1$ and $P_2$:

$$
H(x + y) \approx H(x) + \frac{P_2}{P_1}
$$

(when the added component is small compared to the original).

---

## The Gaussian Case

If $x \sim \mathcal{N}(0, P_1)$ and $y \sim \mathcal{N}(0, P_2)$ are independent:

$$
x + y \sim \mathcal{N}(0, P_1 + P_2)
$$

And:

$$
H(x+y) = \frac{1}{2}\log(2\pi e (P_1 + P_2))
$$

The sum of Gaussians is Gaussian, and the entropy adds "logarithmically in power" (powers add, entropy of the result corresponds to total power).

---

## Application to Noisy Channels

If signal $x$ with power $P$ is added to noise $n$ with power $N$:

$$
H(x + n) = \frac{1}{2}\log(2\pi e (P + N))
$$

The output entropy depends on the total power. The **mutual information** (signal entropy minus conditional entropy) is what matters for capacity:

$$
I(x; x+n) = H(x+n) - H(n) = \frac{1}{2}\log\left(1 + \frac{P}{N}\right)
$$

This is the key formula for the Gaussian channel capacity.

---

*End of Part III. Next: [Part IV — The Continuous Channel](../part-iv/24-capacity-of-continuous-channel.md)*
