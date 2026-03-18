# MacOS kalloc memory leak

## 2026-03-18

I sometimes engage in what I will euphemistically call "abuse" of my Macbook.
In this case, I had about a dozen Ghostty tabs open with a `watch` command running
an expensive pipeline of shell, Python, and Go, all while running periodic Docker builds and
vibe-coded Python integration tests.

And every few days, I wondered why my Macbook would [crash](panic.txt).

```text
panic(cpu 2 caller 0xfffffe00288c9d54): zalloc[3]: zone map exhausted while allocating from zone [data_shared.kalloc.1024], likely due to memory leak in zone [data_shared.kalloc.1024] (20G, 21157968 elements allocated) @zalloc.c:4534
```

This same panic happened every week or so and seemed to correlate
with how much abuse I was engaging in.  So I eventually decided to
figure it out.  I found the `zprint` command, which let me see the
state of the kernel's zone allocator, and watched as the number of
`inuse` pages slowly climbed. A little math told me it would reach
20G in a few days.

1. I then one by one stopped the various things I was doing until I found that a Python script running repeatedly in my `watch` was the culprit.
2. But it wasn't just my script, it was *any* Python script.
3. Actually, no, it was happening with `python --version` too
4. Actually, it was any invocation of `pyenv`, since that's what my `python` was pointing to.
5. Actually, it was `pyenv` doing an `exec` on something else.
6. Actually, it was any shell script doing an `exec` on something else.
7. Actually, it was anything doing an `exec` on a shell script.

And, at last, I could reproduce the problem with:

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

Invoke that with 20000000 and you'll have a kernel panic in a few minutes.
