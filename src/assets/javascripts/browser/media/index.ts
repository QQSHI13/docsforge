import {
  EMPTY,
  Observable,
  fromEvent,
  fromEventPattern,
  map,
  merge,
  startWith,
  switchMap
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch media query
 *
 * Note that although `MediaQueryList.addListener` is deprecated we have to
 * use it, because it's the only way to ensure proper downward compatibility.
 *
 * @see https://bit.ly/3dUBH2m - GitHub issue
 *
 * @param query - Media query
 *
 * @returns Media observable
 */
export function watchMedia(query: string): Observable<boolean> {
  const media = matchMedia(query)
  return fromEventPattern<boolean>(next => (
    media.addListener(() => next(media.matches))
  ))
    .pipe(
      startWith(media.matches)
    )
}

/**
 * Watch print mode
 *
 * @returns Print observable
 */
export function watchPrint(): Observable<boolean> {
  const media = matchMedia("print")
  return merge(
    fromEvent(window, "beforeprint").pipe(map(() => true)),
    fromEvent(window, "afterprint").pipe(map(() => false))
  )
    .pipe(
      startWith(media.matches)
    )
}

/* ------------------------------------------------------------------------- */

/**
 * Toggle an observable with a media observable
 *
 * @template T - Data type
 *
 * @param query$ - Media observable
 * @param factory - Observable factory
 *
 * @returns Toggled observable
 */
export function at<T>(
  query$: Observable<boolean>, factory: () => Observable<T>
): Observable<T> {
  return query$
    .pipe(
      switchMap(active => active ? factory() : EMPTY)
    )
}
