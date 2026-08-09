/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search field
 */
export interface SearchField {
  boost?: number                       /* Field boost */
}

/**
 * Search configuration
 */
export interface SearchConfig {
  lang: string[]                       /* Search languages */
  separator: string                    /* Search separator */
  pipeline: SearchPipelineFn[]         /* Search pipeline */
  fields: Record<string, SearchField>  /* Search field */
}

/**
 * Search document
 */
export interface SearchDocument {
  location: string                     /* Document location */
  title: string                        /* Document title */
  text: string                         /* Document text */
  tags?: string[]                      /* Document tags */
  boost?: number                       /* Document boost */
  parent?: SearchDocument              /* Document parent */
}

/**
 * Search options
 */
export interface SearchOptions {
  suggest: boolean                     /* Search suggestions */
}

/* ------------------------------------------------------------------------- */

/**
 * Search index
 */
export interface SearchIndex {
  config: SearchConfig                 /* Search configuration */
  docs: SearchDocument[]               /* Search documents */
  options: SearchOptions               /* Search options */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Search pipeline function
 */
type SearchPipelineFn =
  | "trimmer"                          /* Trimmer */
  | "stopWordFilter"                   /* Stop word filter */
  | "stemmer"                          /* Stemmer */

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Create a search document map
 *
 * This function creates a mapping of URLs (including anchors) to the actual
 * articles and sections. It relies on the invariant that the search index is
 * ordered with the main article appearing before all sections with anchors.
 * If this is not the case, the logic music be changed.
 *
 * @param docs - Search documents
 *
 * @returns Search document map
 */
export function setupSearchDocumentMap(
  docs: SearchDocument[]
): Map<string, SearchDocument> {
  const map = new Map<string, SearchDocument>()
  for (const doc of docs) {
    const [path] = doc.location.split("#")

    /* Add document article */
    const article = map.get(path)
    if (typeof article === "undefined") {
      map.set(path, doc)

      /* Add document section */
    } else {
      map.set(doc.location, doc)
      doc.parent = article
    }
  }

  /* Return search document map */
  return map
}
