# macOS Sandbox Profile Analysis

This directory contains a first-pass reverse-engineering pass over the SBPL
profiles shipped in `/System/Library/Sandbox/Profiles`.

The extractor intentionally does not try to evaluate Scheme forms such as
`define`, `let`, `when`, imports, or helper macros. It only parses unquoted
S-expressions as function invocations, then analyzes invocations whose head is
`allow` or `deny`:

- operation candidates from leading bare symbols;
- filter-returning functions from direct function-call arguments to `allow` and
  `deny`, excluding combinator wrappers;
- observed arity and argument types for filter-returning functions;
- combinator functions such as `require-all`, `require-any`, and `require-not`,
  with child calls still attributed to the enclosing operation;
- helper functions from nested calls inside ordinary function arguments;
- string-like helper return types from parent heads that also accept direct
  string literals;
- modifier names and arguments from `(with MODIFIER [ARG...])` forms;
- lexical variable references from common Scheme forms such as `let`, `lambda`,
  `define`, and `define-once`, which are dropped from the rule matrix;
- glob operation inheritance, where entries like `file-read-data` omit
  filter-returning functions and modifiers already present on `file*` or
  `file-read*`;
- reproducible rendering of the compact web reference through
  `templates/operation-reference.md.tmpl`;
- bare non-operation value references.

Run:

```sh
uv run --with-requirements sandbox/requirements.txt \
  python3 sandbox/scripts/extract_sb_rules.py
```

The operation-reference Markdown is rendered with Jinja2 syntax:

```sh
uv run --with-requirements sandbox/requirements.txt \
  python3 sandbox/scripts/extract_sb_rules.py \
  --operation-template sandbox/templates/operation-reference.md.tmpl
```

Generated files:

- `generated/sandbox-sbpl-reference.md`: Markdown reference for reading.
- `generated/operation-reference.md`: compact operation reference grouped by
  glob operation, listing each operation's specific filters and modifiers.
- `generated/summary.json`: compact aggregate data.
- `generated/rules.json`: extracted rule records with profile, line, source,
  operations, filters, modifiers, and ambiguous bare atoms.

Source context:

- <https://reverse.put.as/wp-content/uploads/2011/09/Apple-Sandbox-Guide-v1.0.pdf>
