# Story 28.3: A Mod Can Be Installed from an HTTPS Link

Status: done

<!-- Implements FR360 to FR362, Epic 28 ADR-1 decision 4 and ADR-5. Bead: VSS-guzf.2 (API-101), closes with this story after merge. Branch story/28-3-a-mod-can-be-installed-from-an-https-link, stacked on story/28-2-a-mod-can-be-installed-by-uploading-its-file (PR #236); the PR targets main and merges after 28.2's. API only. -->

## Story

As an **administrator**,
I want **to give the server a link to a mod's file**,
so that **I can install a mod published on GitHub, Forgejo or S3 without downloading it first**.

## Acceptance Criteria

1. **Given** an Admin key and an `https` link to a mod zip
   **When** `POST /mods/install-from-url` runs with `{url}`
   **Then** the file is downloaded and installed with source `url` and `source_url` the link without its query string, fragment or user info
   *(FR360; ADR-1 decision 4, ADR-5)*

2. **Given** a link or a redirect that is not `https` (without `VS_DEBUG`), more than 5 redirects, or a link with a user name or password
   **Then** 422 `MOD_URL_INVALID`
   *(FR360)*

3. **Given** a host that resolves to a private, loopback, link-local, multicast, reserved or unspecified address, on the first request or after a redirect
   **Then** 422 `MOD_URL_BLOCKED` and no connection is made to it
   **Given** the host is in `VS_MOD_URL_PRIVATE_HOSTS` **Then** a private address is allowed, and loopback, link-local and unspecified stay blocked
   *(FR361)*

4. **Given** a download over the size limit, slower than the limits, or a non-2xx answer
   **Then** 413 `MOD_FILE_TOO_LARGE` or 502 `DOWNLOAD_FAILED`, and nothing is left behind
   *(FR362)*

5. **Given** the file **Then** its name comes from `Content-Disposition`, else the URL path, else `{modid}_{version}.zip`, and it is checked and installed (with `replace`) as Story 28.2's ACs 3 to 6
   *(ADR-4, ADR-5)*

6. Proxies from the environment are not used.

7. **(Quality gates.)** `just check` green; README documents the link install and `VS_MOD_URL_PRIVATE_HOSTS`.

## Tasks / Subtasks

- [x] Task 1: The guarded transport (AC: 3, 6)
  - [x] 1.1: `services/safe_fetch.py`: `address_refusal`, `GuardedBackend` (resolve, check every answer, connect to the checked address), `GuardedTransport` (httpcore pool over it, no proxy, httpcore errors mapped to httpx's)
- [x] Task 2: The link install (AC: 1, 2, 4, 5)
  - [x] 2.1: `services/mod_link.py`: `check_link`, `stored_link`, names, `downloaded` (redirects followed one by one, limits, working folder)
  - [x] 2.2: `POST /mods/install-from-url`; `VS_MOD_URL_PRIVATE_HOSTS`; codes `MOD_URL_INVALID`, `MOD_URL_BLOCKED`; `get_link_transport` for tests
  - [x] 2.3: Tests (`test_mod_link.py`); a live check of TLS through the guard (below)
  - [x] 2.4: Commit `feat(story-28.3/task-2): install a mod from an HTTPS link`
- [x] Task 3: README and `.env.example` (AC: 7)
- [x] Task 4: Validate and move the story to review (AC: 7)

## Dev Notes

### The code today (verified at the tip of 28.2)

- `httpcore.AsyncConnectionPool(network_backend=...)` is public; `httpx.AsyncHTTPTransport` does not take a backend, so `GuardedTransport` maps httpx requests onto an httpcore pool itself.
- httpcore opens TLS with `server_hostname` from the request's origin, not from the address passed to `connect_tcp`, so connecting to the checked IP keeps certificate checks on the host name.
- The tests run with `VS_DEBUG=true` (conftest), so the route tests build `Settings(debug=False)` to check the https-only rule as deployed.

### References

- `epics.md` "Story 28.3"; `architecture/epic-28-mods-from-outside-the-mod-database.md` ADR-5

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (claude-opus-5-5).

### Debug Log References

- `just check` (2026-11-27): exit 0; API 4348 passed, web 3986 passed; Pyright 0/0; lints green.
- Live check (2026-11-27): `GuardedTransport` fetched `https://example.com/` and `https://github.com/` (200, HTTP/1.1, reason phrase read), so TLS by host name works when connecting to the checked address.

### Implementation decisions

- **A host is refused when any of its answers is refused**, not only the one connected to, so a name that answers with a public and a private address cannot be used to reach the private one.
- **Carrier-grade NAT (100.64/10) and unique local IPv6 count as private**: allowed only for a listed host.
- **Redirects are followed by the manager, not httpx**, so each hop's scheme is checked; the address check is in the transport, so it covers every hop anyway.
- **The 300-second limit covers the whole download** (`anyio.fail_after`), on top of httpx's connect (10 s) and read (30 s) timeouts.
- **An unnamed download is named after reading its `modinfo.json`** (`{modid}_{version}.zip`, unusual characters replaced); a file without one is refused by the install as an upload is.
- **Log lines show the link without its query string** (`_loggable_link`), as the stored form does.
- **The download runs in the request**, like a mod database install (ADR-5 decision 1).

### Completion Notes List

- 2026-11-27 (dev-story): Tasks 1 to 4 done. 54 new API tests in `test_mod_link.py`: address classes, the backend (connects to the checked address; split answers; listed hosts; IPv4-mapped loopback; resolver failure), a redirect from a public host to the metadata address refused per connection, a download through the guard, the real transport refusing `127.0.0.1` and `localhost`, link rules, the stored link, names, and the route's answers (GitHub release with a CDN redirect, presigned signature not stored, modinfo naming, http and credentials refused, http redirect, six redirects, error answers, timeouts, both size limits, not a mod, 409 then replace, Monitor 403), and `HTTPS_PROXY` ignored.
- 2026-11-27 (create-story): created from Epic 28's Story 28.3 and ADR-5.

### File List

- `api/src/vintagestory_api/services/safe_fetch.py` (new), `services/mod_link.py` (new), `services/mod_upload.py` (`incoming_folder`), `routers/mods.py`, `config.py`, `models/errors.py`; `api/tests/test_mod_link.py` (new)
- `README.md`, `.env.example`
- this file; `sprint-status.yaml` (through `just sprint set`)

## Review

Reviewer: GLM-5.3-Flash via opencode (read-only, 2026-11-27). Verdict: approve with changes. 0 HIGH, 1 MEDIUM, 5 LOW; all six fixed. The reviewer probed DNS rebinding, numeric and IPv6 host forms, redirects, pooled-connection reuse across hosts, TLS by host name when connecting by IP, proxies, HTTP/2 and the unix-socket path, and found no way past the address check.

1. **MEDIUM: a refused link was logged with its user name and password** (`_loggable_link` dropped only the query and fragment). It now drops user info too, and an unparsable link logs as `<unparsable link>`. Test (checked to fail without the fix).
2. **LOW: any 3xx was followed** (`is_redirect`), so a 304 read as "a redirect without a location". Only 301, 302, 303, 307 and 308 are followed (`has_redirect_location`); a 304 is an error answer naming its status. Test.
3. **LOW: no test at exactly five redirects.** Added (followed, six requests).
4. **LOW: no test for credentials in a redirect.** Added (422, one request).
5. **LOW: NAT64, 6to4 and Teredo forms not pinned.** `64:ff9b::7f00:1` (reserved), `2002:7f00:1::` and `2001::7f00:1` (private) added to the address tests.
6. **LOW: a mod whose ID and version give no usable name was stored as `download.zip`.** It gets `mod_<random>.zip`.

After the fixes `just check` exit 0: API 4355 passed, web 3986 passed.

## Change Log

- 2026-11-27: Story 28.3 created (create-story).
- 2026-11-27: Story 28.3 implemented (dev-story): Tasks 1 to 4; status review.
- 2026-11-27: Code review (GLM-5.3-Flash via opencode): approve with changes; 0 HIGH, 1 MEDIUM, 5 LOW; all fixed (see "Review"). Status done.
