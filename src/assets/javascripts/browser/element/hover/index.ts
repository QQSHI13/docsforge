import {
  Observable,
  debounce,
  defer,
  fromEvent,
  identity,
  map,
  merge,
  startWith,
  timer
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch element hover
 *
 * The second parameter allows to specify a timeout in milliseconds after which
 * the hover state will be reset to `false`. This is useful for tooltips which
 * should disappear after a certain amount of time, in order to allow the user
 * to move the cursor from the host to the tooltip.
 *
 * @param el - Element
 * @param timeout - Timeout
 *
 * @returns Element hover observable
 */
export function watchElementHover(
  el: HTMLElement, timeout?: number
): Observable<boolean> {
  return defer(() => merge(
    fromEvent(el, "mouseenter").pipe(map(() => true)),
    fromEvent(el, "mouseleave").pipe(map(() => false))
  )
    .pipe(
      timeout ? debounce(active => timer(+!active * timeout)) : identity,
      startWith(el.matches(":hover"))
    )
  )
}
