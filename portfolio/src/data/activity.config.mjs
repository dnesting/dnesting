// Which GitHub activity appears in the "Recent GitHub contributions" section.
//
// Contributions to repos owned by anyone else are grouped per organization and
// need no configuration. Repos under OWNER are opt-in: only the groups listed
// in OWN_GROUPS appear, one bullet each. Commits pushed to a fork of an
// upstream repo count toward the upstream organization, not the fork's owner,
// so work done on a fork stays attached to the project it was for.
//
// Privacy comes from the API and is never set here. A group holding any private
// repo is labelled "private" and rendered without links; only its counts are
// published, never repo names it doesn't already carry in `label`.

export const OWNER = 'dnesting';

// How far back a contribution still counts as "recent".
export const WINDOW_DAYS = 30;

// Bullets to render, most recently active first. Groups with no activity in the
// window are dropped before this limit applies.
export const MAX_BULLETS = 6;

export const OWN_GROUPS = [
  { label: "trunk'd", repos: ['trunkd', 'trunkd-archiver', 'trproxy'] },
  { label: 'sense-exporter', repos: ['sense-exporter'] },
  { label: 'ui-dissector', repos: ['ui-dissector'] },
  { label: 'sense', repos: ['sense'] },
];
