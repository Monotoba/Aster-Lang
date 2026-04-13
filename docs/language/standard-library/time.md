# `time` — Timestamps and Timing

```aster
use time
use time: now, sleep, monotonic
```

The `time` module provides access to wall-clock time, monotonic time for measuring
intervals, and simple sleep / formatting utilities.

---

## Current time

### `time.now() -> Float`
Current Unix timestamp — seconds since 1970-01-01 00:00:00 UTC, as a Float.

```aster
t := time.now()   # e.g. 1713000000.123456
```

### `time.now_ms() -> Int`
Current time in integer milliseconds since the Unix epoch.
Useful when you need an integer timestamp.

```aster
ms := time.now_ms()   # e.g. 1713000000123
```

---

## Monotonic clock

### `time.monotonic() -> Float`
A monotonically increasing clock value in seconds. The absolute value is meaningless;
use differences to measure elapsed time. Not affected by system clock adjustments.

```aster
start := time.monotonic()
# ... work ...
elapsed := time.monotonic() - start
print("elapsed: " + str(elapsed) + "s")
```

### `time.clock() -> Float`
CPU process time in seconds (user + system). Useful for benchmarking CPU-bound code,
as it excludes time spent sleeping.

---

## Sleeping

### `time.sleep(seconds) -> Nil`
Pause execution for the given number of seconds. Accepts a Float for sub-second precision.

```aster
time.sleep(0.5)   # sleep 500 milliseconds
time.sleep(1)     # sleep 1 second
```

---

## Formatting

### `time.strftime(fmt: String) -> String`
Format the current local time using a `strftime`-style format string.

Common format codes:

| Code | Meaning | Example |
|------|---------|---------|
| `%Y` | 4-digit year | `2026` |
| `%m` | Month (01–12) | `04` |
| `%d` | Day (01–31) | `13` |
| `%H` | Hour 24h (00–23) | `15` |
| `%M` | Minute (00–59) | `04` |
| `%S` | Second (00–59) | `05` |
| `%A` | Full weekday name | `Sunday` |
| `%B` | Full month name | `April` |

```aster
date := time.strftime("%Y-%m-%d")       # → "2026-04-13"
stamp := time.strftime("%Y-%m-%d %H:%M:%S")
```

---

## Example — benchmark a function

```aster
use time
use list

fn main():
    start := time.monotonic()

    mut total := 0
    nums := list.range(1000000)
    mut i := 0
    while i < len(nums):
        total <- total + nums[i]
        i <- i + 1

    elapsed := time.monotonic() - start
    print("sum: " + str(total))
    print("time: " + str(elapsed) + "s")
```
