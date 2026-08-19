# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

First release. Six commands, no dependencies.

### Added

- `subnet` - CIDR description, splitting, membership tests and summarisation,
  with correct `/31` (RFC 3021 point-to-point) and `/32` host counts
- `scan` - threaded TCP port sweep over a host or a whole CIDR block, with
  flexible port specs (`22`, `22,80`, `1-1024`) and service annotation
- `latency` - TCP connect timing with min/avg/p95/max, packet loss and jitter
- `dns` - forward, reverse and round-trip resolution through `getaddrinfo`
- `http` - endpoint health with hop-by-hop redirect chain walking
- `mac` - MAC normalisation across notations, OUI vendor lookup, and decoding
  of the locally-administered and multicast flag bits
- Global `--json` flag on every command
- Optional `netprobe.ini` for per-command defaults, applied as argparse
  defaults so explicit flags always win
- 84 tests and a CI matrix over ubuntu/windows/macos on Python 3.9 and 3.12

[Unreleased]: https://github.com/saeed205/netprobe-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saeed205/netprobe-cli/releases/tag/v0.1.0
