import {
  EMPTY,
  Observable,
  catchError,
  filter,
  fromEvent,
  map,
  mergeMap,
  of,
  switchMap
} from "rxjs"

import { configuration } from "~/_"
import {
  getElements,
  getLocation,
  setLocation
} from "~/browser"

import { Sitemap, fetchSitemap } from "../sitemap"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Setup options
 */
interface SetupOptions {
  document$: Observable<Document>      /* Document subject */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Set up alternate version navigation
 *
 * @param options - Options
 */
export function setupAlternate(
  { document$ }: SetupOptions
): void {
  const alternate = new Map<string, Sitemap>()

  // Fetch sitemaps for all discovered alternate versions
  document$
    .pipe(
      switchMap(() => getElements<HTMLLinkElement>("link[rel=alternate]")),
      map(el => new URL(el.href)),
      filter(url => !alternate.has(url.toString())),
      mergeMap(url => fetchSitemap(url)
        .pipe(
          map(sitemap => [url, sitemap] as const),
          catchError(() => EMPTY)
        )
      )
    )

      // Persist fully qualified URL, because alternate versions may be on
      // entirely different domains, but as long a proper cross-origin policy
      // is set, we can still navigate to them. Also, remove the trailing slash
      // to normalize the URL
      .subscribe(([url, sitemap]) => {
        alternate.set(url.toString().replace(/\/$/, ""), sitemap)
      })

  // Intercept alternate navigation - when refactoring instant navigation later,
  // we should provide a single stream of events that we all subscribe to, and
  // from which we implement version and alternate language navigation
  fromEvent<MouseEvent>(document.body, "click")
    .pipe(
      filter(ev => !ev.metaKey && !ev.ctrlKey),
      switchMap(ev => {
        if (ev.target instanceof Element) {
          const el = ev.target.closest("a")

          // Now, we need to check whether the navigation target is an alternate
          // version. If so, we need to prevent the default navigation behavior
          // and instead navigate to the correct page, if we can resolve it.
          if (el && !el.target) {
            const result = [...alternate].find(([url]) => (
              el.href.startsWith(`${url}/`)
            ))

            // Check, that we got a sitemap at least, so we know that we either
            // navigate on the current site, or to an alternate site
            if (typeof result === "undefined")
              return EMPTY

            // Check that we go to and alternate site
            const [url, sitemap] = result
            const location = getLocation()
            if (location.href.startsWith(url))
              return EMPTY

            // Isolate the part to which we navigate and check if it's in the
            // sitemap that we resolved earlier @todo: refactor this, as the
            // semantics slightly changed due to the new sitemap resolution
            // implementation, which normalizes all URLs.
            const config = configuration()
            let path = location.href.replace(config.base, "")
            path = `${url}/${path}`
            const target = sitemap.has(path.split("#")[0])
              ? new URL(path, config.base)
              : new URL(url)

            // Steal navigation and navigate to the correct page
            ev.preventDefault()
            return of(target)
          }
        }
        return EMPTY
      })
    )
    .subscribe(url => setLocation(url, true))
}
