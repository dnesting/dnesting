#!/usr/bin/env node
// Regenerates src/data/activity.json, which the homepage renders as
// "Recent GitHub contributions". Run before `astro build`:
//
//   GITHUB_TOKEN=<token> node scripts/fetch-activity.mjs
//
// The token needs read access to the private repos named in activity.config.mjs
// (a fine-grained PAT with Contents: read + Metadata: read is enough). Without a
// token the script leaves the committed JSON alone, so builds still work.

import { writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { MAX_BULLETS, OWN_GROUPS, OWNER, WINDOW_DAYS } from '../src/data/activity.config.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(here, '../src/data/activity.json');

// Commits are counted by walking branches, because work on a fork lives on a
// feature branch and never reaches the default branch. These bound that walk.
const HISTORY_PAGE = 100;
const MAX_BRANCHES = 15;
const MAX_PAGES_PER_BRANCH = 6;

const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
if (!token) {
  console.warn('fetch-activity: no GITHUB_TOKEN set — keeping the committed activity.json');
  process.exit(0);
}

const now = new Date();
const since = new Date(now.getTime() - WINDOW_DAYS * 86400000).toISOString().replace(/\.\d+Z$/, 'Z');
const warnings = [];

async function gql(query, variables = {}, { tolerant = false } = {}) {
  const res = await fetch('https://api.github.com/graphql', {
    method: 'POST',
    headers: {
      authorization: `bearer ${token}`,
      'content-type': 'application/json',
      'user-agent': 'dnesting.com-activity',
    },
    body: JSON.stringify({ query, variables }),
  });
  if (!res.ok) throw new Error(`GitHub API ${res.status} ${res.statusText}`);
  const body = await res.json();
  if (body.errors) {
    const msg = body.errors.map((e) => e.message).join('; ');
    // A renamed repo or a revoked grant shouldn't fail the whole build.
    if (!tolerant) throw new Error(msg);
    warnings.push(msg);
  }
  return body.data;
}

const { viewer } = await gql('{ viewer { id login } }');

// Commits authored by the viewer across every branch, deduplicated by OID so a
// commit reachable from both master and a feature branch is counted once.
async function repoCommits(owner, name) {
  const meta = await gql(
    `query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        nameWithOwner isPrivate url
        refs(refPrefix: "refs/heads/", first: ${MAX_BRANCHES},
             orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) { nodes { name } }
      }
    }`,
    { owner, name },
    { tolerant: true }
  );

  const repo = meta?.repository;
  if (!repo) return null;

  const oids = new Set();
  let lastAt = null;

  for (const ref of repo.refs.nodes) {
    let after = null;
    for (let page = 0; page < MAX_PAGES_PER_BRANCH; page++) {
      const data = await gql(
        `query($owner: String!, $name: String!, $ref: String!, $since: GitTimestamp!, $author: ID!, $after: String) {
          repository(owner: $owner, name: $name) {
            ref(qualifiedName: $ref) {
              target { ... on Commit {
                history(first: ${HISTORY_PAGE}, since: $since, author: {id: $author}, after: $after) {
                  pageInfo { hasNextPage endCursor }
                  nodes { oid committedDate }
                } } }
            }
          }
        }`,
        { owner, name, ref: ref.name, since, author: viewer.id, after },
        { tolerant: true }
      );

      const history = data?.repository?.ref?.target?.history;
      if (!history) break;
      for (const c of history.nodes) {
        oids.add(c.oid);
        if (!lastAt || c.committedDate > lastAt) lastAt = c.committedDate;
      }
      if (!history.pageInfo.hasNextPage) {
        after = null;
        break;
      }
      after = history.pageInfo.endCursor;
    }
    if (after) warnings.push(`${repo.nameWithOwner}#${ref.name}: commit count truncated`);
  }

  return { repo, commits: oids.size, lastAt };
}

const groups = new Map();
function bucket(key, init) {
  if (!groups.has(key)) {
    groups.set(key, { commits: 0, prs: 0, issues: 0, reviews: 0, lastAt: null, ...init });
  }
  return groups.get(key);
}
function touch(group, at) {
  if (at && (!group.lastAt || at > group.lastAt)) group.lastAt = at;
}

// A fork's commits belong to the upstream org, not to OWNER.
const orgOf = (repo) =>
  repo.owner.login === OWNER && repo.isFork && repo.parent ? repo.parent.owner.login : repo.owner.login;

function orgBucket(org) {
  // No label link: an org's landing page says nothing about the contribution.
  // The per-count links below carry the reader to the actual work.
  return bucket(`org:${org}`, { label: org, kind: 'org', private: false, url: null });
}

const REPO_FIELDS = 'nameWithOwner isPrivate isFork owner { login } parent { owner { login } }';

const cc = (
  await gql(
    `query($from: DateTime!) {
      viewer {
        contributionsCollection(from: $from) {
          restrictedContributionsCount
          commitContributionsByRepository(maxRepositories: 100) {
            repository { ${REPO_FIELDS} }
            contributions(first: 1, orderBy: {field: OCCURRED_AT, direction: DESC}) {
              totalCount
              nodes { occurredAt }
            }
          }
          pullRequestContributions(first: 100) {
            nodes { occurredAt pullRequest { repository { ${REPO_FIELDS} } } }
          }
          issueContributions(first: 100) {
            nodes { occurredAt issue { repository { ${REPO_FIELDS} } } }
          }
          pullRequestReviewContributions(first: 100) {
            nodes { occurredAt pullRequest { repository { ${REPO_FIELDS} } } }
          }
        }
      }
    }`,
    { from: since }
  )
).viewer.contributionsCollection;

// GitHub's own per-repo commit counts. These include commits on branches that
// were merged and then deleted, which a branch walk can no longer reach — so
// they win wherever they exist. Private repos and forks never appear here.
const counted = new Map();
for (const r of cc.commitContributionsByRepository) {
  counted.set(r.repository.nameWithOwner, {
    commits: r.contributions.totalCount,
    lastAt: r.contributions.nodes[0]?.occurredAt ?? null,
  });
}

// OWNER's own repos: only the configured groups, one bullet each. Built before
// the collection is walked so pull requests and issues can route into them.
const ownRepos = new Map();
for (const [i, spec] of OWN_GROUPS.entries()) {
  const repos = [];
  for (const name of spec.repos) {
    const walked = await repoCommits(OWNER, name);
    if (!walked) continue;
    const github = counted.get(walked.repo.nameWithOwner);
    repos.push({
      repo: walked.repo,
      commits: github ? github.commits : walked.commits,
      lastAt: [github?.lastAt, walked.lastAt].filter(Boolean).sort().pop() ?? null,
    });
  }
  if (!repos.length) continue;

  const g = bucket(`own:${i}`, { label: spec.label, kind: 'repo', private: false });
  g.private = repos.some((r) => r.repo.isPrivate);
  g.publicRepos = repos.filter((r) => !r.repo.isPrivate).map((r) => r.repo.nameWithOwner);
  g.url = !g.private && repos.length === 1 ? repos[0].repo.url : null;

  for (const r of repos) {
    g.commits += r.commits;
    touch(g, r.lastAt);
    ownRepos.set(r.repo.nameWithOwner, g);
  }
}

function add(repo, at, field, n = 1) {
  const own = ownRepos.get(repo.nameWithOwner);
  if (own) {
    // Commits in configured repos are already counted above.
    if (field !== 'commits') {
      own[field] += n;
      touch(own, at);
    }
    return;
  }
  const org = orgOf(repo);
  if (org === OWNER) return; // unconfigured repos of OWNER's are not published
  const g = orgBucket(org);
  g[field] += n;
  touch(g, at);
}

for (const r of cc.commitContributionsByRepository) {
  add(r.repository, r.contributions.nodes[0]?.occurredAt, 'commits', r.contributions.totalCount);
}
for (const n of cc.pullRequestContributions.nodes) add(n.pullRequest.repository, n.occurredAt, 'prs');
for (const n of cc.issueContributions.nodes) add(n.issue.repository, n.occurredAt, 'issues');
for (const n of cc.pullRequestReviewContributions.nodes) {
  add(n.pullRequest.repository, n.occurredAt, 'reviews');
}

// Forks pushed inside the window: their commits are invisible to
// contributionsCollection, so walk them and credit the upstream org.
const forks = (
  await gql(
    `query {
      viewer {
        repositories(first: 100, isFork: true, affiliations: [OWNER],
                     orderBy: {field: PUSHED_AT, direction: DESC}) {
          nodes { name pushedAt isPrivate parent { nameWithOwner owner { login } } }
        }
      }
    }`
  )
).viewer.repositories.nodes.filter((r) => r.parent && r.pushedAt >= since);

// Pushing to a fork is not by itself a contribution to the upstream project —
// it becomes one when a pull request carries it there. Without that, the fork is
// private experimentation that happens to live on GitHub.
async function hasUpstreamPR(nameWithOwner) {
  const data = await gql(
    `query($q: String!) { search(query: $q, type: ISSUE, first: 1) { issueCount } }`,
    { q: `repo:${nameWithOwner} author:${viewer.login} is:pr` },
    { tolerant: true }
  );
  return (data?.search?.issueCount ?? 0) > 0;
}

for (const fork of forks) {
  if (!(await hasUpstreamPR(fork.parent.nameWithOwner))) continue;
  const result = await repoCommits(OWNER, fork.name);
  if (!result?.commits) continue;
  const g = orgBucket(fork.parent.owner.login);
  g.commits += result.commits;
  touch(g, result.lastAt);
}

// Each count links to the narrowest page that actually lists those items, scoped
// to the same window the count covers. A count with no honest destination — any
// private repo, or commits that only exist on fork branches, which GitHub's
// commit search does not index — renders as plain text.
const sinceDay = since.slice(0, 10);

function search(query, type) {
  return `https://github.com/search?q=${encodeURIComponent(query)}&type=${type}&s=updated&o=desc`;
}

function countsFor(g) {
  const scope =
    g.kind === 'org' ? `org:${g.label}` : (g.publicRepos ?? []).map((r) => `repo:${r}`).join(' ');
  const who = viewer.login;

  return [
    {
      kind: 'prs',
      n: g.prs,
      url: scope ? search(`${scope} author:${who} is:pr created:>=${sinceDay}`, 'pullrequests') : null,
    },
    {
      kind: 'issues',
      n: g.issues,
      url: scope ? search(`${scope} author:${who} is:issue created:>=${sinceDay}`, 'issues') : null,
    },
    // Reviews carry no "reviewed at" qualifier, so this link is not windowed.
    {
      kind: 'reviews',
      n: g.reviews,
      url: scope ? search(`${scope} reviewed-by:${who} is:pr`, 'pullrequests') : null,
    },
    // Commits never link. Commit search does not index the fork branches most
    // upstream work lives on, and a merged-then-deleted branch leaves commits
    // GitHub counts but no page can list.
    { kind: 'commits', n: g.commits, url: null },
  ].filter((c) => c.n > 0);
}

const active = [...groups.values()]
  .filter((g) => g.commits + g.prs + g.issues + g.reviews > 0)
  .sort((a, b) => (b.lastAt ?? '').localeCompare(a.lastAt ?? ''))
  .slice(0, MAX_BULLETS)
  .map((g) => ({
    label: g.label,
    kind: g.kind,
    private: g.private,
    url: g.url ?? null,
    lastAt: g.lastAt,
    counts: countsFor(g),
  }));

writeFileSync(
  OUT,
  `${JSON.stringify({ generatedAt: now.toISOString().replace(/\.\d+Z$/, 'Z'), windowDays: WINDOW_DAYS, groups: active }, null, 2)}\n`
);

for (const w of warnings) console.warn(`fetch-activity: ${w}`);
console.log(
  `fetch-activity: wrote ${active.length} group(s) over ${WINDOW_DAYS} days; ` +
    `${cc.restrictedContributionsCount} private contributions were not enumerable`
);
