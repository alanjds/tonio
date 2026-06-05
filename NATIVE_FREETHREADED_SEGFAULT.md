# Intermittent native segfault on free-threaded Python 3.14t

> Analysis written to seed a fresh investigation session. The bug is in the
> **native Rust runtime**, not in the asyncio/Windows backend. It is unrelated
> to the `claude/windows-support-testing-JMTJD` PR — that PR only surfaced it
> via CI re-runs.

## TL;DR

The `linux (3.14t)` and `macos (3.14t)` CI jobs intermittently **segfault**
inside CPython's context machinery (`PyContext_CopyCurrent`) while running the
native Rust backend on **free-threaded** (no-GIL) Python 3.14t. The root cause
is almost certainly **unsynchronized cross-thread sharing and direct re-entry of
`contextvars.Context` objects** in the Rust runtime. Under the GIL (3.13) the
races are serialized away; under free-threading they corrupt interpreter/heap
state and crash.

It is **not a regression** from the Windows/asyncio work — see "Evidence" below.

## Symptoms

Two observed crash signatures, both `Fatal Python error: Segmentation fault`
with `<Cannot show all threads while the GIL is disabled>`:

### Run A — linux, commit `9d99625` (this PR)
```
File "tests/test_context.py", line 40 in _step      # test_contextvar_blocking
...
_tonio...so  (offsets only)
make: *** [Makefile:56: test] Segmentation fault (core dumped)
```

### Run B — macOS, commit `171ccc97` (investigation branch, NONE of this PR's changes)
```
Stack (most recent call first):
  File "tonio/_ctl.py", line 72 in without_tracking
  File "tonio/_ctl.py", line 132 in block_on
  File "tests/test_blocking.py", line 71 in _blocking   # test_block_on

Current thread's C stack trace (most recent call first):
  ...PyContext_CopyCurrent+0x20
  _tonio::runtime::Runtime::_spawn_pygen
  _tonio::runtime::Runtime::__pymethod__spawn_pygen__
  ...pyo3 trampoline...
  _PyFunction_Vectorcall
  _tonio::blocking::BlockingTask::run
  _tonio::blocking::blocking_worker        <-- Rust blocking-threadpool worker thread
  ...std::thread::spawn_unchecked -> thread_start
```

The crash is always **inside CPython's context code, on a Rust blocking-pool
worker thread**, never in our Python changes.

## Why it's intermittent and pre-existing (evidence)

- Same investigation branch: **passed** native at `8815de93`, **segfaulted** at
  `171ccc97` — identical native code, different outcome → nondeterministic.
- Different failing test per run: `test_contextvar_blocking` (Run A) vs
  `test_block_on` (Run B) — timing-dependent, hallmark of a data race.
- The crash reproduced on the investigation branch which contains **none** of
  the Windows/asyncio PR changes.
- Every shared file the PR touched is inert on the native path (env-gated, or
  `_spawn_pygen` returns `None` on native), so it cannot be the cause.

## Reproduction notes

- **Cannot reproduce on this dev box**: the local interpreter is CPython
  **3.13.12 (with GIL)**. The race requires the **free-threaded 3.14t** build.
- To reproduce:
  ```bash
  uv python install 3.14t
  uv venv .venv && uv sync --group build --group test
  uv run --no-sync maturin develop --uv          # build native _tonio ext
  # loop until it crashes (intermittent):
  for i in $(seq 1 200); do make test || { echo "CRASHED on run $i"; break; }; done
  ```
- Likely amplified by load: `test_contextvar_blocking` runs
  `map_blocking(_step, range(50))` → 50 `spawn_blocking` tasks over a worker
  pool (conftest: `blocking_threadpool_size=8`), each mutating one ContextVar;
  `test_block_on` nests a `block_on` (which calls `_spawn_pygen`) inside a
  blocking task. Both maximize concurrent context operations across threads.

## Root-cause hypothesis (primary)

tonio shares `contextvars.Context` objects **across threads** and re-enters them
**directly**, which is unsafe. Key code:

1. **Capture on the event-loop thread, enter on a worker thread**
   `src/runtime.rs:563` `_spawn_blocking` captures the context on the *caller's*
   thread:
   ```rust
   let ctx = unsafe { PyContext_CopyCurrent() };          // event-loop thread
   let (task, ...) = BlockingTask::new(py, f, args, kwargs, ctx);
   self.blocking_pool.run(task);                          // ctx MOVED to a worker thread
   ```
   `src/blocking.rs:62` `BlockingTask::run` then enters that moved context on a
   **different (worker) thread**, with no copy:
   ```rust
   if let Some(ctx) = ctx { PyContext_Enter(ctx); }       // worker thread
   PyObject_Call(callable, args, ...);                    // re-enters runtime -> _spawn_pygen
   if let Some(ctx) = ctx { PyContext_Exit(ctx); }
   ```

2. **Stored context re-entered every tick, no copy**
   `src/runtime.rs:527` `_spawn_pygen` captures `PyContext_CopyCurrent()` into a
   `PyGenCtxHandle`. `src/handles.rs:139` `PyGenCtxHandle::call` then does, on
   every scheduler tick:
   ```rust
   let ctx = self.ctx.as_ptr();
   PyContext_Enter(ctx);                                  // SAME stored ctx, no copy
   PyIter_Send(self.coro.as_ptr(), ...);
   PyContext_Exit(ctx);
   ```
   and reschedules itself reusing `self.ctx` (lines 153/168/181).

3. **The authors already know direct entry is unsafe.** The *Thrower* paths copy
   first — `src/handles.rs:417` and `:482`:
   ```rust
   //: copy context to avoid threadstate issues
   let cctx = pyo3::ffi::PyContext_Copy(ctx);
   PyContext_Enter(cctx); ... PyContext_Exit(cctx);
   ```
   The `_spawn_blocking` / `BlockingTask::run` and `PyGenCtxHandle::call` /
   `PyAsyncGenCtxHandle` paths **do not** do this — they enter the shared/stored
   context directly. That asymmetry is the prime suspect.

### Why no-GIL makes it crash
A `contextvars.Context` is tied to the thread/thread-state that entered it and
is not safe to enter concurrently or from multiple threads. `PyContext_Enter`
manipulates the current thread state's context stack and the context's
`entered`/`prev` linkage; `PyContext_Copy`/`CopyCurrent` read the source
context's immutable HAMT (with concurrent refcounting). With the GIL these
operations interleave atomically and the bug is hidden. Free-threaded 3.14t runs
worker threads and the event loop truly in parallel, so concurrent
Enter/Exit/Copy/CopyCurrent on shared `Context` objects (and refcount churn via
`clone_ref` / raw `into_ptr` / `from_owned_ptr`) corrupt state. The fault
surfaces at the next `PyContext_CopyCurrent` because that's where the poisoned
structure is touched — the crash site is a symptom, not the origin.

## Secondary hypothesis

Refcount / object-ownership races on `Py<PyAny>` values transferred between the
event-loop thread and worker threads (`self.ctx.clone_ref(py)`,
`target.into_ptr()`, `args.into_ptr()`, `Bound::from_owned_ptr(...)`). Audit
every place a `Py*` is created on one thread and dropped/cloned on another.

## Fast confirmation experiment

The runtime has a `use_pyctx` flag (`context=True/False`). `tests/conftest.py`
builds the runtime with `context=True`, which routes through the
`*CtxHandle` / context-entering paths above. If you build a runtime with
`context=False` (routes to `PyGenHandle` / `BlockingTask` with `ctx=None`, no
`PyContext_*` calls) and the segfault **disappears** under the repro loop, the
context machinery is confirmed as the root cause.

## Suggested fix directions (to validate, not prescriptive)

1. **Never enter a `Context` captured on another thread.** Either:
   - copy the context immediately before entering, *on the executing thread*
     (mirror the Thrower paths) in `BlockingTask::run`,
     `PyGenCtxHandle::call`, and `PyAsyncGenCtxHandle` — and verify the source
     context isn't being mutated concurrently while copied; or
   - snapshot the needed ContextVar values and build a fresh `Context` per
     worker/handle so no `Context` object is ever shared between threads.
2. Ensure each scheduler re-entry that reuses `self.ctx` uses a per-tick copy or
   guarantees single-thread ownership of that handle.
3. Re-audit cross-thread `Py*` ownership transfers for refcount safety under
   free-threading.
4. Add a stress test (`map_blocking` + nested `block_on` over a ContextVar) run
   many iterations in CI on 3.14t to catch regressions.

## Key references

- `src/runtime.rs:527` `_spawn_pygen`, `:539` `_spawn_pyasyncgen`,
  `:551` `_spawn_blocking` (PyContext_CopyCurrent capture sites)
- `src/blocking.rs:62` `BlockingTask::run` (PyContext_Enter on worker thread),
  `:147` `blocking_worker`
- `src/handles.rs:139` `PyGenCtxHandle::call`, `:320` `PyAsyncGenCtxHandle`,
  `:417`/`:482` Thrower paths (the "copy to avoid threadstate issues" pattern)
- `tonio/_ctl.py:69` `without_tracking`, `:119` `block_on`,
  `:105` `spawn_blocking`, `:144` `map_blocking`
- `tests/conftest.py` (runtime built with `context=True`)
- Failing tests: `tests/test_context.py::test_contextvar_blocking`,
  `tests/test_blocking.py::test_block_on`
- CI runs: linux `9d99625` (run 27013581170), macOS `171ccc97`
  (run 26905292403, job 79368416518)
