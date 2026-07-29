#!/usr/bin/env python3
"""Synchronize and validate rule snapshots declared in sources.yaml."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "sources.yaml"
RULES_ROOT = ROOT / "rules"
CHECKSUMS_PATH = ROOT / "checksums.sha256"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class SyncError(RuntimeError):
    """Raised when a synchronization safety check fails."""


def run(command: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    print(f"+ {shlex.join(command)}", flush=True)
    return subprocess.run(
        command,
        check=True,
        input=input_text,
        text=True,
    )


def capture(command: list[str]) -> str:
    print(f"+ {shlex.join(command)}", flush=True)
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def clean_relative_path(value: object, *, label: str) -> PurePosixPath:
    if not isinstance(value, str) or not value:
        raise SyncError(f"{label} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise SyncError(f"{label} must be a safe relative path: {value!r}")
    return path


def load_manifest() -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    try:
        document = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SyncError(f"cannot read {MANIFEST_PATH}: {exc}") from exc

    if not isinstance(document, dict) or document.get("version") != 1:
        raise SyncError("sources.yaml must be a version 1 mapping")

    sources = document.get("sources")
    rules = document.get("rules")
    if not isinstance(sources, dict) or not sources:
        raise SyncError("sources.yaml must define at least one source")
    if not isinstance(rules, list) or not rules:
        raise SyncError("sources.yaml must define at least one rule")

    normalized_sources: dict[str, dict[str, str]] = {}
    for source_id, metadata in sources.items():
        if not isinstance(source_id, str) or not isinstance(metadata, dict):
            raise SyncError("every source must be a named mapping")
        repository = metadata.get("repository")
        ref = metadata.get("ref")
        license_id = metadata.get("license")
        if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
            raise SyncError(f"invalid GitHub repository for {source_id}: {repository!r}")
        if not isinstance(ref, str) or not ref:
            raise SyncError(f"invalid ref for {source_id}: {ref!r}")
        if not isinstance(license_id, str) or not license_id:
            raise SyncError(f"invalid license identifier for {source_id}")
        normalized_sources[source_id] = {
            "repository": repository,
            "ref": ref,
            "license": license_id,
        }

    normalized_rules: list[dict[str, str]] = []
    provider_targets: dict[str, str] = {}
    target_providers: dict[str, str] = {}
    source_inputs: set[tuple[str, str, str]] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise SyncError(f"rule {index} must be a mapping")
        required = ("provider", "client", "format", "source", "upstream_path", "target_path")
        if any(not isinstance(rule.get(key), str) or not rule[key] for key in required):
            raise SyncError(f"rule {index} is missing a required string field")

        provider = rule["provider"]
        client = rule["client"]
        source_id = rule["source"]
        if source_id not in normalized_sources:
            raise SyncError(f"{provider} references unknown source {source_id!r}")
        if rule["format"] != "clash-classical":
            raise SyncError(f"{provider} has unsupported format {rule['format']!r}")

        upstream_path = clean_relative_path(
            rule["upstream_path"], label=f"{provider} upstream_path"
        )
        target_path = clean_relative_path(
            rule["target_path"], label=f"{provider} target_path"
        )
        if target_path.parts[:2] != ("rules", client):
            raise SyncError(
                f"{provider} target_path must start with rules/{client}/"
            )
        if target_path.suffix not in {".yaml", ".yml"}:
            raise SyncError(f"{provider} target must be a YAML file")
        target = target_path.as_posix()
        prior_target = provider_targets.setdefault(provider, target)
        if prior_target != target:
            raise SyncError(
                f"provider {provider!r} maps to both {prior_target!r} and {target!r}"
            )
        prior_provider = target_providers.setdefault(target, provider)
        if prior_provider != provider:
            raise SyncError(
                f"target {target!r} maps to both {prior_provider!r} and {provider!r}"
            )
        source_input = (provider, source_id, upstream_path.as_posix())
        if source_input in source_inputs:
            raise SyncError(
                f"duplicate source input for {provider}: "
                f"{source_id}/{upstream_path.as_posix()}"
            )
        source_inputs.add(source_input)
        transform = rule.get("transform")
        if transform not in (None, "shadowrocket-list-to-clash-classical"):
            raise SyncError(f"{provider} has unsupported transform {transform!r}")

        normalized_rules.append({key: rule[key] for key in required})
        normalized_rules[-1]["upstream_path"] = upstream_path.as_posix()
        normalized_rules[-1]["target_path"] = target_path.as_posix()
        normalized_rules[-1]["transform"] = transform

    return normalized_sources, normalized_rules


def validate_clash_rule(path: Path, provider: str) -> None:
    read_clash_payload(path, provider)


def read_clash_payload(path: Path, provider: str) -> list[str]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise SyncError(f"{provider}: invalid YAML in {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise SyncError(f"{provider}: rule file must contain a YAML mapping")
    payload = document.get("payload")
    if not isinstance(payload, list) or not payload:
        raise SyncError(f"{provider}: payload must be a non-empty list")
    for index, item in enumerate(payload):
        if not isinstance(item, str) or not item.strip():
            raise SyncError(
                f"{provider}: payload item {index} must be a non-empty string"
            )
    return payload


def normalize_clash_rule(item: str, *, provider: str) -> str:
    rule_type, separator, argument = item.strip().partition(",")
    rule_type = rule_type.strip()
    argument = argument.strip()
    if not separator or not rule_type or not argument:
        raise SyncError(f"{provider}: malformed classical rule {item!r}")

    if rule_type in {"IP-CIDR", "IP-CIDR6"}:
        address, option_separator, options = argument.partition(",")
        address = address.strip()
        expected_version = 4 if rule_type == "IP-CIDR" else 6
        try:
            if "/" in address:
                parsed_version = ipaddress.ip_network(address, strict=False).version
            else:
                parsed_version = ipaddress.ip_address(address).version
                address = f"{address}/{'32' if expected_version == 4 else '128'}"
        except ValueError as exc:
            raise SyncError(f"{provider}: invalid IP rule {item!r}") from exc
        if parsed_version != expected_version:
            raise SyncError(f"{provider}: wrong address family in {item!r}")
        argument = address
        if option_separator:
            argument += f",{options.strip()}"

    return f"{rule_type},{argument}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_shadowrocket_payload(
    source: Path,
    *,
    upstream_path: str,
    provider: str,
) -> list[str]:
    try:
        text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise SyncError(f"{provider}: cannot read Shadowrocket list: {exc}") from exc

    payload: list[str] = []
    for line_number, original_line in enumerate(text.splitlines(), start=1):
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        elif re.fullmatch(r"[A-Z][A-Z0-9-]*,.+", line):
            payload.append(line)
        else:
            raise SyncError(
                f"{provider}: unsupported line {line_number} in {upstream_path}: "
                f"{original_line!r}"
            )

    if not payload:
        raise SyncError(f"{provider}: Shadowrocket list contains no rules")
    return payload


def grouped_rules(
    rules: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for rule in rules:
        groups.setdefault(rule["target_path"], []).append(rule)
    return groups


def checksum_document(rules: list[dict[str, str]], base: Path = ROOT) -> str:
    lines = [
        f"{sha256(base / target)}  {target}"
        for target in sorted(grouped_rules(rules))
    ]
    return "\n".join(lines) + "\n"


def validate_tree(rules: list[dict[str, str]], base: Path = ROOT) -> None:
    groups = grouped_rules(rules)
    expected = set(groups)
    clients = {rule["client"] for rule in rules}
    actual: set[str] = set()
    for client in clients:
        client_dir = base / "rules" / client
        if not client_dir.is_dir():
            raise SyncError(f"missing managed rule directory: {client_dir}")
        actual.update(
            path.relative_to(base).as_posix()
            for path in client_dir.rglob("*")
            if path.is_file()
        )
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SyncError(f"managed rule set mismatch; missing={missing}, extra={extra}")

    for target, inputs in groups.items():
        validate_clash_rule(base / target, inputs[0]["provider"])


def write_if_changed(path: Path, content: str) -> bool:
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)
    return True


def clone_sources(
    sources: dict[str, dict[str, str]],
    rules: list[dict[str, str]],
    workspace: Path,
) -> dict[str, Path]:
    checkouts: dict[str, Path] = {}
    for source_id, metadata in sources.items():
        source_rules = [rule for rule in rules if rule["source"] == source_id]
        if not source_rules:
            raise SyncError(f"source {source_id!r} is not used by any rule")
        checkout = workspace / source_id
        run(
            [
                "gh",
                "repo",
                "clone",
                metadata["repository"],
                str(checkout),
                "--",
                "--depth=1",
                "--filter=blob:none",
                "--sparse",
                "--branch",
                metadata["ref"],
            ]
        )
        sparse_paths = "\n".join(
            sorted({rule["upstream_path"] for rule in source_rules})
        )
        run(
            [
                "git",
                "-C",
                str(checkout),
                "sparse-checkout",
                "set",
                "--no-cone",
                "--stdin",
            ],
            input_text=f"{sparse_paths}\n",
        )
        commit = capture(["git", "-C", str(checkout), "rev-parse", "HEAD"])
        print(
            f"Source {metadata['repository']}@{metadata['ref']}: {commit}",
            flush=True,
        )
        checkouts[source_id] = checkout
    return checkouts


def build_aggregate(
    sources: dict[str, dict[str, str]],
    inputs: list[dict[str, str]],
    checkouts: dict[str, Path],
    target: Path,
) -> tuple[int, int]:
    provider = inputs[0]["provider"]
    output = [
        "# Generated aggregate rule provider. Do not edit manually.",
        f"# Provider: {provider}",
        "payload:",
    ]
    seen: set[str] = set()
    input_count = 0

    for rule in inputs:
        source = checkouts[rule["source"]] / rule["upstream_path"]
        if not source.is_file() or source.is_symlink():
            raise SyncError(
                f"{provider}: upstream file is missing or not regular: {source}"
            )

        metadata = sources[rule["source"]]
        if rule["transform"] == "shadowrocket-list-to-clash-classical":
            payload = read_shadowrocket_payload(
                source,
                upstream_path=rule["upstream_path"],
                provider=provider,
            )
        else:
            payload = read_clash_payload(source, provider)

        output.append("")
        output.append(
            "  # Source: "
            f"https://github.com/{metadata['repository']}/blob/"
            f"{metadata['ref']}/{rule['upstream_path']}"
        )
        input_count += len(payload)
        for item in payload:
            item = normalize_clash_rule(item, provider=provider)
            if item in seen:
                continue
            seen.add(item)
            output.append(f"  - {json.dumps(item, ensure_ascii=False)}")

    if not seen:
        raise SyncError(f"{provider}: aggregate contains no rules")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    validate_clash_rule(target, provider)
    return input_count, len(seen)


def staged_tree(
    sources: dict[str, dict[str, str]],
    rules: list[dict[str, str]],
    stage: Path,
) -> None:
    clone_root = stage / "upstreams"
    clone_root.mkdir()
    checkouts = clone_sources(sources, rules, clone_root)

    for target_path, inputs in grouped_rules(rules).items():
        target = stage / "snapshot" / target_path
        input_count, unique_count = build_aggregate(
            sources,
            inputs,
            checkouts,
            target,
        )
        print(
            f"Built {inputs[0]['provider']}: {unique_count} unique rules from "
            f"{len(inputs)} sources ({input_count - unique_count} duplicates removed)",
            flush=True,
        )

    validate_tree(rules, stage / "snapshot")


def trees_match(rules: list[dict[str, str]], staged: Path) -> bool:
    try:
        validate_tree(rules, ROOT)
    except SyncError:
        return False
    return all(
        (ROOT / target).read_bytes() == (staged / target).read_bytes()
        for target in grouped_rules(rules)
    )


def replace_clients(rules: list[dict[str, str]], staged: Path) -> None:
    clients = sorted({rule["client"] for rule in rules})
    RULES_ROOT.mkdir(exist_ok=True)
    swapped: list[tuple[Path, Path | None]] = []
    try:
        for client in clients:
            current = RULES_ROOT / client
            incoming = staged / "rules" / client
            backup = RULES_ROOT / f".{client}-backup-{uuid.uuid4().hex}"
            prior: Path | None = None
            if current.exists():
                current.rename(backup)
                prior = backup
            try:
                incoming.rename(current)
            except Exception:
                if prior is not None and prior.exists():
                    prior.rename(current)
                raise
            swapped.append((current, prior))
    except Exception:
        for current, backup in reversed(swapped):
            if current.exists():
                shutil.rmtree(current)
            if backup is not None and backup.exists():
                backup.rename(current)
        raise
    else:
        for _, backup in swapped:
            if backup is not None:
                shutil.rmtree(backup)


def synchronize(
    sources: dict[str, dict[str, str]], rules: list[dict[str, str]]
) -> None:
    if shutil.which("gh") is None or shutil.which("git") is None:
        raise SyncError("gh and git must both be available")

    with tempfile.TemporaryDirectory(prefix=".sync-stage-", dir=ROOT) as stage_name:
        stage = Path(stage_name)
        staged_tree(sources, rules, stage)
        snapshot = stage / "snapshot"
        checksums = checksum_document(rules, snapshot)

        if trees_match(rules, snapshot):
            checksum_changed = write_if_changed(CHECKSUMS_PATH, checksums)
            print(
                "Rule snapshots are unchanged"
                + ("; checksums refreshed" if checksum_changed else ""),
                flush=True,
            )
            return

        replace_clients(rules, snapshot)
        write_if_changed(CHECKSUMS_PATH, checksums)
        validate_tree(rules, ROOT)
        print(f"Updated {len(grouped_rules(rules))} rule snapshots", flush=True)


def validate_repository(rules: list[dict[str, str]]) -> None:
    validate_tree(rules, ROOT)
    expected_checksums = checksum_document(rules)
    try:
        actual_checksums = CHECKSUMS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        raise SyncError(f"cannot read {CHECKSUMS_PATH}: {exc}") from exc
    if actual_checksums != expected_checksums:
        raise SyncError("checksums.sha256 does not match the managed rule files")
    print(f"Validated {len(grouped_rules(rules))} managed rule files", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("sync", "validate"))
    args = parser.parse_args()

    try:
        sources, rules = load_manifest()
        if args.command == "sync":
            synchronize(sources, rules)
        else:
            validate_repository(rules)
    except (SyncError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
