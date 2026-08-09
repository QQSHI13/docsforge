import {
  ObservableInput,
  Subject,
  first,
  merge,
  of,
  switchMap
} from "rxjs"

import { feature } from "~/_"
import { watchToggle, watchWorker } from "~/browser"

import { SearchIndex } from "../../config"
import {
  SearchMessage,
  SearchMessageType
} from "../message"

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Set up search worker
 *
 * This function creates and initializes a web worker that is used for search,
 * so that the user interface doesn't freeze. In general, the application does
 * not care how search is implemented, as long as the web worker conforms to
 * the format expected by the application as defined in `SearchMessage`. This
 * allows the author to implement custom search functionality, by providing a
 * custom web worker via configuration.
 *
 * Material for MkDocs' built-in search implementation makes use of Lunr.js, an
 * efficient and fast implementation for client-side search. Leveraging a tiny
 * iframe-based web worker shim, search is even supported for the `file://`
 * protocol, enabling search for local non-hosted builds.
 *
 * If the protocol is `file://`, search initialization is deferred to mitigate
 * freezing, as it's now synchronous by design - see https://bit.ly/3C521EO
 *
 * @see https://bit.ly/3igvtQv - How to implement custom search
 *
 * @param url - Worker URL
 * @param index$ - Search index observable input
 *
 * @returns Search worker
 */
export function setupSearchWorker(
  url: string, index$: ObservableInput<SearchIndex>
): Subject<SearchMessage> {
  const worker$ = watchWorker<SearchMessage>(url)
  merge(
    of(location.protocol !== "file:"),
    watchToggle("search")
  )
    .pipe(
      first(active => active),
      switchMap(() => index$)
    )
      .subscribe(({ config, docs }) => worker$.next({
        type: SearchMessageType.SETUP,
        data: {
          config,
          docs,
          options: {
            suggest: feature("search.suggest")
          }
        }
      }))

  /* Return search worker */
  return worker$
}
