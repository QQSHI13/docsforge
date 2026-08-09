import {
  Observable,
  Subject,
  combineLatest,
  distinctUntilChanged,
  distinctUntilKeyChanged,
  endWith,
  finalize,
  first,
  fromEvent,
  ignoreElements,
  map,
  merge,
  shareReplay,
  takeUntil,
  tap
} from "rxjs"

import {
  getElement,
  getLocation,
  setToggle,
  watchElementFocus,
  watchToggle
} from "~/browser"
import {
  SearchMessage,
  SearchMessageType,
  isSearchReadyMessage
} from "~/integrations"

import { Component } from "../../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search query
 */
export interface SearchQuery {
  value: string                        /* Query value */
  focus: boolean                       /* Query focus */
}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Watch options
 */
interface WatchOptions {
  worker$: Subject<SearchMessage>      /* Search worker */
}

/**
 * Mount options
 */
interface MountOptions {
  worker$: Subject<SearchMessage>      /* Search worker */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Watch search query
 *
 * Note that the focus event which triggers re-reading the current query value
 * is delayed by `1ms` so the input's empty state is allowed to propagate.
 *
 * @param el - Search query element
 * @param options - Options
 *
 * @returns Search query observable
 */
export function watchSearchQuery(
  el: HTMLInputElement, { worker$ }: WatchOptions
): Observable<SearchQuery> {

  /* Support search deep linking */
  const { searchParams } = getLocation()
  if (searchParams.has("q")) {
    setToggle("search", true)

    /* Set query from parameter */
    el.value = searchParams.get("q")!
    el.focus()

    /* Remove query parameter on close */
    watchToggle("search")
      .pipe(
        first(active => !active)
      )
        .subscribe(() => {
          const url = getLocation()
          url.searchParams.delete("q")
          history.replaceState({}, "", `${url}`)
        })
  }

  /* Intercept focus and input events */
  const focus$ = watchElementFocus(el)
  const value$ = merge(
    worker$.pipe(first(isSearchReadyMessage)),
    fromEvent(el, "keyup"),
    focus$
  )
    .pipe(
      map(() => el.value),
      distinctUntilChanged()
    )

  /* Combine into single observable */
  return combineLatest([value$, focus$])
    .pipe(
      map(([value, focus]) => ({ value, focus })),
      shareReplay(1)
    )
}

/**
 * Mount search query
 *
 * @param el - Search query element
 * @param options - Options
 *
 * @returns Search query component observable
 */
export function mountSearchQuery(
  el: HTMLInputElement, { worker$ }: MountOptions
): Observable<Component<SearchQuery, HTMLInputElement>> {
  const push$ = new Subject<SearchQuery>()
  const done$ = push$.pipe(ignoreElements(), endWith(true))

  /* Handle value change */
  combineLatest([
    worker$.pipe(first(isSearchReadyMessage)),
    push$
  ], (_, query) => query)
    .pipe(
      distinctUntilKeyChanged("value")
    )
      .subscribe(({ value }) => worker$.next({
        type: SearchMessageType.QUERY,
        data: value
      }))

  /* Handle focus change */
  push$
    .pipe(
      distinctUntilKeyChanged("focus")
    )
      .subscribe(({ focus }) => {
        if (focus)
          setToggle("search", focus)
      })

  /* Handle reset */
  fromEvent(el.form!, "reset")
    .pipe(
      takeUntil(done$)
    )
      .subscribe(() => el.focus())

  // Focus search query on label click - note that this is necessary to bring
  // up the keyboard on iOS and other mobile platforms, as the search dialog is
  // not visible at first, and programatically focusing an input element must
  // be triggered by a user interaction - see https://t.ly/Cb30n
  const label = getElement("header [for=__search]")
  fromEvent(label, "click")
    .subscribe(() => el.focus())

  /* Create and return component */
  return watchSearchQuery(el, { worker$ })
    .pipe(
      tap(state => push$.next(state)),
      finalize(() => push$.complete()),
      map(state => ({ ref: el, ...state })),
      shareReplay(1)
    )
}
