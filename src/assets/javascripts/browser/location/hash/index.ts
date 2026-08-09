import {
  Observable,
  filter,
  fromEvent,
  map,
  merge,
  shareReplay,
  startWith
} from "rxjs"

import { getOptionalElement } from "~/browser"
import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve location hash
 *
 * @returns Location hash
 */
export function getLocationHash(): string {
  return location.hash.slice(1)
}

/**
 * Set location hash
 *
 * Setting a new fragment identifier via `location.hash` will have no effect
 * if the value doesn't change. When a new fragment identifier is set, we want
 * the browser to target the respective element at all times, which is why we
 * use this dirty little trick.
 *
 * @param hash - Location hash
 */
export function setLocationHash(hash: string): void {
  const el = h("a", { href: hash })
  el.addEventListener("click", ev => ev.stopPropagation())
  el.click()
}

/* ------------------------------------------------------------------------- */

/**
 * Watch location hash
 *
 * @param location$ - Location observable
 *
 * @returns Location hash observable
 */
export function watchLocationHash(
  location$: Observable<URL>
): Observable<string> {
  return merge(
    fromEvent<HashChangeEvent>(window, "hashchange"),
    location$
  )
    .pipe(
      map(getLocationHash),
      startWith(getLocationHash()),
      filter(hash => hash.length > 0),
      shareReplay(1)
    )
}

/**
 * Watch location target
 *
 * @param location$ - Location observable
 *
 * @returns Location target observable
 */
export function watchLocationTarget(
  location$: Observable<URL>
): Observable<HTMLElement> {
  return watchLocationHash(location$)
    .pipe(
      map(id => getOptionalElement(`[id="${id}"]`)!),
      filter(el => typeof el !== "undefined")
    )
}
