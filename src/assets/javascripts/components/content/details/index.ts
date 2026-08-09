import {
  Observable,
  Subject,
  defer,
  filter,
  finalize,
  map,
  merge,
  tap
} from "rxjs"

import { Component } from "../../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Details
 */
export interface Details {
  action: "open" | "close"             /* Details state */
  reveal?: boolean                     /* Details is revealed */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  target$: Observable<HTMLElement>     /* Location target observable */
  print$: Observable<boolean>          /* Media print observable */
}

/**
 * Mount options
 */
interface MountOptions {
  target$: Observable<HTMLElement>     /* Location target observable */
  print$: Observable<boolean>          /* Media print observable */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch details
 *
 * @param el - Details element
 * @param options - Options
 *
 * @returns Details observable
 */
export function watchDetails(
  el: HTMLDetailsElement, { target$, print$ }: WatchOptions
): Observable<Details> {
  let open = true
  return merge(

    /* Open and focus details on location target */
    target$
      .pipe(
        map(target => target.closest("details:not([open])")!),
        filter(details => el === details),
        map(() => ({
          action: "open", reveal: true
        }) as Details)
      ),

    /* Open details on print and close afterwards */
    print$
      .pipe(
        filter(active => active || !open),
        tap(() => open = el.open),
        map(active => ({
          action: active ? "open" : "close"
        }) as Details)
      )
  )
}

/**
 * Mount details
 *
 * This function ensures that `details` tags are opened on anchor jumps and
 * prior to printing, so the whole content of the page is visible.
 *
 * @param el - Details element
 * @param options - Options
 *
 * @returns Details component observable
 */
export function mountDetails(
  el: HTMLDetailsElement, options: MountOptions
): Observable<Component<Details>> {
  return defer(() => {
    const push$ = new Subject<Details>()
    push$.subscribe(({ action, reveal }) => {
      el.toggleAttribute("open", action === "open")
      if (reveal)
        el.scrollIntoView()
    })

    /* Create and return component */
    return watchDetails(el, options)
      .pipe(
        tap(state => push$.next(state)),
        finalize(() => push$.complete()),
        map(state => ({ ref: el, ...state }))
      )
  })
}
