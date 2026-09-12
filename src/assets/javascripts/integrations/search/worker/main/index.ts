import {
  MarzIndex,
  initialize
} from "marz-search"

import { getElement } from "~/browser/element/_"
import "~/polyfills"

import { Search } from "../../_"
import { SearchConfig } from "../../config"
import {
  SearchMessage,
  SearchMessageType
} from "../message"

/* ----------------------------------------------------------------------------
 * Data
 * ------------------------------------------------------------------------- */

/**
 * Search index
 */
let index: Search

/* ----------------------------------------------------------------------------
 * Helper functions
 * ------------------------------------------------------------------------- */

/**
 * Resolve the base URL for search assets
 *
 * The Marz WebAssembly module lives next to the worker script, but when the
 * worker runs inside of an `iframe` (when using `iframe-worker` as a shim),
 * the base URL must be determined by searching for the first `script` element
 * with a `src` attribute, which will contain the contents of this script.
 *
 * @returns Base URL for search assets
 */
function assetBase(): string {
  let base = ".."

  /* Detect `iframe-worker` and fix base URL */
  if (typeof parent !== "undefined" && "IFrameWorker" in parent) {
    const worker = getElement<HTMLScriptElement>("script[src]")
    const [path] = worker.src.split("/worker")

    /* Prefix base with path — anchor to the leading ".." so a later ".."
       sequence can never be replaced unintentionally */
    base = base.replace(/^\.\./, path)
  }

  /* Return base URL */
  return base
}

/**
 * Set up the Marz search index
 *
 * This function fetches the WebAssembly module, initializes it, and loads the
 * prebuilt index that the backend emitted next to `search_index.json`. The
 * expected language guards against a pipeline shipping the wrong per-locale
 * file — if it doesn't match the bytes, loading is retried without the
 * assertion, so a stale file degrades instead of disabling search.
 *
 * @param config - Search configuration
 * @param bytes - Marz binary index
 *
 * @returns Promise resolving with the loaded index
 */
async function setupSearchIndex(
  config: SearchConfig, bytes: Uint8Array
): Promise<MarzIndex> {
  const response = await fetch(`${assetBase()}/marz/marz_wasm_bg.wasm`)
  if (!response.ok)
    throw new Error(
      `could not fetch Marz runtime: ${response.status} ${response.statusText}`
    )

  /* Initialize WebAssembly from explicit bytes — bundlers rewrite asset
     paths, so the default resolution next to the glue code can't be trusted */
  await initialize(new Uint8Array(await response.arrayBuffer()))

  /* Load the prebuilt index */
  const expected = config.lang.join(",")
  try {
    return MarzIndex.load(bytes, expected)
  } catch (err) {
    console.warn(
      `Marz index language mismatch (expected ${expected}), ` +
        "loading without assertion"
    )
    console.warn(err)
    return MarzIndex.load(bytes)
  }
}

/* ----------------------------------------------------------------------------
 * Functions
 * ------------------------------------------------------------------------- */

/**
 * Message handler
 *
 * @param message - Source message
 *
 * @returns Target message
 */
export async function handler(
  message: SearchMessage
): Promise<SearchMessage> {
  switch (message.type) {

    /* Search setup message */
    case SearchMessageType.SETUP:
      index = new Search(
        message.data,
        await setupSearchIndex(message.data.config, message.data.marz)
      )
      return {
        type: SearchMessageType.READY
      }

    /* Search query message */
    case SearchMessageType.QUERY:
      const query = message.data
      try {
        return {
          type: SearchMessageType.RESULT,
          data: index.search(query)
        }

      /* Return empty result in case of error */
      } catch (err) {
        console.warn(`Invalid query: ${query}`)
        console.warn(err)
        return {
          type: SearchMessageType.RESULT,
          data: { items: [] }
        }
      }

    /* All other messages */
    default:
      throw new TypeError("Invalid message type")
  }
}

/* ----------------------------------------------------------------------------
 * Worker
 * ------------------------------------------------------------------------- */

/* Handle messages */
addEventListener("message", async ev => {
  postMessage(await handler(ev.data))
})
