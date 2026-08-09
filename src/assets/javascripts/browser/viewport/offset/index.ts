import {
  Observable,
  fromEvent,
  map,
  merge,
  startWith
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Viewport offset
 */
export interface ViewportOffset {
  x: number                            /* Horizontal offset */
  y: number                            /* Vertical offset */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Retrieve viewport offset
 *
 * On iOS Safari, viewport offset can be negative due to overflow scrolling.
 * As this may induce strange behaviors downstream, we'll just limit it to 0.
 *
 * @returns Viewport offset
 */
export function getViewportOffset(): ViewportOffset {
  return {
    x: Math.max(0, scrollX),
    y: Math.max(0, scrollY)
  }
}

/* ------------------------------------------------------------------------- */

/**
 * Watch viewport offset
 *
 * @returns Viewport offset observable
 */
export function watchViewportOffset(): Observable<ViewportOffset> {
  return merge(
    fromEvent(window, "scroll", { passive: true }),
    fromEvent(window, "resize", { passive: true })
  )
    .pipe(
      map(getViewportOffset),
      startWith(getViewportOffset())
    )
}
