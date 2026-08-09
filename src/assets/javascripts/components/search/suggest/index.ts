import {
  Observable,
  Subject,
  asyncScheduler,
  combineLatestWith,
  distinctUntilChanged,
  filter,
  finalize,
  fromEvent,
  map,
  merge,
  observeOn,
  tap
} from "rxjs"

import { Keyboard } from "~/browser"
import {
  SearchMessage,
  SearchResult,
  isSearchResultMessage
} from "~/integrations"

import { Component, getComponentElement } from "../../_"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Search suggestions
 */
export interface SearchSuggest {}

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Mount options
 */
interface MountOptions {
  keyboard$: Observable<Keyboard>      /* Keyboard observable */
  worker$: Subject<SearchMessage>      /* Search worker */
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Mount search suggestions
 *
 * This function will perform a lazy rendering of the search results, depending
 * on the vertical offset of the search result container.
 *
 * @param el - Search result list element
 * @param options - Options
 *
 * @returns Search result list component observable
 */
export function mountSearchSuggest(
  el: HTMLElement, { worker$, keyboard$ }: MountOptions
): Observable<Component<SearchSuggest>> {
  const push$ = new Subject<SearchResult>()

  /* Retrieve query component and track all changes */
  const query  = getComponentElement("search-query")
  const query$ = merge(
    fromEvent(query, "keydown"),
    fromEvent(query, "focus")
  )
    .pipe(
      observeOn(asyncScheduler),
      map(() => query.value),
      distinctUntilChanged(),
    )

  /* Update search suggestions */
  push$
    .pipe(
      combineLatestWith(query$),
      map(([{ suggest }, value]) => {
        const words = value.split(/([\s-]+)/)
        if (suggest?.length && words[words.length - 1]) {
          const last = suggest[suggest.length - 1]
          if (last.startsWith(words[words.length - 1]))
            words[words.length - 1] = last
        } else {
          words.length = 0
        }
        return words
      })
    )
      .subscribe(words => el.textContent = words.join(""))

  /* Set up search keyboard handlers */
  keyboard$
    .pipe(
      filter(({ mode }) => mode === "search")
    )
      .subscribe(key => {
        switch (key.type) {

          /* Right arrow: accept current suggestion */
          case "ArrowRight":
            if (
              el.innerText.length &&
              query.selectionStart === query.value.length
            )
              query.value = el.innerText
            break
        }
      })

  /* Filter search result message */
  const result$ = worker$
    .pipe(
      filter(isSearchResultMessage),
      map(({ data }) => data)
    )

  /* Create and return component */
  return result$
    .pipe(
      tap(state => push$.next(state)),
      finalize(() => push$.complete()),
      map(() => ({ ref: el }))
    )
}
