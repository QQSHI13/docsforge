import {
  Observable,
  defer,
  finalize,
  fromEvent,
  map,
  merge,
  switchMap,
  take,
  throwError
} from "rxjs"

import { h } from "~/utilities"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Create and load a `script` element
 *
 * This function returns an observable that will emit when the script was
 * successfully loaded, or throw an error if it wasn't.
 *
 * @param src - Script URL
 *
 * @returns Script observable
 */
export function watchScript(src: string): Observable<void> {
  const script = h("script", { src })
  return defer(() => {
    document.head.appendChild(script)
    return merge(
      fromEvent(script, "load"),
      fromEvent(script, "error")
        .pipe(
          switchMap(() => (
            throwError(() => new ReferenceError(`Invalid script: ${src}`))
          ))
        )
    )
      .pipe(
        map(() => undefined),
        finalize(() => document.head.removeChild(script)),
        take(1)
      )
  })
}
