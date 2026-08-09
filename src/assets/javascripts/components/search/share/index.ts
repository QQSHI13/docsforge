import {
  Observable,
  Subject,
  endWith,
  finalize,
  fromEvent,
  ignoreElements,
  map,
  takeUntil,
  tap
} from "rxjs"

import { getLocation } from "~/browser"

import { Component } from "../../_"
import { SearchQuery } from "../query"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search sharing
 */
export interface SearchShare {
  url: URL                             /* Deep link for sharing */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  query$: Observable<SearchQuery>      /* Search query observable */
}

/**
 * Mount options
 */
interface MountOptions {
  query$: Observable<SearchQuery>      /* Search query observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount search sharing
 *
 * @param _el - Search sharing element
 * @param options - Options
 *
 * @returns Search sharing observable
 */
export function watchSearchShare(
  _el: HTMLElement, { query$ }: WatchOptions
): Observable<SearchShare> {
  return query$
    .pipe(
      map(({ value }) => {
        const url = getLocation()
        url.hash = ""

        /* Compute readable query strings */
        value = value
          .replace(/\s+/g, "+")        /* Collapse whitespace */
          .replace(/&/g, "%26")        /* Escape '&' character */
          .replace(/=/g, "%3D")        /* Escape '=' character */

        /* Replace query string */
        url.search = `q=${value}`
        return { url }
      })
    )
}

/**
 * Mount search sharing
 *
 * @param el - Search sharing element
 * @param options - Options
 *
 * @returns Search sharing component observable
 */
export function mountSearchShare(
  el: HTMLAnchorElement, options: MountOptions
): Observable<Component<SearchShare>> {
  const push$ = new Subject<SearchShare>()
  const done$ = push$.pipe(ignoreElements(), endWith(true))
  push$.subscribe(({ url }) => {
    el.setAttribute("data-clipboard-text", el.href)
    el.href = `${url}`
  })

  /* Prevent following of link */
  fromEvent(el, "click")
    .pipe(
      takeUntil(done$)
    )
      .subscribe(ev => ev.preventDefault())

  /* Create and return component */
  return watchSearchShare(el, options)
    .pipe(
      tap(state => push$.next(state)),
      finalize(() => push$.complete()),
      map(state => ({ ref: el, ...state }))
    )
}
