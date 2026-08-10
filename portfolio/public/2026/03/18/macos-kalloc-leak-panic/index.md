---
title: MacOS kalloc memory leak
---

# MacOS kalloc memory leak

## 2026-03-18

I found a kernel memory leak in MacOS that's caused a dozen kernel panics for me over the past year.
But it requires some pretty significant abuse of the system to trigger: roughly 20M `exec` calls on shell scripts or Python running under `pyenv`.

The [panic](panic.txt) looks like:

```text
panic(cpu 2 caller 0xfffffe00288c9d54): zalloc[3]: zone map exhausted while allocating from zone [data_shared.kalloc.1024], likely due to memory leak in zone [data_shared.kalloc.1024] (20G, 21157968 elements allocated) @zalloc.c:4534
```

It took me the better part of a day to track down the exact behavior that was causing this:

1. Figured out how to quantify the problem: `zprint` shows you in-use allocations of the kernel's zone allocator, and `data_shared.kalloc.1024` was the one that was mentioned in the panic and I could see it was growing by O(100)/s.
2. Methodically stopped what I was doing in a dozen Ghostty terminal panes until the numbers stopped climbing.
3. The biggest contributor was ~10 `watch` invocations that were running a pipeline with a few Python scripts every few seconds.
4. Reproduced by running those scripts in a 'stress' loop
5. Then realizing `python --version` did it too
6. Then realizing it was any `pyenv` invocation
7. Then narrowing it down to any `exec` of a shell script

At last, I could reproduce the problem with:

```sh
#!/bin/bash

if [[ "$#" -eq 0 ]]; then
  echo "Watch 'cur inuse' grow:"
  zprint -L | awk 'NR<=3 || /^data_shared.kalloc.1024/'
  "$0" 1000
  zprint -L | egrep "^data_shared.kalloc.1024 "

elif [[ "$1" -gt 0 ]]; then
  exec "$0" $(( $1 - 1 ))
fi
```

```
chmod +x repro.sh
./repro.sh
```

If it produces no output, your Mac may not have the same problem.
Otherwise, invoke that with `20000000` and you'll have a kernel panic in a few minutes or hours.

And yes, the realization that I had invoked Python scripts 20M times since my last crash caused me to refactor my life a bit.
