import {
  Observable,
  combineLatest,
  map,
  shareReplay
} from "rxjs"

import {
  ViewportOffset,
  watchViewportOffset
} from "../offset"
import {
  ViewportSize,
  watchViewportSize
} from "../size"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Viewport
 */
export interface Viewport {
  offset: ViewportOffset               /* Viewport offset */
  size: ViewportSize                   /* Viewport size */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch viewport
 *
 * @returns Viewport observable
 */
export function watchViewport(): Observable<Viewport> {
  return combineLatest([
    watchViewportOffset(),
    watchViewportSize()
  ])
    .pipe(
      map(([offset, size]) => ({ offset, size })),
      shareReplay(1)
    )
}
