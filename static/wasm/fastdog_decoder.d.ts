/* tslint:disable */
/* eslint-disable */
export function init(): void;
export function decode_fastdog_binary(data: Uint8Array): any;
export function decode_fastdog_binary_zero_copy(data: Uint8Array): any;
export function decode_fastdog_to_binary(data: Uint8Array): Uint8Array;
export function get_decode_stats(data: Uint8Array): any;
export function validate_fastdog_format(data: Uint8Array): boolean;
export function get_format_info(data: Uint8Array): any;
export function benchmark_decode(data: Uint8Array, iterations: number): any;
export class StreamDecoder {
  free(): void;
  constructor();
  add_chunk(chunk: Uint8Array): any;
  reset(): void;
  get_progress(): number;
  get_buffer_size(): number;
  get_expected_size(): number | undefined;
}

export type InitInput = RequestInfo | URL | Response | BufferSource | WebAssembly.Module;

export interface InitOutput {
  readonly memory: WebAssembly.Memory;
  readonly init: () => void;
  readonly decode_fastdog_binary: (a: number, b: number) => any;
  readonly decode_fastdog_binary_zero_copy: (a: number, b: number) => any;
  readonly decode_fastdog_to_binary: (a: number, b: number) => [number, number];
  readonly get_decode_stats: (a: number, b: number) => any;
  readonly validate_fastdog_format: (a: number, b: number) => number;
  readonly get_format_info: (a: number, b: number) => any;
  readonly benchmark_decode: (a: number, b: number, c: number) => any;
  readonly __wbg_streamdecoder_free: (a: number, b: number) => void;
  readonly streamdecoder_new: () => number;
  readonly streamdecoder_add_chunk: (a: number, b: number, c: number) => any;
  readonly streamdecoder_reset: (a: number) => void;
  readonly streamdecoder_get_progress: (a: number) => number;
  readonly streamdecoder_get_buffer_size: (a: number) => number;
  readonly streamdecoder_get_expected_size: (a: number) => number;
  readonly __wbindgen_free: (a: number, b: number, c: number) => void;
  readonly __wbindgen_malloc: (a: number, b: number) => number;
  readonly __wbindgen_realloc: (a: number, b: number, c: number, d: number) => number;
  readonly __wbindgen_export_3: WebAssembly.Table;
  readonly __wbindgen_start: () => void;
}

export type SyncInitInput = BufferSource | WebAssembly.Module;
/**
* Instantiates the given `module`, which can either be bytes or
* a precompiled `WebAssembly.Module`.
*
* @param {{ module: SyncInitInput }} module - Passing `SyncInitInput` directly is deprecated.
*
* @returns {InitOutput}
*/
export function initSync(module: { module: SyncInitInput } | SyncInitInput): InitOutput;

/**
* If `module_or_path` is {RequestInfo} or {URL}, makes a request and
* for everything else, calls `WebAssembly.instantiate` directly.
*
* @param {{ module_or_path: InitInput | Promise<InitInput> }} module_or_path - Passing `InitInput` directly is deprecated.
*
* @returns {Promise<InitOutput>}
*/
export default function __wbg_init (module_or_path?: { module_or_path: InitInput | Promise<InitInput> } | InitInput | Promise<InitInput>): Promise<InitOutput>;
