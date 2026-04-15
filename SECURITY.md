# Security policy

## Reporting a vulnerability

If you believe you have found a security vulnerability in mcptest, **please do
not open a public issue**. Instead:

1. Use GitHub's private vulnerability reporting:
   <https://github.com/jacquesbagui/mcptest/security/advisories/new>
2. Or email the maintainer directly: **jacques.bagui@gmail.com** with a
   subject line starting with `[mcptest security]`.

Include, to the extent possible:

- A description of the vulnerability and its impact.
- Steps to reproduce (a minimal contract or code sample is ideal).
- The affected package(s) and version(s).
- Any suggested mitigation.

You should receive an acknowledgment within **5 business days**. If you do not,
please follow up — the maintainer may have missed the first message.

## Supported versions

mcptest is pre-1.0. Only the latest released versions of `mcptest` (PyPI) and
`mcptest` (npm) receive security fixes. Once 1.0 ships, this section will be
updated with a formal support matrix.

## Scope

In scope:

- The Python package `mcptest` (CLI + core).
- The Node.js package `mcptest` (SDK).
- The contents of this repository, including CI workflows.

Out of scope:

- Third-party MCP servers tested *with* mcptest — report those upstream.
- Denial of service caused by a user's own contract against their own server.

## Disclosure

We aim to publish a coordinated fix and advisory within **30 days** of a
confirmed report, sooner when feasible. Credit is given in the advisory unless
you prefer otherwise.
