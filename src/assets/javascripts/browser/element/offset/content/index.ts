import {
  Observable,
  animationFrameScheduler,
  auditTime,
  fromEvent,
  map,
  merge,
  startWith
} from "rxjs"

import { ElementOffset } from "../_"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve element content offset (= scroll offset)
 *
 * @param el - Element
 *
 * @returns Element content offset
 */
export function getElementContentOffset(
  el: HTMLElement
): ElementOffset {
  return {
    x: el.scrollLeft,
    y: el.scrollTop
  }
}

/* ------------------------------------------------------------------------- */

/**
 * Watch element content offset
 *
 * @param el - Element
 *
 * @returns Element content offset observable
 */
export function watchElementContentOffset(
  el: HTMLElement
): Observable<ElementOffset> {
  return merge(
    fromEvent(el, "scroll"),
    fromEvent(window, "scroll"),
    fromEvent(window, "resize")
  )
    .pipe(
      auditTime(0, animationFrameScheduler),
      map(() => getElementContentOffset(el)),
      startWith(getElementContentOffset(el))
    )
}
