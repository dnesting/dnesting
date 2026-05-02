#!/usr/bin/env python3
"""Extract allow/deny forms from macOS Sandbox profile (.sb) files.

This is intentionally a lightweight SBPL/S-expression pass, not a full Scheme
interpreter. It records rule forms wherever they occur, but only classifies
surface syntax that can be inferred from the source text.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import datetime
import json
import re
import subprocess
from pathlib import Path
from typing import Iterable, Optional, Union


PROFILE_DIR = Path("/System/Library/Sandbox/Profiles")
SANDBOX_DIR = Path(__file__).resolve().parents[0]
DEFAULT_OPERATION_TEMPLATE = SANDBOX_DIR / "operation-reference.md.tmpl"


@dataclasses.dataclass(frozen=True)
class Atom:
    value: str
    line: int


@dataclasses.dataclass(frozen=True)
class ListExpr:
    items: list["Expr"]
    line: int


Expr = Union[Atom, ListExpr]


@dataclasses.dataclass(frozen=True)
class Token:
    value: str
    line: int


@dataclasses.dataclass(frozen=True)
class RuleInstance:
    profile: Path
    rule: ListExpr
    bound_names: frozenset[str]
    bound_origins: dict[str, dict]


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch.isspace():
            i += 1
            continue
        if ch == ";":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if text.startswith("#|", i):
            i += 2
            depth = 1
            while i < n and depth:
                if text[i] == "\n":
                    line += 1
                    i += 1
                elif text.startswith("#|", i):
                    depth += 1
                    i += 2
                elif text.startswith("|#", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            continue
        if text.startswith("#;", i):
            tokens.append(Token("#;", line))
            i += 2
            continue
        if ch in "()'`":
            tokens.append(Token(ch, line))
            i += 1
            continue
        if ch == ",":
            start_line = line
            if i + 1 < n and text[i + 1] == "@":
                tokens.append(Token(",@", start_line))
                i += 2
            else:
                tokens.append(Token(",", start_line))
                i += 1
            continue
        if ch == '"' or (ch == "#" and i + 1 < n and text[i + 1] == '"'):
            start = i
            start_line = line
            if ch == "#":
                i += 1
            i += 1
            escaped = False
            while i < n:
                c = text[i]
                if c == "\n":
                    line += 1
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    i += 1
                    break
                i += 1
            tokens.append(Token(text[start:i], start_line))
            continue
        start = i
        start_line = line
        while i < n:
            c = text[i]
            if c.isspace() or c in "();'`,":
                break
            if text.startswith("#|", i) or text.startswith("#;", i):
                break
            i += 1
        tokens.append(Token(text[start:i], start_line))
    return tokens


class Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.i = 0

    def parse_all(self) -> list[Expr]:
        forms: list[Expr] = []
        while self.i < len(self.tokens):
            expr = self.parse_expr()
            if expr is not None:
                forms.append(expr)
        return forms

    def parse_expr(self) -> Optional[Expr]:
        if self.i >= len(self.tokens):
            return None
        tok = self.tokens[self.i]
        self.i += 1
        if tok.value == "#;":
            self.parse_expr()
            return None
        if tok.value in {"'", "`", ",", ",@"}:
            quoted = self.parse_expr()
            if quoted is None:
                return Atom(tok.value, tok.line)
            return ListExpr([Atom({"'": "quote", "`": "quasiquote", ",": "unquote", ",@": "unquote-splicing"}[tok.value], tok.line), quoted], tok.line)
        if tok.value == "(":
            items: list[Expr] = []
            while self.i < len(self.tokens) and self.tokens[self.i].value != ")":
                expr = self.parse_expr()
                if expr is not None:
                    items.append(expr)
            if self.i < len(self.tokens) and self.tokens[self.i].value == ")":
                self.i += 1
            return ListExpr(items, tok.line)
        if tok.value == ")":
            return Atom(tok.value, tok.line)
        return Atom(tok.value, tok.line)


def atom_value(expr: Expr) -> Optional[str]:
    return expr.value if isinstance(expr, Atom) else None


def list_head(expr: Expr) -> Optional[str]:
    if isinstance(expr, ListExpr) and expr.items:
        return atom_value(expr.items[0])
    return None


def expr_to_source(expr: Expr) -> str:
    if isinstance(expr, Atom):
        return expr.value
    return "(" + " ".join(expr_to_source(item) for item in expr.items) + ")"


def is_string_literal(value: str) -> bool:
    return value.startswith('"') or value.startswith('#"')


def atom_type(value: str, bound_names: frozenset[str]) -> str:
    if value.startswith('#"'):
        return "string"
    if value.startswith('"'):
        return "string"
    if re.fullmatch(r"-?\d+", value):
        return "integer"
    if re.fullmatch(r"#[oO][0-7]+", value):
        return "integer"
    if re.fullmatch(r"#[bB][01]+", value):
        return "integer"
    if re.fullmatch(r"#[dD]-?\d+", value):
        return "integer"
    if re.fullmatch(r"#[xX][0-9a-fA-F]+", value):
        return "integer"
    if value in bound_names:
        return "variable-reference"
    if value.startswith("#"):
        return "scheme-literal"
    return "symbol"


def argument_record(expr: Expr, bound_names: frozenset[str]) -> dict:
    if isinstance(expr, Atom):
        return {
            "source": expr.value,
            "type": atom_type(expr.value, bound_names),
        }
    head = list_head(expr) or ""
    return {
        "source": expr_to_source(expr),
        "type": "function-call",
        "function": head,
    }


def argument_records(exprs: Iterable[Expr], bound_names: frozenset[str]) -> list[dict]:
    return [argument_record(expr, bound_names) for expr in exprs]


def binding_names(bindings: Expr) -> set[str]:
    names: set[str] = set()
    if not isinstance(bindings, ListExpr):
        return names
    for binding in bindings.items:
        if isinstance(binding, ListExpr) and binding.items:
            name = atom_value(binding.items[0])
            if name and is_symbol_atom(name):
                names.add(name)
    return names


def binding_origins(bindings: Expr, form: str) -> dict[str, dict]:
    origins: dict[str, dict] = {}
    if not isinstance(bindings, ListExpr):
        return origins
    for binding in bindings.items:
        if isinstance(binding, ListExpr) and binding.items:
            name = atom_value(binding.items[0])
            if name and is_symbol_atom(name):
                origins[name] = {
                    "form": form,
                    "line": binding.line,
                    "source": expr_to_source(binding),
                }
    return origins


def parameter_names(params: Expr) -> set[str]:
    names: set[str] = set()
    if isinstance(params, Atom):
        if is_symbol_atom(params.value):
            names.add(params.value)
    elif isinstance(params, ListExpr):
        for item in params.items:
            if isinstance(item, Atom) and is_symbol_atom(item.value) and item.value != ".":
                names.add(item.value)
    return names


def parameter_origins(params: Expr, form: str, line: int) -> dict[str, dict]:
    return {
        name: {
            "form": form,
            "line": line,
            "source": name,
        }
        for name in parameter_names(params)
    }


def walk_rules(
    exprs: Iterable[Expr],
    bound_names: frozenset[str] = frozenset(),
    bound_origins: Optional[dict[str, dict]] = None,
    quoted: bool = False,
) -> Iterable[tuple[ListExpr, frozenset[str], dict[str, dict]]]:
    if bound_origins is None:
        bound_origins = {}
    for expr in exprs:
        if not isinstance(expr, ListExpr) or not expr.items:
            continue
        head = list_head(expr)
        if quoted:
            continue
        if head in {"allow", "deny"}:
            yield expr, bound_names, bound_origins
        next_quoted = head in {"quote", "quasiquote"}
        if next_quoted:
            continue
        if head in {"let", "let*", "letrec"} and len(expr.items) >= 2:
            origins = binding_origins(expr.items[1], head)
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_rules(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        if head == "lambda" and len(expr.items) >= 2:
            origins = parameter_origins(expr.items[1], head, expr.line)
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_rules(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        if head in DEFINE_FORMS:
            origins = parameter_origins(ListExpr(expr.items[1].items[1:], expr.items[1].line), head, expr.line) if len(expr.items) >= 2 and isinstance(expr.items[1], ListExpr) else {}
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_rules(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        yield from walk_rules(expr.items[1:], bound_names=bound_names, bound_origins=bound_origins)


def walk_with_filter_predicates(
    exprs: Iterable[Expr],
    bound_names: frozenset[str] = frozenset(),
    bound_origins: Optional[dict[str, dict]] = None,
    quoted: bool = False,
) -> Iterable[tuple[ListExpr, Expr, frozenset[str], dict[str, dict]]]:
    if bound_origins is None:
        bound_origins = {}
    for expr in exprs:
        if not isinstance(expr, ListExpr) or not expr.items:
            continue
        head = list_head(expr)
        if quoted:
            continue
        if head == "with-filter" and len(expr.items) >= 2:
            yield expr, expr.items[1], bound_names, bound_origins
        next_quoted = head in {"quote", "quasiquote"}
        if next_quoted:
            continue
        if head in {"let", "let*", "letrec"} and len(expr.items) >= 2:
            origins = binding_origins(expr.items[1], head)
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_with_filter_predicates(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        if head == "lambda" and len(expr.items) >= 2:
            origins = parameter_origins(expr.items[1], head, expr.line)
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_with_filter_predicates(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        if head in DEFINE_FORMS:
            origins = parameter_origins(ListExpr(expr.items[1].items[1:], expr.items[1].line), head, expr.line) if len(expr.items) >= 2 and isinstance(expr.items[1], ListExpr) else {}
            next_bound = frozenset(set(bound_names) | set(origins))
            yield from walk_with_filter_predicates(expr.items[2:], bound_names=next_bound, bound_origins={**bound_origins, **origins})
            continue
        yield from walk_with_filter_predicates(expr.items[1:], bound_names=bound_names, bound_origins=bound_origins)


def is_symbol_atom(value: str) -> bool:
    return not (
        value.startswith('"')
        or value.startswith('#"')
        or value.startswith("#")
        or value in {".", ")", "("}
        or value == ""
    )


def operation_like(value: str) -> bool:
    if value == "default":
        return True
    prefixes = (
        "appleevent-",
        "authorization-",
        "darwin-notification-",
        "device-",
        "distributed-notification-",
        "file",
        "generic-",
        "hid-",
        "iokit",
        "ipc-",
        "job-",
        "mach",
        "managed-preference-",
        "necp-",
        "network",
        "nvram",
        "process-",
        "pseudo-",
        "qtn-",
        "signal",
        "socket-",
        "syscall",
        "sysctl",
        "system-",
        "user-preference",
    )
    exact = {"dynamic-code-generation", "lsopen"}
    return value in exact or value.startswith(prefixes)


def likely_bare_reference(value: str) -> bool:
    if value == "filter":
        return True
    reference_suffixes = (
        "-filter",
        "-path-filter",
        "-regex",
        "-subpath",
        "-paths",
        "_subpaths",
        "-directory",
        "-blacklist",
    )
    return value.endswith(reference_suffixes)


LOGICAL_FILTERS = {"require-all", "require-any", "require-not"}
STRUCTURAL_RULE_BODY_HELPERS = {"apply-message-filter"}
DEFINE_FORMS = {"define", "define-once"}


def string_literal_value(value: str) -> Optional[str]:
    if not value.startswith('"'):
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value[1:-1]


def imported_profile_paths(exprs: Iterable[Expr], profile_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for expr in exprs:
        if not isinstance(expr, ListExpr) or len(expr.items) < 2:
            continue
        if list_head(expr) != "import":
            continue
        target = atom_value(expr.items[1])
        if not target:
            continue
        imported = string_literal_value(target)
        if imported:
            paths.append(profile_dir / imported)
    return paths


def global_define_origins(exprs: Iterable[Expr], profile: Optional[str] = None) -> dict[str, dict]:
    origins: dict[str, dict] = {}
    for expr in exprs:
        if not isinstance(expr, ListExpr) or len(expr.items) < 2:
            continue
        head = list_head(expr)
        if head not in DEFINE_FORMS:
            continue
        target = expr.items[1]
        name = None
        if isinstance(target, Atom) and is_symbol_atom(target.value):
            name = target.value
        elif isinstance(target, ListExpr) and target.items:
            candidate = atom_value(target.items[0])
            if candidate and is_symbol_atom(candidate):
                name = candidate
        if name:
            origins[name] = {
                "form": head or "",
                "line": expr.line,
                "source": expr_to_source(expr),
            }
            if profile:
                origins[name]["profile"] = profile
    return origins


def collect_function_occurrences(
    expr: Expr,
    profile: str,
    rule_line: int,
    parent: Optional[str],
    bound_names: frozenset[str],
    quoted: bool = False,
) -> list[dict]:
    occurrences: list[dict] = []
    if isinstance(expr, ListExpr) and expr.items:
        head = list_head(expr)
        if quoted or head in {"quote", "quasiquote"}:
            return occurrences
        if head and head not in {"allow", "deny"}:
            occurrences.append(
                {
                    "function": head,
                    "parent": parent,
                    "profile": profile,
                    "line": expr.line,
                    "rule_line": rule_line,
                    "args": argument_records(expr.items[1:], bound_names),
                    "source": expr_to_source(expr),
                }
            )
        for item in expr.items[1:]:
            occurrences.extend(collect_function_occurrences(item, profile, rule_line, parent=head, bound_names=bound_names))
    return occurrences


def collect_string_literal_heads(expr: Expr, quoted: bool = False) -> list[str]:
    heads: list[str] = []
    if isinstance(expr, ListExpr) and expr.items:
        head = list_head(expr)
        if quoted or head in {"quote", "quasiquote"}:
            return heads
        if head and any(isinstance(item, Atom) and is_string_literal(item.value) for item in expr.items[1:]):
            heads.append(head)
        for item in expr.items[1:]:
            heads.extend(collect_string_literal_heads(item))
    return heads


def filter_occurrence(expr: ListExpr, profile: str, rule_line: int, bound_names: frozenset[str]) -> dict:
    return {
        "function": list_head(expr),
        "profile": profile,
        "line": expr.line,
        "rule_line": rule_line,
        "args": argument_records(expr.items[1:], bound_names),
        "source": expr_to_source(expr),
    }


def classify_invocation_arg(expr: Expr, profile: str, rule_line: int, bound_names: frozenset[str]) -> tuple[list[str], list[dict], list[dict], list[dict], list[str], list[str]]:
    """Return (filter_names, filter_calls, combinators, helper_functions, value_refs, variable_refs).

    SBPL is a programming language, so a parenthesized argument is a function
    call. We infer that direct function-call arguments to allow/deny, and
    function calls nested under logical combinators, are filter-returning
    functions. Nested calls inside ordinary function arguments are just helper
    functions.
    """

    if not isinstance(expr, ListExpr) or not expr.items:
        return [], [], [], [], [], []

    head = list_head(expr)
    if not head or head in {"quote", "quasiquote"}:
        return [], [], [], [], [], []

    if head in bound_names:
        return [], [], [], [], [], [head]

    if head in LOGICAL_FILTERS:
        filters: list[str] = []
        combinators = [
            {
                "function": head,
                "profile": profile,
                "line": expr.line,
                "rule_line": rule_line,
                "args": argument_records(expr.items[1:], bound_names),
                "source": expr_to_source(expr),
            }
        ]
        filter_calls: list[dict] = []
        functions: list[dict] = []
        value_refs: list[str] = []
        variable_refs: list[str] = []
        for item in expr.items[1:]:
            if isinstance(item, ListExpr):
                child_filters, child_filter_calls, child_combinators, child_functions, child_value_refs, child_variable_refs = classify_invocation_arg(item, profile, rule_line, bound_names)
                filters.extend(child_filters)
                filter_calls.extend(child_filter_calls)
                combinators.extend(child_combinators)
                functions.extend(child_functions)
                value_refs.extend(child_value_refs)
                variable_refs.extend(child_variable_refs)
            elif isinstance(item, Atom) and is_symbol_atom(item.value):
                if item.value in bound_names:
                    variable_refs.append(item.value)
                else:
                    value_refs.append(item.value)
        return filters, filter_calls, combinators, functions, value_refs, variable_refs

    if head in STRUCTURAL_RULE_BODY_HELPERS:
        functions = [
            {
                "function": head,
                "parent": "rule-filter-position",
                "profile": profile,
                "line": expr.line,
                "rule_line": rule_line,
                "args": argument_records(expr.items[1:], bound_names),
                "source": expr_to_source(expr),
            }
        ]
        return [], [], [], functions, [], []

    # A few Scheme helpers can appear directly where a filter expression is
    # expected, for example `(apply require-any filters)`. Keep these out of
    # the operation/filter matrix and report them as functions instead.
    if head in {"apply"}:
        functions = [
            {
                "function": head,
                "parent": "rule-filter-position",
                "profile": profile,
                "line": expr.line,
                "rule_line": rule_line,
                "args": argument_records(expr.items[1:], bound_names),
                "source": expr_to_source(expr),
            }
        ]
        value_refs = []
        variable_refs = []
        for index, item in enumerate(expr.items[1:]):
            if not isinstance(item, Atom) or not is_symbol_atom(item.value):
                continue
            if index == 0:
                continue
            if item.value in bound_names:
                variable_refs.append(item.value)
            elif item.value not in LOGICAL_FILTERS:
                value_refs.append(item.value)
        for item in expr.items[1:]:
            if isinstance(item, ListExpr):
                functions.extend(collect_function_occurrences(item, profile, rule_line, parent=head, bound_names=bound_names))
        return [], [], [], functions, value_refs, variable_refs

    filters = [head]
    filter_calls = [filter_occurrence(expr, profile, rule_line, bound_names)]
    functions = []
    value_refs = []
    variable_refs = []
    for item in expr.items[1:]:
        if isinstance(item, ListExpr):
            functions.extend(collect_function_occurrences(item, profile, rule_line, parent=head, bound_names=bound_names))
        elif isinstance(item, Atom) and is_symbol_atom(item.value) and likely_bare_reference(item.value):
            if item.value in bound_names:
                variable_refs.append(item.value)
            else:
                value_refs.append(item.value)
    return filters, filter_calls, [], functions, value_refs, variable_refs


def collect_modifier_occurrence(expr: Expr) -> Optional[dict]:
    if isinstance(expr, ListExpr) and list_head(expr) == "with":
        modifier = None
        args: list[str] = []
        for item in expr.items[1:]:
            if modifier is None and isinstance(item, Atom) and is_symbol_atom(item.value):
                modifier = item.value
            elif modifier is not None:
                args.append(expr_to_source(item))
        if modifier:
            return {
                "modifier": modifier,
                "args": args,
                "line": expr.line,
                "source": expr_to_source(expr),
            }
    return None


def leading_bare_atoms(rule: ListExpr) -> list[str]:
    candidates: list[str] = []
    for item in rule.items[1:]:
        if isinstance(item, ListExpr):
            if list_head(item) == "with":
                continue
            break
        value = atom_value(item)
        if value and is_symbol_atom(value):
            candidates.append(value)
        else:
            break
    return candidates


def classify_rule(rule: ListExpr, known_ops: set[str], profile: str, bound_names: frozenset[str], bound_origins: dict[str, dict]) -> dict:
    action = atom_value(rule.items[0])
    operations: list[str] = []
    value_refs: list[str] = []
    variable_refs: list[str] = []
    top_filter_heads: list[str] = []
    all_filter_heads: list[str] = []
    filter_occurrences: list[dict] = []
    combinator_occurrences: list[dict] = []
    function_occurrences: list[dict] = []
    string_literal_heads: list[str] = []
    modifier_occurrences: list[dict] = []

    before_filter = True
    for item in rule.items[1:]:
        if isinstance(item, ListExpr):
            if list_head(item) == "with":
                modifier = collect_modifier_occurrence(item)
                if modifier:
                    modifier_occurrences.append(modifier)
            else:
                before_filter = False
                top_head = list_head(item)
                if top_head:
                    top_filter_heads.append(top_head)
                filters, filter_calls, combinators, functions, bare_refs, filter_variable_refs = classify_invocation_arg(item, profile, rule.line, bound_names)
                all_filter_heads.extend(filters)
                filter_occurrences.extend(filter_calls)
                combinator_occurrences.extend(combinators)
                function_occurrences.extend(functions)
                value_refs.extend(bare_refs)
                variable_refs.extend(filter_variable_refs)
                string_literal_heads.extend(collect_string_literal_heads(item))
            continue

        value = atom_value(item)
        if not value or not is_symbol_atom(value):
            continue
        if value in bound_names:
            variable_refs.append(value)
            continue
        if before_filter and (value in known_ops or (operation_like(value) and not likely_bare_reference(value))):
            operations.append(value)
        else:
            value_refs.append(value)

    return {
        "action": action,
        "line": rule.line,
        "operations": operations,
        "value_refs": value_refs,
        "top_filter_heads": top_filter_heads,
        "filter_heads": sorted(set(all_filter_heads)),
        "filter_occurrences": filter_occurrences,
        "function_heads": sorted({occurrence["function"] for occurrence in function_occurrences}),
        "function_occurrences": function_occurrences,
        "combinator_heads": sorted({occurrence["function"] for occurrence in combinator_occurrences}),
        "combinator_occurrences": combinator_occurrences,
        "string_literal_heads": sorted(set(string_literal_heads)),
        "modifiers": sorted({occurrence["modifier"] for occurrence in modifier_occurrences}),
        "modifier_occurrences": modifier_occurrences,
        "variable_refs": sorted(set(variable_refs)),
        "variable_ref_origins": {
            name: bound_origins[name]
            for name in sorted(set(variable_refs))
            if name in bound_origins
        },
        "bound_names": sorted(bound_names),
        "source": expr_to_source(rule),
    }


def load_rules(profile_dir: Path) -> tuple[list[dict], list[dict], dict[str, str]]:
    parsed: list[RuleInstance] = []
    with_filter_predicates: list[dict] = []
    errors: dict[str, str] = {}

    forms_cache: dict[Path, list[Expr]] = {}

    def parse_profile(path: Path) -> list[Expr]:
        resolved = path.resolve()
        if resolved not in forms_cache:
            text = resolved.read_text(encoding="utf-8")
            forms_cache[resolved] = Parser(tokenize(text)).parse_all()
        return forms_cache[resolved]

    def imported_define_origins(path: Path, seen: Optional[set[Path]] = None) -> dict[str, dict]:
        resolved = path.resolve()
        if seen is None:
            seen = set()
        if resolved in seen:
            return {}
        seen.add(resolved)
        origins: dict[str, dict] = {}
        forms = parse_profile(resolved)
        for imported in imported_profile_paths(forms, profile_dir):
            if not imported.exists():
                continue
            imported_resolved = imported.resolve()
            origins.update(imported_define_origins(imported_resolved, seen))
            origins.update(global_define_origins(parse_profile(imported_resolved), imported_resolved.name))
        return origins

    corpus_define_origins: dict[str, dict] = {}
    for path in sorted(profile_dir.glob("*.sb")):
        try:
            for name, origin in global_define_origins(parse_profile(path), path.name).items():
                corpus_define_origins.setdefault(name, origin)
        except Exception as exc:  # pragma: no cover - diagnostic script
            errors[str(path)] = repr(exc)

    for path in sorted(profile_dir.glob("*.sb")):
        try:
            forms = parse_profile(path)
            profile_bound_origins = {
                **corpus_define_origins,
                **imported_define_origins(path),
                **global_define_origins(forms, path.name),
            }
            profile_bound_names = frozenset(profile_bound_origins)
            for rule, bound_names, bound_origins in walk_rules(forms, bound_names=profile_bound_names, bound_origins=profile_bound_origins):
                parsed.append(RuleInstance(path, rule, bound_names, bound_origins))
            for wrapper, predicate, bound_names, bound_origins in walk_with_filter_predicates(forms, bound_names=profile_bound_names, bound_origins=profile_bound_origins):
                filters, filter_calls, combinators, functions, value_refs, variable_refs = classify_invocation_arg(predicate, path.name, wrapper.line, bound_names)
                with_filter_predicates.append(
                    {
                        "profile": path.name,
                        "path": str(path),
                        "line": wrapper.line,
                        "predicate": expr_to_source(predicate),
                        "filter_heads": sorted(set(filters)),
                        "filter_occurrences": filter_calls,
                        "combinator_heads": sorted({occurrence["function"] for occurrence in combinators}),
                        "combinator_occurrences": combinators,
                        "function_heads": sorted({occurrence["function"] for occurrence in functions}),
                        "function_occurrences": functions,
                        "value_refs": sorted(set(value_refs)),
                        "variable_refs": sorted(set(variable_refs)),
                        "variable_ref_origins": {
                            name: bound_origins[name]
                            for name in sorted(set(variable_refs))
                            if name in bound_origins
                        },
                        "source": expr_to_source(wrapper),
                    }
                )
        except Exception as exc:  # pragma: no cover - diagnostic script
            errors[str(path)] = repr(exc)

    known_ops: set[str] = set()
    for instance in parsed:
        leading = leading_bare_atoms(instance.rule)
        while leading and leading[0] in instance.bound_names:
            leading = leading[1:]
        if leading and operation_like(leading[0]) and not likely_bare_reference(leading[0]):
            known_ops.add(leading[0])
        known_ops.update(atom for atom in leading if operation_like(atom) and not likely_bare_reference(atom))

    rules: list[dict] = []
    for instance in parsed:
        classified = classify_rule(instance.rule, known_ops, instance.profile.name, instance.bound_names, instance.bound_origins)
        classified["profile"] = instance.profile.name
        classified["path"] = str(instance.profile)
        rules.append(classified)
    return rules, with_filter_predicates, errors


def argument_type_label(arg: dict) -> str:
    if arg["type"] == "function-call":
        return f"function-call:{arg.get('function', '')}"
    return arg["type"]


def source_argument_record(source: str) -> dict:
    if source.startswith("("):
        match = re.match(r"\((\S+)", source)
        return {
            "source": source,
            "type": "function-call",
            "function": match.group(1) if match else "",
        }
    return {
        "source": source,
        "type": atom_type(source, frozenset()),
    }


def summarize_function_arguments(occurrences: Iterable[dict]) -> dict:
    arities: collections.Counter[int] = collections.Counter()
    positional: dict[int, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    examples: list[dict] = []
    for occurrence in occurrences:
        args = occurrence.get("args", [])
        arities[len(args)] += 1
        for index, arg in enumerate(args):
            positional[index][argument_type_label(arg)] += 1
        if len(examples) < 5:
            examples.append(
                {
                    "profile": occurrence["profile"],
                    "line": occurrence["line"],
                    "source": occurrence["source"],
                    "args": args,
                }
            )
    return {
        "arities": dict(arities.most_common()),
        "arguments": {
            str(index): dict(counter.most_common())
            for index, counter in sorted(positional.items())
        },
        "examples": examples,
    }


def summarize_modifier_arguments(occurrences: Iterable[dict]) -> dict:
    adapted = [
        {
            **occurrence,
            "args": [source_argument_record(arg) for arg in occurrence.get("args", [])],
        }
        for occurrence in occurrences
    ]
    return summarize_function_arguments(adapted)


def glob_ancestors(operation: str, all_operations: set[str]) -> list[str]:
    ancestors = [
        candidate
        for candidate in all_operations
        if candidate.endswith("*")
        and candidate != operation
        and operation.startswith(candidate[:-1])
    ]
    return sorted(ancestors, key=lambda name: (len(name), name))


def operation_specific_view(operations: dict) -> tuple[dict, dict]:
    all_operations = set(operations)
    groups: dict[str, list[str]] = {
        op: sorted(
            candidate
            for candidate in all_operations
            if candidate != op and op.endswith("*") and candidate.startswith(op[:-1])
        )
        for op in all_operations
        if op.endswith("*")
    }
    groups = {op: members for op, members in sorted(groups.items()) if members}

    specific: dict[str, dict] = {}
    for op, data in operations.items():
        ancestors = glob_ancestors(op, all_operations)
        inherited_filters: set[str] = set()
        inherited_modifiers: set[str] = set()
        for ancestor in ancestors:
            inherited_filters.update(operations[ancestor]["filters"])
            inherited_modifiers.update(operations[ancestor]["modifiers"])
        filters = {
            key: value
            for key, value in data["filters"].items()
            if key not in inherited_filters
        }
        modifiers = {
            key: value
            for key, value in data["modifiers"].items()
            if key not in inherited_modifiers
        }
        specific[op] = {
            "glob_ancestors": ancestors,
            "filters": filters,
            "modifiers": modifiers,
            "filter_examples": {
                key: data.get("filter_examples", {}).get(key, [])
                for key in filters
            },
            "modifier_examples": {
                key: data.get("modifier_examples", {}).get(key, [])
                for key in modifiers
            },
            "inherited_filter_functions": sorted(inherited_filters.intersection(data["filters"])),
            "inherited_modifiers": sorted(inherited_modifiers.intersection(data["modifiers"])),
        }
    return groups, specific


def macos_marketing_name(version: str) -> str:
    major = version.split(".", 1)[0]
    return {
        "26": "Tahoe",
        "15": "Sequoia",
        "14": "Sonoma",
        "13": "Ventura",
        "12": "Monterey",
        "11": "Big Sur",
    }.get(major, "")


def generation_metadata() -> dict:
    metadata = {
        "date": datetime.date.today().isoformat(),
        "macos_product_name": "macOS",
        "macos_product_version": "",
        "macos_build_version": "",
        "macos_marketing_name": "",
    }
    try:
        output = subprocess.check_output(["sw_vers"], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return metadata
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if key == "ProductName":
            metadata["macos_product_name"] = value
        elif key == "ProductVersion":
            metadata["macos_product_version"] = value
            metadata["macos_marketing_name"] = macos_marketing_name(value)
        elif key == "BuildVersion":
            metadata["macos_build_version"] = value
    return metadata


def generated_from_label(summary: dict) -> str:
    metadata = summary["generation"]
    product = metadata["macos_product_name"]
    marketing = metadata["macos_marketing_name"]
    version = metadata["macos_product_version"]
    build = metadata["macos_build_version"]
    bits = [product]
    if marketing:
        bits.append(marketing)
    if version:
        bits.append(version)
    label = " ".join(bits)
    if build:
        label += f" (build {build})"
    return f"{label} on {metadata['date']}"


def render_argument_type_summary(arguments: dict, max_positions: int = 8, max_types: int = 4) -> str:
    bits: list[str] = []
    sorted_items = sorted(arguments.items(), key=lambda item: int(item[0]))
    for index, types in sorted_items[:max_positions]:
        rendered_types = ", ".join(f"`{name}` ({count})" for name, count in list(types.items())[:max_types])
        bits.append(f"arg {int(index) + 1}: {rendered_types}")
    if len(sorted_items) > max_positions:
        bits.append(f"... {len(sorted_items) - max_positions} more positions")
    return "; ".join(bits)


CONCRETE_ARGUMENT_TYPES = {"string", "integer", "scheme-literal", "symbol"}


def function_return_type_map(summary: dict) -> dict[str, str]:
    returns: dict[str, str] = {}
    for function, data in summary["functions"].items():
        inferred = data.get("inferred_return_types", {})
        if len(inferred) == 1:
            returns[function] = next(iter(inferred))
    return returns


def resolved_argument_type_counts(arguments: dict, returns: dict[str, str]) -> dict[str, dict[str, int]]:
    resolved: dict[str, dict[str, int]] = {}
    for index, counts in arguments.items():
        direct_types = {name for name in counts if name in CONCRETE_ARGUMENT_TYPES}
        fallback = next(iter(direct_types)) if len(direct_types) == 1 else None
        counter: collections.Counter[str] = collections.Counter()
        for name, count in counts.items():
            if name.startswith("function-call:"):
                function = name.split(":", 1)[1]
                counter[returns.get(function) or fallback or f"{function}(...)"] += count
            else:
                counter[name] += count
        resolved[index] = dict(counter.most_common())
    return resolved


def primary_type_name(counter: dict[str, int]) -> str:
    if not counter:
        return "value"
    names = list(counter)
    if len(names) == 1:
        return names[0]
    total = sum(counter.values())
    for preferred in ("string", "regex-string", "integer", "symbol"):
        if counter.get(preferred, 0) and counter[preferred] * 5 >= total * 4:
            return preferred
    concrete = [name for name in names if name in CONCRETE_ARGUMENT_TYPES]
    if len(concrete) == 1 and all(name == concrete[0] or name in {"variable-reference"} for name in names):
        return concrete[0]
    return "|".join(names[:3])


def argument_signature_parts(data: dict, returns: dict[str, str]) -> list[str]:
    arities = sorted(int(arity) for arity in data.get("arities", {}))
    if not arities:
        return []
    resolved = resolved_argument_type_counts(data.get("arguments", {}), returns)
    max_arity = max(arities)
    if max_arity == 0:
        return []
    positional = [
        primary_type_name(resolved.get(str(index), {}))
        for index in range(max_arity)
    ]
    if len(arities) == 1:
        return positional

    min_arity = min(arities)
    if max_arity > min_arity:
        suffix = positional[min_arity:]
        if suffix and len(set(suffix)) == 1:
            prefix = positional[:min_arity]
            if not prefix or set(prefix) == {suffix[0]}:
                return [f"{suffix[0]}..."]
            return prefix + [f"{suffix[0]}..."]
    if positional and len(set(positional)) == 1:
        return [f"{positional[0]}..."]
    return positional


def function_signature(function: str, data: dict, returns: dict[str, str]) -> str:
    parts = argument_signature_parts(data, returns)
    if not parts:
        return f"({function})"
    return f"({function} {' '.join(parts)})"


def modifier_signature(modifier: str, data: dict) -> str:
    parts = argument_signature_parts(data.get("argument_summary", {}), {})
    if not parts:
        return f"(with {modifier})"
    return f"(with {modifier} {' '.join(parts)})"


def argument_example(args: list[dict]) -> str:
    if not args:
        return ""
    values: list[str] = []
    for arg in args:
        if isinstance(arg, dict):
            values.append(arg["source"])
        else:
            values.append(str(arg))
    return " ".join(values)


def occurrence_examples(examples: Iterable[dict], limit: int = 2) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for example in examples:
        value = argument_example(example.get("args", []))
        if not value or value in seen:
            continue
        seen.add(value)
        values.append(value)
        if len(values) >= limit:
            break
    return values


def render_examples(values: Iterable[str], fallback: str = "") -> str:
    rendered = []
    for value in values:
        escaped = value
        if len(escaped) > 120:
            escaped = escaped[:117] + "..."
        rendered.append(f"`{escaped}`")
    return ", ".join(rendered) if rendered else fallback


def table_escape(value: str) -> str:
    escaped: list[str] = []
    previous = ""
    for ch in value:
        if ch == "|" and previous != "\\":
            escaped.append("\\|")
        else:
            escaped.append(ch)
        previous = ch
    return "".join(escaped)


def table_join(items: Iterable[str]) -> str:
    return ", ".join(items)


def symbol_values_from_occurrences(occurrences: Iterable[dict], argument_summary: dict) -> list[str]:
    symbol_positions = {
        int(position)
        for position, counts in argument_summary.get("arguments", {}).items()
        if "symbol" in counts
    }
    if not symbol_positions:
        return []
    values: set[str] = set()
    for occurrence in occurrences:
        args = occurrence.get("args", [])
        for index in symbol_positions:
            if index >= len(args):
                continue
            arg = args[index]
            if isinstance(arg, dict) and arg.get("type") == "symbol":
                values.add(arg["source"])
    return sorted(values)


def symbol_values_display(values: list[str]) -> str:
    if not values:
        return ""
    return ", ".join(f"`{value}`" for value in values)


def code_list(values: Iterable[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def operation_usage_items(summary: dict, kind: str, name: str) -> list[str]:
    items: list[str] = []
    for op in sorted_operation_names(summary["operation_specific"]):
        data = summary["operation_specific"][op]
        collection = data["filters"] if kind == "filter" else data["modifiers"]
        if name in collection:
            items.append(f"`{op}` ({collection[name]})")
    return items


def operation_group_prefix(operation: str) -> str:
    return operation.rstrip("*").split("-", 1)[0]


def grouped_root_operations(roots: list[str], prefix_counts: collections.Counter[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    i = 0
    while i < len(roots):
        prefix = operation_group_prefix(roots[i])
        j = i + 1
        if prefix_counts[prefix] > 1:
            while j < len(roots) and operation_group_prefix(roots[j]) == prefix:
                j += 1
        else:
            while j < len(roots) and prefix_counts[operation_group_prefix(roots[j])] == 1:
                j += 1
        groups.append(roots[i:j])
        i = j
    return groups


def operation_reference_context(summary: dict) -> dict:
    returns = function_return_type_map(summary)
    parent_by_op = operation_parent_map(summary)
    children_by_parent: dict[str, list[str]] = collections.defaultdict(list)
    for op, parent in parent_by_op.items():
        children_by_parent[parent].append(op)

    child_ops = set(parent_by_op)
    root_globs = [
        op
        for op in summary["operations"]
        if op.endswith("*") and op not in child_ops
    ]
    ungrouped = [
        op
        for op in summary["operations"]
        if op not in child_ops and not op.endswith("*")
    ]

    def operation_record(op: str, depth: int) -> dict:
        specific = summary["operation_specific"][op]
        filters = []
        for name in sorted(specific["filters"]):
            example = render_examples(occurrence_examples(specific["filter_examples"].get(name, []), limit=1))
            filters.append(
                {
                    "signature": function_signature(name, summary["filter_functions"][name], returns),
                    "example": example,
                    "has_example": bool(example),
                }
            )
        modifiers = []
        for name in sorted(specific["modifiers"]):
            example = render_examples(occurrence_examples(specific["modifier_examples"].get(name, []), limit=1))
            modifiers.append(
                {
                    "signature": modifier_signature(name, summary["modifiers"][name]),
                    "example": example,
                    "has_example": bool(example),
                }
            )
        return {
            "heading": "#" * min(depth + 2, 6),
            "name": op,
            "filters": filters,
            "has_filters": bool(filters),
            "modifiers": modifiers,
            "has_modifiers": bool(modifiers),
            "separator_after": False,
        }

    def append_operation(records: list[dict], op: str, depth: int) -> None:
        records.append(operation_record(op, depth))
        for child in sorted_operation_names(children_by_parent.get(op, [])):
            append_operation(records, child, depth + 1)

    filters = []
    filter_names = sorted(set(summary["filter_functions"]) | set(summary["with_filter_filters"]))
    for name in filter_names:
        data = summary["filter_functions"].get(name) or summary["with_filter_filters"][name]
        examples = render_examples(occurrence_examples(data["examples"], limit=2), fallback="-")
        symbols = symbol_values_from_occurrences(data["examples"], data)
        only_with_filter = name not in summary["filter_functions"]
        filters.append(
            {
                "signature": function_signature(name, data, returns),
                "operations": "`with-filter`" if only_with_filter else table_join(operation_usage_items(summary, "filter", name)) or "-",
                "examples": examples,
                "symbols": symbol_values_display(symbols),
                "has_symbols": bool(symbols),
            }
        )

    modifiers = []
    for name in sorted(summary["modifiers"]):
        data = summary["modifiers"][name]
        examples = render_examples(occurrence_examples(data["argument_summary"]["examples"], limit=2), fallback="-")
        symbols = symbol_values_from_occurrences(data["argument_summary"]["examples"], data["argument_summary"])
        modifiers.append(
            {
                "signature": modifier_signature(name, data),
                "operations": table_join(operation_usage_items(summary, "modifier", name)) or "-",
                "examples": examples,
                "symbols": symbol_values_display(symbols),
                "has_symbols": bool(symbols),
            }
        )

    operations: list[dict] = []
    prefix_counts = collections.Counter(operation_group_prefix(op) for op in summary["operations"])
    root_groups = grouped_root_operations(sorted_operation_names([*root_globs, *ungrouped]), prefix_counts)
    for group in root_groups:
        group_records: list[dict] = []
        for op in group:
            append_operation(group_records, op, 1)
        if group_records:
            group_records[-1]["separator_after"] = True
        operations.extend(group_records)

    return {
        "generated_from": generated_from_label(summary),
        "source_profile_dir": summary["source_profile_dir"],
        "profile_count": summary["profile_count"],
        "rule_count": summary["rule_count"],
        "operation_count": len(summary["operations"]),
        "filter_count": len(filter_names),
        "modifier_count": len(summary["modifiers"]),
        "operations": operations,
        "filters": filters,
        "modifiers": modifiers,
        "with_filter_predicate_count": summary["with_filter_predicate_count"],
        "with_filter_only_predicates": code_list(summary["with_filter_only_predicates"]),
        "has_with_filter_only_predicates": bool(summary["with_filter_only_predicates"]),
    }


def render_template(path: Path, context: dict) -> str:
    try:
        import jinja2
    except ImportError as exc:
        raise SystemExit(
            "Missing template dependency: Jinja2. Run with "
            "`uv run --with-requirements sandbox/requirements.txt python3 sandbox/scripts/extract_sb_rules.py` "
            "or install `Jinja2` in the active Python environment."
        ) from exc
    env = jinja2.Environment(
        autoescape=False,
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
        undefined=jinja2.StrictUndefined,
    )
    env.filters["table_escape"] = table_escape
    return env.from_string(path.read_text(encoding="utf-8")).render(context)


def sorted_operation_names(names: Iterable[str]) -> list[str]:
    return sorted(names, key=lambda name: (name.replace("*", ""), 0 if name.endswith("*") else 1, name))


def operation_parent_map(summary: dict) -> dict[str, str]:
    parents: dict[str, str] = {}
    for op, data in summary["operation_specific"].items():
        ancestors = data["glob_ancestors"]
        if ancestors:
            parents[op] = max(ancestors, key=lambda name: (len(name.rstrip("*")), name))
    return parents


def summarize(rules: list[dict], with_filter_predicates: list[dict], errors: dict[str, str]) -> dict:
    operation_counts: collections.Counter[str] = collections.Counter()
    filter_counts: collections.Counter[str] = collections.Counter()
    top_filter_counts: collections.Counter[str] = collections.Counter()
    combinator_counts: collections.Counter[str] = collections.Counter()
    combinator_examples: dict[str, list[dict]] = collections.defaultdict(list)
    modifier_counts: collections.Counter[str] = collections.Counter()
    modifier_arg_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    modifier_occurrences_by_name: dict[str, list[dict]] = collections.defaultdict(list)
    modifier_examples: dict[str, list[dict]] = collections.defaultdict(list)
    function_counts: collections.Counter[str] = collections.Counter()
    function_parent_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    function_examples: dict[str, list[dict]] = collections.defaultdict(list)
    filter_function_occurrences: dict[str, list[dict]] = collections.defaultdict(list)
    helper_function_occurrences: dict[str, list[dict]] = collections.defaultdict(list)
    string_accepting_counts: collections.Counter[str] = collections.Counter()
    operation_filters: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    operation_modifiers: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    operation_actions: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    operation_examples: dict[str, list[dict]] = collections.defaultdict(list)
    operation_filter_examples: dict[str, dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    operation_modifier_examples: dict[str, dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    value_ref_counts: collections.Counter[str] = collections.Counter()
    variable_ref_counts: collections.Counter[str] = collections.Counter()
    variable_ref_examples: dict[str, list[dict]] = collections.defaultdict(list)
    variable_ref_origins: dict[str, dict] = {}
    with_filter_counts: collections.Counter[str] = collections.Counter()
    with_filter_occurrences: dict[str, list[dict]] = collections.defaultdict(list)
    with_filter_combinator_counts: collections.Counter[str] = collections.Counter()

    for rule in rules:
        for head in rule["string_literal_heads"]:
            string_accepting_counts[head] += 1
        for filt in rule["filter_heads"]:
            filter_counts[filt] += 1
        for filt in rule["top_filter_heads"]:
            top_filter_counts[filt] += 1
        for occurrence in rule["filter_occurrences"]:
            filter_function_occurrences[occurrence["function"]].append(occurrence)
        for occurrence in rule["combinator_occurrences"]:
            combinator = occurrence["function"]
            combinator_counts[combinator] += 1
            if len(combinator_examples[combinator]) < 5:
                combinator_examples[combinator].append(
                    {
                        "profile": occurrence["profile"],
                        "line": occurrence["line"],
                        "source": occurrence["source"],
                    }
                )
        for occurrence in rule["modifier_occurrences"]:
            modifier = occurrence["modifier"]
            modifier_counts[modifier] += 1
            modifier_occurrences_by_name[modifier].append(
                {
                    **occurrence,
                    "profile": rule["profile"],
                }
            )
            arg_key = " ".join(occurrence["args"])
            if arg_key:
                modifier_arg_counts[modifier][arg_key] += 1
            if len(modifier_examples[modifier]) < 5:
                modifier_examples[modifier].append(
                    {
                        "args": occurrence["args"],
                        "profile": rule["profile"],
                        "line": occurrence["line"],
                        "source": occurrence["source"],
                    }
                )
        for occurrence in rule["function_occurrences"]:
            function = occurrence["function"]
            helper_function_occurrences[function].append(occurrence)
            parent = occurrence["parent"] or ""
            function_counts[function] += 1
            function_parent_counts[function][parent] += 1
            if len(function_examples[function]) < 5:
                function_examples[function].append(
                    {
                        "parent": parent,
                        "profile": occurrence["profile"],
                        "line": occurrence["line"],
                        "source": occurrence["source"],
                    }
                )
        for atom in rule["value_refs"]:
            value_ref_counts[atom] += 1
        for name in rule["variable_refs"]:
            variable_ref_counts[name] += 1
            if name in rule.get("variable_ref_origins", {}) and name not in variable_ref_origins:
                origin = rule["variable_ref_origins"][name]
                variable_ref_origins[name] = {
                    **origin,
                    "profile": origin.get("profile", rule["profile"]),
                }
            if len(variable_ref_examples[name]) < 3:
                variable_ref_examples[name].append(
                    {
                        "profile": rule["profile"],
                        "line": rule["line"],
                        "source": rule["source"],
                    }
                )
        for op in rule["operations"]:
            operation_counts[op] += 1
            operation_actions[op][rule["action"]] += 1
            for filt in rule["filter_heads"]:
                operation_filters[op][filt] += 1
            for mod in rule["modifiers"]:
                operation_modifiers[op][mod] += 1
            for occurrence in rule["filter_occurrences"]:
                function = occurrence["function"]
                if len(operation_filter_examples[op][function]) < 5:
                    operation_filter_examples[op][function].append(occurrence)
            for occurrence in rule["modifier_occurrences"]:
                modifier = occurrence["modifier"]
                if len(operation_modifier_examples[op][modifier]) < 5:
                    operation_modifier_examples[op][modifier].append(
                        {
                            **occurrence,
                            "profile": rule["profile"],
                        }
                    )
            if len(operation_examples[op]) < 5:
                operation_examples[op].append(
                    {
                        "profile": rule["profile"],
                        "line": rule["line"],
                        "source": rule["source"],
                    }
                )

    for predicate in with_filter_predicates:
        for filt in predicate["filter_heads"]:
            with_filter_counts[filt] += 1
        for occurrence in predicate["filter_occurrences"]:
            with_filter_occurrences[occurrence["function"]].append(occurrence)
        for occurrence in predicate["combinator_occurrences"]:
            with_filter_combinator_counts[occurrence["function"]] += 1

    function_return_inferences: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    function_return_examples: dict[str, list[dict]] = collections.defaultdict(list)
    string_accepting_heads = set(string_accepting_counts)
    for rule in rules:
        for occurrence in rule["function_occurrences"]:
            parent = occurrence["parent"]
            if parent in string_accepting_heads:
                function = occurrence["function"]
                function_return_inferences[function]["string"] += 1
                if len(function_return_examples[function]) < 5:
                    function_return_examples[function].append(
                        {
                            "reason": f"`{parent}` also appears with string literals",
                            "parent": parent,
                            "profile": occurrence["profile"],
                            "line": occurrence["line"],
                            "source": occurrence["source"],
                        }
                    )

    operations_summary = {
        op: {
            "count": count,
            "actions": dict(operation_actions[op]),
            "filters": dict(operation_filters[op].most_common()),
            "modifiers": dict(operation_modifiers[op].most_common()),
            "filter_examples": {
                function: examples
                for function, examples in operation_filter_examples[op].items()
            },
            "modifier_examples": {
                modifier: examples
                for modifier, examples in operation_modifier_examples[op].items()
            },
            "examples": operation_examples[op],
        }
        for op, count in operation_counts.most_common()
    }
    operation_groups, operation_specific = operation_specific_view(operations_summary)

    return {
        "source_profile_dir": str(PROFILE_DIR),
        "generation": generation_metadata(),
        "profile_count": len({rule["profile"] for rule in rules}),
        "rule_count": len(rules),
        "parse_errors": errors,
        "operations": operations_summary,
        "operation_groups": operation_groups,
        "operation_specific": operation_specific,
        "filters": dict(filter_counts.most_common()),
        "filter_functions": {
            function: {
                "rule_count": filter_counts[function],
                "occurrence_count": len(filter_function_occurrences[function]),
                **summarize_function_arguments(filter_function_occurrences[function]),
            }
            for function, _ in filter_counts.most_common()
        },
        "top_level_filters": dict(top_filter_counts.most_common()),
        "combinators": {
            combinator: {
                "count": count,
                "examples": combinator_examples[combinator],
            }
            for combinator, count in combinator_counts.most_common()
        },
        "modifiers": {
            modifier: {
                "count": count,
                "arguments": dict(modifier_arg_counts[modifier].most_common()),
                "argument_summary": summarize_modifier_arguments(modifier_occurrences_by_name[modifier]),
                "examples": modifier_examples[modifier],
            }
            for modifier, count in modifier_counts.most_common()
        },
        "with_filter_predicate_count": len(with_filter_predicates),
        "with_filter_filters": {
            function: {
                "count": with_filter_counts[function],
                **summarize_function_arguments(with_filter_occurrences[function]),
            }
            for function, _ in with_filter_counts.most_common()
        },
        "with_filter_only_predicates": sorted(
            function
            for function in with_filter_counts
            if function not in filter_counts
        ),
        "with_filter_combinators": dict(with_filter_combinator_counts.most_common()),
        "functions": {
            function: {
                "count": count,
                "parents": dict(function_parent_counts[function].most_common()),
                "inferred_return_types": dict(function_return_inferences[function].most_common()),
                "argument_summary": summarize_function_arguments(helper_function_occurrences[function]),
                "examples": function_examples[function],
                "return_type_examples": function_return_examples[function],
            }
            for function, count in function_counts.most_common()
        },
        "string_accepting_heads": dict(string_accepting_counts.most_common()),
        "variable_references": dict(variable_ref_counts.most_common()),
        "variable_reference_details": {
            name: {
                "count": count,
                "origin": variable_ref_origins.get(name),
                "examples": variable_ref_examples[name],
            }
            for name, count in variable_ref_counts.most_common()
        },
        "value_references": dict(value_ref_counts.most_common()),
    }


def write_markdown(summary: dict, out: Path) -> None:
    returns = function_return_type_map(summary)
    lines: list[str] = []
    lines.append("# macOS Sandbox SBPL Rule Reference")
    lines.append("")
    lines.append("This reverse-engineered reference is generated from the SBPL profiles shipped in `/System/Library/Sandbox/Profiles`. It is based on observed `allow` and `deny` forms, not on Apple documentation or a full SBPL interpreter, so it is descriptive rather than authoritative: some entries may be higher-order helper functions rather than primitive filters or modifiers, and absence from this corpus does not prove that an operation, filter, modifier, or operation/filter pairing is unsupported.")
    lines.append("")
    lines.append("Source context: [Apple Sandbox Guide v1.0](https://reverse.put.as/wp-content/uploads/2011/09/Apple-Sandbox-Guide-v1.0.pdf), an older public reverse-engineered guide to SBPL.")
    lines.append("")
    lines.append(f"Generated from: {generated_from_label(summary)}.")
    lines.append("")
    lines.append("The old Apple Sandbox Guide describes the basic shape as `(action operation [filter modifiers])`, but the current shipped profiles use a broader Scheme-like SBPL surface syntax. In this corpus, `(with ...)` modifier forms can appear before or after operation names, and rule forms can appear nested inside other expressions.")
    lines.append("")
    lines.append("## Corpus")
    lines.append("")
    lines.append(f"- Source directory: `{summary['source_profile_dir']}`")
    lines.append(f"- Profiles with extracted rules: {summary['profile_count']}")
    lines.append(f"- Extracted `allow`/`deny` forms: {summary['rule_count']}")
    lines.append(f"- Parse errors: {len(summary['parse_errors'])}")
    lines.append("")
    lines.append("## Extraction Model")
    lines.append("")
    lines.append("- A rule is a function invocation: any unquoted list whose first atom is `allow` or `deny`.")
    lines.append("- Operation candidates are the leading bare symbols in rule argument position. The pass seeds operation names from first-position symbols and from symbols matching observed operation families such as `file-*`, `mach-*`, `iokit-*`, `process-*`, `syscall-*`, `system-*`, and similar prefixes.")
    lines.append("- Parenthesized rule arguments are function calls. Direct function-call arguments to `allow`/`deny` are candidates for filter-returning functions, but wrapper/combinator calls are separated from predicate-like calls.")
    lines.append("- Logical combinators such as `require-all`, `require-any`, and `require-not` are recorded as combinator functions. Their child function calls are attributed to the enclosing operation; the combinator itself is not counted as a filter-returning function.")
    lines.append("- Nested calls inside ordinary function arguments are helper functions. For example, in `(path (param \"foo\"))`, `path` is the filter-returning function and `param` is a string-like helper function.")
    lines.append("- Bare non-operation symbols are value references. If lexical scope proves they are bound, they are also listed as dropped variable references.")
    lines.append("- Helper function return types are inferred conservatively from parent context. If a parent head appears elsewhere with direct string literals, a nested helper under that parent is recorded as string-like.")
    lines.append("- Modifiers are parsed as `(with MODIFIER [ARG...])`. Only the first atom after `with` is the modifier name; later forms are modifier arguments.")
    lines.append("- Lexical variables bound by common Scheme forms (`let`, `let*`, `letrec`, `lambda`, function-style `define`/`define-once`, profile-wide `define`/`define-once`, imported top-level definitions, and helper names defined elsewhere in the observed corpus) are excluded from operation and filter-returning function counts.")
    lines.append("- Operation names ending in `*` are treated as glob operations. More-specific operations inherit the glob operation's filter-returning functions and modifiers; inherited entries are pruned from the more-specific operation tables.")
    lines.append("")

    if summary["value_references"]:
        lines.append("## Bare Value References")
        lines.append("")
        lines.append("These unbound bare symbols appear as arguments to `allow`/`deny` or filter-returning functions. They are treated as value references, not operations or filters.")
        lines.append("")
        lines.append("| Reference | Count |")
        lines.append("| --- | ---: |")
        for atom, count in list(summary["value_references"].items())[:100]:
            lines.append(f"| `{atom}` | {count} |")
        lines.append("")

    lines.append("## Modifiers")
    lines.append("")
    lines.append("| Modifier | Occurrences | Observed arguments |")
    lines.append("| --- | ---: | --- |")
    for mod, data in summary["modifiers"].items():
        args = ", ".join(f"`{arg}` ({count})" for arg, count in list(data["arguments"].items())[:6]) or "-"
        lines.append(f"| `{mod}` | {data['count']} | {args} |")
    lines.append("")

    if summary["variable_references"]:
        lines.append("## Dropped Variable References")
        lines.append("")
        lines.append("These bound symbols appeared as arguments where a filter-returning function or operation-like item could otherwise be inferred. They were dropped from the rule matrix because an enclosing lexical form binds them.")
        lines.append("")
        lines.append("| Variable | References |")
        lines.append("| --- | ---: |")
        for variable, count in list(summary["variable_references"].items())[:100]:
            lines.append(f"| `{variable}` | {count} |")
        lines.append("")

        lines.append("## Dropped Variable Reference Details")
        lines.append("")
        lines.append("These examples help distinguish local or profile-defined helper values from primitive-looking filters. The origin column is the lexical binding visible to the extracted rule when one was available.")
        lines.append("")
        lines.append("| Variable | Origin | Example use |")
        lines.append("| --- | --- | --- |")
        for variable, data in list(summary["variable_reference_details"].items())[:100]:
            origin = data.get("origin")
            if origin:
                origin_source = origin["source"].replace("|", "\\|")
                if len(origin_source) > 120:
                    origin_source = origin_source[:117] + "..."
                origin_text = f"`{origin['profile']}:{origin['line']}` `{origin_source}`"
            else:
                origin_text = "-"
            example = data["examples"][0] if data["examples"] else None
            if example:
                example_source = example["source"].replace("|", "\\|")
                if len(example_source) > 120:
                    example_source = example_source[:117] + "..."
                example_text = f"`{example['profile']}:{example['line']}` `{example_source}`"
            else:
                example_text = "-"
            lines.append(f"| `{variable}` | {origin_text} | {example_text} |")
        lines.append("")

    if summary["operation_groups"]:
        lines.append("## Operation Globs")
        lines.append("")
        lines.append("Specific operations are grouped under glob operations when their names share the glob prefix. The operation tables below omit filter-returning functions and modifiers already present on ancestor globs.")
        lines.append("")
        lines.append("| Glob operation | Specific operations |")
        lines.append("| --- | --- |")
        for glob, members in summary["operation_groups"].items():
            lines.append(f"| `{glob}` | " + ", ".join(f"`{member}`" for member in members) + " |")
        lines.append("")

    lines.append("## Filter-Returning Functions")
    lines.append("")
    lines.append("Counts include direct function-call arguments to `allow`/`deny` and child function calls nested under logical combinators. Helper calls inside ordinary function arguments are excluded and reported in the next section.")
    lines.append("")
    lines.append("| Function | Signature | Rules | Calls | Arities | Argument types |")
    lines.append("| --- | --- | ---: | ---: | --- | --- |")
    for filt in sorted(summary["filter_functions"]):
        data = summary["filter_functions"][filt]
        arities = ", ".join(f"{arity}:{count}" for arity, count in data["arities"].items()) or "-"
        args = render_argument_type_summary(resolved_argument_type_counts(data["arguments"], returns), max_positions=4) or "-"
        lines.append(f"| `{filt}` | `{function_signature(filt, data, returns)}` | {data['rule_count']} | {data['occurrence_count']} | {arities} | {args} |")
    lines.append("")

    if summary["combinators"]:
        lines.append("## Combinator Functions")
        lines.append("")
        lines.append("These function calls combine child filter expressions. They are tracked as functions, but are not counted as filter-returning predicates for operations.")
        lines.append("")
        lines.append("| Function | Occurrences |")
        lines.append("| --- | ---: |")
        for combinator, data in summary["combinators"].items():
            lines.append(f"| `{combinator}` | {data['count']} |")
        lines.append("")

    lines.append("## Helper Functions")
    lines.append("")
    lines.append("These are nested calls found inside arguments to filter-returning functions, such as `(param \"HOME\")` inside `(subpath ...)`. They are not attributed to operations as filters.")
    lines.append("")
    lines.append("| Function | Count | Inferred return | Common parents |")
    lines.append("| --- | ---: | --- | --- |")
    for function, data in summary["functions"].items():
        inferred_returns = ", ".join(f"`{name}` ({count})" for name, count in data["inferred_return_types"].items()) or "-"
        parents = ", ".join(f"`{name}`" for name in list(data["parents"])[:8]) or "-"
        lines.append(f"| `{function}` | {data['count']} | {inferred_returns} | {parents} |")
    lines.append("")

    lines.append("## String-Like Contexts")
    lines.append("")
    lines.append("A head appears here when it has direct string or regex-string literals in the corpus. Nested helper calls under these heads are evidence that the helper returns a string-like value.")
    lines.append("")
    lines.append("| Head | Literal-bearing forms |")
    lines.append("| --- | ---: |")
    for head, count in summary["string_accepting_heads"].items():
        lines.append(f"| `{head}` | {count} |")
    lines.append("")

    lines.append("## Filter Function Details")
    lines.append("")
    for function, data in summary["filter_functions"].items():
        lines.append(f"### `{function}`")
        lines.append("")
        lines.append(f"- Rule count: {data['rule_count']}")
        lines.append(f"- Call occurrences: {data['occurrence_count']}")
        if data["arities"]:
            lines.append("- Observed arities: " + ", ".join(f"`{k}` ({v})" for k, v in data["arities"].items()))
        if data["arguments"]:
            lines.append("- Observed argument types: " + render_argument_type_summary(resolved_argument_type_counts(data["arguments"], returns), max_positions=12))
        lines.append("- Examples:")
        for example in data["examples"][:3]:
            source = example["source"].replace("|", "\\|")
            if len(source) > 180:
                source = source[:177] + "..."
            lines.append(f"  - `{example['profile']}:{example['line']}` `{source}`")
        lines.append("")

    lines.append("## Operations")
    lines.append("")
    lines.append("| Operation | Count | Actions | Filter-returning functions | Modifiers |")
    lines.append("| --- | ---: | --- | --- | --- |")
    for op, data in summary["operations"].items():
        actions = ", ".join(f"{k}:{v}" for k, v in sorted(data["actions"].items()))
        specific = summary["operation_specific"][op]
        filters = ", ".join(f"`{name}`" for name in list(specific["filters"])[:12]) or "-"
        modifiers = ", ".join(f"`{name}`" for name in list(specific["modifiers"])[:8]) or "-"
        lines.append(f"| `{op}` | {data['count']} | {actions} | {filters} | {modifiers} |")
    lines.append("")

    lines.append("## Operation Details")
    lines.append("")
    for op, data in summary["operations"].items():
        specific = summary["operation_specific"][op]
        lines.append(f"### `{op}`")
        lines.append("")
        lines.append(f"- Occurrences: {data['count']}")
        lines.append("- Actions: " + ", ".join(f"`{k}` ({v})" for k, v in sorted(data["actions"].items())))
        if specific["glob_ancestors"]:
            lines.append("- Glob ancestors: " + ", ".join(f"`{name}`" for name in specific["glob_ancestors"]))
        if specific["filters"]:
            lines.append("- Specific filter-returning functions: " + ", ".join(f"`{k}` ({v})" for k, v in list(specific["filters"].items())[:30]))
        else:
            lines.append("- Specific filter-returning functions: none")
        if specific["inherited_filter_functions"]:
            lines.append("- Inherited/pruned filter-returning functions: " + ", ".join(f"`{name}`" for name in specific["inherited_filter_functions"]))
        if specific["modifiers"]:
            lines.append("- Specific modifiers: " + ", ".join(f"`{k}` ({v})" for k, v in specific["modifiers"].items()))
        else:
            lines.append("- Specific modifiers: none")
        if specific["inherited_modifiers"]:
            lines.append("- Inherited/pruned modifiers: " + ", ".join(f"`{name}`" for name in specific["inherited_modifiers"]))
        lines.append("- Examples:")
        for example in data["examples"][:3]:
            source = example["source"].replace("|", "\\|")
            if len(source) > 220:
                source = source[:217] + "..."
            lines.append(f"  - `{example['profile']}:{example['line']}` `{source}`")
        lines.append("")

    lines.append("## Modifier Details")
    lines.append("")
    for mod, data in summary["modifiers"].items():
        lines.append(f"### `{mod}`")
        lines.append("")
        lines.append(f"- Occurrences: {data['count']}")
        if data["arguments"]:
            lines.append("- Observed arguments: " + ", ".join(f"`{k}` ({v})" for k, v in data["arguments"].items()))
        else:
            lines.append("- Observed arguments: none")
        lines.append("- Examples:")
        for example in data["examples"][:3]:
            source = example["source"].replace("|", "\\|")
            if len(source) > 180:
                source = source[:177] + "..."
            lines.append(f"  - `{example['profile']}:{example['line']}` `{source}`")
        lines.append("")

    lines.append("## Function Details")
    lines.append("")
    for function, data in summary["functions"].items():
        lines.append(f"### `{function}`")
        lines.append("")
        lines.append(f"- Occurrences: {data['count']}")
        if data["inferred_return_types"]:
            lines.append("- Inferred returns: " + ", ".join(f"`{k}` ({v})" for k, v in data["inferred_return_types"].items()))
        else:
            lines.append("- Inferred returns: unknown")
        lines.append("- Observed parents: " + ", ".join(f"`{k}` ({v})" for k, v in list(data["parents"].items())[:30]))
        if data["argument_summary"]["arities"]:
            lines.append("- Observed arities: " + ", ".join(f"`{k}` ({v})" for k, v in data["argument_summary"]["arities"].items()))
        if data["argument_summary"]["arguments"]:
            lines.append("- Observed argument types: " + render_argument_type_summary(data["argument_summary"]["arguments"], max_positions=12))
        if data["return_type_examples"]:
            lines.append("- Return inference examples:")
            for example in data["return_type_examples"][:3]:
                source = example["source"].replace("|", "\\|")
                if len(source) > 180:
                    source = source[:177] + "..."
                lines.append(f"  - `{example['profile']}:{example['line']}` under `{example['parent']}`: `{source}`")
        lines.append("- Examples:")
        for example in data["examples"][:3]:
            source = example["source"].replace("|", "\\|")
            if len(source) > 180:
                source = source[:177] + "..."
            lines.append(f"  - `{example['profile']}:{example['line']}` under `{example['parent']}`: `{source}`")
        lines.append("")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_operation_reference(summary: dict, out: Path, template: Path) -> None:
    rendered = render_template(template, operation_reference_context(summary))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered.rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, default=PROFILE_DIR)
    parser.add_argument("--out-dir", type=Path, default=SANDBOX_DIR / "generated")
    parser.add_argument("--operation-template", type=Path, default=DEFAULT_OPERATION_TEMPLATE)
    args = parser.parse_args()

    rules, with_filter_predicates, errors = load_rules(args.profiles)
    summary = summarize(rules, with_filter_predicates, errors)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "rules.json").write_text(json.dumps(rules, indent=2, sort_keys=True), encoding="utf-8")
    (args.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(summary, args.out_dir / "sandbox-sbpl-reference.md")
    write_operation_reference(summary, args.out_dir / "operation-reference.md", args.operation_template)
    print(f"profiles={summary['profile_count']} rules={summary['rule_count']} operations={len(summary['operations'])} filter_functions={len(summary['filters'])} combinators={len(summary['combinators'])} helper_functions={len(summary['functions'])} modifiers={len(summary['modifiers'])} variables={len(summary['variable_references'])} errors={len(errors)}")


if __name__ == "__main__":
    main()
