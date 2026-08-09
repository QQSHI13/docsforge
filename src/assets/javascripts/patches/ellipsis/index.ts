import {
  EMPTY,
  Observable,
  filter,
  finalize,
  map,
  mergeMap,
  skip,
  switchMap,
  take,
  takeUntil
} from "rxjs"

import { feature } from "~/_"
import {
  Viewport,
  getElements,
  watchElementVisibility
} from "~/browser"
import { mountInlineTooltip2 } from "~/components/tooltip2"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Patch options
 */
interface PatchOptions {
  document$: Observable<Document>      /* Document observable */
  viewport$: Observable<Viewport>      /* Viewport observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Patch ellipsis
 *
 * This function will fetch all elements that are shortened with ellipsis, and
 * filter those which are visible. Once they become visible, they stay in that
 * state, even though they may be hidden again. This optimization is necessary
 * to reduce pressure on the browser, with elements fading in and out of view.
 *
 * @param options - Options
 */
export function patchEllipsis(
  { document$, viewport$ }: PatchOptions
): void {
  document$
    .pipe(
      switchMap(() => getElements(".md-ellipsis")),
      mergeMap(el => watchElementVisibility(el)
        .pipe(
          takeUntil(document$.pipe(skip(1))),
          filter(visible => visible),
          map(() => el),
          take(1)
        )
      ),
      filter(el => el.offsetWidth < el.scrollWidth),
      mergeMap(el => {
        const text = el.innerText
        const host = el.closest("a") || el
        host.title = text

        // Do not mount improved tooltip if feature is disabled
        if (!feature("content.tooltips"))
          return EMPTY

        /* Mount tooltip */
        return mountInlineTooltip2(host, { viewport$ })
          .pipe(
            takeUntil(document$.pipe(skip(1))),
            finalize(() => host.removeAttribute("title"))
          )
      })
    )
      .subscribe()

  // @todo move this outside of here and fix memleaks
  if (feature("content.tooltips"))
    document$
      .pipe(
        switchMap(() => getElements(".md-status")),
        mergeMap(el => mountInlineTooltip2(el, { viewport$ }))
      )
        .subscribe()
}
