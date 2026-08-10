// Top-of-page copy: the hero and the capabilities chip list.
// `kicker`, `headline`, and `blurb` are RAW HTML emitted via `set:html` in
// Hero.astro so the exact inline markup (the `<span class="a">`, `<br>`, and
// `<b>`) and straight apostrophes are preserved byte-for-byte. A non-technical
// editor edits the text between the tags here.
export const site = {
  hero: {
    kicker: "Hey, I'm David.",
    headline: 'I <span class="a">void<br>warranties.</span>',
    blurb:
      'Engineer and leader drawn to complex systems with a bias toward <b>adversarial thinking, incident response, resiliency, reliability, security, and privacy</b>. Google SRE, Deputy CIO of a 700-person org, and built both AI programs and platforms. Nights and weekends find me with a soldering iron, a software-defined radio, and blowing through AI usage limits.'
  },
  // The scannable "toolkit" chips under the pitch.
  capabilities: ['Go', 'Python', 'Kubernetes', 'AI', 'SDR', 'Hardware', 'Policy', 'TS/SCI'],
};
