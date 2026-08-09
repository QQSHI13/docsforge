import {
  Observable,
  Subject,
  map,
  shareReplay,
  switchMap
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Helper types
 * ------------------------------------------------------------------------- */

/**
 * Options
 */
interface Options {
  progress$?: Subject<number>          // Progress subject
  headers?: Record<string, string>    // Extra request headers
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Fetch the given URL
 *
 * This function returns an observable that emits the response as a blob and
 * completes, or emits an error if the request failed. The caller can cancel
 * the request by unsubscribing at any time, which will automatically abort
 * the inflight request and complete the observable.
 *
 * Note that we use `XMLHTTPRequest` not because we're nostalgic, but because
 * it's the only way to get progress events for downloads and also allow for
 * cancellation of requests, as the official Fetch API does not support this
 * yet, even though we're already in 2024.
 *
 * @param url - Request URL
 * @param options - Options
 *
 * @returns Data observable
 */
export function request(
  url: URL | string, options?: Options
): Observable<Blob> {
  return new Observable<Blob>(observer => {
    const req = new XMLHttpRequest()
    req.open("GET", `${url}`)
    req.responseType = "blob"
    for (const [name, value] of Object.entries(options?.headers ?? {}))
      req.setRequestHeader(name, value)

    // Handle response
    req.addEventListener("load", () => {
      if (req.status >= 200 && req.status < 300) {
        observer.next(req.response)
        observer.complete()

      // Every response that is not in the 2xx range is considered an error
      } else {
        observer.error(new Error(req.statusText))
      }
    })

    // Handle network errors
    req.addEventListener("error", () => {
      observer.error(new Error("Network error"))
    })

    // Handle aborted requests
    req.addEventListener("abort", () => {
      observer.complete()
    })

    // Handle download progress
    if (typeof options?.progress$ !== "undefined") {
      req.addEventListener("progress", event => {
        if (event.lengthComputable) {
          options.progress$!.next((event.loaded / event.total) * 100)

        // Hack: Chromium doesn't report the total number of bytes if content
        // is compressed, so we need this fallback - see https://t.ly/ZXofI
        } else {
          const length = req.getResponseHeader("Content-Length") ?? 0
          options.progress$!.next((event.loaded / +length) * 100)
        }
      })

      // Immediately set progress to 5% to indicate that we're loading
      options.progress$.next(5)
    }

    // Send request and automatically abort request upon unsubscription
    req.send()
    return () => req.abort()
  })
}

/* ------------------------------------------------------------------------- */

/**
 * Fetch JSON from the given URL
 *
 * @template T - Data type
 *
 * @param url - Request URL
 * @param options - Options
 *
 * @returns Data observable
 */
export function requestJSON<T>(
  url: URL | string, options?: Options
): Observable<T> {
  return request(url, options)
    .pipe(
      switchMap(res => res.text()),
      map(body => JSON.parse(body) as T),
      shareReplay(1)
    )
}

/**
 * Fetch HTML from the given URL
 *
 * @param url - Request URL
 * @param options - Options
 *
 * @returns Data observable
 */
export function requestHTML(
  url: URL | string, options?: Options
): Observable<Document> {
  const dom = new DOMParser()
  return request(url, {
    ...options,
    // DocsForge: let the service worker distinguish instant-navigation page
    // fetches from asset fetches (XHR sends `Accept: */*` and has no
    // `destination`), so servePage() picks the preferred-locale variant
    // instead of serveAsset() returning the canonical (default-locale) file.
    headers: {
      ...(options?.headers ?? {}),
      "X-DocsForge-Instant-Nav": "1"
    }
  })
    .pipe(
      switchMap(res => res.text()),
      map(res => dom.parseFromString(res, "text/html")),
      shareReplay(1)
    )
}

/**
 * Fetch XML from the given URL
 *
 * @param url - Request URL
 * @param options - Options
 *
 * @returns Data observable
 */
export function requestXML(
  url: URL | string, options?: Options
): Observable<Document> {
  const dom = new DOMParser()
  return request(url, options)
    .pipe(
      switchMap(res => res.text()),
      map(res => dom.parseFromString(res, "text/xml")),
      shareReplay(1)
    )
}
