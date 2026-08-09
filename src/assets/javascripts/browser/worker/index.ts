import {
  Observable,
  Subject,
  endWith,
  fromEvent,
  ignoreElements,
  mergeWith,
  share,
  takeUntil
} from "rxjs"

/* ----------------------------------------------------------------------------
 * Types
 * ------------------------------------------------------------------------- */

/**
 * Worker message
 */
export interface WorkerMessage {
  type: unknown                        /* Message type */
  data?: unknown                       /* Message data */
}

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Create an observable for receiving from a web worker
 *
 * @template T - Data type
 *
 * @param worker - Web worker
 *
 * @returns Message observable
 */
function recv<T>(worker: Worker): Observable<T> {
  return fromEvent<MessageEvent<T>, T>(worker, "message", ev => ev.data)
}

/**
 * Create a subject for sending to a web worker
 *
 * @template T - Data type
 *
 * @param worker - Web worker
 *
 * @returns Message subject
 */
function send<T>(worker: Worker): Subject<T> {
  const send$ = new Subject<T>()
  send$.subscribe(data => worker.postMessage(data))

  /* Return message subject */
  return send$
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Create a bidirectional communication channel to a web worker
 *
 * @template T - Data type
 *
 * @param url - Worker URL
 * @param worker - Worker
 *
 * @returns Worker subject
 */
export function watchWorker<T extends WorkerMessage>(
  url: string, worker = new Worker(url)
): Subject<T> {
  const recv$ = recv<T>(worker)
  const send$ = send<T>(worker)

  /* Create worker subject and forward messages */
  const worker$ = new Subject<T>()
  worker$.subscribe(send$)

  /* Return worker subject */
  const done$ = send$.pipe(ignoreElements(), endWith(true))
  return worker$
    .pipe(
      ignoreElements(),
      mergeWith(recv$.pipe(takeUntil(done$))),
      share()
    ) as Subject<T>
}
