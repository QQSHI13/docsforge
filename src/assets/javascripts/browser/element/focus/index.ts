import {
  Observable,
  debounceTime,
  distinctUntilChanged,
  fromEvent,
  map,
  merge,
  shareReplay,
  startWith
} from "rxjs"

import { getActiveElement } from "../_"

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Focus observable
 *
 * Previously, this observer used `focus` and `blur` events to determine whether
 * an element is focused, but this doesn't work if there are focusable elements
 * within the elements itself. A better solutions are `focusin` and `focusout`
 * events, which bubble up the tree and allow for more fine-grained control.
 *
 * `debounceTime` is necessary, because when a focus change happens inside an
 * element, the observable would first emit `false` and then `true` again.
 */
const observer$ = merge(
  fromEvent(document.body, "focusin"),
  fromEvent(document.body, "focusout")
)
  .pipe(
    debounceTime(1),
    startWith(undefined),
    map(() => getActiveElement() || document.body),
    shareReplay(1)
  )

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch element focus
 *
 * @param el - Element
 *
 * @returns Element focus observable
 */
export function watchElementFocus(
  el: HTMLElement
): Observable<boolean> {
  return observer$
    .pipe(
      map(active => el.contains(active)),
      distinctUntilChanged()
    )
}
