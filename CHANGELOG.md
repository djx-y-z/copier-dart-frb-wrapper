## [Unreleased]

### Fixed

- **Upstream tag validation is derived from `version_tag_prefix` instead of a hardcoded `v?`** (`template/scripts/src/check_updates.dart.jinja`) — the guard added in v3.0.0 rejected anything not matching `^v?\d+\.\d+\.\d+$`, but the prefix itself is a template variable, so every project generated with a non-default prefix failed its own scheduled update check on the first step with `Refusing unexpected upstream tag_name format`. The workflow's blanket `|| true` (fixed below) kept the run green, so the breakage stayed invisible — a real upstream release would simply never have been picked up. openmls_dart (`version_tag_prefix: "openmls-v"`) had been in that state since adopting v3.0.0. The pattern is now built from `RegExp.escape(_tagPrefix)` and applied to all three untrusted inputs: the API response, manual `--version` input (previously not validated at all), and the tag recorded in `rust/Cargo.toml`. The no-`upstream_crates` branch is deliberately excluded — `getCrateVersion()` returns the crate's own unprefixed version, which is not a tag and must not be validated as one. New `template/test/scripts/check_updates_test.dart.jinja` guards the regression, building its fixtures from the configured prefix so a project with a custom prefix exercises its own format.
- **The build hook no longer re-runs on every single build** (`template/hook/build.dart.jinja`) — `output.dependencies.add(skipMarkerUri)` ran unconditionally, including when `.skip_<package>_hook` does not exist, which is the normal state for every consumer. `hooks_runner` classifies a declared-but-missing file as modified during the build and forces a redundant second hook pass, on every build, for everyone. Measured on a real project with an instrumented hook: 1→2→3 invocations across three consecutive builds before, 1→1→1 after. The marker is now declared only inside the `existsSync()` branch; invalidation is unaffected, because removing an existing marker makes the declared dependency disappear and drops the cached skip result (verified through a full codegen cycle: marker present → hook skips → marker removed → hook re-runs → library registered).
- **`description` is quoted and escaped in generated manifests** (`template/pubspec.yaml.jinja`, `template/rust/Cargo.toml.jinja`) — the description was emitted as an unquoted YAML plain scalar, so any value containing `": "` (e.g. `"messaging: 1:1"`) produced an unparseable `pubspec.yaml` and killed the post-generation `flutter create` tasks, leaving a half-generated project with `.git` already initialized. Both manifests now emit a double-quoted string with `\` and `"` escaped (the same escaping is valid for YAML and TOML). Found while generating enigma_dart.
- **Freshly generated projects pass `make analyze`** (`template/test/{{ package_name }}_test.dart.jinja`) — the two imports were emitted in a fixed order (`package:test` first), but the `directives_ordering` lint wants package imports sorted by URI, so the correct order depends on how `package_name` compares to `"test"` (e.g. `package:enigma` must come first, `package:zebra` last). The template now orders the imports conditionally on the package name.
- **`cargo check` / `make rust-check` work before the first codegen run** (`template/rust/src/frb_generated.rs`) — `lib.rs` declares `mod frb_generated;` but the file only existed after `make codegen`, so a freshly generated project failed `cargo check` with E0583. A placeholder file (overwritten by codegen) ships with the template.
- **Dependabot can rebase and clean up its own branches** (`template/.github/rulesets/signing-commit.json`, `template/.github/rulesets/delete-branches.json`, `template/.github/rulesets/README.md.jinja`) — both rulesets target `~ALL` branches and `signing-commit.json` has an empty `bypass_actors`, so `non_fast_forward` applied to every branch with no exemption for anyone, not even an admin. Dependabot refreshes an open PR by force-pushing a rewritten commit, so its grouped `github-actions` PR could never be rebased onto a moved `main`: on the first scheduled run after the Dependabot config shipped in v3.0.0, it commented *"Dependabot attempted to update this pull request, but because the branch … is protected it was unable to do so"* and left the PR frozen at the state it was opened in. `deletion` from `delete-branches.json` blocked `@dependabot recreate` and post-merge branch cleanup for the same reason. Observed in openmls_dart and true by construction of every project generated since v3.0.0. Both rulesets now exclude `refs/heads/dependabot/**/*` — the trailing `/*` is load-bearing, because these are `fnmatch` patterns in pathname mode where a bare `**` does not cross a `/`, so `refs/heads/dependabot/**` matches only a one-segment `dependabot/foo` and misses the `dependabot/github_actions/github-actions-<hash>` shape Dependabot actually generates (deeper still when a config scopes updates to a directory); confirmed against the live evaluation endpoint, `gh api repos/<slug>/rules/branches/<url-encoded-branch>`, for one-, two- and five-segment names plus an unrelated branch and `main` as controls. The fix is deliberately a `ref_name.exclude` rather than an `Integration` bypass actor: the rulesets target `~ALL`, so a bypass actor would be exempt on `main` as well, which is strictly worse. Nothing is weakened by the exclusion — Dependabot's commits carry a valid GitHub signature regardless of the rule, and they still have to pass `main`'s own `pull_request` gate and `required_signatures` to land. The runbook documents the reasoning, and the "add a bypass actor for your bot" note now warns that a force-push or delete need is scoped with `exclude`, not with a bypass. Branches from `peter-evans/create-pull-request` (`update-{{ package_name }}-*`, `update-template-*`) are intentionally left in scope: those PRs are recreated per version rather than refreshed in place, so the force-push path has not been exercised.

### Changed

- **Update workflows distinguish checker exit codes instead of swallowing them** (`template/.github/workflows/check-{{ package_name }}-updates.yml.jinja`, `template/.github/workflows/check-template-updates.yml.jinja`) — both checkers already exit 0 when up to date, 1 when an update is available and 2 on failure, but the workflows ran them under `|| true`, making a crashed checker indistinguishable from "no updates available". That is precisely what hid the tag-validation bug above behind green scheduled runs. Exit codes >1 now fail the workflow with an `::error::` annotation. Manual `target_version` input is additionally validated in the workflow shell — it is interpolated into `ARGS` and reaches a shell before the Dart checker ever sees it — using a pattern built from `{{ version_tag_prefix }}`.
- **The test workflow triggers on `hook/`, `scripts/` and `Makefile` changes** (`template/.github/workflows/test.yml.jinja`) — edits to the build hook, tooling scripts and the Makefile previously ran no tests at all, even though `test/hook/` and `test/scripts/` cover exactly those. Workflow files are now watched on pull requests too, not only on pushes. `THIRD_PARTY_NOTICES.txt` and `.gitattributes` are watched as well, because `make verify-third-party-notices` runs in this workflow: the notices file is the artefact being checked, and `.gitattributes` decides which bytes a checkout materialises for it. Without them the one commit that can break — or fix — that check was also the one commit that did not run it, so a stale inventory reached `main` unverified and surfaced only in the release preflight of both stages. Found the hard way in openmls_dart: the commit that repaired its `.gitattributes` handling of that very file triggered no run at all and had to be dispatched by hand.
- **GitHub Actions moved to their current majors** (`template/.github/workflows/*.jinja`, `template/.github/actions/setup-fvm/action.yml.jinja`) — `actions/checkout` v4→v7, `actions/upload-artifact` v4→v7, `actions/download-artifact` v4→v8, `actions/cache` v4→v6, `actions/create-github-app-token` v2→v3, `android-actions/setup-android` v3.2.2→v4.0.1 and `schneegans/dynamic-badges-action` v1.7.0→v1.9.0. Most of the majors are the Node 20→24 runtime migration, which requires nothing on GitHub-hosted runners (it needs runner ≥2.327.1, so a self-hosted runner would have to be updated first). Three carry behaviour worth knowing. `download-artifact` v8 now **fails** a run on an artifact digest mismatch instead of logging a warning — a welcome hardening of `build-<package>.yml`'s release job, which is exactly the step that packages the native archives consumers download, and recoverable by re-dispatching because it fails before the GitHub Release is created. `checkout` v7 refuses to check out a fork PR under `pull_request_target`/`workflow_run`; no checkout in the template passes an explicit `ref`, so all of them resolve to the base or default branch and are unaffected. `setup-android` v4 defaults to cmdline-tools 20.0 and still reads `ANDROID_SDK_ROOT` from the environment, which is what `build-<package>.yml` interpolates into `ANDROID_NDK_HOME`. The two SHA-pinned third-party actions were verified against their upstream tag refs before bumping. Note that Dependabot cannot see these files — `*.yml.jinja` is not a manifest it scans — so template action pins are bumped by hand, from the PR Dependabot opens in a generated project.

### Added

- **Third-party notice inventory for the shipped native library** (`template/scripts/generate_third_party_notices.dart.jinja`, `template/scripts/src/third_party_notices.dart.jinja`, `template/scripts/src/spdx_license_texts.dart`, `template/test/scripts/third_party_notices_test.dart.jinja`, `template/Makefile.jinja`, `template/.gitattributes`) — the prebuilt library is statically linked against its whole Rust dependency tree, and MIT, BSD and Apache-2.0 all require those notices to accompany a binary distribution, including an application that embeds the library. Flutter's `LicenseRegistry` does not cover them: it aggregates `LICENSE` files of pub packages, and Rust crates are not pub packages. `make third-party-notices` generates `THIRD_PARTY_NOTICES.txt` at the package root from `cargo tree --locked --edges normal,build` unioned across every released target (wasm32 only when `enable_web`), resolves each crate's SPDX expression and licence texts via `cargo metadata`, and pools identical texts by reference — the Apache-2.0 text alone can appear in a hundred crates, and pooling cut openmls_dart's file from 1.9 MB to under 500 KB. `make verify-third-party-notices` diffs the committed file byte-for-byte. Three decisions carry the weight. **Build edges are kept**, because that is how vendored native code reaches the binary: a `*-src` crate carrying C sources is a build-dependency of its `*-sys` wrapper, so `--edges normal` silently dropped the statically linked OpenSSL from openmls_dart's inventory, and no mechanical rule tells such a crate apart from a pure build tool. **`--locked`**, because without it a stale `Cargo.lock` lets cargo re-resolve the graph, so the same commit could produce different inventories on different machines. **The file is not declared under `flutter: assets:`**, because a package-declared asset is bundled into every consuming application whether used or not; README documents the two lines an app needs to surface it itself. Licence discovery goes three directories deep, so licences shipped beside vendored code are found (SQLCipher's, the Dart SDK headers', the Unicode tables'), and walks up to the repository root for git dependencies, which keep their licence there rather than in the member directory. For a crate that ships no licence file of its own, the canonical text of the licence it declares is supplied from `spdx_license_texts.dart`: only invariant texts verbatim (Apache-2.0 and MPL-2.0 carry no per-crate copyright line), MIT composed from the crate's `authors` metadata and labelled as such in the output, and a licence whose copyright line cannot be recovered reported as SPDX-only rather than guessed at.
- **Notice regeneration wired into `make rust-update`, and verified in CI and both release stages** (`template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`, `template/.github/workflows/build-{{ package_name }}.yml.jinja`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`) — the inventory is derived from the dependency graph, so any lockfile change invalidates it. Regenerating inside `rust-update` means the scheduled update workflow, which already calls that target, refreshes the notices in the same PR instead of landing a stale file and failing its own CI. `test-reusable.yml` verifies it once on the Linux x86_64 leg (the generator unions every release target regardless of host), and `build-<package>.yml` verifies it in `check-release`, before the build matrix starts — every archive it produces embeds the file alongside `LICENSE`, and a hand-pushed tag skips the release script's own gate. Both release stages call `assertNoticesCurrent()` in preflight, ahead of anything irreversible: a pushed tag and a published pub.dev version cannot be taken back. **Adopting this in an existing project:** run `make third-party-notices` once and commit the result, otherwise the new CI step fails on a file that does not exist yet. Fresh generations get the same step in the post-generation message.
- **Write ordering and durability stated as a requirement in the FRB store-callback guidance** (`template/.claude/skills/frb-patterns/SKILL.md.jinja`) — the `DartFn` store-callback example already had the correct shape (`storage_write(key, value).await;` before `Ok(result)`), but nothing said that the `.await` is load-bearing rather than incidental style, so there was no reason for a reader to preserve it. A new *Write Ordering and Durability* section states the two rules a wrapper that delegates state persistence to Dart must satisfy: **(1)** every write callback is awaited before the operation's result is returned — a fire-and-forget write, or one awaited after `Ok(...)` is built, lets the caller act on output whose state may never be stored; **(2)** the Dart callback must not resolve its future until the write is durable — resolving once the value sits in a map, an unflushed file or a write-behind queue satisfies rule 1 while still losing the write to a crash. The split matters because the two obligations sit on different sides: rule 1 is the wrapper's and holds by construction once every callback is awaited, while rule 2 is the application's and **cannot be inferred from the callback signature**, so the wrapper has to state it explicitly or consumers will not know it exists. What a lost or rolled-back write actually costs is protocol-specific, so the section defers that to the generated package's own `SECURITY.md` rather than asserting anything cryptographic here. Extracted from libsignal_dart, where the price is concrete: message keys are derived deterministically from stored state with no per-message nonce guard, so a lost or rolled-back session write makes the next send reuse a message key and IV — confirmed there by restoring an earlier session record and observing a byte-identical AES-CBC body.
- **DartFn callbacks documented as non-failable** (`template/.claude/skills/frb-patterns/SKILL.md.jinja`) — a `DartFnFuture<T>` has no error channel, so a Dart closure that throws does not reach the Rust side as a `Result`: FRB panics the worker thread with `Dart throws exception but Rust side assume it is not failable: <the error>`. The skill documented only the opposite direction (`Result<T, String>` → Dart exception, under *Error Handling*), which invites the assumption that the two are symmetric. They are not, nothing in the callback signature says so, and nothing fails at compile time — the first sign is a panicking worker at runtime. A new *Callbacks Are Not Failable* section states the two consequences: **(1)** the Dart-facing interface has to document that implementations must not throw, since the implementer is the one who has to honour it; **(2)** a callback cannot act as a veto — to let the Dart side reject something, give the callback a return type that expresses rejection (`DartFnFuture<bool>`, not `DartFnFuture<()>`) so the Rust side branches on it. The section also notes that a write-back callback invoked *after* the operation's real work is done cannot abort that work whatever it returns, so a check that must be able to stop an operation has to run before it — usually a read callback rather than a write one. *Error Handling* gains a cross-reference so the asymmetry is visible from either side. Found in libsignal_dart while widening a store callback to its upstream argument list: the upstream trait documents that the store should "produce an error" when it sees a replayed pre-key combination, and a store implementing that literally by throwing would have panicked the worker instead of failing the decryption.
- **`make rust-test` and a CI step that runs it** (`template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`) — the crate's own `#[cfg(test)]` tests were never executed anywhere in CI. That matters beyond coverage: projects routinely cite a specific unit test as the reachability justification for an advisory ignore in `.cargo/audit.toml` / `rust/deny.toml` (openmls_dart cites `classical_ops_do_not_init_libcrux` for six libcrux RUSTSEC entries), and that justification was going unverified on every run. Runs on the Linux x86_64 matrix leg only, same rationale as clippy.
- **freezed toolchain preinstalled with working version bounds** (`template/pubspec.yaml.jinja`) — the first data-carrying enum/struct in the FRB API makes codegen emit freezed sealed classes and fail with `MissingDep: Please add freezed to your dev_dependencies`. The template now ships `freezed_annotation ^3.0.0` (dependencies) plus `freezed >=3.0.0 <3.2.6` and `build_runner >=2.4.0 <2.6.0` (dev_dependencies). The upper bounds are load-bearing: pub resolves `freezed ^3.0.0` to the `3.2.6-dev.1` prerelease, which fails flutter_rust_bridge_codegen's dependency version check, and `build_runner >=2.6` AOT-compiles builders via `dart compile`, which refuses to run in packages using native build hooks (`hook/build.dart`) — both discovered while wiring enigma_dart's typed `EnigmaError`.

## [3.0.3] - 2026-07-21

### Fixed

- **`make release-frb` / `make release` no longer abort on an unrelated diverged tag** (`scripts/src/release_frb.dart.jinja`, `scripts/src/release.dart.jinja`) — the release preconditions ran `git fetch origin --tags --quiet` but never used the fetched tags: the "tag already on origin?" check queries origin directly with `git ls-remote`, and the behind/ahead check only needs `origin/main`. So a single diverged tag anywhere in the namespace (a local-vs-remote object mismatch, e.g. an old release tag) made the fetch exit non-zero and aborted the release for a reason unrelated to it. Narrowed to `git fetch origin main --no-tags --quiet`, which refreshes `origin/main` for the behind/ahead check and cannot fail on tag divergence; behaviour is otherwise identical.

## [3.0.2] - 2026-07-21

### Changed

- **`make release` no longer leaves an empty `## [Unreleased]` heading behind** (`scripts/src/release.dart.jinja`, `finalizeChangelog`) — finalizing a release now renames `## [Unreleased]` to `## [X.Y.Z] - <date>` *in place* instead of splitting it into a fresh empty `## [Unreleased]` plus the dated heading, so the released version sits at the top of the CHANGELOG with no empty section above it. The footer `[Unreleased]:` compare link is **intentionally retained** (rewritten to `vX.Y.Z...HEAD`): it is the single source of truth for the base URL + previous version that `finalizeChangelog` and the section-creating scripts read, and the next unreleased change recreates the `## [Unreleased]` heading. Docs (`CLAUDE.md.jinja`, `CONTRIBUTING.md.jinja`, `release-package` skill) and the `finalizeChangelog` docstring updated; the load-bearing footer link is now documented so it is not deleted as "stale".

### Fixed

- **The native-update auto-PR recreates `## [Unreleased]` when it is absent** (`scripts/src/update_changelog.dart.jinja`) — with the change above, the normal post-release state has no `## [Unreleased]` heading, so an automated dependency-update PR now lands on the "create the section" path first. That path already existed (`_createUnreleasedSection`) but was near-dead and untested; `_insertChangelogEntry` is renamed to the public `insertChangelogEntry` (pure; exposed for testing) and covered by new `test/scripts/update_changelog_test.dart.jinja` (absent → create, present → insert-without-duplication). `finalizeChangelog`'s test for the empty section is inverted accordingly.
- **Docs describe the stage-2 step order correctly** (`CLAUDE.md.jinja`, `CONTRIBUTING.md.jinja`, `Makefile.jinja`, `scripts/release.dart.jinja` docstring + `--help`, `release-package` skill) — every description of `make release` now lists the `make publish-dry-run` validation *before* the `pubspec.yaml` bump and CHANGELOG finalize, matching the actual order since v3.0.1 (the dry-run runs on the clean, pre-bump tree). Stale references to a "fresh empty `## [Unreleased]` left by a package release" in `release_frb.dart.jinja` and `release_frb_test.dart.jinja` comments were corrected too.

## [3.0.1] - 2026-07-20

### Fixed

- **`scripts/src/release.dart.jinja` — `make release` runs the pub.dev dry-run *before* the version bump** — `dart pub publish --dry-run` exits non-zero (65) on *any* warning (observed on Dart SDK 3.10.3), and the stage-2 release ran it on the bumped-but-uncommitted tree, which self-inflicts a "checked-in files are modified in git" warning — so `make release` aborted with `publish-dry-run reported errors` before it could commit, on every release. The dry-run now runs on the clean, pre-bump tree; it only validates package *structure* (files present, archive size, pubspec validity), which a version bump or CHANGELOG edit cannot change, so validation keeps identical catching power without the self-inflicted failure. The now-dead `try/catch … checkout` revert around the dry-run is removed.

## [3.0.0] - 2026-07-20

### Changed (BREAKING)

- **`.github/workflows/build-{{ package_name }}.yml.jinja` — native build trigger changed to a pushed `{{ crate_name }}-*` tag** (created by `make release-frb`) instead of `push` to `main`; a step validates the tag equals the `rust/Cargo.toml` crate version. `workflow_dispatch` is retained for first-run/forced rebuilds. **After `copier update`, existing projects must adopt the two-stage `make release-frb` → `make release` flow — native binaries no longer publish on every push to `main`.**
- **Native-crate release decoupled from dependency updates** (`scripts/src/check_updates.dart.jinja`, `scripts/src/update_changelog.dart.jinja` + entry points, `.github/workflows/check-{{ package_name }}-updates.yml.jinja`) — automated update PRs no longer bump the `{{ crate_name }}` crate version, no longer build binaries, and no longer stamp the `{{ crate_name }}` CHANGELOG highlight (all now deliberate release steps). Removed the SemVer-mirror crate bump and the AI-severity reconciliation (`_reconcileCrateVersion`, `--crate-version-before`, the `bump`/`bump_verified`/`crate_version` outputs and the `bump-unverified` label). `update_changelog` still threads `--from` into a compare link for the "Changed" entry. Dependency updates accumulate on `main` (CI builds from source and tests them).

### Added

- **`scripts/release.dart.jinja` + `scripts/src/release.dart.jinja` + `Makefile.jinja` (`release`)** — `make release` cuts the Dart package release (stage 2 → pub.dev): verifies the stage-1 `{{ crate_name }}-<crate>` native release exists on GitHub, bumps `pubspec.yaml`, finalizes the CHANGELOG (`[Unreleased]` → dated version + a fresh `[Unreleased]` + the bottom compare links, with the previous version and base URL derived from the existing `[Unreleased]` link), runs `make publish-dry-run`, then signs a commit + `vX.Y.Z` tag and pushes. Pure, tested `finalizeChangelog()` (`test/scripts/release_test.dart.jinja`); `getPackageVersion()` added to `common.dart.jinja`. Commit/tag/push inherit the terminal so the signing passphrase is entered interactively.
- **`scripts/release_frb.dart.jinja` + `scripts/src/release_frb.dart.jinja` + `.claude/skills/release-frb-crate/`** — `make release-frb` cuts the native-crate release (stage 1): bumps `rust/Cargo.toml`, stamps the `{{ crate_name }}` CHANGELOG highlight, signs a commit + `{{ crate_name }}-<version>` tag, and pushes to trigger the native build. New `release-frb-crate` skill. The two release commands share git/terminal helpers in `scripts/src/release_common.dart` (no-jinja).
- **`.github/rulesets/` + `scripts/setup_repo_protections.dart` + `Makefile.jinja` (`setup-repo-protections`)** — the branch and release-tag rulesets ship as committed JSON (source of truth, editable in-repo): `protect-main.json`, `signing-commit.json`, `delete-branches.json`, `protect-release-tags.json`. `make setup-repo-protections` applies them all via `gh` (idempotent by ruleset name; `--update` overwrites) and configures the `native-build` environment with the current user as a required reviewer. `signing-commit.json` ships with an empty bypass — a project's automation App has a per-repo Integration id, added per the runbook in `.github/rulesets/README.md`.
- **`.github/workflows/test-reusable.yml.jinja`** — a `make check-targets` step (Linux x86_64 leg) fails CI when the iOS/macOS/Android minimum deployment targets drift out of sync across the CI build env vars, the example Xcode projects and the README platform table (the checker already existed but was never run automatically).
- **`template/.github/dependabot.yml`** — Dependabot for GitHub Actions in generated projects: weekly grouped update PRs (Monday 06:00 UTC, `chore(deps)` prefix) bump the pinned actions — both the commit SHA and its `# vX.Y.Z` comment — across the workflows and the composite actions (a `directories` glob covers `/.github/actions/*`, since `/` only scans `.github/workflows/`); `dtolnay/rust-toolchain` is ignored (master-SHA pin, no versioned releases). The file is static (no `.jinja` — nothing to parameterize). Note: Dependabot does not parse the template's own `.jinja` sources — those pins remain manually synced during backports, as before.
- **`scripts/README.md.jinja`** — the template now ships a `scripts/` index README (previously missing) documenting each dev script and its `make` command plus the "always use `make`" convention, parametrized by package / native-library name.

### Changed

- **`.github/workflows/build-{{ package_name }}.yml.jinja` (deployment targets)** — the macOS build now sets `MACOSX_DEPLOYMENT_TARGET: '{{ macos_min_version }}'` (previously rustc's per-target default) and the Android build links against the declared minSdk via cargo-ndk `--platform {{ android_min_sdk }}` (previously cargo-ndk's default), so the prebuilt binaries' minimum OS versions match the documented support table.
- **`scripts/check_deployment_targets.dart.jinja`, `scripts/get_android_min_sdk.dart`** — with the platform scaffolding gone, the checker verifies the CI workflow (`IPHONEOS_DEPLOYMENT_TARGET`, `MACOSX_DEPLOYMENT_TARGET`, cargo-ndk `--platform`) instead of the podspecs/`build.gradle`, and `get_android_min_sdk.dart` reads `android_min_sdk` from `.copier-answers.yml` (the source of truth) directly.
- **`.claude/skills/build-native/SKILL.md.jinja`** — rewritten to match the actual Makefile interface (`make build [ARGS="--target <rust-target>"]` / `build-android` / `build-web`, artifacts in `rust/target/`); it previously documented a `make build ARGS="<platform>"` interface and `bin/` / `jniLibs/` outputs that never existed in this template.
- **`lib/src/{{ package_name }}.dart.jinja`** — loader doc comments no longer reference Cargokit (the fallback is flutter_rust_bridge's default loader; the build hook provisions the library).
- **`.claude/skills/release-package/SKILL.md.jinja`** — rewritten around `make release` (stage 2), with the stage-1 prerequisite, versioning guidance and a manual fallback.
- **`CLAUDE.md.jinja`, `CONTRIBUTING.md.jinja`** — a two-stage "Release Flow" (`make release-frb` → `make release`) and a "Repository rulesets & tag protection" section; **`copier.yml`** `_message_after_copy` now points new projects at `make setup-repo-protections`.

### Fixed

- **`scripts/src/release_frb.dart.jinja` stages `rust/Cargo.lock`** — the stage-1 release now syncs and stages the crate's own `Cargo.lock` version stanza alongside `Cargo.toml` (new `getCrateName()` in `common.dart.jinja` + `bumpCargoLockVersion()`), so the pre-commit `cargo check` no longer leaves the lock dirty (which blocked the stage-2 clean-tree preflight) and the signed `{{ crate_name }}-*` tag no longer carries a stale lock.
- **Build hook download/cache resilience (`hook/build.dart.jinja`)** — a version-keyed cache entry is reused only after a `.download-complete` marker proves the extraction finished (no reuse of a library left truncated by an interrupted `tar`); a local `rust/target/` build is used only when it matches the target OS **and** architecture (never a host build bundled for a cross-target); the checksums fetch and binary download retry transient HTTP 5xx/429; the web path skips the checksums fetch when the cache is warm and declares the local WASM outputs + the `web/pkg` version marker as dependencies.
- **`scripts/check_deployment_targets.dart.jinja` fails closed** — a missing checked file or a vanished pattern is now a failure (exit non-zero) instead of a silently-skipped success, so the deployment-target drift gate can't go green after a CI env var is renamed away.
- **Release-script robustness** — `stampFrbHighlight` inserts a `### For Users` parent when the section lacks one; `runInherit` (`release_common.dart`) fails loud on any non-zero exit (previously swallowed when no message was passed); `finalizeChangelog` validates the `--date` (`YYYY-MM-DD`) before stamping the immutable released heading; and the commit-failure messages state the bump is left staged and how to recover.
- **Rendering/docstring polish** — `LICENSE.jinja` and `rust/.cargo/config.toml.jinja` no longer render stray leading blank lines; the hook `.skip_{{ package_name }}_hook` docstring now describes the actual behavior (an internal escape that registers no asset — local builds are auto-detected without it).

### Removed

- **Platform-plugin scaffolding** (`template/ios/`, `template/macos/`, `template/android/`, `template/linux/`, `template/windows/`) — generated packages are plain Dart FFI packages (no `flutter: plugin:` section in `pubspec.yaml`), so flutter_tools never consumed the podspecs, the Gradle project or the CMakeLists; native delivery is via `hook/build.dart`. `.gitignore.jinja` / `.pubignore.jinja` now anchor-ignore the old platform dirs (`/ios/`, `/macos/`, …) so stale local artifacts are neither committed nor published.

### Security

- **Build provenance attestation (Sigstore, SLSA Build L2)** — `build-{{ package_name }}.yml.jinja` now attests every native-release archive via `actions/attest-build-provenance` (`subject-checksums` reuses the SHA256 file the build hook verifies) and attaches the Sigstore bundle (`{{ crate_name }}-<version>.sigstore.jsonl`) to the release for fully offline verification; the release notes and `SECURITY.md.jinja` document `gh attestation verify` usage and the honest limitation that the hook itself does not verify attestations.
- **Upstream tag names validated before reaching the shell** — `check_updates.dart.jinja` / `check_template_updates.dart` reject a release `tag_name` that is not a plain semver-ish tag before it lands in `GITHUB_OUTPUT`, and the two update-checker workflows pass step outputs/inputs into `run:` blocks via `env:` instead of inline `${{ }}` interpolation — closing a shell-injection path from upstream release names (backport of the liboqs audit).
- **Least-privilege `GITHUB_TOKEN` everywhere** — `publish.yml.jinja` and `build-{{ package_name }}.yml.jinja` now default to `contents: read` with job-level opt-ups (`id-token: write` on the pub.dev publish job, `contents: write` on the release jobs); the update-checker workflows drop `contents/pull-requests: write` entirely (all writes go through the App token).
- **Third-party actions pinned to commit SHAs** — `dart-lang/setup-dart`, `peter-evans/create-pull-request`, `android-actions/setup-android`, `ilammy/msvc-dev-cmd`, `schneegans/dynamic-badges-action`, `Swatinem/rust-cache`, `dtolnay/rust-toolchain` (toolchain now passed via the `toolchain` input since the ref no longer selects it).
- **`setup-make` verifies gnumake.exe by SHA256** — release assets are mutable, so the size check alone did not lock the Windows make binary; a hardcoded SHA256 input (updated together with the version) now does.
- **`Swatinem/rust-cache` repinned to the v2.9.1 commit** — the previous pin `42dc69e…` was the floating `v2` tag *object* (one commit ahead of the v2.9.1 release), not an immutable commit; it would break every Rust job the moment upstream re-tags `v2`. Now pinned to the release commit `c19371144df3bb44fab255c43d04cbc2ab54d1c4` in `.github/actions/setup-rust/action.yml.jinja` and `.github/workflows/fuzz.yml.jinja`.
- **`publish.yml.jinja` — release notes via `--notes-file`** — the version and changelog now go through `env:` and the notes are written with `printf`, so a literal `EOF` line in the changelog can no longer terminate the inline heredoc early and execute the remaining text as shell under the `contents: write` token.
- **`build-{{ package_name }}.yml.jinja` — fail-loud release, fail-closed probe** — `create-release` no longer delete-then-recreates an existing GitHub Release (a duplicate create now fails loudly instead of silently clobbering already-published binaries that consumers' build hooks download), and `check_exists_frb_release.dart.jinja` now distinguishes exists / missing / inconclusive, aborting on an API error instead of proceeding on a false "missing".
- **`fuzz.yml.jinja` — dispatch `duration` input validated + via `env:`** — the `workflow_dispatch` duration is rejected unless it is a positive integer and is passed to the fuzz command through `env:` instead of inline `${{ }}` interpolation, closing a shell-injection path.
- **`.github/workflows/build-{{ package_name }}.yml.jinja` — `native-build` environment gate** — the `create-release` job (which publishes the consumer-downloaded native binaries) now runs in a `native-build` environment. Once required reviewers are configured it gates every native publish — both a `{{ crate_name }}-*` tag push **and** a `workflow_dispatch` run — behind human approval, mirroring the `pub.dev` environment that gates pub.dev publishing. A tag ruleset cannot cover the dispatch path, so this environment is the load-bearing control.
- **`.github/rulesets/protect-release-tags.json` (+ `.github/rulesets/README.md`, `SECURITY.md.jinja`)** — a repository ruleset restricts *creating, moving and deleting* **all tags** to Admins/Maintainers and requires them signed (targets `~ALL` — the release-triggering `{{ crate_name }}-*` / `v*` are the critical subset), so a plain `write` collaborator cannot mint a release tag that triggers a native / pub.dev publish. Rationale, apply/verify/rollback commands and residual risks are documented in `.github/rulesets/README.md`.

## [2.5.2] - 2026-07-16

### Fixed

- **`hook/build.dart.jinja`** (gated on `enable_web`) — the web build hook now records the provisioned crate version in `web/pkg/.wasm-version` and re-downloads when it changes, instead of skipping whenever the two WASM files merely exist. Previously, upgrading the generated package kept the prior version's WASM in the consuming app's `web/pkg/` (it survives `flutter clean`), so on web any FRB entry that calls Dart store callbacks panicked with an argument-count mismatch (`called Option::unwrap() on a None value`) once the wire signature had changed between versions. The download cache is now version-keyed (`web/<version>/`), WASM files are copied unconditionally (the old mtime guard skipped a fresh-but-older source on downgrade), and `rust/Cargo.toml` is a declared web-build dependency so a version bump re-runs the hook — all mirroring the native path (which was unaffected).

## [2.5.1] - 2026-07-13

### Added

- **`README.md`** — "Create a new project with Claude Code" subsection under Usage: clone the template (which bundles the `create-project` skill) and run `/create-project` in Claude Code as an alternative to the raw Copier commands.

### Changed

- **`.github/workflows/release.yml`** — the generated GitHub Release notes now present two installation paths under "Installation": the existing **Using Copier** commands and a new **Using Claude Skills** variant that clones the tagged template (which bundles the `create-project` skill) and invokes `/create-project` in Claude Code.

## [2.5.0] - 2026-07-12

### Added

- **`test/hook/build_hook_test.dart.jinja`** — tests for the download-cache key (device vs simulator, version invalidation, architecture distinction, exact artifact identity); ported from fork [ospaarmann/openmls_dart](https://github.com/ospaarmann/openmls_dart) (credit: Ole Spaarmann).
- **`Makefile.jinja`** — `setup-frb-codegen` target that installs `flutter_rust_bridge_codegen` pinned to `FRB_CODEGEN_VERSION` (derived from `frb_version`), so CI and local codegen runs use the same binary and generate identical bindings; `setup-rust-tools` now delegates to it instead of installing an unpinned latest.
- **`LICENSE.appstore.jinja`** — AGPL §7 additional permission for app-store distribution (generic Feeel/wger wording, ported from libsignal_dart): AGPL-compliant apps may convey the package in object-code form through app stores whose terms conflict with the AGPL, provided the source stays available through an unrestricted channel. Generated only when `license == 'AGPL-3.0'` (removed by a post-gen task otherwise); scoped to the repository's own code with an explicit note that it cannot cover the bundled upstream native library. README's License section documents the exception; `LICENSE` itself is untouched so GitHub/pub.dev keep detecting plain AGPL-3.0.
- **`rust/fuzz/examples/gen_corpus.rs`** — seed-corpus generator stub (gated on `enable_fuzzing`, ported as a generic pattern from libsignal_dart's `fuzz-seed`): writes valid inputs to `rust/fuzz/corpus/<target>/` so libFuzzer starts from structurally-correct data; ships working seeds for the placeholder `example` target with instructions to extend per real target. New `make fuzz-seed` target (+ help/CLAUDE.md/SECURITY.md mentions), and the Fuzz workflow regenerates the corpus before every run (skipping gracefully if the generator file was deleted).
- **`scripts/update_changelog.dart.jinja`** — new `--from <ver>` option: fetches the upstream commit list between the two tags via the GitHub compare API and feeds it to the AI alongside the release notes, producing complete changelog entries even when upstream release notes are terse. The update workflow passes `--from` automatically.
- **`copier.yml`** — new `enable_fuzzing` variable (default `true`) that scaffolds a cargo-fuzz harness for the generated package.
- **`rust/fuzz/Cargo.toml.jinja`, `rust/fuzz/fuzz_targets/example.rs.jinja`, `rust/fuzz/.gitignore`** — cargo-fuzz harness with a placeholder target wired to the generated `init_*` function; gated on `enable_fuzzing`.
- **`.github/workflows/fuzz.yml.jinja`** — Fuzz workflow that builds and runs every fuzz target (discovered via `cargo fuzz list`) on `rust/**` pull requests and weekly, with a per-input `-timeout` watchdog and crash-artifact upload; gated on `enable_fuzzing`.
- **`rust/deny.toml.jinja`** — cargo-deny policy (advisories, license allow-list keyed on `license`, source allow-list keyed on `native_repo`).
- **`Makefile.jinja`** — `rust-deny` target; `rust-clippy` target (`cargo clippy --all-targets -- -D warnings`); `setup-fuzz` / `fuzz` / `fuzz-list` targets gated on `enable_fuzzing`; `cargo-deny` added to `setup-rust-tools`.
- **`.github/workflows/test-reusable.yml.jinja`** — `deny` job (cargo-deny) alongside the existing `audit` job; a Rust `clippy` step in the `test` job (Linux x86_64 leg, `-D warnings`).
- **`.github/actions/setup-rust/action.yml.jinja`** — installs the `clippy` component (dtolnay/rust-toolchain's minimal profile omits it, so the new `make rust-clippy` CI step needs it explicit).
- **`README.md.jinja`** — "Known Limitations" section (gated on `enable_web`) documenting that `flutter build web --wasm` / `flutter run -d chrome --wasm` (dart2wasm) is not supported. Calls into Rust fail with `Type 'JSValue' is not a subtype of type 'List<dynamic>'` because FRB's generated Dart decoders use implicit JS-array casts that only work under dart2js. Tracking upstream: [flutter_rust_bridge#2575](https://github.com/fzyzcjy/flutter_rust_bridge/issues/2575)

### Changed

- **`copier.yml`** — `frb_version` default bumped to `^2.12.0`.
- **`scripts/src/check_updates.dart.jinja`** — `--update` now also bumps the wrapper crate's version in `rust/Cargo.toml`, mirroring the upstream SemVer delta (upstream patch/minor/major bump → same component bumped in the crate, lower components reset; falls back to patch for unparseable versions). Previously a manual "Before Merge" step on every automated update PR; the AI changelog step therefore picks up the correct new crate version for the Highlights line.
- **`scripts/src/update_changelog.dart.jinja`** — the AI now also classifies the update severity (new required `bump` field: patch/minor/major, judged from release notes + commit list rather than version numbers) and, via the new `--crate-version-before` option, raises the crate version above the SemVer-mirror bump when its verdict is more severe — 0.x upstreams routinely ship breaking changes in minor releases, which pure mirroring under-bumps. The AI verdict never lowers the mirror bump. When the verdict is missing or invalid, the mirror bump stands and the PR gets a `bump-unverified` label plus a prominent ⚠️ warning in the body; breaking changelog bullets are prefixed with `**BREAKING:**`. The changelog step now runs before `Update Cargo.lock` so the lock file always reflects the final crate version.
- **`.github/workflows/check-{{ package_name }}-updates.yml.jinja`**:
  - idempotency gate: if an open update PR for the same version already exists, the scheduled run skips regeneration instead of force-pushing a near-identical commit over the PR branch (which also wiped any manual commits pushed to it); `force_update` bypasses the gate
  - installs the pinned FRB codegen binary (`make setup-frb-codegen`) and runs `make get` before `make codegen` — previously the binary was never installed on the runner, so the codegen step failed with exit 127 on every run and every update PR carried the `codegen-failed` label
  - PR body: removed the now-automated "Bump rust/Cargo.toml version" / "Run make rust-check" manual checklist items
- **`.claude/skills/update-{{ package_name }}/SKILL.md.jinja`** — Step 1 rewritten from "read the release notes" to a full upstream-diff analysis: commit list and changed files between tags via the compare API, diff scoped to the bound crates and the API surface referenced in `rust/src/api/`, upstream `Cargo.toml` deltas (MSRV, advisories); CHANGELOG verification now checks the AI entry against those findings.
- **`CLAUDE.md`** — all local template-testing commands now pass `--vcs-ref HEAD` with a note explaining that Copier otherwise renders from the latest git tag, silently ignoring uncommitted changes.

### Fixed

- **`hook/build.dart.jinja`** — download cache is now keyed by crate version and the full platform variant (`<version>-ios-device-arm64` vs `<version>-ios-simulator-arm64`) instead of `targetOS-targetArch`. On Apple-silicon hosts iOS device and simulator builds both mapped to `ios-arm64`, so whichever built first poisoned the cache for the other and dyld rejected the bundled library at runtime (`incompatible platform: have 'iOS-simulator', need 'iOS'`); a version bump could also serve a stale cached binary. Ported from [ospaarmann/openmls_dart](https://github.com/ospaarmann/openmls_dart) (credit: Ole Spaarmann).
- **`copier.yml`** — `_tasks` no longer set `working_directory` to `_copier_conf.dst_path` (tasks already run in the destination by default); with a relative destination path the value resolved against the destination itself (e.g. `gen/gen`) and every task failed. The `example_cli` task now uses a relative `working_directory: example_cli`
- **`CLAUDE.md.jinja`** — removed the `make build ARGS="--release"` example: the Makefile's `build` target already passes `--release`, so the duplicated flag made the documented command fail
- **`scripts/src/check_updates.dart.jinja`** — `updateVersionFiles` now matches `upstream_version` in `.copier-answers.yml` regardless of YAML quoting style (double-quoted, single-quoted, or unquoted) and preserves the original quoting when writing the new version. Previously the regex only matched double-quoted values, so projects whose `.copier-answers.yml` was written with single quotes (Copier's default) silently skipped the update

### Security

- **`hook/build.dart.jinja`** — native-library checksum verification is now **fail-closed**: if the SHA256 checksums cannot be fetched or lack an entry for the archive, the build aborts instead of loading an unverified binary. A `<PACKAGE_NAME>_ALLOW_UNVERIFIED_DOWNLOAD=1` escape hatch is provided for releases without a checksums file.
- **`rust/Cargo.toml.jinja`** — hand-written Rust is compiled with `unsafe_code = "deny"`, and the wrapper crate's release profile enables `overflow-checks` (scoped to the crate so audited upstream dependencies are untouched).
- **`rust/src/lib.rs.jinja`** — the FRB-generated module carries `#[allow(unsafe_code)]` so the deny lint applies only to hand-written code.
- **`.github/workflows/test-reusable.yml.jinja`** — least-privilege `permissions: contents: read` default on the reusable workflow.
- **`SECURITY.md.jinja`** — corrected inaccurate claims (removed the "Signed Releases" wording) and documented the fail-closed verification, cargo-deny, hardened profile, static analysis (Dart analyze + `cargo clippy` in CI), and (when enabled) fuzzing.

## [2.4.0] - 2026-02-15

### Added

- **`README.md.jinja`** — coverage badge (shields.io endpoint via GitHub Gist) with username auto-filled from `github_repo`
- **`CONTRIBUTING.md.jinja`** — "Setting up Coverage Badge" section with step-by-step guide (create Gist, PAT, repository secret/variable)
- **`CONTRIBUTING.md.jinja`** — "Setting up pub.dev Publishing" section with OIDC setup on pub.dev and GitHub environment configuration with deployment protection rules
- **`scripts/check_deployment_targets.dart.jinja`** — new script to check deployment target consistency (iOS/macOS/Android) across all project files. Reads expected values from `.copier-answers.yml` and verifies podspecs, CI workflows, Xcode projects, build.gradle, and README match. Supports `--update` to fix mismatches and `--set <version>` to change a target everywhere
- **`Makefile.jinja`** — `check-targets` command for running the deployment targets checker
- **`setup-rust/action.yml.jinja`** — Rust dependency caching via `Swatinem/rust-cache@v2` (speeds up CI builds, especially Windows where vendored OpenSSL takes ~10 min)
- **`setup-rust/action.yml.jinja`** — Strawberry Perl configuration for Windows to fix OpenSSL build (MSYS2 Perl from Git Bash is incompatible)
- **`build-{{ package_name }}.yml.jinja`** — `IPHONEOS_DEPLOYMENT_TARGET` env var for iOS builds using `ios_min_version` template variable (fixes linker errors when vendored C code is compiled with newer Xcode)

### Changed

- **`README.md`** — expanded "On GitHub (create environment)" instructions with detailed deployment protection rules steps and explanation why the `pub.dev` environment is required

### Changed

- **`copier.yml`** — post-generation message now references `CONTRIBUTING.md` instead of `README.md` for GitHub Actions setup instructions
- **`Makefile.jinja`** — replaced `dart run scripts/` with `dart scripts/` for 6 commands (`check-new-*-version`, `check-exists-*-frb-release`, `check-template-updates`, `update-changelog`, `version`, `get-version`), removing `.skip_*_hook` workaround where present. Scripts only use `dart:` and relative imports, so `dart run` (which triggers build hooks) is unnecessary

### Fixed

- **`hook/build.dart.jinja`** — local WASM builds now take priority over cached/downloaded files. Previously, if WASM files already existed in `web/pkg/`, the hook would skip updating them even when a newer local build was available in `rust/target/wasm32/`, causing stale content hash mismatches

### Removed

- **`pubspec.yaml.jinja`** — removed `flutter:` version constraint from `environment:` section. Pure Dart packages with native code don't need Flutter SDK constraint; `sdk:` is sufficient

## [2.3.2] - 2026-02-08

### Changed

- **`README.md.jinja`** — replaced vertical platform support table (one row per architecture) with compact horizontal layout showing platforms as columns with **Support** and **Arch** rows

## [2.3.1] - 2026-02-08

### Changed

- **`frb-patterns` Claude skill** — improved FRB patterns documentation with additional patterns from real-world usage:
  - Added anti-pattern example (`❌ WRONG`) to Constructor-Style API Pattern section showing incorrect top-level function vs correct `impl` block approach
  - Added "Adapter Pattern for Upstream Traits" subsection with generic `StoreAdapter` example for bridging DartFn callbacks to upstream trait implementations via `#[async_trait(?Send)]`
  - Added "No Threading on WASM" warning about `parking_lot::Mutex` and single-threaded web constraints

## [2.3.0] - 2026-02-08

### Changed

- **`macos_min_version` default**: `10.14` → `10.15`

## [2.2.3] - 2026-02-07

### Removed

- **`prepare-release` Claude command** — redundant; the `release-package` Claude skill already covers this functionality
- **`update-template` Claude command** — redundant; the `update-template` Claude skill already covers this functionality

### Changed

- **`CLAUDE.md.jinja`** — replaced "Claude Commands" section with "Claude Skills" section

## [2.2.2] - 2026-02-07

### Fixed

- **`platform_io.dart.jinja`** — added `coverage:ignore` annotations for untestable platform code (AOT mode library loading, `openLibraryFromPath`)

## [2.2.1] - 2026-02-07

### Fixed

- **`.gitignore.jinja`** / **`.pubignore.jinja`** — only ignore `.claude/settings.local.json` instead of the entire `.claude/*` directory (previously required `!.claude/skills/` exclusion pattern)

## [2.2.0] - 2026-02-07

### Added

- **`release-package` Claude skill** — detailed guide for preparing package releases (versioning rules, CHANGELOG format, pre-release validation, publishing flow)
- **`prepare-release` Claude command** — slash command (`/project:prepare-release`) to automate release preparation: update pubspec.yaml version, update CHANGELOG.md, run publish-dry-run
- **`update-template` Claude command** — slash command (`/project:update-template`) to automate copier template update: check for updates, run copier update, resolve conflicts, verify quality

## [2.1.1] - 2026-02-07

### Changed

- **`build-{{ package_name }}.yml.jinja`** — upstream library reference in release notes is now a bold markdown link to the GitHub release (e.g., `**Based on [libsignal v0.87.0](https://github.com/signalapp/libsignal/releases/tag/v0.87.0)**`)

## [2.1.0] - 2026-02-07

### Added

- **`ios_min_version` variable** (default: `13.0`) — iOS minimum deployment target, used in `ios/*.podspec`
- **`macos_min_version` variable** (default: `10.14`) — macOS minimum deployment target, used in `macos/*.podspec`

### Fixed

- **`build-{{ package_name }}.yml.jinja`** — fix `${VERSION}` not interpolated in release notes (heredoc used `<<'EOF'` which disables variable expansion, changed to `<<EOF`)
- **`build-{{ package_name }}.yml.jinja`** — add upstream native library version to release notes when `upstream_crates` is set (e.g., "Based on libsignal v0.87.0")

## [2.0.1] - 2026-02-07

### Changed

- **`template/{{ _copier_conf.answers_file }}.jinja`** - remove comment

## [2.0.0] - 2026-02-07

### Changed (BREAKING)

- **`upstream_crate` variable removed** — consolidated into `upstream_crates` (comma-separated). Use `upstream_crates=libsignal-protocol` for single crate, `upstream_crates=libsignal-protocol,libsignal-core` for multiple
- **`strip_version_prefix` boolean replaced with `version_tag_prefix` string** — default `"v"` strips `v` prefix from tags like `v1.0.0`. Set to custom prefix (e.g. `release-v`) for repos with non-standard tag schemes (like `release-v1.0.0`)

### Changed

- All template conditionals simplified from `upstream_crate or upstream_crates` to just `upstream_crates`
- `check_updates.dart.jinja` — version normalization now uses configurable `_tagPrefix` constant with fallback to `v`/`V`
- `common.dart.jinja` — removed separate `getUpstreamVersion()` for single crate; unified to use `upstream_crates` loop
- `Cargo.toml.jinja` — unified dependency generation to single loop for `upstream_crates`
- Updated all documentation (README, CLAUDE.md, CONTRIBUTING.md) and skills to reflect new variable names
- `copier.yml` — simplified `upstream_version` visibility condition, consolidated post-generation message

### Added

- **`template/{{ _copier_conf.answers_file }}.jinja`** — Copier answers file template for generated projects (enables `copier update` to track template version)

## [1.9.0] - 2026-02-06

### Fixed

- **`test.yml.jinja`** — fix `workflow_run` trigger referencing wrong workflow name (`"Build {{ package_name }} Native Libraries"` → `"Build {{ package_name }} FRB Libraries"`), causing tests to never auto-trigger after build completion
- **`build-{{ package_name }}.yml.jinja`** — fix env var name in check-release step (`GH_TOKEN` → `GITHUB_TOKEN`). The Dart script reads `GITHUB_TOKEN`, not `GH_TOKEN` (which is for the `gh` CLI)
- **`example_pubspec.yaml.jinja`** — upgrade `flutter_lints` from `^5.0.0` to `^6.0.0`
- **`.pubignore.jinja`** — include Rust source files in published package (only exclude `rust/target/` build artifacts, not entire `rust/` directory); add trailing newline

## [1.8.0] - 2026-02-06

### Changed

- **`CLAUDE.md` template** — merged "Quick Reference" table into "Available Makefile Commands" section to eliminate duplication. Added missing commands: `setup-protoc`, `setup-web`, `setup-android`, `doc`, `rust-update`, `check-new-*-version`, `check-template-updates`, `update-changelog` (with Jinja2 conditionals for optional features)

### Fixed

- **`analysis_options.yaml` template** — added `example/**` and `example_cli/**` to analyzer excludes. These are separate packages with their own `analysis_options.yaml` and should not be analyzed as part of the main package. Without this exclude, `flutter analyze` fails in CI when `example_cli/` dependencies are not resolved

### Added

- **`check_updates.dart` script** — now also updates `upstream_version` in `.copier-answers.yml` when updating upstream version (step 4 in `updateVersionFiles()`). The check-updates workflow PR body shows `.copier-answers.yml` status alongside other updated files

## [1.7.2] - 2026-02-05

### Changed

- **`update-template` Claude skill** — document manual `_commit` update in `.copier-answers.yml` when copier fails to update it (merge conflicts or no file changes)

## [1.7.1] - 2026-02-05

### Added

- **`update-template` Claude skill** — step-by-step guide for reviewing automated PRs, running `copier update`, resolving conflicts, and quality checks
  - Documents `--defaults` flag for non-interactive `copier update` (required for Claude Code)

## [1.7.0] - 2026-02-05

### Added

- **`check-template-updates.yml` workflow** — daily CI check for new copier template versions with automated notification PR containing version comparison, changelog, and update instructions
- **`check_template_updates.dart` script** — checks `.copier-answers.yml` against latest template release, supports `--json`, `--ci-output`, `--version`, `--force` flags
- **`make check-template-updates` target** — Makefile command for template version checking
- **`update-template` Claude skill** — step-by-step guide for reviewing automated PRs, running `copier update`, resolving conflicts, and quality checks
  - Documents `--defaults` flag for non-interactive `copier update` (required for Claude Code)

### Changed

- Renamed Claude skill `ffi-patterns` → `frb-patterns` to match Flutter Rust Bridge architecture
- Removed unused `GITHUB_TOKEN` from `check_updates.dart` (not needed for public GitHub API with 1 req/day)

## [1.6.0] - 2026-02-05

### Added

- **`get_android_min_sdk.dart` script** — reads `minSdk` from `android/build.gradle` dynamically
- **Auto-format on generation** — added `dart format .` as post-generation task to ensure all generated Dart code is properly formatted

### Changed

- **`make build-android` reads minSdk dynamically** — no longer hardcoded, reads from `android/build.gradle` via script (single source of truth)
- **Simplified example app naming:**
  - Flutter example: `--project-name` changed from `{{ package_name }}_example` to `example`
  - CLI example: main file changed from `bin/{{ package_name }}_cli.dart` to `bin/main.dart`
- **Updated `update-{{ package_name }}` skill documentation:**
  - Updated commands to use `make check-new-{{ package_name }}-version` instead of `make check`
  - Simplified manual update process documentation
  - Removed SKILL.md from auto-updated files list (no longer contains version-specific examples)
- **Improved Jinja2 whitespace handling** — using `{%-` / `-%}` syntax in workflow files to prevent extra blank lines
- **Removed auto-update of SKILL.md** — `check_updates.dart` no longer updates `.claude/skills/update-{{ package_name }}/SKILL.md`

### Removed

- **Redundant comment in `build.gradle.jinja`** — removed "Native libraries are in src/main/jniLibs/" comment

## [1.5.0] - 2026-02-04

### Changed

- **Renamed `make update` → `make rust-update`** — clearer naming indicating this command updates Rust dependencies (Cargo.lock)
- **Synchronized `hook/build.dart.jinja` with reference project:**
  - Added section separator comments (`// ===`) for Web Build Support, Native Build Support, Download Support
  - Simplified `_AssetInfo` class — removed `linkMode` field (always `DynamicLoadingBundled()`)
  - Simplified `_resolveAssetInfo` — uses new `_getPlatformArchName` helper
  - Replaced `_linuxArchName`, `_macOSArchName`, `_iOSTargetName` with unified `_archName` and `_getPlatformArchName`
  - Added extended documentation header with "How it works" and "For development" sections

## [1.4.0] - 2026-02-04

### Fixed

- **Native library loading for pure Dart CLI applications:**
  - **JIT mode** (`dart run`): loads from `.dart_tool/lib/`
  - **AOT mode** (`dart build cli`): loads from `bundle/lib/` relative to executable
  - Enables standalone executables to be distributed and run from any location

### Security

- **Remove CWD-based library search** to prevent library hijacking attacks:
  - Previously searched `rust/target/release/` in current working directory
  - Attacker could place malicious library in CWD to hijack application
  - Now only searches trusted paths: build hook locations and executable-relative paths

### Changed

- **Simplified library loading** — removed `findLibraryPath` and `findPackageRoot` functions from `platform_io.dart`

## [1.3.6] - 2026-02-03

### Added

- **"Review Automated PR" section in update skill** — new detailed checklist with 10 steps for reviewing automated dependency update PRs, including:
  - Analyzing release notes for breaking changes
  - Fixing Rust compilation errors
  - Bumping FRB crate version
  - Syncing Cargo.lock

### Changed

- **Improved check-updates workflow PR instructions:**
  - Added "Bump `rust/Cargo.toml` version" step to Before Merge section
  - Added "Run `make rust-check`" step to sync Cargo.lock
  - Simplified After Merge section (removed redundant rust/Cargo.toml mention)
- **AI changelog now generates two Highlights lines:**
  - One for native library version (e.g., `**testlib v1.0.0** — description`)
  - One for FRB crate version (e.g., `**test_sync_frb v1.0.2** — Rust FFI bindings`)
  - Added `_readFrbVersion()` function to read crate version from `rust/Cargo.toml`

## [1.3.5] - 2026-02-03

### Changed

- **`create-project` skill improvements:**
  - Added complete post-generation workflow with numbered steps
  - Added warning that `make build` is required before `make test`
  - Added "Quality Verification" section with all quality checks (`make analyze`, `make test`, `make format-check`, `make rust-check`, `make rust-audit`, `make publish-dry-run`)
  - Added "Platform-Specific Builds" section

## [1.3.4] - 2026-02-03

### Added

- **`create-project` Claude skill** — new skill for generating projects from the template, supports both local files (`--vcs-ref HEAD`) and GitHub with specific version (`--vcs-ref v1.0.0`)

## [1.3.3] - 2026-02-03

### Fixed

- **Dart formatting compliance** — all generated `.dart` files now pass `dart format --set-exit-if-changed`:
  - Added blank line after shebang (`#!/usr/bin/env dart`) in scripts
  - Fixed Jinja2 whitespace handling using `{%-` / `-%}` syntax to prevent extra blank lines
  - Corrected indentation in long expressions (Process.run, Map literals, replaceAll, etc.)
  - Removed extra blank lines in test files and conditional blocks

## [1.3.2] - 2026-02-03

### Added

- **get_flutter_version.dart script** — new cross-platform script to read Flutter version from `.fvmrc`

### Changed

- **FVM setup reads version from .fvmrc** — Makefile now uses `dart scripts/get_flutter_version.dart` instead of hardcoded version, making it easier to update Flutter version in one place
- **Git repository initialized on project creation** — added `git init` task to copier post-generation
- **example_cli dependencies** — added `dart pub get` task after pubspec.yaml replacement to ensure dependencies are resolved

### Fixed

- **Unused import in widget test** — removed `package:flutter/material.dart` import from `example_widget_test.dart.jinja`

## [1.3.1] - 2026-02-03

### Added

- **Widget test for Flutter example app** — new `example_widget_test.dart.jinja` with basic app tests

### Changed

- **analysis_options.yaml improvements:**
  - Added exclude for FRB-generated files (`lib/src/rust/**`)
  - Added exclude for build scripts (`hook/**`, `scripts/**`)
- **FVM setup command** — changed `fvm install` to `fvm use --force` for more reliable setup
- **Example apps cleanup:**
  - Flutter example now uses custom widget test instead of default
  - CLI example removes default `test/` and `lib/` directories
- **Code style improvements across templates:**
  - Class fields moved after constructors (Dart style guide)
  - Cascade notation (`..writeln`) for StringBuffer operations
  - Tear-off syntax for callbacks (`tearDown(cleanup)`)
  - Better JSON type casting in platform_io.dart and update_changelog.dart
- **Script documentation** — improved doc comments with proper formatting and `library;` directives
- **Unused import warnings** — added `// ignore: unused_import` in example apps

### Fixed

- **Lint compliance** — added appropriate `ignore_for_file` directives:
  - `avoid_dynamic_calls` in platform_io.dart
  - `avoid_classes_with_only_static_members` in common.dart
- **Test file improvements:**
  - Fixed import order (test package first)
  - Simplified test assertions using `returnsNormally`
  - Removed redundant version tests

## [1.3.0] - 2026-02-02

### Added

- **New template variables for Android:**
  - `android_gradle_version` (default: `8.11.1`) — Android Gradle plugin version
  - `android_java_version` (default: `17`, choices: `11`, `17`, `21`) — Java version for Android compilation
- **Example app improvements:**
  - Added `.gitignore` files for both Flutter and CLI examples
  - Added `analysis_options.yaml` for CLI example (disables `avoid_print` lint)
  - Added iOS/macOS xcconfig files for proper CocoaPods configuration
  - Added `--org` parameter when creating Flutter example app
- **Pre-commit hook now runs `make rust-check`** — validates Rust code before commits
- **Test workflow triggers on `rust/**` changes** — ensures tests run when Rust code is modified
- **Coverage badge now uses color range** — badge color reflects coverage percentage (50-90% range)

### Changed

- **Android defaults updated:**
  - `android_min_sdk`: `21` → `24` (Android 7.0+)
  - `android_compile_sdk`: `34` → `36`
- **Rust Cargo.lock is now committed** — removed from `.gitignore` for reproducible builds
- **Simplified Makefile:**
  - Removed `make combine` target (unused)
  - Removed `make regen` alias (use `make codegen` directly)
  - Removed `.skip_{{ package_name }}_hook` workarounds from build commands
  - Added informative build completion messages
- **Improved pre-commit hook** — added colored output and Rust checking
- **Improved check-updates workflow:**
  - Simplified status tracking with boolean `success` outputs
  - Cleaner PR description format
- **Improved test-reusable workflow:**
  - Simplified Rust setup (removed explicit target specification)
  - Removed badge secrets validation step
- **Cleaned up Jinja2 whitespace** — using `{%-` syntax for cleaner output in multiple templates
- **Updated .pubignore** — added `docs/`, `rust/target/`, generated plugin files

### Fixed

- **LICENSE.jinja** — added complete AGPL-3.0 license text (was truncated)
- **analysis_options.yaml** — removed incorrect exclude for `lib/src/bindings/**`

### Removed

- **security-review Claude skill** — removed from generated projects
- **combine_artifacts.dart script** — no longer needed

## [1.2.0] - 2026-02-01

### Changed

- **BREAKING: Flat template structure** - Template no longer creates a `{{ package_name }}/` subdirectory
  - Files are now generated directly in the destination directory
  - Enables proper `copier update` support for existing projects
  - New usage: `mkdir my_package && cd my_package && copier copy <template> .`
- Updated `_tasks` working directories to use `{{ _copier_conf.dst_path }}` directly
- Updated post-copy message with new workflow instructions

### Fixed

- `copier update` now works correctly for existing projects

## [1.1.0] - 2026-02-01

### Added

- **Multiple upstream crates support**: New `upstream_crates` variable for projects that depend on multiple crates from the same git repository (e.g., `libsignal-protocol,libsignal-core,signal-crypto`)
- Updated `rust/Cargo.toml.jinja` to generate dependencies for all specified crates
- Updated `scripts/src/common.dart.jinja` with `getUpstreamVersion()` function supporting multiple crates
- Updated `scripts/src/check_updates.dart.jinja` to update all upstream crate versions simultaneously
- Updated `scripts/check_exists_frb_release.dart.jinja` for multiple crates support
- Updated `.github/workflows/build-*.yml.jinja` for multiple crates support

### Changed

- `upstream_crates` and `upstream_crate` are now mutually exclusive - use one or the other
- Improved documentation for upstream crate configuration in `copier.yml`

## [1.0.0] - 2026-02-01

### Added

#### Core Features
- Copier template for Flutter Rust Bridge (FRB) projects
- Flutter Rust Bridge integration for type-safe Dart-Rust bindings
- Dart Native Assets build hook for automatic library download
- SHA256 checksum verification for supply chain security
- Retry logic for network operations with exponential backoff

#### Cross-Platform Support
- Android (arm64-v8a, armeabi-v7a, x86_64)
- iOS (arm64 device, arm64/x86_64 simulator)
- macOS (arm64, x86_64)
- Linux (x64, arm64)
- Windows (x64)
- Web/WASM (optional via `enable_web`)

#### GitHub Actions Workflows
- `test.yml` / `test-reusable.yml` - Multi-platform testing with coverage
- `build-<package>.yml` - Native library builds for all platforms
- `publish.yml` - pub.dev publishing with OIDC + GitHub Release creation
- `check-<package>-updates.yml` - Automated upstream version checking
- Rust security audit via `cargo-audit`
- Coverage badge support via GitHub Gist

#### Template Variables
- Required: `package_name`, `description`, `native_library_name`, `github_repo`, `native_repo`
- Rust config: `crate_name`, `rust_edition`, `rust_version`, `frb_version`
- Upstream crate: `upstream_crate`, `upstream_version`, `strip_version_prefix`
- Flutter/Dart: `flutter_version`, `dart_sdk_version`, `flutter_sdk_version`
- Android: `android_min_sdk`, `android_compile_sdk`, `android_ndk_version`
- Feature flags: `enable_web`, `enable_claude`
- Metadata: `license`, `topics`

#### Developer Experience
- FVM (Flutter Version Manager) integration with Windows support
- Makefile with common commands (setup, codegen, build, test, coverage)
- Claude Code skills for generated projects (optional via `enable_claude`)
- Comprehensive documentation templates (README, CONTRIBUTING, SECURITY, CHANGELOG, CLAUDE.md)
- Automatic example app creation (Flutter GUI + CLI)
- Variable validators with helpful error messages
- Jinja2 templating with case conversion filters (jinja2-strcase)

#### Generated Project Features
- Pre-configured `analysis_options.yaml` with recommended lints
- GitHub Actions setup instructions in README
- Coverage badge setup guide
- Security policy template
- Git hooks for pre-commit checks

[Unreleased]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.5.2...v3.0.0
[2.5.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.5.1...v2.5.2
[2.5.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.5.0...v2.5.1
[2.5.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.4.0...v2.5.0
[2.4.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.3.2...v2.4.0
[2.3.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.3.1...v2.3.2
[2.3.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.3.0...v2.3.1
[2.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.3...v2.3.0
[2.2.3]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.2...v2.2.3
[2.2.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.1...v2.2.2
[2.2.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.9.0...v2.0.0
[1.9.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.2...v1.8.0
[1.7.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.1...v1.7.2
[1.7.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.7.0...v1.7.1
[1.7.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.6...v1.4.0
[1.3.6]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.4...v1.3.5
[1.3.4]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.3...v1.3.4
[1.3.3]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.2...v1.3.3
[1.3.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.1...v1.3.2
[1.3.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/releases/tag/v1.0.0
