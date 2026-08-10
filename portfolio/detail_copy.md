# Detail-page copy drafts

First-person, David's voice. Honesty-calibrated (none are shipping products; trunk'd + Vega-Bray are demoable; sdrlight is deliberately framed as in-progress). Trim to taste.

---

## trunk'd  ·  Live demo
**Public-safety radio, made legible — RF to browser in under a second.**

Trunked P25 radio — the kind fire, EMS, and police run — is incomprehensible at volume: dozens of simultaneous talkgroups, no thread, no context. trunk'd captures that traffic from software-defined radios, transcodes and transcribes each transmission as it arrives with a local Whisper-compatible engine, and serves a live, geofenced incident board to any browser. From SDR hardware to the WebSocket frame that updates your screen stays comfortably under one second.

The pipeline is event-sourced on NATS JetStream with three durable streams — raw PCM (a ~48h crash buffer), Opus audio (a ~30d DVR window), and a permanent metadata log that's the source of truth. Each feeds a small, single-responsibility Go service: **ingest** (speaks trunk-recorder's protocol, mints deterministic ULIDs, runs active/active with a lease-gated reconciler), **transcoder** (per-packet Opus, the only encode in the system), **transcriber** (streaming STT with cloud fallback), **archiver** (muxes to GCS without re-encoding), **index** (a SQLite/FTS5 projection serving REST search), and **player** (a WebSocket server; the browser owns the playlist). The Svelte console adds a unified query grammar, karaoke-highlighted transcripts, an AI-summarized incident board, and a live latency badge. The `cmd/` tree runs to 25 Go binaries.

Live and demoable (OIDC-gated; ask for access), capturing DC-area P25 traffic continuously.

**Keywords:** Go · NATS JetStream · event sourcing · Kubernetes · SDR · P25 · WebSocket · SQLite/FTS5 · Whisper STT · GCS · Svelte · OpenTelemetry · Prometheus

---

## Vega-Bray Observatory  ·  Live demo
**Reverse-engineering a 20-inch telescope mount that hadn't moved in 15 years.**

The 20-inch Maksutov at Vega-Bray had been dark for roughly 15 years. The original control electronics were gone or obsolete — no docs, no protocol spec, no reference hardware. What remained: a heavy German equatorial mount, two worm-gear axes, IM483 stepper drivers. I treated it as a reverse-engineering problem.

**Drivetrain first.** I reconstructed gear ratios by photographing gear trains, counting teeth, and cross-checking against live motion. RA is 2,880:1, DEC 2,700:1 (the DEC 2-start worm is still an open verification item — I'm honest about it in the docs). Both axes run µ4 microstepping: 6,400 and 6,000 steps/degree.

**ESP32 firmware** — portable C++17 core. Step generation lives in LEDC PWM silicon so WiFi and serial can't jitter the pulse train. The mount speaks a documented LX200 dialect (Meade's 1990s protocol, reverse-engineered and verified against Stellarium's actual wire behavior), extended with a vendor command family. Disconnect the Linux box and it still knows time, site, and pointing; the hand controller is hardwired and never gateable by software.

**Go pointing service (`telescoped`)** — sole owner of the serial link, with a "poisoned conversation" resync model (one dropped exchange can corrupt every later read), a conductor/queue layer, a JSON+SSE API, and a Stellarium listener. **Meridian**, the web UI, is night-safe with a day-to-red theme slider, a LINK→REFERENCED→SYNCED readiness ladder, and an omnibox command line. `make sim` runs the whole stack against a simulated mount — no hardware needed.

Demoable now in simulation. The real hardware slews and tracks but needs supervision — no collision avoidance yet, and the dome is still hand-cranked.

**Keywords:** ESP32 · Go · C++17 · embedded · reverse engineering · LX200 · stepper control · LEDC PWM · serial protocol · React · pointing model

---

## sdrlight  ·  Details  (in-progress — vision framing)
**Scheduling commodity radios like compute.**

I've spent a lot of time thinking about what it would mean to treat a shelf of cheap USB software-defined radios the way Kubernetes treats compute: a pool of fungible, schedulable resources with well-defined claims against them.

sdrlight is that idea, still mostly on paper. The architecture I'm building treats physical SDRs as cluster devices allocated through Kubernetes DRA, then virtualizes them upward — a workload asks for "20 MHz somewhere around 2.4 GHz" via a `RadioClaim`, not for a specific dongle on a specific node. The system decides which captures satisfy the request, whether two consumers can share a wideband capture, and how to hand a claim to a different radio without the consumer noticing.

The zero-copy angle is the part I most want to get right. IQ data is high-rate and latency-sensitive; a naively copied path burns CPU and adds jitter. The design routes samples through a shared-memory pool of immutable loans — read-only handles into the same allocation, where a slow consumer can't stall the writer. Whether that's achievable without privilege escalation inside an unprivileged pod is the hard part the implementation still has to prove.

Some behaviors work in a pre-Streamplane prototype. Most of the architecture is at the interface-scaffolding stage. Honest status: this is where I'm building toward, not where it is.

**Keywords:** SDR · Kubernetes DRA · zero-copy shared memory · mesh/federation · RTL-SDR · Go · signal processing · unprivileged workloads

---

## Luna  ·  Details  (mostly a photo gallery)
**A 1-meter lunar relief.**

Luna is a 1-meter lunar relief sculpture I made mostly to see if I could.

The starting point was gigabytes of NASA elevation data — SLDEM-2015 lunar topography, delivered as high-bit-depth GeoTIFFs. I wrote a Python pipeline to ingest it, sample and rescale the heightfield, and emit tiled OBJ meshes sized to a printer bed. Getting the tiling and seam math right took longer than I expected; the pipeline also handles smoothing and depth-scaling so the relief reads at viewing distance without exaggerating the Moon's already-subtle topography.

From there: printed in PETG on a hardboard backing, assembled, mounted. PETG holds fine detail without the warping PLA can show on larger prints; the hardboard gave a rigid, light substrate.

The last layer is projection mapping. Using MadMapper, I drive animated lunar imagery — craters lit at oblique angles, terminator lines crawling across the surface — directly onto the physical relief, where the real contours interact with projected light in a way a flat screen can't. That part is genuinely fun to show people.

**Keywords:** NASA elevation data · SLDEM-2015 · mesh generation · PETG · 3D printing · projection mapping · MadMapper

---

## Mainframe separation  ·  Details  (OPM)
When DCSA began separating from OPM into DoD, it exposed a structural problem we'd lived around for years: OPM and DCSA shared a single mainframe environment — two chassis side-by-side in one basement data center. One room, one site, no redundancy. When DCSA left they'd take their subsidy with them, and we needed to stand on our own regardless.

I led the split. We procured four new, appropriately sized mainframes — two for DCSA, two for OPM — and put the second of each pair in a *separate* data center. It was the first time OPM's mainframe footprint had any geographic redundancy at all.

About two weeks after go-live, a water line in the ceiling of the old basement data center burst — the kind of incident that would have taken the whole thing down under the old architecture. Under the new one it was a cleanup problem, not a mission-impact problem. I'll take that as validation.

The quieter challenge was organizational: on-prem staff now had to maintain infrastructure they weren't physically next to. Mainframe teams are used to hands-on access, and shifting that culture — building confidence in remote operations — took deliberate attention alongside the technical work.

**Keywords:** mainframe migration · redundancy · disaster recovery · data-center strategy · DCSA/OPM separation · single-point-of-failure · remote operations

---

## Virtual call center  ·  Details  (OPM)
OPM's Retirement Services call center was a pressure point. Volume was high, the software was aging and unreliable, and the underlying problem was simple: people were calling to do things the website should have let them do. The technology wasn't the root cause — the product experience was.

I led a UX and product review of the service-center site, identified the task categories driving call volume, and we rebuilt those flows so retirees could actually complete them online — instrumented, because if you can't measure adoption you can't make the case for it.

The harder fight was organizational: a settled belief that modernizing the call center was a multi-year undertaking, and a reflexive distrust of cloud. So I made a different argument. On the drive back from one of those meetings I built a fully functional Twilio prototype of the call center — the complete phone menu tree, mission-capable — in about three hours. Not a demo with asterisks; something that worked the way a production system would.

The prototype didn't fix anything on its own. But it made the "multi-year" estimate hard to defend with a straight face. The barrier wasn't technical, and now that was concrete.

**Keywords:** Twilio · IVR · call-center modernization · UX research · product sprint · cloud telephony · self-service · analytics

---

## Auto-fixer for vulnerabilities  ·  Details  (USDS)
A government agency I was working with had a large legacy codebase in ASP Classic. A security review surfaced thousands of vulnerabilities across it — XSS, SQL injection, and related classes — and a contractor estimated six to nine months to remediate them by hand.

That timeline didn't sit right. The fixes were mechanical: find where user data entered the system, trace how it flowed, and inject the right sanitization at each unsafe use. Mechanical work is what computers are for.

So I built the tool. First a parser for ASP Classic — not a full implementation, but enough to produce a faithful AST for the patterns that mattered. Then a taint-analysis pass tracking data from its sources (form inputs, query strings, cookies) through assignments and calls to every unsafe sink. Then automated remediation: for each flagged site, rewrite the AST to inject the correct escaping or parameterization and serialize back to source. It's essentially a small compiler pipeline — parse, IR, dataflow analysis, codegen — pointed at a security problem instead of a performance one.

The result: weeks instead of months, applied consistently across the whole codebase with no hand-editing fatigue or missed cases.

**Keywords:** static analysis · AST · taint analysis · dataflow · automated remediation · ASP Classic · compiler techniques · security engineering

---

## College Scorecard  ·  Details  (USDS / Dept. of Education)
The Obama administration wanted to give students and families an honest way to compare colleges — not by prestige, but by real economic outcomes: what a degree from a given school was actually worth a decade later.

Getting the data was the hard part. Working with the Treasury Department, the team accessed anonymized tax-return records tied to federal student-loan borrowers — one of the largest datasets ever used to evaluate higher-education outcomes — and computed projected ten-year earnings by institution and field of study, a financial signal that had never existed in public form.

My contribution was early-stage: UX research, design, and the initial prototype of both the consumer application and the underlying data pipeline. That meant talking to prospective students and families about the questions they were actually trying to answer, turning those into interface concepts, and building rough working prototypes to stress-test the data model before the full build. Others carried it forward — the production site and final API were built and shipped by a larger team.

The deliverable was an open-data release plus a reference application. That site — collegescorecard.ed.gov — launched in 2015 and is still live.

**Keywords:** open data · UX research · data pipeline · higher-ed outcomes · human-centered design · U.S. Digital Service

---

## No subpage
**Expert Witness, Electronic Frontier Foundation** — tile links straight to the Federal News Network article. Framed as the EFF's Privacy Act suit over the DOGE move into OPM systems.
