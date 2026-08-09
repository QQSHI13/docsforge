/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Visitor function
 *
 * @param value - String value
 *
 * @returns String term(s)
 */
type VisitorFn = (
  value: string
) => string | string[]

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Default transformation function
 *
 * 1. Trim excess whitespace from left and right.
 *
 * 2. Search for parts in quotation marks and prepend a `+` modifier to denote
 *    that the resulting document must contain all parts, converting the query
 *    to an `AND` query (as opposed to the default `OR` behavior). While users
 *    may expect parts enclosed in quotation marks to map to span queries, i.e.
 *    for which order is important, Lunr.js doesn't support them, so the best
 *    we can do is to convert the parts to an `AND` query.
 *
 * 3. Replace control characters which are not located at the beginning of the
 *    query or preceded by white space, or are not followed by a non-whitespace
 *    character or are at the end of the query string. Furthermore, filter
 *    unmatched quotation marks.
 *
 * 4. Split the query string at whitespace, then pass each part to the visitor
 *    function for tokenization, and append a wildcard to every resulting term
 *    that is not explicitly marked with a `+`, `-`, `~` or `^` modifier, since
 *    it ensures consistent and stable ranking when multiple terms are entered.
 *    Also, if a fuzzy or boost modifier are given, but no numeric value has
 *    been entered, default to 1 to not induce a query error.
 *
 * @param query - Query value
 * @param fn - Visitor function
 *
 * @returns Transformed query value
 */
export function transform(
  query: string, fn: VisitorFn = term => term
): string {
  return query

    /* => 1 */
    .trim()

    /* => 2 */
    .split(/"([^"]+)"/g)
      .map((parts, index) => index & 1
        ? parts.replace(/^\b|^(?![^\x00-\x7F]|$)|\s+/g, " +")
        : parts
      )
      .join("")

    /* => 3 */
    .replace(/"|(?:^|\s+)[*+\-:^~]+(?=\s+|$)/g, "")

    /* => 4 */
    .split(/\s+/g)
      .reduce((prev, term) => {
        const next = fn(term)
        return [...prev, ...Array.isArray(next) ? next : [next]]
      }, [] as string[])
      .map(term => /([~^]$)/.test(term) ? `${term}1` : term)
      .map(term => /(^[+-]|[~^]\d+$)/.test(term) ? term : `${term}*`)
      .join(" ")
}
