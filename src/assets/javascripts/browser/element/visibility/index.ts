import {
  NEVER,
  Observable,
  Subject,
  defer,
  distinctUntilChanged,
  filter,
  finalize,
  map,
  merge,
  of,
  shareReplay,
  switchMap,
  tap
} from "rxjs"

import {
  getElementContentSize,
  getElementSize,
  watchElementContentOffset
} from "~/browser"

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Intersection observer entry subject
 */
const entry$ = new Subject<IntersectionObserverEntry>()

/**
 * Intersection observer observable
 *
 * This observable will create an `IntersectionObserver` on first subscription
 * and will automatically terminate it when there are no more subscribers.
 *
 * @see https://bit.ly/3iIYfEm - Google Groups on performance
 */
const observer$ = defer(() => of(
  new IntersectionObserver(entries => {
    for (const entry of entries)
      entry$.next(entry)
  }, {
    threshold: 0
  })
))
  .pipe(
    switchMap(observer => merge(NEVER, of(observer))
      .pipe(
        finalize(() => observer.disconnect())
      )
    ),
    shareReplay(1)
  )

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch element visibility
 *
 * @param el - Element
 *
 * @returns Element visibility observable
 */
export function watchElementVisibility(
  el: HTMLElement
): Observable<boolean> {
  return observer$
    .pipe(
      tap(observer => observer.observe(el)),
      switchMap(observer => entry$
        .pipe(
          filter(({ target }) => target === el),
          finalize(() => observer.unobserve(el)),
          map(({ isIntersecting }) => isIntersecting)
        )
      )
    )
}

/**
 * Watch element boundary
 *
 * This function returns an observable which emits whether the bottom content
 * boundary (= scroll offset) of an element is within a certain threshold.
 *
 * @param el - Element
 * @param threshold - Threshold
 *
 * @returns Element boundary observable
 */
export function watchElementBoundary(
  el: HTMLElement, threshold = 16
): Observable<boolean> {
  return watchElementContentOffset(el)
    .pipe(
      map(({ y }) => {
        const visible = getElementSize(el)
        const content = getElementContentSize(el)
        return y >= (
          content.height - visible.height - threshold
        )
      }),
      distinctUntilChanged()
    )
}
