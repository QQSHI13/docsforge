import {
  Observable,
  Subject,
  defer,
  delay,
  finalize,
  map,
  merge,
  of,
  switchMap,
  tap
} from "rxjs"

import { getElement } from "~/browser"

import { Component } from "../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Dialog
 */
export interface Dialog {
  message: string                      /* Dialog message */
  active: boolean                      /* Dialog is active */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  alert$: Subject<string>              /* Alert subject */
}

/**
 * Mount options
 */
interface MountOptions {
  alert$: Subject<string>              /* Alert subject */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch dialog
 *
 * @param _el - Dialog element
 * @param options - Options
 *
 * @returns Dialog observable
 */
export function watchDialog(
  _el: HTMLElement, { alert$ }: WatchOptions
): Observable<Dialog> {
  return alert$
    .pipe(
      switchMap(message => merge(
        of(true),
        of(false).pipe(delay(2000))
      )
        .pipe(
          map(active => ({ message, active }))
        )
      )
    )
}

/**
 * Mount dialog
 *
 * This function reveals the dialog in the right corner when a new alert is
 * emitted through the subject that is passed as part of the options.
 *
 * @param el - Dialog element
 * @param options - Options
 *
 * @returns Dialog component observable
 */
export function mountDialog(
  el: HTMLElement, options: MountOptions
): Observable<Component<Dialog>> {
  const inner = getElement(".md-typeset", el)
  return defer(() => {
    const push$ = new Subject<Dialog>()
    push$.subscribe(({ message, active }) => {
      el.classList.toggle("md-dialog--active", active)
      inner.textContent = message
    })

    /* Create and return component */
    return watchDialog(el, options)
      .pipe(
        tap(state => push$.next(state)),
        finalize(() => push$.complete()),
        map(state => ({ ref: el, ...state }))
      )
  })
}
