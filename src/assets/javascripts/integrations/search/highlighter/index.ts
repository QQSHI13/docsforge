import escapeHTML from "escape-html"

import { SearchConfig } from "../config"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search highlight function
 *
 * @param value - Value
 *
 * @returns Highlighted value
 */
export type SearchHighlightFn = (value: string) => string

/**
 * Search highlight factory function
 *
 * @param query - Query value
 *
 * @returns Search highlight function
 */
export type SearchHighlightFactoryFn = (query: string) => SearchHighlightFn

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Create a search highlighter
 *
 * @param config - Search configuration
 *
 * @returns Search highlight factory function
 */
export function setupSearchHighlighter(
  config: SearchConfig
): SearchHighlightFactoryFn {
  // Hack: temporarily remove pure lookaheads and lookbehinds
  const regex = config.separator.split("|").map(term => {
    const temp = term.replace(/(\(\?[!=<][^)]+\))/g, "")
    return temp.length === 0 ? "�" : term
  })
    .join("|")

  const separator = new RegExp(regex, "img")
  const highlight = (_: unknown, data: string, term: string) => {
    return `${data}<mark data-md-highlight>${term}</mark>`
  }

  /* Return factory function */
  return (query: string) => {
    query = query
      .replace(/[\s*+\-:~^]+/g, " ")
      .replace(/&/g, "&amp;")
      .trim()

    /* Create search term match expression */
    const match = new RegExp(`(^|${config.separator}|)(${
      query
        .replace(/[|\\{}()[\]^$+*?.-]/g, "\\$&")
        .replace(separator, "|")
    })`, "img")

    /* Highlight string value */
    return value => escapeHTML(value)
      .replace(match, highlight)
      .replace(/<\/mark>(\s+)<mark[^>]*>/img, "$1")
  }
}
