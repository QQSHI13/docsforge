import {
  Observable,
  animationFrameScheduler,
  auditTime,
  fromEvent,
  map,
  merge,
  startWith
} from "rxjs"

import { watchElementSize } from "../../size"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Element offset
 */
export interface ElementOffset {
  x: number                            /* Horizontal offset */
  y: number                            /* Vertical offset */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve element offset
 *
 * @param el - Element
 *
 * @returns Element offset
 */
export function getElementOffset(
  el: HTMLElement
): ElementOffset {
  return {
    x: el.offsetLeft,
    y: el.offsetTop
  }
}

/**
 * Retrieve absolute element offset
 *
 * @param el - Element
 *
 * @returns Element offset
 */
export function getElementOffsetAbsolute(
  el: HTMLElement
): ElementOffset {
  const rect = el.getBoundingClientRect()
  return {
    x: rect.x + window.scrollX,
    y: rect.y + window.scrollY
  }
}

/* ------------------------------------------------------------------------- */

/**
 * Watch element offset
 *
 * @param el - Element
 *
 * @returns Element offset observable
 */
export function watchElementOffset(
  el: HTMLElement
): Observable<ElementOffset> {
  return merge(
    fromEvent(window, "load"),
    fromEvent(window, "resize")
  )
    .pipe(
      auditTime(0, animationFrameScheduler),
      map(() => getElementOffset(el)),
      startWith(getElementOffset(el))
    )
}

/**
 * Watch absolute element offset
 *
 * @param el - Element
 *
 * @returns Element offset observable
 */
export function watchElementOffsetAbsolute(
  el: HTMLElement
): Observable<ElementOffset> {
  return merge(
    watchElementOffset(el),
    watchElementSize(document.body) // @todo find a better way for this
  )
    .pipe(
      map(() => getElementOffsetAbsolute(el)),
      startWith(getElementOffsetAbsolute(el))
    )
}
