---
tags:
  - information-theory
  - coding
  - examples
---

# 10. Discussion and Examples

## Practical Coding Techniques

Shannon concludes Part I by discussing how the theoretical limits translate into practice.

---

## Morse Code as Suboptimal Coding

Morse code uses:
- Dot = 1 time unit
- Dash = 3 time units
- Letter space = 3 units
- Word space = 6 units

It approximately follows the frequency of English letters (E = ·, Q = −−·−), but:
- Not a prefix code (requires timing/spacing to disambiguate)
- Codeword lengths are not optimal for the actual frequencies
- Telegraph channel constraints (§1) limit possible sequences

Shannon's theory shows Morse is reasonable but not optimal. A Huffman-style code would be more efficient.

---

## Commercial Telegraph Codes

Historical telegraph codes (e.g., "ACME = 'ship immediately'") exploit word-level redundancy:
- Common phrases → short code words
- Achieved 3:1 to 5:1 compression over letter-by-letter transmission
- Essentially word-level Huffman coding

Standardized greeting/anniversary telegrams extended this to encode entire sentences into short number sequences.

---

## Block Coding for English

Shannon suggests: group English letters into blocks of 5, assign each block a code word. With $27^5 \approx 1.4 \times 10^7$ blocks and $H \approx 1$ bit/char, typical blocks are $\approx 2^5 = 32$ instead of $27^5$ possibilities. This could achieve 5:1 compression.

In practice, modern text compression (gzip, bzip2) achieves 3:1 to 10:1 depending on text type, using adaptive dictionary methods (LZ77) plus entropy coding (Huffman/ANS).

---

## The Efficiency of English

Given:
- $H \approx 1$ bit/character for English
- Printed text: ~6 characters per word, ~2 words per inch
- Reading speed: ~300 words/minute

Information rate of reading: $\approx 300 \times 6 \times 1 = 1800$ bits/minute $= 30$ bits/second.

This is remarkably slow compared to digital transmission rates, reflecting how much redundancy language carries — which is essential for robust communication in noisy human environments.

---

*End of Part I. Next: [Part II — The Discrete Channel with Noise](../part-ii/11-noisy-channel-representation.md)*
