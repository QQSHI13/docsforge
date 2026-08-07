---
tags:
  - information-theory
  - differential-entropy
  - coordinate-transform
---

# Appendix 6: Continuous Entropy Properties

## Coordinate Transformations and Entropy

This appendix rigorously derives how differential entropy changes under coordinate transformations.

---

## Change of Variables

Let $X$ have density $p_X(x)$. Let $Y = g(X)$ where $g$ is differentiable and invertible.

By the change of variables formula:

$$p_Y(y) = p_X(g^{-1}(y)) \left|\frac{d g^{-1}}{dy}\right| = p_X(x) \left|\frac{dx}{dy}\right|$$

---

## Entropy Transformation

$$H(Y) = -\int p_Y(y) \log p_Y(y) \, dy$$

$$= -\int p_X(x) \left|\frac{dx}{dy}\right| \log\left(p_X(x) \left|\frac{dx}{dy}\right|\right) \left|\frac{dy}{dx}\right| \, dx$$

$$= -\int p_X(x) \left(\log p_X(x) + \log\left|\frac{dx}{dy}\right|\right) \, dx$$

$$= H(X) + \mathbb{E}\left[\log \left|\frac{dy}{dx}\right|\right]$$

Or equivalently:

$$H(Y) = H(X) - \mathbb{E}\left[\log \left|\frac{dx}{dy}\right|\right]$$

---

## Linear Transformation

For $Y = aX$:

$$\frac{dy}{dx} = a, \quad H(Y) = H(X) + \log |a|$$

Scaling by $|a| > 1$ increases entropy; scaling by $|a| < 1$ decreases it.

This explains why differential entropy is not scale-invariant.

---

## Multi-Dimensional Case

For vector $Y = g(X)$ with Jacobian $J_{ij} = \frac{\partial g_i}{\partial x_j}$:

$$H(Y) = H(X) + \mathbb{E}\left[\log |\det J|\right]$$

---

## Volume Interpretation

Differential entropy measures entropy relative to Lebesgue measure. If the "natural" measure on the space has density $w(x)$ with respect to Lebesgue measure, the **relative entropy** is:

$$H_w(X) = -\int p(x) \log \frac{p(x)}{w(x)} \, dx$$

This is coordinate-invariant! The choice of $w(x)$ plays the role of a "reference measure."

For example, on the unit interval, $w(x) = 1$ (uniform). On the sphere, $w$ is the uniform surface measure.

---

## Why This Matters

The coordinate dependence of differential entropy means:
- $H(X)$ alone has no absolute meaning
- Differences $H(X) - H(Y)$ are meaningful (invariant)
- Mutual information $I(X;Y)$ is always invariant
- Rate-distortion functions are invariant under coordinate changes

This is why information theorists prefer **mutual information** and **KL divergence** for fundamental results, using differential entropy only as a computational tool.

---

## End of Appendices

This completes the mathematical foundations. The main text of "A Mathematical Theory of Communication" is now fully documented.
