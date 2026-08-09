import {
  Observable,
  fromEvent,
  map,
  mergeMap,
  switchMap,
  takeWhile,
  tap,
  withLatestFrom
} from "rxjs"

import { getElements } from "~/browser"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Patch options
 */
interface PatchOptions {
  document$: Observable<Document>      /* Document observable */
  tablet$: Observable<boolean>         /* Media tablet observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Patch indeterminate checkboxes
 *
 * This function replaces the indeterminate "pseudo state" with the actual
 * indeterminate state, which is used to keep navigation always expanded.
 *
 * @param options - Options
 */
export function patchIndeterminate(
  { document$, tablet$ }: PatchOptions
): void {
  document$
    .pipe(
      switchMap(() => getElements<HTMLInputElement>(
        ".md-toggle--indeterminate"
      )),
      tap(el => {
        el.indeterminate = true
        el.checked = false
      }),
      mergeMap(el => fromEvent(el, "change")
        .pipe(
          takeWhile(() => el.classList.contains("md-toggle--indeterminate")),
          map(() => el)
        )
      ),
      withLatestFrom(tablet$)
    )
      .subscribe(([el, tablet]) => {
        el.classList.remove("md-toggle--indeterminate")
        if (tablet)
          el.checked = false
      })
}
