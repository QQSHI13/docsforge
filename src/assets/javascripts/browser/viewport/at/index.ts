import {
  Observable,
  combineLatest,
  distinctUntilKeyChanged,
  map
} from "rxjs"

import { Header } from "~/components"

import { getElementOffset } from "../../element"
import { Viewport } from "../_"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  viewport$: Observable<Viewport>      /* Viewport observable */
  header$: Observable<Header>          /* Header observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch viewport relative to element
 *
 * @param el - Element
 * @param options - Options
 *
 * @returns Viewport observable
 */
export function watchViewportAt(
  el: HTMLElement, { viewport$, header$ }: WatchOptions
): Observable<Viewport> {
  const size$ = viewport$
    .pipe(
      distinctUntilKeyChanged("size")
    )

  /* Compute element offset */
  const offset$ = combineLatest([size$, header$])
    .pipe(
      map(() => getElementOffset(el))
    )

  /* Compute relative viewport, return hot observable */
  return combineLatest([header$, viewport$, offset$])
    .pipe(
      map(([{ height }, { offset, size }, { x, y }]) => ({
        offset: {
          x: offset.x - x,
          y: offset.y - y + height
        },
        size
      }))
    )
}
