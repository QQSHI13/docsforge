import type {
  MarzIndex,
  SearchResult as MarzHit
} from "marz-search"

import {
  SearchDocument,
  SearchIndex,
  SearchOptions,
  setupSearchDocumentMap
} from "../config"
import {
  SearchQueryTerms,
  getSearchQueryTerms,
  parseSearchQuery,
  transformSearchQuery
} from "../query"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search item
 */
export interface SearchItem
  extends SearchDocument
{
  score: number                        /* Score (relevance) */
  terms: SearchQueryTerms              /* Search query terms */
}

/**
 * Search result
 */
export interface SearchResult {
  items: SearchItem[][]                /* Search items */
  suggest?: string[]                   /* Search suggestions */
}

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Reference the backend uses for root ("") entries, since Marz refs must not
 * be empty. Keep in sync with MARZ_ROOT_REF in docsforge/core/search.py.
 */
const MARZ_ROOT_REF = "/"

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Highlight matched terms in a string
 *
 * Every matched term is located in the original value with a literal,
 * case-insensitive search, and all occurrences are wrapped in `<mark>`
 * elements, last to first so earlier offsets stay valid.
 *
 * @param input - Input value
 * @param terms - Matched index terms
 *
 * @returns Highlighted string value
 */
function highlightMatches(input: string, terms: string[]): string {
  const lowered = input.toLowerCase()
  const spans: Array<[number, number]> = []
  for (const term of terms) {
    if (!term)
      continue

    /* Locate all occurrences (lowercasing may shift offsets for Turkish dotted capitals — accepted) */
    const needle = term.toLowerCase()
    let from = 0
    for (;;) {
      const at = lowered.indexOf(needle, from)
      if (at === -1)
        break
      spans.push([at, at + needle.length])
      from = at + Math.max(needle.length, 1)
    }
  }

  /* Return input unchanged, if nothing matched */
  if (!spans.length)
    return input

  /* Merge overlapping and abutting spans */
  spans.sort((a, b) => a[0] - b[0] || a[1] - b[1])
  const merged: Array<[number, number]> = []
  for (const [start, end] of spans) {
    const last = merged[merged.length - 1]
    if (last && start <= last[1])
      last[1] = Math.max(last[1], end)
    else
      merged.push([start, end])
  }

  /* Wrap occurrences, last to first */
  let output = input
  for (let index = merged.length - 1; index >= 0; index--) {
    const [start, end] = merged[index]
    output = [
      output.slice(0, start),
      "<mark>",
      output.slice(start, end),
      "</mark>",
      output.slice(end)
    ].join("")
  }

  /* Return highlighted string */
  return output
}

/* ----------------------------------------------------------------------------
 * Class
 * ------------------------------------------------------------------------- */

/**
 * Search index
 */
export class Search {

  /**
   * Search document map
   */
  protected map: Map<string, SearchDocument>

  /**
   * Search options
   */
  protected options: SearchOptions

  /**
   * Declared index fields
   */
  protected fields: string[]

  /**
   * The underlying Marz search index
   */
  protected index: MarzIndex

  /**
   * Create the search integration
   *
   * @param data - Search index
   * @param index - Loaded Marz index
   */
  public constructor({ config, docs, options }: SearchIndex, index: MarzIndex) {
    /* Set up document map, fields and options */
    this.map = setupSearchDocumentMap(docs)
    this.fields = Object.keys(config.fields)
    this.options = options

    /* Set up document index */
    this.index = index
  }

  /**
   * Search for matching documents
   *
   * @param query - Search query
   *
   * @returns Search result
   */
  public search(query: string): SearchResult {
    const transformed = transformSearchQuery(query, this.fields)
    if (!transformed)
      return { items: [] }

    /* Parse query to extract clauses for analysis */
    const clauses = parseSearchQuery(transformed)
      .filter(clause => (
        clause.presence !== "prohibited"
      ))

    /* Perform search — an unparseable query yields no results */
    let hits: MarzHit[]
    try {
      hits = this.index.search(transformed)
    } catch {
      return { items: [] }
    }

    /* Post-process results */
    const groups = hits

      /* Apply post-query boosts based on title and search query terms */
      .reduce<SearchItem[]>((item, { ref, score, matches }) => {
        let doc = this.map.get(ref)
        if (typeof doc === "undefined" && ref === MARZ_ROOT_REF)
          doc = this.map.get("")
        if (typeof doc !== "undefined") {

          /* Shallow copy document */
          doc = { ...doc }
          if (doc.tags)
            doc.tags = [...doc.tags]

          /* Compute and analyze search query terms */
          const matched = Object.keys(matches)
          const terms = getSearchQueryTerms(clauses, matched)

          /* Highlight with the matched query terms — the same mechanism as
             ?h= highlighting. Never raw index terms: marz stems them
             ("docsforge" → "docsforg"), which would mark partial words. */
          const highlightTerms = Object.keys(terms).filter(term => terms[term])

          /* Highlight matches in fields */
          const values = doc as unknown as Record<string, unknown>
          for (const field of this.fields) {
            const value = values[field]
            if (typeof value === "undefined")
              continue

            /* Highlight strings and string arrays (e.g. tags) */
            if (Array.isArray(value))
              values[field] = value.map(entry => (
                typeof entry === "string"
                  ? highlightMatches(entry, highlightTerms)
                  : entry
              ))
            else if (typeof value === "string")
              values[field] = highlightMatches(value, highlightTerms)
          }

          /* Highlight title and text and apply post-query boosts */
          const boost = +!doc.parent +
            Object.values(terms)
              .filter(t => t).length /
            Math.max(Object.keys(terms).length, 1)

          /* Append item */
          item.push({
            ...doc,
            score: score * (1 + boost ** 2),
            terms
          })
        }
        return item
      }, [])

      /* Sort search results again after applying boosts */
      .sort((a, b) => b.score - a.score)

      /* Group search results by article */
      .reduce((items, result) => {
        const doc = this.map.get(result.location)
        if (typeof doc !== "undefined") {
          const ref = doc.parent
            ? doc.parent.location
            : doc.location
          items.set(ref, [...items.get(ref) || [], result])
        }
        return items
      }, new Map<string, SearchItem[]>())

    /* Ensure that every item set has an article */
    for (const [ref, items] of groups)
      if (!items.find(item => item.location === ref)) {
        const doc = this.map.get(ref)!
        items.push({ ...doc, score: 0, terms: {} })
      }

    /* Generate search suggestions, if desired */
    let suggest: string[] | undefined
    if (this.options.suggest) {
      const wanted = clauses
        .map(clause => clause.term.toLowerCase())
        .filter(term => term.length > 0)

      /* Collect title words starting with a query term */
      const seen = new Set<string>()
      suggest = []
      if (wanted.length) {
        for (const doc of this.map.values()) {
          for (const word of doc.title.split(/[\s\-_.,;:!?()[\]{}"'/\\|<>]+/)) {
            if (!word || seen.has(word))
              continue
            if (wanted.some(term => word.toLowerCase().startsWith(term))) {
              seen.add(word)
              suggest.push(word)
              if (suggest.length >= 10)
                break
            }
          }
          if (suggest.length >= 10)
            break
        }
      }
    }

    /* Return search result */
    return {
      items: [...groups.values()],
      ...typeof suggest !== "undefined" && { suggest }
    }
  }
}
