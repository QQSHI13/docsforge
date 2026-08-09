/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Round a number for display with repository facts
 *
 * This is a reverse-engineered version of GitHub's weird rounding algorithm
 * for stars, forks and all other numbers. While all numbers below `1,000` are
 * returned as-is, bigger numbers are converted to fixed numbers:
 *
 * - `1,049` => `1k`
 * - `1,050` => `1.1k`
 * - `1,949` => `1.9k`
 * - `1,950` => `2k`
 *
 * @param value - Original value
 *
 * @returns Rounded value
 */
export function round(value: number): string {
  if (value > 999) {
    const digits = +((value - 950) % 1000 > 99)
    return `${((value + 0.000001) / 1000).toFixed(digits)}k`
  } else {
    return value.toString()
  }
}
