import {
  Observable,
  Subject,
  finalize,
  map,
  tap
} from "rxjs"

import { Component } from "../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Consent
 */
export interface Consent {
  hidden: boolean                      /* Consent is hidden */
}

/**
 * Consent defaults
 */
export interface ConsentDefaults {
  analytics?: boolean                  /* Consent for Analytics */
  github?: boolean                     /* Consent for GitHub */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  target$: Observable<HTMLElement>     /* Target observable */
}

/**
 * Mount options
 */
interface MountOptions {
  target$: Observable<HTMLElement>     /* Target observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch consent
 *
 * @param el - Consent element
 * @param options - Options
 *
 * @returns Consent observable
 */
export function watchConsent(
  el: HTMLElement, { target$ }: WatchOptions
): Observable<Consent> {
  return target$
    .pipe(
      map(target => ({ hidden: target !== el }))
    )
}

/* ------------------------------------------------------------------------- */

/**
 * Mount consent
 *
 * @param el - Consent element
 * @param options - Options
 *
 * @returns Consent component observable
 */
export function mountConsent(
  el: HTMLElement, options: MountOptions
): Observable<Component<Consent>> {
  const internal$ = new Subject<Consent>()
  internal$.subscribe(({ hidden }) => {
    el.hidden = hidden
  })

  /* Create and return component */
  return watchConsent(el, options)
    .pipe(
      tap(state => internal$.next(state)),
      finalize(() => internal$.complete()),
      map(state => ({ ref: el, ...state }))
    )
}
