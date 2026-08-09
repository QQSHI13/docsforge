import { EMPTY, Observable } from "rxjs"

import { fetchSourceFactsFromGitHub } from "../github"
import { fetchSourceFactsFromGitLab } from "../gitlab"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Repository facts for repositories
 */
export interface RepositoryFacts {
  stars?: number                       /* Number of stars */
  forks?: number                       /* Number of forks */
  version?: string                     /* Latest version */
}

/**
 * Repository facts for organizations
 */
export interface OrganizationFacts {
  repositories?: number                /* Number of repositories */
}

/* ------------------------------------------------------------------------- */

/**
 * Repository facts
 */
export type SourceFacts =
  | RepositoryFacts
  | OrganizationFacts

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Fetch repository facts
 *
 * @param url - Repository URL
 *
 * @returns Repository facts observable
 */
export function fetchSourceFacts(
  url: string
): Observable<SourceFacts> {

  /* Try to match GitHub repository */
  let match = url.match(/^.+github\.com\/([^/]+)\/?([^/]+)?/i)
  if (match) {
    const [, user, repo] = match
    return fetchSourceFactsFromGitHub(user, repo)
  }

  /* Try to match GitLab repository */
  match = url.match(/^.+?([^/]*gitlab[^/]+)\/(.+?)\/?$/i)
  if (match) {
    const [, base, slug] = match
    return fetchSourceFactsFromGitLab(base, slug)
  }

  /* Fallback */
  return EMPTY
}
