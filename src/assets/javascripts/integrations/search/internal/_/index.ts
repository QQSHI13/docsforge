/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Visitor function
 *
 * @param start - Start offset
 * @param end - End offset
 */
type VisitorFn = (
  start: number, end: number
) => void

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Split a string using the given separator
 *
 * @param input - Input value
 * @param separator - Separator
 * @param fn - Visitor function
 */
export function split(
  input: string, separator: RegExp, fn: VisitorFn
): void {
  separator = new RegExp(separator, "g")

  /* Split string using separator */
  let match: RegExpExecArray | null
  let index = 0
  do {
    match = separator.exec(input)

    /* Emit non-empty range */
    const until = match?.index ?? input.length
    if (index < until)
      fn(index, until)

    /* Update last index */
    if (match) {
      const [term] = match
      index = match.index + term.length

      /* Support zero-length lookaheads */
      if (term.length === 0)
        separator.lastIndex = match.index + 1
    }
  } while (match)
}
