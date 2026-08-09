import {
  Observable,
  Subject,
  defer,
  finalize,
  map,
  tap
} from "rxjs"

import { Component } from "../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Progress indicator
 */
export interface Progress {
  value: number                        // Progress value
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Mount options
 */
interface MountOptions {
  progress$: Subject<number>           // Progress subject
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount progress indicator
 *
 * @param el - Progress indicator element
 * @param options - Options
 *
 * @returns Progress indicator component observable
 */
export function mountProgress(
  el: HTMLElement, { progress$ }: MountOptions
): Observable<Component<Progress>> {

  // Mount component on subscription
  return defer(() => {
    const push$ = new Subject<Progress>()
    push$.subscribe(({ value }) => {
      el.style.setProperty("--md-progress-value", `${value}`)
    })

    // Create and return component
    return progress$
      .pipe(
        tap(value => push$.next({ value })),
        finalize(() => push$.complete()),
        map(value => ({ ref: el, value }))
      )
  })
}
