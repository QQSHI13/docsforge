/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Terms containing characters from these scripts are indexed by Marz as
 * overlapping n-grams, so a trailing wildcard would narrow them to a prefix
 * lookup instead — and on single-language indexes may match nothing at all.
 * Such terms are passed through unstarred.
 */
const marzNoWildcard = /[\p{sc=Han}\p{sc=Hiragana}\p{sc=Katakana}\p{sc=Hangul}\p{sc=Thai}]/u

/**
 * Marz transformation function
 *
 * 1. Trim excess whitespace from left and right.
 *
 * 2. Search for parts in quotation marks and prepend a `+` modifier to denote
 *    that the resulting document must contain all parts, converting the query
 *    to an `AND` query (as opposed to the default `OR` behavior).
 *
 * 3. Replace control characters which are not located at the beginning of the
 *    query or preceded by white space, or are not followed by a non-whitespace
 *    character or are at the end of the query string. Furthermore, filter
 *    unmatched quotation marks, and drop unknown `field:` prefixes (Marz
 *    rejects queries against undeclared fields, so `foo:bar` becomes `bar`
 *    instead of failing the whole query).
 *
 * 4. Split the query string at whitespace, then append a wildcard to every
 *    resulting term that is not explicitly marked with a `+`, `-`, `~` or
 *    `^` modifier and contains no CJK-script characters, since it ensures
 *    consistent and stable ranking when multiple terms are entered. Also, if
 *    a fuzzy or boost modifier are given, but no numeric value has been
 *    entered, default to 1 to not induce a query error.
 *
 * @param query - Query value
 * @param fields - Declared index fields
 *
 * @returns Transformed query value
 */
export function transformMarz(
  query: string, fields: string[] = ["title", "text", "tags"]
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

    /* Drop unknown field prefixes */
    .replace(/(^|\s)([A-Za-z_]\w*):(?=\S)/g, (match, space, field) =>
      fields.includes(field) ? match : space
    )

    /* => 4 */
    .split(/\s+/g)
      .map(term => /([~^]$)/.test(term) ? `${term}1` : term)
      .map(term =>
        /(^[+-]|[~^]\d+$)/.test(term) || marzNoWildcard.test(term)
          ? term
          : `${term}*`
      )
      .join(" ")
}
