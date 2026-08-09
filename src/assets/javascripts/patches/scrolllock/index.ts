import {
  Observable,
  combineLatest,
  delay,
  map,
  of,
  switchMap,
  withLatestFrom
} from "rxjs"

import {
  Viewport,
  watchToggle
} from "~/browser"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Patch options
 */
interface PatchOptions {
  viewport$: Observable<Viewport>      /* Viewport observable */
  tablet$: Observable<boolean>         /* Media tablet observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Patch the document body to lock when search is open
 *
 * For mobile and tablet viewports, the search is rendered full screen, which
 * leads to scroll leaking when at the top or bottom of the search result. This
 * function locks the body when the search is in full screen mode, and restores
 * the scroll position when leaving.
 *
 * @param options - Options
 */
export function patchScrolllock(
  { viewport$, tablet$ }: PatchOptions
): void {
  combineLatest([watchToggle("search"), tablet$])
    .pipe(
      map(([active, tablet]) => active && !tablet),
      switchMap(active => of(active)
        .pipe(
          delay(active ? 400 : 100)
        )
      ),
      withLatestFrom(viewport$)
    )
      .subscribe(([active, { offset: { y }}]) => {
        if (active) {
          document.body.setAttribute("data-md-scrolllock", "")
          document.body.style.top = `-${y}px`
        } else {
          const value = -1 * parseInt(document.body.style.top, 10)
          document.body.removeAttribute("data-md-scrolllock")
          document.body.style.top = ""
          if (value)
            window.scrollTo(0, value)
        }
      })
}
