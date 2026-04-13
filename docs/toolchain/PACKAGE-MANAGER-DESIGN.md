Below is a **design-locking v1 specification** for the Aster package manager and registry, updated to incorporate your changes.

I have treated the following as **locked requirements** for v1:

* `authors` is a **list of author records**
* each author record must contain **`name`**
* all other author fields are optional
* `authors` must contain **at least one** author record
* `supported_platforms` is a **list**
* allowed platform values are exactly: **`linux`**, **`mac`**, **`win`**

I also tightened several areas that were still exploratory in the earlier draft so this can serve as a real implementation spec.

---

# Aster Package Manager and Registry Specification v1

## 1. Document Control

**Document Title:** Aster Package Manager and Registry Specification
**Version:** 1.0.0
**Status:** Design-Locking
**Applies To:** Aster package manager client, package format, registry catalog, submission workflow
**Normative Language:** The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as defined by RFC-style engineering convention.

---

## 2. Purpose

This specification defines the first locked version of the Aster package management ecosystem. It covers:

* package manifest format
* package archive format
* dependency and version handling
* package search and catalog access
* package submission for review
* registry metadata
* security requirements
* command-line interface behavior
* lockfile behavior
* error handling expectations
* implementation and test requirements

This specification is intended to be stable enough to guide:

* client implementation
* registry implementation
* package authoring
* interoperability testing
* future versioned evolution of the Aster ecosystem

---

## 3. Design Goals

The Aster package system v1 MUST satisfy the following goals:

1. **Easy to use**
2. **Secure by default**
3. **Reproducible**
4. **Version-aware**
5. **Deterministic**
6. **Discoverable**
7. **Moderated for public publication**
8. **Simple to bootstrap**
9. **Capable of future migration to more advanced infrastructure**

## 3.1 Target Users

### Package Author

Wants to create a package quickly, build and test it locally, declare dependencies, version releases cleanly, and submit for public consideration.

### Package Consumer

Wants to find packages by name or topic, inspect metadata and trust signals, install predictable versions safely, and update without breaking their project.

### Registry Moderator

Wants to review package submissions, validate metadata, reject malicious or low-quality packages, manage namespace conflicts, and maintain ecosystem integrity.

---

## 4. Non-Goals for v1

The following are explicitly out of scope for v1:

* paid packages
* package monetization
* peer-to-peer package distribution
* instant unreviewed public publishing
* arbitrary install-time scripts
* binary ABI guarantees
* enterprise/private registry federation
* transitive trust federation across third-party signing authorities
* cross-registry implicit dependency fallback
* Unicode package names

---

## 5. System Components

The Aster package ecosystem v1 consists of four logical components:

### 5.1 Aster CLI client

The CLI command family is rooted at:

```bash
aster pkg ...
```

### 5.2 Manifest

The package manifest file name is:

```text
aster.toml
```

### 5.3 Lockfile

The project dependency lockfile name is:

```text
aster.lock
```

### 5.4 Package artifact

The distributable package archive extension is:

```text
.apkg
```

### 5.5 Registry

The public registry is logically split into:

* **catalog/index metadata**
* **artifact storage**
* **submission/review service**

---

## 6. Normative High-Level Decisions

The following decisions are frozen for v1:

1. The manifest file is `aster.toml`.
2. The lockfile is `aster.lock`.
3. The package artifact extension is `.apkg`.
4. Public publication is **moderated**.
5. Public package names are globally unique within the public registry.
6. Package names are lowercase ASCII only.
7. Semantic Versioning is required.
8. Package integrity verification is mandatory.
9. Reproducible package building is required.
10. `authors` is a required non-empty list of author records.
11. `supported_platforms` is an optional list restricted to `linux`, `mac`, `win`.
12. Arbitrary install scripts are forbidden in v1.
13. The resolver is deterministic.
14. Direct git dependencies MAY exist in development workflows, but the public registry format is authoritative for published packages.
15. The system is source-package first.

---

## 7. Package Types

A package MUST declare one of these package types:

* `library`
* `application`
* `tool`

Rules:

* A `library` is primarily intended to be imported or linked into other Aster projects.
* An `application` is intended to produce a runnable program.
* A `tool` is intended to provide command-line or development utility behavior.

---

## 8. Package Naming Rules

Package names MUST satisfy all of the following:

* lowercase ASCII only
* start with a letter
* contain only letters, digits, and hyphens
* length 2 through 64 characters inclusive
* MUST NOT end with a hyphen
* MUST NOT contain adjacent hyphens
* MUST NOT be a reserved system name
* MUST be unique within the target registry namespace

Normative regex:

```text
^[a-z](?:[a-z0-9]|-(?=[a-z0-9])){1,63}$
```

Examples of valid names:

* `json`
* `httpkit`
* `net-core`
* `tiny-test`

Examples of invalid names:

* `HTTPKit`
* `9parser`
* `my_package`
* `a`
* `net--core`
* `-parser`

Reserved names for v1 include at minimum:

* `aster`
* `std` — reserved because it is a bundled stdlib module name; it is not an installable package
* `core`
* `builtin`
* `registry`
* `system`

The registry MAY reserve additional names. Bundled stdlib module names (`math`, `str`, `io`, `list`, `random`, `time`, `path`, `linalg`) are not individually reserved at the registry level but SHOULD be avoided to prevent confusion; the registry MAY warn on submission.

---

## 9. Versioning

### 9.1 Package version format

A package version MUST follow Semantic Versioning:

```text
MAJOR.MINOR.PATCH
```

The following forms are valid:

* `1.2.3`
* `1.2.3-alpha.1`
* `1.2.3-rc.2`
* `1.2.3+build.5`
* `1.2.3-rc.2+build.5`

### 9.2 Version ordering

The resolver MUST implement Semantic Versioning precedence rules:

* prerelease versions sort lower than their corresponding stable release
* build metadata does not affect precedence

### 9.3 Dependency constraint syntax

v1 MUST support:

* exact: `1.2.3`
* caret: `^1.2.3`
* tilde: `~1.2.3`
* lower bound: `>=1.2.3`
* bounded range: `>=1.2.3,<2.0.0`
* comma-joined conjunctions

v1 MUST NOT support arbitrary boolean expression syntax beyond comma-joined AND constraints.

Examples:

* `^1.4.0`
* `>=1.0.0,<2.0.0`
* `~2.3.1`

---

## 10. Manifest Specification: `aster.toml`

## 10.1 General rules

The manifest:

* MUST be valid TOML
* MUST be UTF-8 encoded
* MUST use Unix-style forward slash paths in path fields
* MUST NOT contain duplicate keys
* MUST be canonicalizable by the Aster client

## 10.2 Required top-level tables

The following tables are required:

* `[package]`
* `[aster]`

At least one of the following package role tables MUST also be present:

* `[lib]`
* `[app]`
* `[tool]`

Optional tables:

* `[dependencies]`
* `[dev-dependencies]`
* `[build]`
* `[submission]`

---

## 10.3 `[package]` table

Required fields:

* `name`
* `version`
* `type`
* `description`
* `license`
* `authors`

Optional fields:

* `repository`
* `documentation`
* `homepage`
* `keywords`
* `categories`
* `readme`
* `supported_platforms`
* `changes`
* `source_root`

### 10.3.1 Field definitions

#### `package.name`

Type: string
Required: yes

Must follow package naming rules.

#### `package.version`

Type: string
Required: yes

Must follow Semantic Versioning.

#### `package.type`

Type: string enum
Required: yes

Allowed values:

* `library`
* `application`
* `tool`

#### `package.description`

Type: string
Required: yes

Constraints:

* trimmed
* minimum length: 10
* maximum length: 300
* single-paragraph summary in v1

#### `package.license`

Type: string
Required: yes

Free-form string in v1, though SPDX identifiers are strongly preferred.

#### `package.authors`

Type: array of author records
Required: yes
Minimum items: 1

Each item MUST be an inline table or an array-of-tables record containing at least:

* `name`

Allowed author fields:

* `name` — required string
* `web_url` — optional string URL
* `contact` — optional string
* `email` — optional string
* `country` — optional string
* `organization` — optional string

Only `name` is required.

Rules:

* author names MUST be non-empty after trimming
* duplicate identical author records SHOULD be rejected by validation
* `contact` is intentionally generic and may be email, handle, or other contact form
* if both `contact` and `email` are present, both are preserved

#### `package.repository`

Type: string URL
Required: no

#### `package.documentation`

Type: string URL
Required: no

#### `package.homepage`

Type: string URL
Required: no

#### `package.keywords`

Type: array of strings
Required: no

Constraints:

* each keyword length 2 to 32
* lowercase recommended
* maximum 20 keywords

#### `package.categories`

Type: array of strings
Required: no

Constraints:

* maximum 10 categories

#### `package.readme`

Type: string path
Required: no, but public submission requires either `readme` or sufficiently complete long description support in a future extension

v1 public submission requirement: `readme` SHOULD be present and SHOULD point to an existing file.

#### `package.supported_platforms`

Type: array of enum strings
Required: no

Allowed values only:

* `linux`
* `mac`
* `win`

Rules:

* values MUST be unique
* ordering does not matter semantically
* if omitted, the package is treated as platform-agnostic or unspecified
* if present, installation on a non-listed platform MUST fail unless the user explicitly overrides with an unsafe flag defined in a future extension
* `mac` means macOS
* `win` means Windows

#### `package.changes`

Type: string
Required: no

Purpose: optional short description of changes from prior release.

#### `package.source_root`

Type: string path
Required: no

Default if omitted: `src`

---

## 10.4 `[aster]` table

Required fields:

* `min_version`

Optional fields:

* `max_version`

Definitions:

#### `aster.min_version`

Type: string version
Required: yes

Defines the minimum supported Aster toolchain version.

#### `aster.max_version`

Type: string version
Required: no

Defines the maximum supported Aster toolchain version, inclusive unless otherwise revised in a future spec.

Rules:

* if `max_version` is present, it MUST be greater than or equal to `min_version`
* install MUST fail if target Aster version falls outside supported range

---

## 10.5 Role tables

Exactly one primary role table MUST be present, matching `package.type`.

### 10.5.1 `[lib]`

Required when `package.type = "library"`.

Required fields:

* `entry`

`entry` is the library entry path.

### 10.5.2 `[app]`

Required when `package.type = "application"`.

Required fields:

* `entry`

Optional fields:

* `name`

### 10.5.3 `[tool]`

Required when `package.type = "tool"`.

Required fields:

* `entry`

Optional fields:

* `command`

If `command` is omitted, the package name is used as the default exposed command name.

---

## 10.6 Dependency tables

### 10.6.1 `[dependencies]`

Type: table mapping dependency name to version constraint string.

Example:

```toml
[dependencies]
json = "^1.2.0"
tls = ">=2.0.0,<3.0.0"
```

Rules:

* keys MUST be valid package names
* values MUST be valid version constraints
* self-dependency is forbidden
* circular dependency may exist across packages in theory, but the install/build system MUST reject cycles that make resolution or build order impossible

### 10.6.2 `[dev-dependencies]`

Same syntax as `[dependencies]`, but only applies to development workflows:

* testing
* linting
* docs generation
* local development

Dev dependencies MUST NOT be included as runtime dependencies of published consumers unless also listed in `[dependencies]`.

---

## 10.7 `[build]` table

Optional.

Allowed fields in v1:

* `backend` — optional string
* `requires_native` — optional boolean
* `generated_sources` — optional boolean

Rules:

* arbitrary install scripts are forbidden
* this table is declarative only in v1
* `requires_native = true` signals native or external toolchain requirements
* registries MAY use this for review classification and warnings

---

## 10.8 `[submission]` table

Optional local authoring metadata, not all fields necessarily included in published canonical manifest.

Allowed fields in v1:

* `category_notes`
* `review_notes`

This table MUST NOT affect dependency resolution or install semantics.

---

## 10.9 Normative manifest example

```toml
[package]
name = "httpkit"
version = "1.4.2"
type = "library"
description = "HTTP client library for Aster applications."
license = "MIT"
repository = "https://github.com/aster-lang/httpkit"
documentation = "https://docs.aster-lang.org/httpkit"
homepage = "https://aster-lang.org/packages/httpkit"
keywords = ["http", "network", "client"]
categories = ["networking"]
readme = "README.md"
supported_platforms = ["linux", "mac", "win"]
changes = "Improved timeout handling and connection reuse."
source_root = "src"

[[package.authors]]
name = "Jane Smith"
web_url = "https://example.org"
contact = "@janesmith"
email = "jane@example.org"
country = "US"
organization = "Aster Network Group"

[aster]
min_version = "0.9.0"
max_version = "2.0.0"

[lib]
entry = "src/httpkit/lib.aster"

[dependencies]
tls = "^2.1.0"
json = ">=1.0.0,<2.0.0"

[dev-dependencies]
testkit = "^0.8.0"

[build]
backend = "default"
requires_native = false
generated_sources = false
```

---

## 11. Manifest Validation Rules

Validation MUST fail if any of the following occur:

* missing required tables
* missing required fields
* unknown enum value in `supported_platforms`
* empty `authors` list
* author record missing `name`
* invalid version string
* invalid dependency constraint
* entry file path escapes package root
* `package.type` does not match provided role table
* invalid package name
* malformed URL where URL is required
* duplicate entries in `supported_platforms`
* duplicate dependency keys
* identical package name and dependency name
* nonexistent required entry path at build time

Validation SHOULD fail if:

* `readme` is missing for public publication
* no tests are present
* description is too vague
* keywords/categories are duplicated

---

## 12. Lockfile Specification: `aster.lock`

## 12.1 Purpose

The lockfile records the fully resolved dependency graph and integrity information required for reproducible installs.

## 12.2 Requirements

* MUST be machine-generated
* MUST be deterministic
* MUST be UTF-8
* MUST be committed for applications and tools
* MAY be omitted for published libraries, though local development SHOULD still generate one

## 12.3 Required fields

The exact textual format MAY be TOML or another structured encoding chosen by implementation, but v1 strongly recommends TOML.

Each locked dependency record MUST include:

* package name
* exact resolved version
* source identifier
* artifact checksum
* dependency list
* platform restriction if applicable

Illustrative example:

```toml
version = 1

[[package]]
name = "httpkit"
resolved_version = "1.4.2"
source = "registry:default"
checksum = "sha256:3b8a4d..."
dependencies = ["json", "tls"]

[[package]]
name = "json"
resolved_version = "2.0.1"
source = "registry:default"
checksum = "sha256:f9e92a..."
dependencies = []
```

---

## 13. Package Archive Format: `.apkg`

## 13.1 Format decision

A `.apkg` file in v1 MUST be:

* a reproducible tar archive
* compressed with zstd

Conceptually:

```text
tar + zstd
```

## 13.2 File extension

The external filename MUST end with:

```text
.apkg
```

Whether the internal MIME/type machinery refers to tar+zstd is implementation-specific.

## 13.3 Canonical archive layout

A package archive MUST contain the following logical structure:

```text
manifest/aster.toml
src/...
tests/...
docs/README.md            (if readme included)
LICENSE                   (or license file if present)
checksums/SHA256SUMS
meta/buildinfo.json
meta/package.json
```

### Required archive members

* `manifest/aster.toml`
* `checksums/SHA256SUMS`
* `meta/buildinfo.json`
* package source files
* declared entry file

### Optional archive members

* `tests/...`
* `docs/...`
* additional metadata files
* license file when present in source root

## 13.4 Archive reproducibility rules

The archive builder MUST normalize:

* file order: lexicographic UTF-8 byte order
* file ownership: zeroed or canonicalized
* timestamps: canonical fixed value
* permissions: canonicalized safe values
* path separators: `/`
* path traversal: forbidden
* symlinks: forbidden in v1 unless explicitly allowed in a later revision

## 13.5 Checksums

`checksums/SHA256SUMS` MUST contain SHA-256 for every packaged file except itself unless self-entry semantics are explicitly defined by implementation.

The registry MUST also record a SHA-256 checksum for the full `.apkg` artifact.

## 13.6 Build metadata

`meta/buildinfo.json` MUST include at minimum:

* package name
* package version
* Aster build tool version
* build timestamp in canonical or normalized form
* source file count
* artifact checksum
* manifest checksum

---

## 14. Catalog / Registry Metadata Model

## 14.1 Registry separation

The registry consists of:

1. metadata catalog
2. artifact storage
3. submission/review service

These MAY be backed by separate systems so long as the external protocol is coherent.

## 14.2 Package catalog record

Each package in the catalog MUST expose at minimum:

* name
* latest stable version
* available versions
* description
* authors
* supported Aster versions
* supported platforms
* dependency metadata
* review state
* artifact checksum
* publication timestamps

## 14.3 Version catalog record

Each published package version record MUST include at minimum:

* package name
* version
* package type
* manifest checksum
* artifact checksum
* artifact URL or artifact locator
* dependency map
* supported platforms
* Aster compatibility range
* authors
* review status
* publication timestamp
* yanked flag
* deprecated flag

## 14.4 Searchable fields

v1 catalog search MUST support:

* exact package name
* prefix match
* substring or tokenized description search
* keywords
* categories
* author name

v1 SHOULD support ranking by:

* exact match first
* prefix match second
* token relevance next

Popularity ranking is out of scope for v1.

## 14.5 Catalog trust and state signals

Each catalog entry SHOULD display one or more trust and state signals to help users make informed decisions without implying all packages are equally trustworthy:

* `official` — maintained by the Aster core team
* `reviewed` — accepted by moderators and verified for policy compliance
* `community` — accepted, community-maintained
* `experimental` — accepted but marked unstable or pre-1.0
* `deprecated` — author has marked this package superseded
* `yanked` — removed from active use; existing installs continue to work but new installs are blocked
* `security-warning` — a known vulnerability or active advisory exists

The client MUST surface `yanked` and `security-warning` prominently and MUST NOT silently install a yanked version.

---

## 15. Submission and Review Workflow

## 15.1 Publication model

Public publication in v1 is **submission for review**, not direct self-publication.

## 15.2 Submission command

Normative command:

```bash
aster pkg submit dist/my-package-1.2.0.apkg
```

## 15.3 Submission pipeline

Submission MUST proceed through these stages:

1. local validation
2. authentication
3. upload
4. server validation
5. pending review
6. moderator decision
7. accepted or rejected
8. if accepted, catalog publication

## 15.4 Submission states

The registry MUST support these states:

* `draft`
* `submitted`
* `pending-review`
* `accepted`
* `rejected`
* `withdrawn`
* `superseded`

## 15.5 Server-side validation

The registry MUST validate:

* package name
* package version
* package uniqueness for submitted version
* manifest completeness
* checksums
* archive structure
* path safety
* entry file existence
* dependency constraint syntax
* author record presence
* allowed `supported_platforms` values
* package size limits
* namespace policy
* obvious malicious structural patterns

## 15.6 Moderator review criteria

Moderators MUST be able to reject for:

* typosquatting
* misleading naming
* missing or deceptive metadata
* malformed archive
* policy violations
* suspicious build requirements
* reserved namespace misuse
* duplicate version republishing
* security risk indicators

---

## 16. Security Specification

## 16.1 Security baseline

The package manager MUST be secure by default.

## 16.2 Integrity verification

On install, the client MUST verify:

* artifact checksum against registry metadata
* manifest checksum if separately tracked
* lockfile checksum if lockfile is in use

Install MUST fail on mismatch.

## 16.3 Trusted sources

The client MUST distinguish source kinds explicitly:

* official registry
* configured third-party registry
* local path
* direct git

The resolved source MUST be visible in diagnostics and machine-readable output.

## 16.4 Namespace protection

The public registry MUST enforce:

* ASCII-only names
* reserved names
* uniqueness
* reviewer checks against obvious typosquatting

Unicode homoglyph handling is simplified by forbidding Unicode names in v1.

## 16.5 Install-time execution

v1 MUST NOT allow arbitrary install scripts.

v1 MAY allow declarative build metadata only.

Any future executable hooks require a new spec version.

## 16.6 Secure mode

The client SHOULD support a strict security mode. If implemented in v1, it MUST enforce at least:

* official registry only
* lockfile required when installing into an existing locked project
* checksum verification mandatory
* prerelease disallowed unless explicitly requested

## 16.7 Advisory and state metadata

The registry model MUST reserve room for:

* `deprecated`
* `yanked`
* `security-warning`

The client SHOULD surface this information clearly.

---

## 17. Resolution Rules

## 17.1 Determinism

Dependency resolution MUST be deterministic for the same:

* manifest
* lockfile
* registry state
* platform
* Aster version

## 17.2 Default selection policy

Without a lockfile, the resolver MUST:

* choose the highest compatible stable version
* avoid prereleases unless explicitly requested or only prereleases satisfy constraints
* reject incompatible Aster-version ranges
* reject platform-incompatible packages

## 17.3 With a lockfile

When a lockfile exists, the resolver MUST prefer locked versions unless the user explicitly requests update behavior.

## 17.4 Conflict behavior

On an irreconcilable dependency conflict, resolution MUST fail with a clear, actionable error.

Silent fallback is forbidden.

---

## 18. CLI Specification

## 18.1 Required commands

The v1 CLI MUST provide:

```bash
aster pkg init
aster pkg check
aster pkg build
aster pkg test
aster pkg search <query>
aster pkg info <package-spec>
aster pkg install <package-spec>
aster pkg remove <package>
aster pkg update
aster pkg lock
aster pkg submit <artifact>
aster pkg login
aster pkg logout
aster pkg whoami
aster pkg list
aster pkg sources
```

## 18.2 Command behavior summary

### `aster pkg init`

Creates a new package skeleton and initial manifest.

### `aster pkg check`

Validates manifest, layout, and package structure without building.

### `aster pkg build`

Builds `.apkg` package artifact and related metadata.

### `aster pkg test`

Runs package tests.

### `aster pkg search <query>`

Searches the catalog.

### `aster pkg info <package-spec>`

Shows package or package-version details.

### `aster pkg install <package-spec>`

Resolves and installs package dependencies.

### `aster pkg remove <package>`

Removes installed dependency from project manifest and local state as appropriate.

### `aster pkg update`

Updates dependencies within manifest constraints.

### `aster pkg lock`

Resolves and writes `aster.lock`.

### `aster pkg submit <artifact>`

Submits a built package for moderation.

### `aster pkg login/logout/whoami`

Manages registry authentication state.

### `aster pkg list`

Lists project dependencies or installed packages depending on context.

### `aster pkg sources`

Lists configured package sources.

## 18.3 Output requirements

The CLI:

* MUST provide human-readable output by default
* MUST support `--json` for machine-readable output on commands where structured output makes sense
* MUST use stable nonzero exit codes on failure
* SHOULD provide actionable suggestions on common user errors

## 18.4 CLI integration with the Aster toolchain

The `aster pkg` command family MUST be wired into the existing Aster CLI entry point (`src/aster_lang/cli.py` in the reference Python implementation) as a sub-command group. The `pkg` sub-command MUST be registered as a peer of existing top-level commands (`run`, `check`, `fmt`, `doc`, etc.).

The implementation SHOULD use a dispatch pattern such that each `aster pkg <verb>` maps to a handler in a dedicated `src/aster_lang/pkg/` sub-package, keeping package-manager logic isolated from the interpreter and semantic layers.

---

## 19. Example Package Specifications

### 19.1 Library example

```toml
[package]
name = "jsonx"
version = "2.0.1"
type = "library"
description = "JSON parser and serializer for Aster."
license = "MIT"
readme = "README.md"

[[package.authors]]
name = "Aster Team"

[aster]
min_version = "0.9.0"

[lib]
entry = "src/jsonx/lib.aster"
```

### 19.2 Tool example

```toml
[package]
name = "fmtx"
version = "1.0.0"
type = "tool"
description = "Code formatter for Aster."
license = "Apache-2.0"
supported_platforms = ["linux", "mac", "win"]

[[package.authors]]
name = "Dana Cole"
web_url = "https://example.com"

[aster]
min_version = "0.9.0"

[tool]
entry = "src/fmtx/main.aster"
command = "fmtx"
```

---

## 20. Registry API Surface

This section defines the minimum conceptual API surface. Exact HTTP wire format MAY be fixed in an implementation companion doc, but the semantics are locked.

## 20.1 Read operations

The registry MUST support:

* fetch package list metadata
* fetch individual package metadata
* fetch package-version metadata
* search
* fetch artifact
* fetch submission status for authenticated users

## 20.2 Write operations

The registry MUST support:

* authentication
* artifact submission
* submission status lookup
* moderator accept/reject workflows

## 20.3 Conceptual endpoints

Illustrative minimum set:

```text
GET  /api/v1/packages
GET  /api/v1/packages/{name}
GET  /api/v1/packages/{name}/versions/{version}
GET  /api/v1/search?q=...
GET  /api/v1/artifacts/{name}/{version}
POST /api/v1/submissions
GET  /api/v1/submissions/{id}
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/whoami
```

---

## 21. Local State Layout

A conforming client SHOULD maintain user-local state under:

```text
~/.aster/
```

Suggested structure:

```text
~/.aster/
  cache/
  registries/
  auth/
  logs/
  config.toml
```

Project-local state:

```text
./aster.toml
./aster.lock
```

The client MUST NOT store secrets in world-readable files.

---

## 22. Error Model

## 22.1 General requirements

Errors MUST be:

* precise
* actionable
* deterministic
* script-detectable

## 22.2 Required categories

The implementation MUST distinguish at least these categories:

* manifest error
* validation error
* resolution error
* integrity error
* network error
* authentication error
* authorization error
* submission error
* registry error
* platform compatibility error
* Aster version compatibility error

## 22.3 Error message quality standard

Errors MUST be human-centered. Avoid terse internal messages.

Bad example:

```text
resolution failed
```

Good example:

```text
Could not install package "httpkit".

Reason:
  dependency "tls" requires version >=3.0.0,<4.0.0
  project lockfile pins "tls" to 2.7.1

Suggested actions:
  aster pkg update tls
  aster pkg install httpkit --update
```

## 22.4 Suggested canonical error codes

Suggested stable symbolic codes:

* `APKG001` invalid manifest
* `APKG002` missing required field
* `APKG003` invalid package name
* `APKG004` invalid version
* `APKG005` invalid dependency constraint
* `APKG006` missing author record
* `APKG007` invalid supported platform
* `APKG008` entry file missing
* `APKG009` build failed
* `APKG010` checksum mismatch
* `APKG011` dependency resolution failed
* `APKG012` incompatible Aster version
* `APKG013` incompatible platform
* `APKG014` unauthorized submission
* `APKG015` submission rejected
* `APKG016` duplicate published version
* `APKG017` reserved package name
* `APKG018` unsafe archive structure

These symbolic codes SHOULD remain stable once implemented.

---

## 23. TDD-Oriented Implementation Plan

The user’s stated engineering preferences strongly fit TDD here. v1 should be implemented with tests first.

## 23.1 Phase 1: Manifest and validation

Implement first:

* package name validator
* semver parser
* dependency constraint parser
* author record validator
* platform enum validator
* manifest loader
* manifest canonicalizer

Tests first:

* valid and invalid package names
* valid and invalid versions
* author record requirements
* empty authors list rejection
* invalid `supported_platforms` rejection
* missing role table rejection
* role mismatch rejection

## 23.2 Phase 2: Archive builder

Implement:

* canonical file collector
* deterministic archive builder
* SHA-256 manifest and file checksums
* buildinfo generation

Tests first:

* repeated builds produce identical checksum
* path traversal is rejected
* missing entry file fails
* forbidden symlink behavior fails
* checksum file matches packaged files

## 23.3 Phase 3: Resolver and lockfile

Implement:

* dependency graph builder
* deterministic resolver
* lockfile writer/reader
* platform/Aster compatibility enforcement

Tests first:

* simple dependency resolution
* transitive resolution
* conflict rejection
* prerelease avoidance
* lockfile pin reuse
* platform rejection
* Aster version rejection

## 23.4 Phase 4: Catalog client

Implement:

* search
* info
* artifact fetch
* checksum verification

Tests first:

* exact name search
* keyword search
* version metadata parsing
* checksum mismatch rejection

## 23.5 Phase 5: Submission client and review flow

Implement:

* login/logout/whoami
* submit
* status lookup

Tests first:

* upload success
* unauthorized failure
* duplicate version rejection
* malformed package rejection

---

## 24. Minimum Acceptance Test Matrix

A v1 implementation is not conformant until at least the following pass:

### Manifest

* valid minimal library manifest accepted
* manifest with one valid author accepted
* manifest with zero authors rejected
* manifest with author record missing `name` rejected
* manifest with invalid platform value rejected
* manifest with duplicate platform entries rejected

### Build

* valid package builds `.apkg`
* repeated builds are byte-identical
* missing entry path fails
* illegal archive path fails

### Resolve / Install

* highest compatible stable version chosen
* prerelease not chosen by default
* incompatible platform rejected
* incompatible Aster version rejected
* checksum mismatch rejected

### Submit

* valid artifact submission accepted into pending state
* malformed artifact rejected
* duplicate name/version rejected
* unauthorized submit rejected

---

## 25. Recommended Implementation Architecture

For v1, I recommend this split:

### Client

* Python implementation for bootstrap speed and tooling ergonomics
* strict validation layer
* deterministic packer and resolver
* JSON output support for automation

### Registry bootstrap

* package metadata index in git-backed or sparse-HTTP-readable form
* package artifacts stored in controlled release storage
* separate authenticated submission service

### Later evolution path

The client interfaces should be designed so the backend can evolve from:

* GitHub-hosted source and releases
  to
* dedicated `packages.aster-lang.org`
  without breaking manifest or lockfile compatibility.

---

## 26. Open Items Explicitly Deferred to v2+

These are intentionally not locked in v1:

* signed publisher keys
* binary package variants
* optional prebuilt artifacts
* namespaces or org-owned package scopes
* private registries
* install hook execution model
* richer license validation
* popularity metrics
* advanced search ranking
* package yanking policy details beyond reserved metadata fields

---

## 27. Final Locked v1 Summary

The Aster package manager v1 is defined as:

* `aster pkg` CLI
* `aster.toml` manifest
* `aster.lock` lockfile
* `.apkg` reproducible source-package archive
* moderated submission workflow
* deterministic resolution
* mandatory integrity verification
* no arbitrary install scripts
* required non-empty author record list
* optional constrained supported-platform list with values:

  * `linux`
  * `mac`
  * `win`

This is a solid, implementable base that is conservative, secure, and extensible.

---

## 28. Example User Session

The following session illustrates the intended user experience for the common author and consumer workflows.

**Author workflow:**

```bash
# Create a new library package
aster pkg init

# Validate the manifest and layout
aster pkg check

# Build the distributable artifact
aster pkg build

# Authenticate with the registry
aster pkg login

# Submit the built artifact for moderation
aster pkg submit dist/httpkit-1.4.2.apkg
```

**Consumer workflow:**

```bash
# Search for packages
aster pkg search http
aster pkg search "json parser"

# Inspect a package before installing
aster pkg info httpkit
aster pkg info httpkit@1.4.2

# Install a package
aster pkg install httpkit@^1.4

# List installed dependencies
aster pkg list

# Update dependencies within manifest constraints
aster pkg update
```

These flows represent the primary paths the system MUST optimize for ergonomics, speed, and clarity of feedback.

