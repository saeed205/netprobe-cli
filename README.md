# netprobe-cli

[![CI](https://github.com/saeed205/netprobe-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/saeed205/netprobe-cli/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small CLI toolkit for everyday network diagnostics: subnet math, port sweeps,
latency statistics, DNS checks, HTTP health and MAC vendor lookup.

**Zero dependencies.** Everything runs on the Python standard library. No
transitive dependency tree just to work out how many hosts fit in a /27.

## Install

```bash
pip install .
```

Or run it straight from a checkout without installing:

```bash
python -m netprobe subnet 10.0.0.0/24
```

## Commands

### `subnet` - CIDR math

```console
$ netprobe subnet 10.20.30.0/26
network         : 10.20.30.0
prefix          : 26
netmask         : 255.255.255.192
wildcard        : 0.0.0.63
broadcast       : 10.20.30.63
total_addresses : 64
usable_hosts    : 62
first_host      : 10.20.30.1
last_host       : 10.20.30.62
version         : 4
is_private      : yes
```

Split a block, or test membership via the exit status:

```bash
netprobe subnet 10.0.0.0/24 --split-into 26
netprobe subnet 10.0.0.0/8 --contains 10.4.5.6 && echo "inside"
```

The `/31` and `/32` cases are handled properly: a `/31` is a two-host
point-to-point link under RFC 3021 and a `/32` is a single host route, so
neither reserves a broadcast address.

### `scan` - TCP port sweep

```bash
netprobe scan 10.0.0.5                      # 20 common ports
netprobe scan 10.0.0.5 -p 22,80,8000-8010
netprobe scan 10.0.0.0/28 -p 22 -w 128      # a whole subnet
```

### `latency` - connect time, loss and jitter

```console
$ netprobe latency example.com -p 443 -c 10
target    : example.com:443
sent      : 10
received  : 10
loss_pct  : 0.0
min_ms    : 18.44
avg_ms    : 21.07
p95_ms    : 27.31
max_ms    : 28.02
jitter_ms : 3.19
```

TCP handshakes, not ICMP - no root needed, and it is rarely filtered. The
**p95** is the number to watch; an average hides the tail users complain about.

### `dns` - forward, reverse and round-trip

```bash
netprobe dns example.com -f v4
netprobe dns 8.8.8.8 -x           # PTR
netprobe dns example.com -r       # resolve, then PTR back
```

Resolution goes through `getaddrinfo`, so it reflects what applications on the
host actually see - `/etc/hosts` and nsswitch included.

### `http` - endpoint health and redirect chains

```bash
netprobe http example.com
netprobe http example.com -L      # walk every redirect hop
netprobe http internal.lan -k     # skip TLS verification
```

### `mac` - normalise and identify

```console
$ netprobe mac 000c.29ab.cdef
mac                  : 00:0c:29:ab:cd:ef
oui                  : 000C29
vendor               : VMware, Inc.
locally_administered : no
multicast            : no
note                 : -
cisco                : 000c.29ab.cdef
```

Accepts colon, hyphen, Cisco dotted or bare hex. A locally administered
address (randomised phone MACs, most virtual NICs) is called out as such
rather than reported as an unhelpful `unknown` vendor.

## JSON output

Every command takes the global `--json` flag:

```bash
netprobe --json scan 10.0.0.0/28 -p 22 | jq -r '.[].host'
```

Single-result commands emit a JSON object, list commands emit an array - so
you never have to index `[0]` to reach a scalar result.

## Config file

Defaults can live in `netprobe.ini` instead of being retyped:

```ini
[defaults]
json = false

[scan]
timeout = 0.4
workers = 128
```

Search order: `$NETPROBE_CONFIG`, then `./netprobe.ini`, then the platform
config directory. Anything passed on the command line still wins. See
[`netprobe.ini.example`](netprobe.ini.example).

## Exit status

| code | meaning |
|---|---|
| `0` | success, or the tested condition held |
| `1` | the check failed - nothing resolved, nothing open, endpoint unhealthy |
| `2` | usage error |
| `130` | interrupted |

That makes the commands usable directly in monitoring checks and shell
conditionals.

## Development

```bash
python -m unittest discover -s tests -v
python -m ruff check .
```

84 tests, no test dependencies to install. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT - see [LICENSE](LICENSE).
