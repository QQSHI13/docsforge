---
tags:
  - information-theory
  - coding
  - prefix-code
---

# 8. Representation of the Encoding and Decoding Operations

## The Encoding Problem

We have:
- A **source** producing symbols from alphabet $\mathcal{X}$ with entropy $H$ bits/symbol
- A **channel** accepting symbols from alphabet $\mathcal{Y}$ with capacity $C$ bits/second
- A requirement to transmit source output through the channel

An **encoder** maps sequences of source symbols to sequences of channel symbols. A **decoder** does the reverse.

The question: what properties must this mapping have for reliable, efficient communication?

---

## Types of Codes

### Non-Singular Codes
No two distinct source symbols map to the same codeword. This is the minimum requirement for decodability.

### Uniquely Decodable Codes
Any concatenation of codewords can be parsed in **only one way**. More stringent than non-singular — a non-singular code might still be ambiguous when codewords are concatenated.

**Example of NOT uniquely decodable:**
- $A \to 0$, $B \to 01$, $C \to 1$
- Sequence "01" could be $B$ or $AC$

### Instantaneous (Prefix) Codes
No codeword is a prefix of another codeword. This allows **immediate decoding** — you know a codeword is complete as soon as you see it, without lookahead.

```mermaid
tree
    root[""] --> 0["0: A"]
    root --> 1["1"]
    1 --> 10["10: B"]
    1 --> 11["11"]
    11 --> 110["110: C"]
    11 --> 111["111: D"]
```

Prefix codes are always uniquely decodable, and uniquely decodable codes can always be replaced by prefix codes with the same lengths.

---

## The Source Coding Problem

Given source symbol probabilities $p_1, \ldots, p_n$, assign codeword lengths $l_1, \ldots, l_n$ (in bits, if channel is binary) to minimize expected length:

$$
L = \sum_i p_i l_i
$$

subject to the **Kraft inequality** (for prefix codes):

$$
\sum_{i=1}^{n} 2^{-l_i} \leq 1
$$

The Kraft inequality is necessary and sufficient for the existence of a prefix code with lengths $\{l_i\}$.

---

## Shannon's Source Coding Theorem (Noiseless)

**Theorem (§9, preview):** For any $\epsilon > 0$, there exists a coding scheme such that:

$$
H \leq L \leq H + \epsilon
$$

Conversely, no code can achieve $L < H$.

**In words:**
- You can compress to arbitrarily close to the entropy rate
- You cannot compress below the entropy rate without loss

This is the **fundamental limit of lossless compression**.

---

## Examples of Codes

### Morse Code (Historical)
- E → · (1 unit)
- T → − (3 units)
- Q → −−·− (7 units)

Not a prefix code (dots and dashes have different lengths, but no formal prefix constraint). Decoding requires timing information (spaces between symbols).

### Huffman Code (1952, Optimal Prefix)
Given probabilities, build a binary tree by repeatedly merging the two least probable symbols. Produces the prefix code with minimum expected length.

**Example:**
| Symbol | Probability | Huffman Code | Length |
|--------|-------------|-------------|--------|
| A | 0.4 | 1 | 1 |
| B | 0.2 | 01 | 2 |
| C | 0.2 | 000 | 3 |
| D | 0.1 | 0010 | 4 |
| E | 0.1 | 0011 | 4 |

Expected length: $0.4(1) + 0.2(2) + 0.2(3) + 0.1(4) + 0.1(4) = 2.2$ bits

Entropy: $H \approx 2.12$ bits. Huffman achieves within 1 bit of optimal.

---

## Block Coding

Instead of coding symbol-by-symbol, code blocks of $N$ symbols at once. As $N \to \infty$, block coding achieves $L \to H$.

For $N$-blocks from a memoryless source with entropy $H$:
- There are $\approx 2^{NH}$ typical blocks
- Assign each a unique binary code of length $NH$
- Average per-symbol length $\to H$

This is how practical compressors (gzip, zstd, LZ77 family) achieve near-entropy performance.

---

*Next: [§9 — The Fundamental Theorem for a Noiseless Channel](09-fundamental-theorem-noiseless.md)*
