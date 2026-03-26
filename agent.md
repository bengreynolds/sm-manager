# Agent Contract

This file defines how work in this repository should be executed.

## Mission

Build a low-resource, local-first social media automation manager with:

- one shared control plane
- per-platform adapters
- web UI plus headless mode
- secure secret handling
- predictable automation and auditability

## Mandatory Reading Order

For every task:

1. read this file
2. read the relevant platform `planning.md`
3. only then make or modify implementation decisions

## Platform Scope Rule

Instagram is the only platform that may be actively implemented until the user explicitly authorizes the next platform.

Facebook, TikTok, and X remain roadmap-only.

## Engineering Rules

- prefer official APIs over scraping, browser automation, or credential-driven login flows
- do not store usernames, passwords, tokens, or session cookies in plain text files committed to the repo
- design for low memory, low CPU, and local execution first
- keep the system runnable with a single local process whenever practical
- every automation path must support `enabled`, `disabled`, and `dry_run`
- every posting workflow must be idempotent and leave an audit trail
- every account must have independent settings, schedules, and safety switches
- every media asset must carry source metadata, rights status, and dedupe hashes

## Safety Rules

- do not implement unrestricted scraping-and-repost behavior as the default path
- treat attribution as insufficient proof of reuse rights
- prefer owned, licensed, or explicitly approved source content
- if a requested platform behavior conflicts with official API capabilities, document the limitation and propose the safest fallback

## Secret Handling Rules

- prefer OAuth or platform access tokens over raw passwords
- prefer OS keychain-backed storage where possible
- if a portable encrypted vault is required, encrypt at rest and keep the master key outside the repo
- never log secrets

## Delivery Rules

- preserve clear separation between shared core logic and platform-specific behavior
- keep platform directories self-contained
- update the relevant `planning.md` when a major implementation decision changes
- do not start the next platform without explicit user approval
