import { transformMarz } from "../transform"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search query clause presence
 */
export type SearchQueryPresence =
  | "required"                         /* Clause is required */
  | "optional"                         /* Clause is optional */
  | "prohibited"                       /* Clause is prohibited */

/**
 * Search query clause
 */
export interface SearchQueryClause {
  presence: SearchQueryPresence        /* Clause presence */
  term: string                         /* Clause term */
}

/* ------------------------------------------------------------------------- */

/**
 * Search query terms
 */
export type SearchQueryTerms = Record<string, boolean>

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Transform search query
 *
 * This function applies the Marz query transformation, so CJK-script terms
 * are passed through unstarred while Latin-script terms keep the trailing
 * wildcard that stabilizes ranking for multi-term queries.
 *
 * @param query - Search query
 * @param fields - Declared index fields
 *
 * @returns Search query
 */
export function transformSearchQuery(
  query: string, fields: string[] = ["title", "text", "tags"]
): string {
  return transformMarz(query, fields)
}

/* ------------------------------------------------------------------------- */

/**
 * Parse a search query for analysis
 *
 * The query is expected in transformed form (see above): whitespace-separated
 * terms with optional `+`/`-` presence prefixes and `field:` scopes.
 *
 * @param value - Query value
 *
 * @returns Search query clauses
 */
export function parseSearchQuery(
  value: string
): SearchQueryClause[] {
  return value
    .split(/\s+/g)
    .filter(term => term.length > 0)
    .map(term => {
      let presence: SearchQueryPresence = "optional"
      if (term.startsWith("+")) {
        presence = "required"
        term = term.slice(1)
      } else if (term.startsWith("-")) {
        presence = "prohibited"
        term = term.slice(1)
      }

      /* Drop field scope and operator suffixes for display */
      term = term
        .replace(/^[A-Za-z_]\w*:/, "")
        .replace(/[*~^]\d*$/, "")

      /* Return clause */
      return { presence, term }
    })
    .filter(clause => clause.term.length > 0)
}

/**
 * Analyze the search query clauses in regard to the search terms found
 *
 * @param query - Search query clauses
 * @param terms - Search terms
 *
 * @returns Search query terms
 */
export function getSearchQueryTerms(
  query: SearchQueryClause[], terms: string[]
): SearchQueryTerms {

  /* Match query clauses against terms */
  const result: SearchQueryTerms = {}
  for (const clause of query) {
    if (clause.term in result)
      continue

    /* A clause counts as matched when an index term starts with it */
    result[clause.term] = terms.some(term => (
      term.startsWith(clause.term) || clause.term.startsWith(term)
    ))
  }

  /* Return query terms */
  return result
}
