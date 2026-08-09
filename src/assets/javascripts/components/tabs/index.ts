import {
  Observable,
  Subject,
  defer,
  distinctUntilKeyChanged,
  finalize,
  map,
  of,
  switchMap,
  tap
} from "rxjs"

import { feature } from "~/_"
import {
  Viewport,
  watchElementSize,
  watchViewportAt
} from "~/browser"

import { Component } from "../_"
import { Header } from "../header"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Navigation tabs
 */
export interface Tabs {
  hidden: boolean                      /* Navigation tabs are hidden */
}

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

/**
 * Mount options
 */
interface MountOptions {
  viewport$: Observable<Viewport>      /* Viewport observable */
  header$: Observable<Header>          /* Header observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch navigation tabs
 *
 * @param el - Navigation tabs element
 * @param options - Options
 *
 * @returns Navigation tabs observable
 */
export function watchTabs(
  el: HTMLElement, { viewport$, header$ }: WatchOptions
): Observable<Tabs> {
  return watchElementSize(document.body)
    .pipe(
      switchMap(() => watchViewportAt(el, { header$, viewport$ })),
      map(({ offset: { y } }) => {
        return {
          hidden: y >= 10
        }
      }),
      distinctUntilKeyChanged("hidden")
    )
}

/**
 * Mount navigation tabs
 *
 * This function hides the navigation tabs when scrolling past the threshold
 * and makes them reappear in a nice CSS animation when scrolling back up.
 *
 * @param el - Navigation tabs element
 * @param options - Options
 *
 * @returns Navigation tabs component observable
 */
export function mountTabs(
  el: HTMLElement, options: MountOptions
): Observable<Component<Tabs>> {
  return defer(() => {
    const push$ = new Subject<Tabs>()
    push$.subscribe({

      /* Handle emission */
      next({ hidden }) {
        el.hidden = hidden
      },

      /* Handle complete */
      complete() {
        el.hidden = false
      }
    })

    /* Create and return component */
    return (
      feature("navigation.tabs.sticky")
        ? of({ hidden: false })
        : watchTabs(el, options)
    )
      .pipe(
        tap(state => push$.next(state)),
        finalize(() => push$.complete()),
        map(state => ({ ref: el, ...state }))
      )
  })
}
