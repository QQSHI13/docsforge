import { ProjectSchema } from "gitlab"
import {
  EMPTY,
  Observable,
  catchError,
  defaultIfEmpty,
  map,
  zip
} from "rxjs"

import { requestJSON } from "~/browser"

import { SourceFacts } from "../_"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * GitLab release (partial)
 */
interface Release { // @todo remove and use the ReleaseSchema type instead after switching from gitlab to @gitbeaker/rest
  tag_name: string                     /* Tag name */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Fetch GitLab repository facts
 *
 * @param base - GitLab base
 * @param project - GitLab project
 *
 * @returns Repository facts observable
 */
export function fetchSourceFactsFromGitLab(
  base: string, project: string
): Observable<SourceFacts> {
  const url = `https://${base}/api/v4/projects/${encodeURIComponent(project)}`
  return zip(

    /* Fetch version */
    requestJSON<Release>(`${url}/releases/permalink/latest`)
      .pipe(
        catchError(() => EMPTY), // @todo refactor instant loading
        map(({ tag_name }) => ({
          version: tag_name
        })),
        defaultIfEmpty({})
      ),

    /* Fetch stars and forks */
    requestJSON<ProjectSchema>(url)
      .pipe(
        catchError(() => EMPTY), // @todo refactor instant loading
        map(({ star_count, forks_count }) => ({
          stars: star_count,
          forks: forks_count
        })),
        defaultIfEmpty({})
      )
  )
    .pipe(
      map(([release, info]) => ({ ...release, ...info }))
    )
}
