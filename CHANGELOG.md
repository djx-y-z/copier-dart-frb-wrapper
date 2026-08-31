## [Unreleased]

### Changed

- **Dependabot no longer rewrites constraints it was told to leave alone** (`template/.github/dependabot.yml.jinja`) — `pub`'s default versioning strategy is `widen`, "extend only the upper bound to include the new version", and it applies that across the whole manifest rather than only to what it is updating. Measured on the first run in a generated project: a pull request whose four updates were `ffigen`, `lints`, `code_assets` and `hooks` also rewrote `flutter_rust_bridge` from `">=2.12.0 <2.12.1"` to `^2.12.0` — the one constraint that must not float, and the exact regression that broke consumers when 2.13.0 landed inside that caret. It widened `lints`, `ffigen` and `hooks` past bounds set on purpose as well.

  `ignore` is no defence here and it is worth being precise about why: it stops Dependabot opening a pull request *for* a dependency, not editing that dependency's constraint while it edits the file for other reasons. `flutter_rust_bridge` was ignored and was rewritten anyway. `versioning-strategy: increase-if-necessary` is the fix — a constraint that already admits the new version is left alone, so a dependency nothing is updating stays untouched. `cargo` needs none of this: measured on the same run, it changed exactly the one crate it was bumping and left every pin alone.

  `make verify-frb-pins` caught the rewrite on all four platforms before it could merge, on its first real encounter, which is what that gate exists for.

- **The `pub` and `cargo` groups take minor and patch only** (`template/.github/dependabot.yml.jinja`) — grouping a major with everything else blocks the rest: one unmergeable entry takes the whole pull request down, and the only action left is to close it. For `pub` this does what it says — `ffigen` 20 -> 21 and `hooks` 1 -> 2 now arrive on their own.

  For `cargo` it is close to a no-op, and the note in the config says so rather than implying otherwise. Cargo crates are overwhelmingly 0.x, where the *minor* is the breaking bump, and Dependabot classifies by the version string: `rand` 0.9 -> 0.10, `sha2` 0.10 -> 0.11 and `rusqlite` 0.34 -> 0.40 are all `version-update:semver-minor` in its own commit trailers. So the filter does not separate the breaking ones there; CI does, and did — `rand` 0.9 -> 0.10 failed to compile against seven files in a generated project. What the filter still buys is a genuine 1.x -> 2.x arriving on its own.

### Fixed

- **One bullet still told a generated project the changelog step always fails** (`template/CONTRIBUTING.md.jinja`) — 4.6.0 replaced the retired provider and rewrote the three places CONTRIBUTING described it: the update recipe, the "Setting up AI Changelog" section and the make-target line. It missed a fourth, in the bulleted list of what the update automation does, which still read "**currently fails on every run**" eight lines above the section that now explains how to configure the model making it work. The same sweep-for-the-claim-not-the-line that 4.6.0's own entry describes would have caught it; it was found instead by adopting 4.6.0 into a generated project, where the stale bullet came back as the template's side of a merge conflict.

  Only a project generated fresh from 4.6.0 is affected. Both existing projects had long since replaced that whole region with their own one-line summary, so the adoption resolved that hunk in their favour and neither carries the text — checked in both rather than assumed.

## [4.6.0] - 2026-08-31

### Added

- **A `provider/model` list replaces the retired GitHub Models** (`template/scripts/src/ai_client.dart`, `template/test/scripts/ai_client_test.dart`, both `update_changelog` files, both `update_template` files, both update workflows) — GitHub Models was retired on 2026-07-30, which took `make update-changelog` and the CHANGELOG entry of `make update-template` with it in every project generated from this template. Pointing the same code at a different provider would have restored the fault along with the feature: the provider was hard-coded, so every future retirement costs a code change that has to reach every generated project through a template release. `AI_MODELS` now holds an ordered `provider/model` list and the first entry that has a key and answers wins, which makes the next switch a repository-variable edit.

  **There is deliberately no default list.** Unset means nothing is called and the entry is simply not written — a model that writes into a repository's CHANGELOG should be one somebody named rather than one a template picked, and an unset list is also how a generated project says "no AI here" without a provider sitting there waiting for a key to appear. The one case that warns loudly is keys present with no list, because that is a misconfiguration and not an opt-out.

  Anthropic, Google and OpenRouter are each called through their own API over `dart:io` rather than a `curl` subprocess, for two reasons that both bite here: the HTTP status is what decides whether the next entry is tried, and a subprocess puts the key in process arguments where any local process can read it. The next entry is tried only when a model produced **no** answer — a network failure, an auth/rate-limit/server status, a refusal, or a response cut off at the token limit — never on the *content* of an answer, because the next provider would not write a better entry and switching on quality would make the CHANGELOG silently inconsistent, and never on a malformed request, so a bug in what is sent stays visible instead of being papered over by the second entry. The single exception is narrow and was found by walking the list with deliberately invalid keys: Google answers an invalid key with `400 API_KEY_INVALID` where Anthropic uses `401`, and reading that as a malformed request would halt at a misconfigured first entry — precisely what the list exists to survive.

  Nothing is salvaged from a partial answer. The previous code wrote whatever it failed to parse straight into the `changed` field, which turns a malformed answer into a malformed CHANGELOG, and a response truncated at the token limit still contains a brace-delimited fragment that looks extractable. Truncation and refusal are rejected before the content is read at all, and a missing field fails into the state the workflow already handles: no entry, and a pull request labelled `changelog-needed`.

  The key cannot reach a log by construction — one request header per provider, never a URL, never process arguments, never the prompt, and the priority line prints model ids and variable *names* only. The one indirect path is the provider's own error body, which is quoted into logs and pull-request output, so every failure path funnels through one catch and the key is stripped there.

  `ai_client.dart` carries no project- or upstream-specific naming and ships byte-identical to the project it was built and measured in, where a live run cost 14 317 input / 569 output tokens, $0.0858 a call, roughly $0.51 a month at six updates. Ported here with its 48 tests; 186 script tests pass in a render of each of the two projects generated from this template, `make analyze --fatal-infos` reports nothing in `scripts/` or `test/scripts/`, and `make format-check` is clean on one render and reports only the pre-existing `check_updates.dart` case on the other.

  **A generated project is not configured by this release.** It needs `AI_MODELS` as a repository variable and a provider key as a secret before the next scheduled run writes anything; until then the update workflows degrade exactly as they did — pull request opened, entry recorded as not written, `changelog-needed` applied. `AI_MODELS_TOKEN` is now read nowhere and can be deleted.

- **Each project states what it binds and exposes, and the entry is judged against it** (`template/.github/agent-prompts/changelog-scope.md.jinja`, `copier.yml`) — the prompt's job is to classify every upstream change as reaching this package's users or not, and it could not do that against a list it did not have. It now reads `.github/agent-prompts/changelog-scope.md`, alongside the two agent prompts already there. A change earns its own bullet only when it lands in a bound crate **and** touches something named under "Exposed surface"; landing in a bound crate is not sufficient, because most of what those crates contain is never reached from a wrapper.

  It is a file and not an answer because it is the one thing about a wrapper that no `copier.yml` question can hold, and because it is edited over the project's life rather than at generation. `_skip_if_exists` keeps it: written once, never overwritten, and recreated if absent — so an existing project picks it up on its next update and never conflicts on it afterwards. What arrives is a starting point derived from `upstream_crates`; the "Exposed surface" and "Not bound or exposed" lists have to be written by whoever knows them. With the file missing entirely the prompt falls back to the crate list alone, which is weak on purpose: a model given no list at all treats everything upstream as in scope, which is the failure the file exists to prevent.

- **`make verify-frb-pins`, a third gate of the shape the repository already has** (`template/scripts/src/frb_pins.dart`, `template/scripts/verify_frb_pins.dart`, `template/test/scripts/frb_pins_test.dart`, `template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`, `template/.github/workflows/test.yml.jinja`) — five files record the flutter_rust_bridge version, and `frb_generated.dart`'s is compared to the runtime's with `==`, so a disagreement is not untidiness: it is a package that throws on init in somebody else's app. The exact-range constraint shipped in this same release stops the resolver drifting; nothing stopped a person editing four of the five. This reads `pubspec.yaml`, `rust/Cargo.toml`, the Makefile's `FRB_CODEGEN_VERSION`, the committed bindings and `.copier-answers.yml`, and reports every disagreement at once rather than the first — they move as a set, and a reader fixing them one run at a time learns the set only by rediscovering it.

  It also checks the *form* of the pubspec constraint, not only the number, because two wrong forms fail in ways that look nothing alike: a caret admits versions the runtime assert rejects, and a bare `X.Y.Z` admits the right one but makes the package unpublishable, `dart pub publish` exiting 65 on the "should allow more than one version" warning that `make publish-dry-run`, `make release` and `publish.yml` all gate on. Both are rejected with the reason. Absent bindings are tolerated — a project generated but never built has none, and failing there would make the gate impossible to satisfy on a first run.

  It reads every occurrence rather than the first, because the first is not always the one that counts: a `dependency_overrides` entry replaces the dependency outright, a second `flutter_rust_bridge` under `dev_dependencies` resolves beside it, the rendered `rust/Cargo.toml` already carries a `[target.'cfg(target_arch = "wasm32")'.dependencies]` section where a second pin is an ordinary thing to write, and make resolves a later `=` over an earlier `?=`. Each of those was a silent pass. In the other direction, a trailing `# comment` on the constraint and a quoted `frb_version` were silent failures — the second one a hazard the tool invites, since its own error text sends the reader to that file and `copier.yml`'s default for the answer is written quoted.

  `frb_version` also gains a validator, because two answers could render a project that fails its own new gate on the first commit. `2.12` crashed copier mid-render on the missing third component, and a pre-release such as `2.13.0-beta.1` rendered an upper bound of `<2.13.1` — `'0-beta' | int` is `0` — which admits the 2.13.0 final and every other 2.13.0 pre-release, precisely the hole an exact pin exists to close. Both are now answer-time errors that say why.

  Five file reads, no build and no network, so it costs nothing to gate on: it runs on the Linux leg beside `verify-third-party-notices`. `.copier-answers.yml` joins the `test.yml` path filters for the same reason `THIRD_PARTY_NOTICES.txt` is already there — a commit that edits only `frb_version` is exactly the commit that can put the pins out of step, and it was the one commit that would not have run the check.

- **Dependabot watches `pub` and `cargo`, not only `github-actions`** (`template/.github/dependabot.yml.jinja`) — the flutter_rust_bridge break arrived as a silent resolve rather than as a reviewable pull request, and one reason is that no ecosystem carrying it was watched at all. The published package's own constraints and the native crate's dependencies are now both watched weekly, grouped one pull request each. `flutter_rust_bridge` itself is ignored in both, and that is not an oversight: its version has to move in four places at once and the bindings have to be regenerated by that exact codegen, so a pull request editing one file is wrong by construction. `make verify-frb-pins` is what catches it instead. The upstream crates are ignored under `cargo` for a different reason — Dependabot's cargo updater does follow git refs, so without that it would open its own pull request for the same bump `check-<package>-updates.yml` exists to make, with none of the work that one does: no codegen, no bindings tripwire, no CHANGELOG entry, no version badge. Only the package root and `rust/` are watched — `example/`, `example_cli/` and `rust/fuzz/` are not published, their drift cannot reach a consumer, and each extra directory multiplies the weekly pull requests against a repository whose four-platform matrix is the scarce resource.

- **A repair agent and a review agent, off until somebody names one** (`template/.github/workflows/repair-build.yml.jinja`, `template/.github/workflows/ai-review.yml`, `template/.github/agent-prompts/`, `template/.github/agent-config/opencode.json`) — `repair-build.yml` attempts a fix when `main` goes red, files an issue carrying the diagnosis when it cannot, and retires that issue once `main` is green again; `ai-review.yml` reviews a pull request and leaves one comment, updated in place. Both run on either `claude-code` or OpenCode, against the same prompt files, selected by `AGENT_ENGINE` — and neither engine nor model has a default, so an unconfigured project gets a notice and no run rather than a workflow that silently starts spending on a model nobody chose.

  Both use the same three-job split, and it is the security design rather than tidiness: the job the agent runs in holds no credential that can write to the repository, and the job that publishes runs no agent. The reviewer goes further and is read-only by its tool list — no write, no edit, no patch, no shell — because it reports through its final message rather than by leaving a file behind. It **gates nothing** and has no verdict meaning "approved".

  Ported from the project this was built and measured in, where the reviewer has three live runs and the repair agent none. What those runs are worth knowing for: on one unchanged diff the reviewer produced three different lists of findings, one real bug among four claims, and the real bug appeared in a single run of the three. Treat it as a sampling process rather than a check — which is why the workflow refuses to become a merge gate, and why the false-positive rate has to be measured on merged pull requests before that is reconsidered.

  `repair-build.yml` is the only one of the two that needs rendering (a `{% raw %}{% if enable_protoc %}{% endraw %}` around one step); the rest are copied verbatim, and the renderer was checked by diffing its output against the source project — four of the five files come out byte-identical, the fifth differing only in the two lines this template deliberately generalises.

### Changed

- **`make format-check` checks instead of writing** (`template/Makefile.jinja`) — `dart format --set-exit-if-changed .` reformats the files and *then* exits non-zero, so the gate edited the tree it was asked to inspect. Two consequences, both measured. The pre-commit hook aborts the commit on step 1 and leaves behind a modification the committer never made; the second attempt then passes, with that edit still in the tree. And the template-update workflow runs the same gate before `create-pull-request`, so it repaired its own pull request, recorded `format=false` for it, and let `git add -A` commit the repair — a reported failure that cannot be reproduced from the branch it is reported on. `--output=none` makes it read-only (verified: exit 65, file byte-identical on disk). `make format` remains the one that writes. This lands with the fix below, and depends on it: until an update stopped shipping unformatted files, the mutating gate was accidentally load-bearing.

- **The pre-commit Rust gate now also watches the cargo configuration** (`template/.githooks/pre-commit.jinja`) — 4.5.0 justified skipping the gate with "nothing outside `rust/` … no root `.cargo/config.toml` … feeds into it". That was a reading of the current file listing, not of the mechanism, and the mechanism disagrees: cargo resolves its configuration from the **current directory** upwards, not from the manifest, and `make rust-check` is `cargo check --manifest-path rust/Cargo.toml` run from the repository root. Measured on a synthetic crate with cargo 1.92.0: a root `.cargo/config.toml` injecting `--cfg` *is* applied, and `rust/.cargo/config.toml` is *not*. So a commit that changed only the root cargo configuration changed what `cargo check` does and skipped the check that would have run it. `<root>/.cargo/` already exists in a generated project — it holds `audit.toml` — which makes adding a `config.toml` beside it an ordinary thing to do rather than a hypothetical.

  The pathspec is now `rust .cargo rust-toolchain.toml`. `git diff` does not object to a pathspec that matches nothing, so the two new ones cost nothing until they exist, and `.cargo` rather than `.cargo/config.toml` is deliberate: it also matches `audit.toml`, which `cargo check` does not read, so an advisory-triage commit pays for a check it does not need. That is the direction to be wrong in — a false positive costs a warm second, a false negative commits unbuilt Rust — and it covers the legacy extensionless `.cargo/config` too. Every case 4.5.0 was verified against was re-run against the shipped predicate and is unchanged; only the root-cargo-config case moved, from skipped to checked.

- **The test suite no longer skips the pull request that most needs it** (`template/.github/workflows/test.yml.jinja`) — `update-<package>-*` branches were excluded on the grounds that a dependency bump moves the upstream version ahead of the published native binary. That was the more dangerous half of the trade: the bump — the one pull request whose entire payload is new native code — became the only one merged without the suite, clippy, `rust-test`, `cargo-deny`, the MSRV check or `verify-third-party-notices` ever running against it on any of the four platforms. What justified the skip is already handled by the reusable workflow, which runs `make build` before `make test`, after which the build hook finds `rust/target/release` and returns without downloading; nothing caches `.dart_tool`, so on a fresh runner the first hook run happens after that build — which is the procedure that used to be carried out by hand before merging one of these.

- **Three floating inputs decided one way or the other, rather than left unexamined** (`template/pubspec.yaml.jinja`, `template/.github/workflows/test-reusable.yml.jinja`) — `pubspec.lock` is deliberately not committed for a library, so CI re-resolves on every run and every caret is a live input. `lints` is now capped to one minor line: `make analyze ARGS="--fatal-infos"` turns any newly-added info-level lint into a build failure, so a minor published upstream reddens `main` with nobody having changed a line. This is precautionary and not a live fix — 6.1.0 is already published and both generated projects were measured against it with nothing to report, so the mechanism is real but has not yet fired. Patches still arrive inside the range, and the minor bump now comes as a Dependabot pull request the matrix actually evaluates instead of arriving between two unrelated runs. `ffigen`'s floor moves to `^20.1.1`, matching the higher of the two floors the generated projects had drifted to. `hooks` and `code_assets` stay on the caret deliberately — they define the protocol `hook/build.dart` implements and the SDK is the other half of it, so capping them below what the pinned Flutter expects breaks the hook at a consumer's build, which is worse than the drift.

  The `test` job's Rust toolchain stays `stable` while the MSRV job pins, and that asymmetry is now written down where a reader asks about it. A new stable can redden the job through one new clippy lint, since `make rust-clippy` runs with warnings as errors. It is accepted here and nowhere else because a clippy regression cannot reach a consumer: it changes nothing that is published, it fails at exactly one step, and the fix is usually the line clippy names. Pinning would trade that for lint debt that accrues silently and costs far more to pay off in one go.

### Fixed

- **The one FRB pin that floated, and the only one a published package hands to its users** (`copier.yml`, `template/pubspec.yaml.jinja`) — three places name the flutter_rust_bridge version and all three derive from `frb_version`, but only two stripped the caret. `rust/Cargo.toml` rendered `="2.12.0"` and `FRB_CODEGEN_VERSION` rendered `2.12.0`, while `pubspec.yaml` rendered the answer verbatim as `^2.12.0`. The Makefile comment three lines above one of them already stated the invariant the pubspec then broke.

  It is not a range that can be widened safely. `frb_generated.dart` records the version of the generator that produced it, and `BaseEntrypoint._sanityCheckCodegenVersion` compares that string to the runtime package's own with `==`, throwing a `StateError` unless they are equal. Every version inside any range except the one that generated the bindings therefore fails — a caret here is not a loose pin, it is a pin that stops holding as soon as anything else is published. `>=2.12.0 <2.13.0` would be no better: flutter_rust_bridge ships patch releases (2.5.1, 2.7.1, 2.11.1), and a 2.12.1 would break the equality exactly as 2.13.0 did.

  What is rendered is therefore one version written as a range, `>=X.Y.Z <X.Y.Z+1`, rather than the bare `X.Y.Z` the same reasoning first argues for. The bare form cannot be released: `dart pub publish` warns that a single-version constraint "should allow more than one version" and exits 65 on any warning, so `make publish-dry-run` fails — and both `make release` and `publish.yml` gate on it. The range admits the same single version and does not trip the check. Measured rather than assumed, by running four constraint shapes through `dart pub publish --dry-run`; only the bare version produced the warning. The consequence for a consumer is intended: someone depending on two FRB wrappers built against different versions now gets a version-solving failure from `pub get` rather than a resolve that succeeds and then throws at `init()`.

  This is what upstream documents rather than an inference: *"all flutter_rust_bridge-related packages will need to have exactly the same version"*, and the codegen's own `integrate` runs `dart pub add flutter_rust_bridge:<version>`, which writes an exact pin with no caret. The caret was a deviation from what the tool itself produces.

  What it cost was not a red build. `pubspec.lock` is deliberately not committed for a library, so CI re-resolved on every run, and both projects generated from this template published to pub.dev carrying `^2.12.0` in the pubspec and `codegenVersion => '2.12.0'` in the shipped `lib/src/rust/frb_generated.dart`. When 2.13.0 was published on 2026-08-23, every consumer resolving either package fresh got a `StateError` out of `RustLib.init()`. Reproduced end to end: a clean checkout resolves 2.13.0 and 54 tests fail with `codegen version (2.12.0) should be the same as runtime version (2.13.0)`; with the pin exact it resolves 2.12.0 and all 714 pass, with no rebuild and no regeneration.

  The caret is stripped in the pubspec too rather than assumed absent, so a project whose recorded answer still reads `^2.12.0` renders a pubspec, a `FRB_CODEGEN_VERSION` and a `Cargo.toml` pin naming the same single version on its next update, without anyone editing the answers file. Verified by rendering both ways with `copier copy`: stored caret and fresh default produce byte-identical trees apart from the recorded answer itself.

- **`make codegen` used whatever generator was on `PATH`** (`template/Makefile.jinja`) — `FRB_CODEGEN_VERSION` pinned the binary that `setup-frb-codegen` installs, but `codegen` did not depend on that target and invoked `flutter_rust_bridge_codegen` directly. A developer holding a different version regenerated bindings that contradict the `=` pin in `Cargo.toml`, with nothing between that and a commit — the same drift the pins exist to prevent, arriving through the one door they did not cover. `codegen` now takes `setup-frb-codegen` as a prerequisite; where CI already ran the two in sequence this changes nothing, since that target only runs `--version` when the pinned binary is already present.

- **Committing from a git worktree broke the pinned Flutter SDK, for every tool and every project** (`template/.githooks/pre-commit.jinja`) — git exports `GIT_DIR` to every hook and every child process inherits it. In an ordinary checkout that is the relative string `.git`, which is harmless by accident: a tool that changes directory re-resolves it against wherever it now stands. A *worktree* has no such luck — its `.git` is a file rather than a directory, so the exported path is necessarily absolute, and it then follows every child process everywhere it goes.

  Anything downstream that asks git about *itself* is then answered about the repository being committed to. `flutter` does exactly that to determine its own version, and the result is not a failed check but a corrupted toolchain: run from a worktree's hook it read the committing repository's HEAD, found no Flutter tag on it, and wrote `"frameworkVersion": "0.0.0-unknown"`, `"channel": "[user-branch]"` and that repository's SHA as `frameworkRevision` into the pinned SDK's `bin/cache/flutter.version.json`. Being a cache, the damage outlived the hook: every later `flutter` and `dart` invocation, inside a hook or not and in any project sharing that FVM version, failed dependency resolution with "The current Flutter SDK version is 0.0.0-unknown" until the file was deleted by hand. What surfaced it was an example package whose `flutter: ">=3.38.0"` constraint suddenly could not be satisfied, but nothing about it was specific to that constraint — a version of `0.0.0-unknown` fails every lower bound there is.

  Measured, not reasoned: with `GIT_DIR` set to a worktree's gitdir, `git -C <flutter-sdk> rev-parse HEAD` returns the *committing* repository's commit and `git -C <flutter-sdk> describe --tags` returns its tag, while the same commands with `GIT_DIR` unset, or set to the relative `.git` an ordinary checkout exports, answer correctly about the SDK. That difference is the whole bug, and it is why this went unseen: the hook has shipped since the template had one, and a worktree is the only shape that exports the absolute form.

  The three variables are now stripped in the subshell each check runs in, rather than at the top of the file, and the distinction matters. This hook asks git its own questions — `staged_touches_rust` reads the index — and `git commit -a` runs the hook against a *temporary* index named by `GIT_INDEX_FILE`. Unsetting that globally would make the gate read the real index instead and skip the Rust check on exactly the commits that staged Rust through `-a`. A subshell keeps the two apart: git's environment for the hook's own questions, a clean one for the tools it invokes. Verified by running the shipped hook with a worktree's absolute `GIT_DIR` exported — all three steps behave, the Rust gate still skips and fires on the right staged paths, and the SDK's version cache comes out byte-identical, where the same run previously rewrote it.

- **A template update could ship Dart the project's own gate rejects** (`template/scripts/src/update_template.dart`, `template/test/scripts/update_template_test.dart`) — `copier.yml`'s last `_task` is `dart format .`, and it is load-bearing rather than tidiness: the template hard-wraps the Dart it emits, but whether a rendered line fits in 80 columns depends on the *answers*. `check_updates.dart` wraps one `RegExp` per upstream crate, and for a short crate name the wrapped form is precisely what `dart format` collapses — so the same template source is correctly formatted for one project and not for another. Three alternative wrappings were measured and each only moved the range of crate-name lengths that comes out wrong; formatting the rendered tree is the only thing that settles it, which is why the task exists.

  `copier copy` runs that task. `copier update` runs no tasks — deliberately, and it must stay that way: copier executes tasks *between* rendering and replaying the project's diff, and a task dying in that window has been measured to leave the template's version of a customized file in place of the project's with `_commit` bumped as though it had worked. So the formatting now happens after copier returns, where there is no such window.

  Rehearsed as a real `copier update`, not by analogy: a project generated from a v1.0.0 tag, a v1.1.0 that adds a wrapped construct in a region the project never touched, and `make update-template` driving it. Before, copier reported that it "merged everything cleanly", `_commit` landed, and `make format-check` failed — with nothing anywhere in the run pointing at why. After, the step names the file it reformatted and the gate passes. Where the same file is also conflicted the formatter cannot parse it at all and says so; the gate stays red, which is correct, and the pull request is already a draft.

- **The failure reporter could fail** (`template/scripts/src/common.dart.jinja`, `template/test/scripts/common_test.dart`) — `describeGithubFailure` is only ever called while a failure is already being reported, which is exactly why `_firstHeader` avoids `HttpHeaders.value`: a second exception raised there replaces the diagnosis with noise about the diagnosis. `_formatEpochSeconds` was doing precisely that. `int.tryParse` accepts anything up to 2^63 and `seconds * 1000` wraps silently, so an `x-ratelimit-reset` of `99999999999999999` became `7766279631452240920` and `DateTime.fromMillisecondsSinceEpoch` threw `RangeError` — reaching the caller instead of the documented `GithubApiException`. `9223372036854775807` did not throw; it wrapped to 1969 and reported that as the reset time. Without an explicit radix `0x10` also parsed, as 16. Out-of-range and unparseable values now drop the timestamp and keep the rest of the message, and the six cases are pinned in the suite.

  The same function's contract — "throws `GithubApiException` on any non-200" — was false for a body that is not UTF-8. `utf8.decoder` is strict and runs *before* the status code is read, so a 500 carrying an error page in some other encoding surfaced as `FormatException: Invalid UTF-8 byte`, with neither the status nor the URL: strictly less than the bare status code this function was written to replace. Decoding is now lenient, and both regressions fail the suite against the previous code.

- **The step that applies the update still called the API anonymously** (`template/.github/workflows/check-template-updates.yml.jinja`) — 4.5.0 gave the token to the checkers because hosted runners share an egress IP and the anonymous quota is 60/hour against it. `make update-template` re-reads the template CHANGELOG through the same helper, from the same job, seconds later, on the same IP — and its step did not pass the token, because Actions does not export `GITHUB_TOKEN` to a step by itself. Two of the three call sites were authenticated and the third was not. It also fails quietly: that fetch is wrapped, so a refusal leaves the AI with no template changelog to summarise and says so only in a warning. Verified by running the same code path with a deliberately invalid token and getting `HTTP 401 … Bad credentials`, which is proof the header is sent, and without one and watching it succeed anonymously.

- **A conflicted template update produced no pull request at all** (`template/.github/workflows/check-template-updates.yml.jinja`) — the outcome this workflow exists to report was the one it could not deliver. `create-pull-request` begins by creating its own temporary branch, `git checkout -B <temp> HEAD`, and git refuses that while the index holds unmerged entries: `error: you need to resolve your current index first`. Its own `git add -A` comes later and is never reached. So a conflicted run did everything right and then died on git — copier left the files unmerged, the update step counted them, the draft body naming them was assembled, and the step after it failed with `The process '/usr/bin/git' failed with exit code 1`, which names neither conflicts nor the index. Observed on a generated project whose `CLAUDE.md`, `CONTRIBUTING.md` and `README.md` had all drifted from the template, on the first release that touched all three at once.

  The unmerged paths are now staged before the pull request is created, which is what the draft is *for*: what copier left travels in the commit, the pull request opens as a draft listing the files, and a human resolves them on the branch. Only those paths are staged — whatever else belongs in the commit is `create-pull-request`'s own `git add -A`. `-z`/`-0` throughout, because a conflicted path may hold spaces or non-ASCII, and `-r` so an empty list is a no-op: `has_conflicts` is also set by a marker found in a file git considers merged, and that case has nothing to stage.

  What travels is not always a conflict marker, so the step logs the status letters and not just the names. Measured over all four shapes git can leave here: `UU` and `AA` stage the file with `<<<<<<<` in it, but `UD` — the project modified a file this release deletes — stages the project's side, and `DU` — the project deleted a file this release modifies — stages the template's. Neither carries a marker; one side simply wins, and without the letters the pull request shows a clean file while its own body lists that path as conflicted. Staging still covers every shape (`git diff --diff-filter=U` and `git ls-files -u` agree on all four, and `git checkout -B` succeeds after each), so the failure above is fixed either way — the letters are about what the human reading the draft is told.

  Every project generated from this template was exposed, on every release that conflicts with local drift — which is why it went unseen for as long as it did: the projects updating automatically had, until now, never conflicted. Verified by reproducing it rather than by reading it. A generated project was edited where the next release also edits; `copier update` left the index unmerged; `git checkout -B` failed with the exact error above; and with the new step the same command succeeds while `git show :<path>` still carries `<<<<<<< before updating`.

  The local path is deliberately unchanged: `make update-template` still leaves conflicts unstaged, for a human to resolve and stage by name, as it has since 4.4.0.

- **Two more places still described template updates as notifications** (`template/scripts/README.md.jinja`, `template/README.md.jinja`, `template/CONTRIBUTING.md.jinja`) — 4.5.0 corrected that sentence in the generated README and fixed the AI changelog wording in four files. A sweep for the same claims rather than for the changed lines found what the first pass missed: `scripts/README.md` said it twice, in prose and in its numbered CI walkthrough; the generated README's own command list still annotated `make update-changelog` with `(requires AI_MODELS_TOKEN)`, eight lines above the note saying it always fails; and CONTRIBUTING promised the entry "if `AI_MODELS_TOKEN` is configured" in the section describing the automation, which is a different section from the one carrying the warning, so a reader of the first never reaches the second.

- **The template-update workflow reported a gate that could not pass** (`template/.github/workflows/check-template-updates.yml.jinja`) — its sibling `check-<package>-updates.yml` installs protoc under `{% raw %}{% if enable_protoc %}{% endraw %}`; this one never did, while running `make rust-check` as one of the three gates whose results go into the pull-request body. For a project whose Rust depends on a protobuf-backed crate the build script panics with ``Could not find `protoc` `` and the gate records **fail** on every single update. It never turned a run red — the gates are deliberately non-fatal, `if make rust-check; then … else … fi`, and only the body table consumes them — which is worse rather than better: a row that is always red is a row nobody reads, and the one time it means something is the time it is ignored. Confirmed against a real run, where `Run quality gates` is green and the failure text is `error: failed to run custom build command for spqr` … `Could not find protoc`.

## [4.5.0] - 2026-08-16

### Changed

- **The pre-commit hook runs the Rust gate only when the commit touches Rust** (`template/.githooks/pre-commit.jinja`) — the three gates cost about five seconds between them while their caches are warm, and `cargo check` is the one that stops being five seconds: measured on a generated project, 1s warm against **76s** from an empty `rust/target` — which `make clean` produces outright, and a toolchain update or a dependency bump produce in effect. Most commits touch no Rust at all, including the one that carried this change, and for those the wait buys nothing: the check reads a crate that lives entirely under `rust/`, and nothing outside it — no root `rust-toolchain.toml`, no root `.cargo/config.toml` — feeds into it.

  What is compared is the index against HEAD, and three flags are load-bearing rather than decorative. The base is the **empty tree** when HEAD does not resolve, which is the first commit of a freshly generated project — `git diff --cached HEAD` fails outright there. `-- rust` is a **pathspec** rather than a grep over the output, because git prints paths holding spaces or non-ASCII quoted, and `"rust/…` does not match `^rust/`. And `--no-renames` reports a rename as a delete plus an add, so moving a file *out* of `rust/` still counts as touching it. The predicate **fails open** — when git cannot answer, the check runs — and the skip is announced rather than silent, because a gate that quietly stops gating is worse than one that costs a minute. `make rust-check` also runs in CI on every push, so nothing here is the only line of defence.

  Verified case by case against the shipped text, not a retyped copy of it: first commit with Rust staged, Rust staged normally, Rust modified but *not* staged while a doc is committed, `git commit -a` with an unstaged tracked Rust change (the hook does see what `-a` will commit — measured, not assumed), a path under `rust/` holding a space and Cyrillic, a rename out of `rust/`, a deletion inside it, the look-alikes `rust_notes.md` and `rust-tools/` at the root, an empty commit, `--amend` with each of Rust and docs staged, and the predicate run outside a git repository. End to end on a generated project: a documentation commit runs steps 1 and 3, names the skip and lands in 4s; a **broken** Rust file staged still fails the step and leaves no commit; a valid one passes and commits.

### Fixed

- **The documented App permissions left out the one its own update bot needs** (`README.md`, `template/.github/workflows/check-template-updates.yml.jinja`) — the GitHub App setup listed `Contents`, `Pull requests` and `Metadata`. A template update is an ordinary commit over whatever the template owns, and the template owns `.github/workflows/**`; GitHub refuses to let an App write a file there without `Workflows: Read & write`. Nothing surfaces the gap until the first update that happens to touch a workflow, so it can sit for as long as it likes — in the project this was found in, every bot pull request before it carried either `.fvmrc` alone (the notification era) or release scripts and answers, and the first one to include `.github/workflows/` failed two template releases later. The wording of the failure hides it further: `create-pull-request` commits through the Git Data API, so the refusal arrives as `Resource not accessible by integration` on `POST /git/trees`, naming neither the file nor the permission, and only *after* every blob was created — which is itself a `Contents: write` call and therefore proves that permission is fine.

  The permission is now documented, with the two traps that make fixing it on an existing App look like it did not work: **`Actions` is not `Workflows`** (the first governs workflow runs, the second the workflow files), and a permission added to an App does not reach the tokens it issues until **every installation accepts** the change, while the App's own settings page already shows it as granted. `check-template-updates.yml` also gained a failure-only step that says all of this in the run that hit it, so the next occurrence costs a read rather than an investigation.

- **Both update checkers called the GitHub API anonymously, and reported failures as a bare status code** (`template/scripts/src/common.dart.jinja`, `template/scripts/src/check_template_updates.dart`, `template/scripts/src/check_updates.dart.jinja`, `template/test/scripts/common_test.dart`, `template/.github/workflows/check-template-updates.yml.jinja`, `template/.github/workflows/check-{{ package_name }}-updates.yml.jinja`) — reading a public release needs no permission, so both checkers asked for one without a token. Anonymous requests are counted at 60/hour **per source IP**, and GitHub-hosted runners share theirs with everything else running on them, so a scheduled check can be refused for reasons that have nothing to do with the repository it reads: one daily run died on `403`, and the next day's succeeded untouched. Both scripts now send whatever `GITHUB_TOKEN` — or `GH_TOKEN`, so a local run picks up an existing `gh` login — is in the environment, and both workflows pass the job's own read-only token. Quota, not access: the token needs no permission beyond the default even though the repository being read is not the one the job runs in.

  The report was the worse half of it. On failure the scripts kept the status code and dropped the response, so `403` was the whole message — and `403` is also what a genuine permission failure returns, which is how a spent quota became indistinguishable from a repository that does not exist. The shared `githubApiGet` keeps GitHub's own `message` and the `x-ratelimit-*` headers, and mentions the anonymous quota only when the call actually was anonymous; `describeGithubFailure` is pure and covered by tests. Three hand-rolled `HttpClient` blocks collapse into it. `check_exists_frb_release.dart` already authenticated and is untouched; `update_changelog.dart`'s `curl` calls still do not, and are left alone because they are only reached with an AI token.

- **Post-generation setup never told anyone to apply the repository protections** (`README.md`) — `make setup-repo-protections` exists, `.github/rulesets/` is generated, and its README explains every ruleset in it, but the walkthrough a new project actually follows went from Actions secrets straight to repository topics. Until that command is run, the native binary every consumer downloads at build time can be published by anyone with `write` and no review, and the release tags that trigger the build are unprotected — the exact gap the rulesets exist to close. It is now step 4, after the repository exists and the first push has landed, which is what the command requires.

- **The AI changelog setup walked people through creating a token for a service that is being retired** (`README.md`, `template/CONTRIBUTING.md.jinja`, `template/README.md.jinja`, `template/CLAUDE.md.jinja`, `template/.claude/skills/update-template/SKILL.md`) — GitHub Models is in its retirement brownout and answers every call with `GitHub Models is temporarily unavailable as part of a scheduled retirement brownout`, so the changelog step fails on every run. The degradation is correct and stays as it is: the pull request is still opened, its checks table records the entry as **not written** with the error, and the `changelog-needed` label asks for a human. Only what people are told was wrong — two of these walked a reader through creating a token for it, and the update skill told whoever runs it to expect an entry — and each now leads with the status. The remaining mentions are left alone deliberately: the `Makefile` comment and the workflow comments describe wiring that does exist and still runs. Choosing a replacement provider is a separate decision and is not made here.

- **The generated README still described template updates as notifications** (`template/README.md.jinja`) — "creates notification PRs with changelog and update instructions", which is what the workflow did before 4.3.0 taught it to run `copier update` and open a pull request carrying the actual diff. A project generated since then shipped a README describing a workflow it does not have, and the sentence is the one a maintainer would read to decide whether the update needs doing by hand.

## [4.4.0] - 2026-08-15

### Fixed

- **Generated packages could not load their own native library under `flutter test`** (`template/lib/src/platform/platform_io.dart.jinja`, `template/lib/src/{{ package_name }}.dart.jinja`, `template/test/platform/native_asset_search_paths_test.dart.jinja`) — the build hook registers the library as a `CodeAsset`, but a `package:` asset id is not a path: `DynamicLibrary.open()` hands it straight to `dlopen` as a literal path, only `@Native(assetId:)` externals go through the asset mapping, and flutter_rust_bridge needs a `DynamicLibrary` handle — so the file has to be located on disk. `tryLoadNativeAsset` probed two places, `.dart_tool/lib/` and `../lib/` next to the executable. `flutter test` uses neither: flutter_tools installs the hooked library under `build/native_assets/<os>/` (`isolated/native_assets/test/native_assets.dart` builds it as `projectUri.resolve('$buildDir/native_assets/$osName/')`, and `osName` is the same `macos`/`linux`/`windows` token `Platform.operatingSystem` returns) and never creates `.dart_tool/lib/`. On macOS and Linux nothing on `flutter_tester`'s dlopen search path covers that directory, so **every unit test of every Flutter package depending on a generated package failed in `init()` on a clean tree**, while the app itself built and ran fine — a leftover `.dart_tool/lib/` from a previous `dart test` was what made it look intermittent. Windows resolved it by accident: flutter_tools prepends that same directory to the tester's `PATH`, which is where Windows looks for a DLL.

  The directory is now probed, **last**. The order matters and is not the obvious one: that entry is relative to the working directory, so putting it ahead of the executable-relative AOT location would let a `dart build cli` binary shipped to users load whatever happens to sit under `build/native_assets/<os>/` in the directory it was launched from, in preference to the library it shipped with. `.dart_tool/lib/` stays first — it is the hot path, and it was already ahead of the AOT entry. The `Platform.resolvedExecutable` lookup keeps its `try`/`catch` so an embedder that cannot resolve it does not take the other two candidates down with it, and the new test pins both the presence of the entry and its position. Reported against a generated project as [libsignal_dart#63](https://github.com/djx-y-z/libsignal_dart/issues/63) and verified there end to end under Flutter 3.44.8: green with a plain `init()`, with neither `.dart_tool/lib/` nor an AOT bundle present.

- **`copier update` re-ran the entire generation sequence, three times over** (`template/scripts/src/update_template.dart`, `template/scripts/src/check_template_updates.dart`, `template/.claude/skills/update-template/SKILL.md`) — a single `copier update` renders the template **three** times: into a temporary copy of the old version, into the project's own working tree, and into a temporary copy of the new one. It runs `_tasks` in every one of them. Verified directly, with a task that logged its working directory: three invocations, the middle one in the real project. Those tasks exist to *create* a project — `flutter create`, `dart create`, `dart pub get`, `dart format .`, `rm -rf _templates` — and on a project that already exists they only redo work. `make update-template` now passes `--skip-tasks`, which applies to all three renders at once; measured on a freshly generated project, an update went from 22s to 7s, and the gap widens with the size of the example apps. `--trust` is still required and is not waived by it: `_jinja_extensions` is an unsafe feature in its own right, and on an update copier also inspects the *old* template's `_tasks`. `_min_copier_version` moves to `9.3.1` with it: copier added task skipping in 9.2.0 but only passed the CLI flag through to the worker in 9.3.1, so the previously declared `9.0.0` would have accepted a copier that silently ran the tasks anyway.

  Aborting mid-update is the other cost, and it is the one that can actually damage a tree. Where a failing task lands depends on where its trigger lives. A task that fails identically everywhere — `dart pub get` with no network — stops the run in the *first* of the three renders, the temporary copy of the old version, so the project is never reached: measured, the tree stayed clean and `_commit` unmoved. But a task whose trigger lives in the **project** passes that render and fails the next one, which is the project itself. `dart format .` over a locally broken Dart file is exactly that shape, and it was measured too: the run failed, the template's version of a customized file replaced the project's, the local change was gone from the worktree, and `_commit` was bumped anyway — a half-updated tree that reports itself as up to date. No asymmetry between template versions is needed for this; the version-asymmetry path read off copier's source earlier is real, but it is one way in rather than the only one. Copier renders into the tree and runs the tasks (`_main.py:1238`) *before* it replays the project's diff (`:1318`), and a task dying in that gap leaves it open. Skipping the tasks closes it.

  **What this was not**: running the tasks did not eat local edits, and the fix is not what it would be if it had. Copier replays the project's own diff over the freshly rendered tree, and a task that overwrites `example/lib/main.dart` is undone by that replay. Verified end to end on this template — generate, edit `example/lib/main.dart`, add `example_cli/lib/demos/demo1.dart`, update — and both survived untouched. On a probe whose template *also* changed `example/lib/main.dart`, the edit came back the way it should: an ordinary `UU` merge conflict carrying both sides. This is worth stating plainly because the obvious repair is strictly worse than the problem, in two separate ways.

  First, the spelling. Gating the tasks with `when: "{{ _copier_conf.operation == 'copy' }}"` does not work on copier 9.11: `_copier_conf` has no `operation` key. What copier injects for a task's `when:` is `_copier_operation`, set in `_execute_tasks` (`_main.py:364`), and an undefined attribute compares equal to nothing — so the guard evaluates false *during generation too*. A probe task carrying that condition was skipped by a plain `copier copy`. Every task group in `copier.yml` would have carried the same guard, so generation would have produced no `example/`, no `example_cli/`, and left `_templates/` behind.

  Second, and worse, the guard is destructive even spelled correctly. It lands in the *new* template while the *old* one — the version each project is updating **from** — still runs its tasks, so the example apps exist in copier's render of the old version and not in its render of the new one — and copier deletes exactly that difference, as files the template dropped (`_remove_old_files`, `_main.py:1407`, over `dircmp.left_only`). Measured on a probe carrying the same task shapes: the first update after such a release removed `example/lib`, `example/test`, `example/ios`, `example/android`, `example/pubspec.yaml` and `example_cli/bin/main.dart` outright, and left `_templates/` in the tree. Skipping the tasks at the call site has no such transition, because it applies to old and new versions alike. **Do not move this into `copier.yml`.**

- **The update skill sent readers looking for a conflict shape copier does not leave behind** (`template/.claude/skills/update-template/SKILL.md`, `template/scripts/src/update_template.dart`) — the skill's conflict step was `find . -name "*.rej"`. Copier does write `.rej` files, with `git apply --reject`, but in its default `--conflict=inline` mode it immediately converts each one into an inline three-way merge and unlinks it; by the time the command returns there are none. The documented check therefore always came back empty and read as "no conflicts" — the one message it must never send. What copier actually leaves is the ordinary git shape: markers naming the two sides (`<<<<<<< before updating` / `>>>>>>> after updating`) and the path unmerged in the index, so the real signal is `git status --porcelain | grep '^UU'`. The script had it right all along (`_conflictMarker = '<<<<<<< '`); only the documentation disagreed with it.

  Two claims went with it. The commit step used `git add -A`, which also sweeps whatever untracked debris is lying around — `.DS_Store`, editor scratch files, un-ignored build output — into a commit whose message says it came from the template; the manual procedure now stages by name. (The automated path still stages the whole tree — that is `create-pull-request`, not this document, and it is why the script never relies on the index alone.) And the header comment recorded that every conflict so far had landed in Markdown, and leaned on that to explain why the Dart and Rust gates miss them. The update that prompted this work refutes it: conflicts landed in `Makefile`, `pubspec.yaml`, `rust/Cargo.toml`, `rust/src/frb_generated.rs` and two Dart scripts. The same claim was shipping from two further places — the scheduled workflow's own comments, and the warning it writes into the body of every conflicted pull request — and is corrected in both. The reasoning survives in weaker form — `Makefile` and Markdown conflicts do pass every gate, and none of the gates names the update as the cause — so the detection stays, with the justification corrected.

  The skill also now records what `--skip-tasks` does *not* do. `example/web/` is produced by the `flutter create` task, not by any template file, so no update creates it and switching `enable_web` to `true` on an existing project needs `cd example && flutter create . --platforms web` — the command rather than a hand-made directory, because it also records `platform: web` in `example/.metadata`.

- **Four files promised a web pipeline to projects generated without one** (`template/.pubignore.jinja`, `template/scripts/README.md.jinja`, `template/hook/build.dart.jinja`, `template/.claude/skills/frb-patterns/SKILL.md.jinja`) — with `enable_web: false` the generated project still ignored `example/web/pkg/` "auto-downloaded by hook/build.dart", still documented `make build-web` as a local build command, still carried a comment in the build hook explaining that web builds copy WASM files to `web/pkg/` (the comment sat *outside* the `{%- if enable_web %}` that guarded the code it described), and still shipped a whole "Web/WASM Considerations" section in the FRB patterns skill, ending in `make build-web`. None of those targets or paths exist in such a project. Four independent sources agreeing on a pipeline that was never built is enough to send someone looking for it, which is exactly what happened. All four are now conditional; rendering both `enable_web` values confirms each appears only with web enabled.

- **`make get-version` was missing from `.PHONY`** (`template/Makefile.jinja`) — the only target in the file not declared, so it would have been skipped had a `get-version` file ever existed.

## [4.3.0] - 2026-08-03

### Added

- **This repository can release itself with one command** (`Makefile`, `scripts/release.py`, `scripts/test_release.py`, `CONTRIBUTING.md`, `.claude/skills/release-template/SKILL.md`) — the template shipped a release script to every project it generates but had none of its own, so cutting a version here was a documented sequence of git commands with an easy step to get wrong: renaming the `## [Unreleased]` heading, repointing the `[Unreleased]:` compare link, adding the new one, then committing and tagging by hand. `make release ARGS="--version X.Y.Z"` now does all of it, and pushing the tag is what makes `release.yml` publish the GitHub Release. Python with no dependencies, because the one hard dependency this repository already has is copier — which is Python — so a Dart script would add a second toolchain nothing else here needs; rewriting the link footer with sed is exactly the kind of thing that half-works silently.

  It refuses to start unless you are on `main`, the tree is clean, `main` is not behind origin, the tag is unused locally and on origin, the version is greater than the last released one, and `## [Unreleased]` is **not empty** — releasing an empty version is otherwise an easy mistake, since nothing else notices. The previous version and the repository URL are read out of the existing `[Unreleased]:` link rather than being configured, which makes that line the single source of truth for the compare range; it is deliberately kept after a release even though no heading references it any more.

  Two behaviours are carried over from the release scripts this template ships, because they exist for the same problem. **A mistyped signing passphrase does not abort the release** — `ssh-keygen -Y sign` reads the passphrase once and gives up rather than re-prompting, so every signing and push step is retried automatically and Ctrl-C is the way out; the loop is uncapped, but a non-interactive stdin raises on the first failure and it paces itself from the third. **An interrupted release is resumed by re-running the same command**: a run that dies between its commit and its tag leaves a state that blocks a plain re-run, so that state is detected — clean tree, CHANGELOG already finalized to the requested version, and `HEAD`'s subject exactly the subject the release writes — and continued from the tag.

  Verified end to end against a bare origin with a real SSH signing key: the CHANGELOG rewrite, a genuinely signed commit and tag (`git verify-commit` reports a good signature), both pushed, and the resume path — interrupted after the commit, re-run, and the version heading appears exactly once, so the CHANGELOG edit was not applied twice. Every precondition was exercised individually: wrong branch, behind origin, dirty tree in both shapes, an already-released version, an empty `[Unreleased]`, and an older version. So were both answers to the confirmation prompt — declining a fresh release reverts the CHANGELOG edit and leaves no commit or tag, declining a resumed one leaves the commit in place. `make test` covers the resume predicate and the CHANGELOG rewrite.

- **Template updates are applied automatically, not just announced** (`template/scripts/update_template.dart`, `template/scripts/src/update_template.dart`, `template/test/scripts/update_template_test.dart`, `template/Makefile.jinja`, `template/CLAUDE.md.jinja`, `template/.claude/skills/update-template/SKILL.md`, `template/.github/workflows/check-template-updates.yml.jinja`) — the scheduled check now runs `copier update` itself and opens a pull request carrying the result, the way the upstream dependency workflow already does; a generated project no longer has to be updated by hand. Everything the new scripts need comes from `.copier-answers.yml`, so they name neither the project nor its upstream library and ship **plain, non-jinja**, like `check_template_updates.dart` and `release_common.dart`. `update_changelog.dart.jinja` is the counter-example that decided this: it hardcodes the upstream repository and an `{{ package_name }}_highlight` response field, and so cannot be reused for anything else. Copier is pinned (`copier==9.11.1`, `jinja2-strcase==0.0.2`) for the reason the actions are pinned by SHA — this runs unattended, and a copier release that changed how it merges would arrive as a conflict-shaped diff rather than a clean failure.

  Two outcomes are reported separately, because they are independent and both are quiet. A **conflict** leaves both sides in the file: the pull request becomes a draft, lists the files, and says why nothing else caught it — `format-check`, `rust-check` and `analyze` read only Dart and Rust, and copier's conflicts land in Markdown, which passes all three intact. **`_commit` failing to land** is the other: copier can apply every file and still leave `.copier-answers.yml` on the old version, which merges as an un-updated project and re-opens the same pull request on every subsequent run. That one fails the job — deliberately *after* the pull request exists, so the applied work is kept. They do not imply each other, and the update that produced this release is the proof: `_commit` moved to the new version while `CONTRIBUTING.md` was still unmerged.

  Two behaviours of copier drive the design and are not documented by it. It **refuses to update a dirty destination, untracked files included** — verified against a tree whose only change was one new file — and its own message names nothing, so `make update-template` checks first and lists the paths. This also makes the `.fvmrc` drift fix in 4.2.0 a prerequisite rather than a neighbour: while `fvm install` rewrote `.fvmrc` on every run, an automated update could never have started. It does **not** need a git identity, despite building temporary repositories — verified with `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` pointed at `/dev/null` — so no `git config` step is needed on a runner.

  The CHANGELOG entry is written by AI from the template's own changelog **and** the diff that actually landed in the project, because a template release describes changes for every project generated from it and most of a release can arrive somewhere as a no-op; announcing those as changes is the failure mode this guards against. It is filed under `### For Contributors` → `#### Changed`, where template adoptions belong, and the pull request asks a reviewer to move it if the release changes what the published package does at build or run time. The three gates the pre-commit hook runs are executed and reported in the body but never enforced: a template update that breaks a gate is precisely the one a human most needs to see. The `if`/`fi` wrapping each gate is load-bearing, not style — GitHub runs the step with `bash -e`, and it is what keeps a failing gate from killing the job and, with it, the pull request.

### Fixed

- **The release scripts' `git restore` hint never appeared** (`template/scripts/src/release_common.dart`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`, `template/test/scripts/release_common_test.dart`) — interrupting a release before its commit leaves only the release's own files modified, and 4.2.0 added a message that recognises that and names the single `git restore` which discards them. It never fired. The status was read through `git()`, which trims its output; `git status --porcelain` has two positional status columns, so an unstaged modification is `' M path'`, and trimming ate the leading space of the *first* line and shifted that path by one character. `onlyTheseFilesDirty` then matched nothing and rejected the whole status, so every interrupted release got the generic "working tree is not clean" instead — in exactly the case the hint was written for, because a release edits its files without staging them. Found while building this repository's own release script, which had inherited the same shape. Both now read the status through a `gitStatus()` that strips only trailing newlines, and a test pins the two shapes against each other so a future trim cannot pass unnoticed.

- **The template update notification had stopped working, silently** (`template/.github/workflows/check-template-updates.yml.jinja`) — the workflow opened a pull request whose payload was its *description*: a version table, the template's changelog for the range, and manual instructions. Its diff was meant to be empty. But `create-pull-request` opens nothing when there is no diff and exits successfully — stated in its README and guarded by `if (result.hasDiffWithBase)` in the SHA the template pins — so a notification pull request could only ever exist because something else made the tree dirty. That something was `.fvmrc`, rewritten by `fvm install` on every run: in the project this was found in, **every** notification ever opened carried exactly one file, `.fvmrc`, at +3/-3, and nothing else. Fixing that drift in 4.2.0 removed the accidental payload, so the next template release would have produced a green job, a step summary reading "a notification PR has been created", and no pull request anywhere — detectable only as the absence of something nobody was watching for, which is the same shape that hid the FVM cache bug for months. The workflow now has a payload of its own, and the absence is checked instead of assumed: a run that found an update and opened no pull request fails, and says not to read it as "nothing to do".

## [4.2.0] - 2026-08-03

### Added

- **`template/test/scripts/release_common_test.dart`** — covers `isResumableRelease` over each condition that must individually block a resume (a dirty tree, a bump that has not landed, an unrelated commit on top, the previous version's release commit at `HEAD`, a subject that merely starts with the release subject) and `onlyTheseFilesDirty` over the shapes that must not produce a `git restore` suggestion (an untracked path, a rename, an empty status). Plain (non-jinja) like `release_common.dart` itself, and written against generic subject strings so it stays identical in every generated project. The retry loop's own I/O is not unit-tested — it is driven by a terminal by construction — and was verified against a real pty instead.

### Fixed

- **A mistyped signing passphrase no longer aborts a release** (`template/scripts/src/release_common.dart`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`, `template/scripts/release.dart.jinja`, `template/scripts/release_frb.dart.jinja`, `template/.claude/skills/release-package/SKILL.md.jinja`, `template/.claude/skills/release-frb-crate/SKILL.md.jinja`) — git signs a commit or a tag by shelling out to `ssh-keygen -Y sign` (or `gpg`), and both give up after a *single* wrong passphrase rather than re-prompting: `ssh-keygen` reads the passphrase exactly once and calls `fatal()` on the failed load. One typo therefore aborted the release wherever it happened, and the position that hurts is between the commit and the tag, because that state blocks its own recovery — the version bump is committed, no tag exists, and re-running the command trips the "must be greater than the current version" precondition, leaving reverting the commit or tagging and pushing by hand as the only ways out. Both stages now route every signing and push step through a new `runInheritRetry`, which prints the failure and runs the step again, so the passphrase prompt simply comes back the way `ssh` and `sudo` behave — there is no question to answer, and **Ctrl-C is the way out**. That last part is a requirement, not an observation: with `inheritStdio` the interrupt reaches the whole foreground process group, and it was verified at the passphrase prompt itself, where the child owns the terminal. Nothing in this path may install a SIGINT handler without exiting from it, or the only interactive exit disappears.

  Four details carry the weight. **The loop is uncapped**, because an attempt limit would reinstate exactly the failure it exists to prevent — the run that dies on the last allowed typo. **A non-interactive stdin throws on the first failure**, so CI behaviour is unchanged and, more importantly, a step failing structurally where nobody can retype or interrupt anything cannot spin forever. That test is `stdin.echoMode` (which throws on anything that is not a tty) and deliberately **not** `stdin.hasTerminal`, which reports `StdioType.terminal` for any character device and therefore calls a run redirected from `/dev/null` interactive — verified against a pty, a pipe, a file and `/dev/null` on macOS with Dart 3.10. **From the third consecutive failure the loop paces itself** at two seconds and says so; the first retries stay immediate, so a typo is never slowed, while a `git tag -s` failing in milliseconds on a broken key path cannot scroll past faster than it can be read and interrupted. **`alreadyDone`** is consulted after a failure, so a step whose effect is already in place — a commit that landed despite a non-zero exit — reports success rather than being attempted twice, and **`beforeRetry`** re-stages the release files before each commit retry, because a pre-commit hook can rewrite a staged file and the retry must commit what the hook produced; the generated hook runs `make rust-check`, whose `cargo check` rewrites `rust/Cargo.lock` when the crate version moved.

  The retry, the Ctrl-C abort, both non-interactive shapes, and the resume, tag-conflict and abort paths below were all verified end-to-end against real `ssh-keygen` signing with a passphrase-protected key. The hook-rewrites-a-staged-file interaction was not exercised (re-staging unchanged files is a no-op, so the retry is correct either way).

- **An interrupted release is resumed by re-running the same command** (`template/scripts/src/release_common.dart`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`, `template/scripts/release.dart.jinja`, `template/scripts/release_frb.dart.jinja`, `template/.claude/skills/release-package/SKILL.md.jinja`, `template/.claude/skills/release-frb-crate/SKILL.md.jinja`) — the retry above covers a typo, but not a Ctrl-C or a closed terminal, both of which strand the release in the same half-finished state described above. Both stages now recognise that state and continue from the tag (or push) step, skipping the version bump and the CHANGELOG edit so nothing is applied twice, and skipping the revert-on-abort that only makes sense for uncommitted edits. Detection is the one predicate here whose false positive is unrecoverable — it would tag and push a commit that is not the release commit — so `isResumableRelease` requires *all* of: a clean working tree, the version file already reading exactly the requested version, and `HEAD`'s subject equal to the exact subject the release writes. The subject is held in a single `commitSubject` variable passed both to `git commit -m` and to the predicate, so the two cannot drift apart and silently disable resuming. A leftover tag is accepted only when it is this release's tag *and* points at `HEAD`; the same name on any other commit is refused by name and sha, and a tag already on origin still fails closed, now saying the version is already released. The confirmation prompt names only the steps that actually remain, and a resumed run with nothing left to do reports that instead of prompting. Interrupting *before* the commit is the one case nothing can report at the time — Ctrl-C kills the script mid-step — so the next run's "working tree is not clean" now recognises, via `onlyTheseFilesDirty`, when the only modified paths are the release's own files, and names the single `git restore` that discards them; it declines to suggest one for an untracked path or a rename, where the command would not work or would take something else with it.

- **The pre-commit hook never ran in a generated project** (`template/.githooks/pre-commit.jinja`) — the file was committed mode **644**, and git skips a non-executable hook without saying anything: `make setup-fvm` set `core.hooksPath`, reported success, and no commit was ever checked, in any generated project. It is 755 now, and copier carries the bit through (verified on a fresh render). Its content had a second failure that could only surface once the hook started running: it announced *every* step-1 failure as a formatting problem, so a hook invoked from an IDE or GUI git client — which inherits a minimal PATH where `make`, `fvm` and `cargo` are all missing — told you to run `make format` when the real problem was PATH. It now restores the usual install locations before the first check (the Unix `~/.pub-cache` and the Windows/Git-Bash `%LOCALAPPDATA%\Pub\Cache` layouts both, honouring `PUB_CACHE`/`CARGO_HOME`, and **appended** rather than prepended so a tool deliberately placed earlier keeps winning), then checks `make`/`fvm`/`cargo` up front and names what is missing instead of blaming whichever check ran first.

- **`.fvmrc` and `.vscode/settings.json` no longer drift on every `make codegen`** (`template/.fvmrc.jinja`, `template/.vscode/settings.json`, `template/CONTRIBUTING.md.jinja`, `template/.github/actions/setup-fvm/action.yml.jinja`, `.gitignore`) — `flutter_rust_bridge_codegen` shells out to `fvm install` (twice per run), and `fvm install` rewrites both files unless they already match its own output byte for byte. Every codegen therefore left two modified files that had nothing to do with the generated bindings, and in CI they rode along into the automated update PRs. `.fvmrc` is now committed in fvm's own serialization — its key order, LF, and **no trailing newline**, where a trailing newline alone is enough to trigger the rewrite (136 → 135 bytes) — with `"updateVscodeSettings": false`, which is what stops the second file being touched at all. Turning that off means fvm no longer writes `.vscode/settings.json`, so the template ships it instead: otherwise a generated project would have no `dart.flutterSdkPath`, and where fvm lacks privileged access it writes an *absolute, machine-local* path into a file the project commits. The shipped value stays `.fvm/flutter_sdk`, the version-agnostic symlink fvm creates alongside the pinned one, rather than the `.fvm/versions/<v>` that fvm writes into this setting and that would need editing on every Flutter bump (read out of fvm 4.1.2, the pinned version: `_updateCurrentSdkReference` creates the `flutter_sdk` link unconditionally, while `_resolveSdkPath` returns the version-pinned path). It stays POSIX-style on Windows because that is what fvm writes there too — it converts explicitly, "for JSON compatibility on Windows". Only `fvm install` and `fvm use` rewrite these files — `fvm dart`, `fvm flutter` and `make get` were measured not to. A project whose `.vscode/settings.json` was written by fvm may see that file conflict on update; taking the template's version is correct.

  Two consequences are documented in the shipped file itself and in `CONTRIBUTING.md`, because both are things a developer is otherwise told to "fix". **`fvm install` now warns on every run** — with the setting off and a `.vscode/` directory present, fvm prints *"You are using VSCode, but fvm is not managing VSCode settings for this project. Please remove `updateVscodeSettings: false`"*, which is advice to undo this change; it is cosmetic, fvm exposes no way to silence it, and shipping no `.vscode/` would not remove it either, since the same warning fires on `TERM_PROGRAM=vscode` alone. **A machine that cannot create the symlink gets a dangling path**: fvm skips *all* of `.fvm/versions/` and `.fvm/flutter_sdk` when it has no privileged access — verified by running an install with `privilegedAccess: false`, which leaves `.fvm/` holding only `version` and `release` — and with the setting off it no longer writes the absolute fallback path either. On Windows that state is Developer Mode being off; CONTRIBUTING now says to enable it before the first `fvm install`. `privilegedAccess` is reachable only through a config file — it is not in fvm's `ConfigOptions`, so neither `FVM_PRIVILEGED_ACCESS` nor a CLI flag sets it (confirmed: the env var is a no-op). The Windows failure itself is inferred from fvm's `checkIfNeedsPrivilegePermission` path, not observed — everything here was exercised on macOS.

- **`.fvmrc` survives a Windows checkout** (`template/.gitattributes`) — the byte-exact invariant above only holds if the working tree really contains those bytes, and under Windows' default `core.autocrlf=true` a fresh clone lands CRLF, so the file can never match what fvm emits and every `fvm install` rewrites it. git reports the tree clean throughout, because it normalizes CRLF away on diff, so the churn is invisible and the fix would have silently held on Unix only. `.fvmrc -text` disables eol conversion in both directions.

- **A merged pull request no longer leaves its branch behind** (`template/scripts/setup_repo_protections.dart`) — the script applied rulesets and the `native-build` environment but never touched repo settings, so `delete_branch_on_merge` stayed at GitHub's default of off and every merged branch stayed forever. The automation is what makes that a real leak rather than an annoyance: the dependency and template update workflows open one branch per upstream version, several times a week — libsignal_dart had accumulated 42 of them. `delete-branch: true` on `peter-evans/create-pull-request` does not cover this; it only removes branches the action itself closes as obsolete. The script now also sends `PATCH repos/<slug>` with `delete_branch_on_merge=true`, warning rather than failing when it cannot, as the environment step does, and `--no-environment` does not skip it. One caveat worth knowing: GitHub performs the deletion as whoever merged the pull request, so a `deletion` ruleset covering the branch restricts it to that ruleset's bypass actors and the setting may quietly do nothing for anyone else. It cannot make things worse — the branch simply stays, exactly as it does with the setting off.

## [4.1.0] - 2026-07-30

### Added

- **CI verifies the declared MSRV** (`template/.github/workflows/test-reusable.yml.jinja`, `template/.github/actions/setup-rust/action.yml.jinja`) — `rust-version` in `rust/Cargo.toml` was a promise nothing checked, so the first dependency or language feature to raise the real floor would have broken source builds silently. The new `msrv` job reads the version out of the manifest rather than repeating it, so it cannot drift from the claim it checks, then installs that toolchain and runs `make rust-check`, plus protoc where `enable_protoc` is set, since a prost-based build script shells out to it and the job would otherwise fail on tooling rather than on the MSRV. `setup-rust` gained a `toolchain` input (default `stable`).

- **The third-party notice workflow is documented for contributors** (`template/CONTRIBUTING.md.jinja`) — a new *Third-party notices* section records why `--target all` is load-bearing, what the drift message reports, and the exact `cargo-about` invocation that re-validates the inventory against an independent implementation (expected result: the only crate it reports missing is the package's own).

### Fixed

- **The notice inventory no longer depends on the machine that generated it** (`template/scripts/src/third_party_notices.dart.jinja`) — `cargo tree --target <triple>` filters *normal* dependencies by that triple but resolves *build*-dependencies for the **host**, so `collectLinkedCrates` recorded the build graph of whoever ran the generator. A project whose graph contains a host-gated build dependency therefore produces a different inventory on each platform: in libsignal_dart, `prost-build` → `tempfile` → `rustix` selects `errno` on a macOS host and `linux-raw-sys` on a Linux one — one crate swapped for another with the crate count unchanged, so `make verify-third-party-notices` rejected in CI a file that was correct where it was generated. The problem is not confined to build edges — proc-macro subtrees are host-compiled too, which is how `winapi`, reached through `ansi_term` inside a proc-macro crate, stays invisible everywhere but a Windows host — so no per-target query escapes it. The crate set is now taken from `cargo tree --target all`, the only query cargo offers that applies no platform filtering at all. The per-target sweep is kept, because it is the one thing that fails when a declared release target stops resolving. Over-attribution is the deliberate trade: the extra entries are build tooling and platform-gated crates a given build never links, but a file that lists them on every machine is worth more than a narrower one that changes with the machine — the byte-exact check is only viable if the output is reproducible. **A project that already committed a `THIRD_PARTY_NOTICES.txt` must regenerate it after this update** — the file grows by whatever the generating host was hiding (openmls_dart 237 → 264 crates, libsignal_dart 206 → 241).

- **`--check` reports what actually differs** (`template/scripts/src/third_party_notices.dart.jinja`) — the drift message now names the first differing line and samples the lines unique to each side. This check fails on a machine nobody is sitting at, so the CI log is the entire diagnosis, and "the contents differ" left the reader to bisect a 400 KB generated file by hand — which is exactly what the bug above cost.

## [4.0.0] - 2026-07-30

### Changed (BREAKING)

- **Every project must generate and commit `THIRD_PARTY_NOTICES.txt` before its next CI run** (`template/scripts/generate_third_party_notices.dart.jinja`, `template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`, `template/.github/workflows/build-{{ package_name }}.yml.jinja`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`) — the notice inventory added below is verified byte-for-byte by `make verify-third-party-notices`, which now runs in the test workflow, in `build-<package>.yml`'s `check-release` job, and in the preflight of both release stages. A project that adopts this version without generating the file fails all of them on the file's absence. **After `copier update`, run `make third-party-notices` once and commit the result** — it needs a resolved `Cargo.lock`, so run `make build` (or any cargo command that locks the graph) first. Fresh generations get the same step in the post-generation message.

### Added

- **Third-party notice inventory for the shipped native library** (`template/scripts/generate_third_party_notices.dart.jinja`, `template/scripts/src/third_party_notices.dart.jinja`, `template/scripts/src/spdx_license_texts.dart`, `template/test/scripts/third_party_notices_test.dart.jinja`, `template/Makefile.jinja`, `template/.gitattributes`) — the prebuilt library is statically linked against its whole Rust dependency tree, and MIT, BSD and Apache-2.0 all require those notices to accompany a binary distribution, including an application that embeds the library. Flutter's `LicenseRegistry` does not cover them: it aggregates `LICENSE` files of pub packages, and Rust crates are not pub packages. `make third-party-notices` generates `THIRD_PARTY_NOTICES.txt` at the package root from `cargo tree --locked --edges normal,build` unioned across every released target (wasm32 only when `enable_web`), resolves each crate's SPDX expression and licence texts via `cargo metadata`, and pools identical texts by reference — the Apache-2.0 text alone can appear in a hundred crates, and pooling cut openmls_dart's file from 1.9 MB to under 500 KB. `make verify-third-party-notices` diffs the committed file byte-for-byte. Three decisions carry the weight. **Build edges are kept**, because that is how vendored native code reaches the binary: a `*-src` crate carrying C sources is a build-dependency of its `*-sys` wrapper, so `--edges normal` silently dropped the statically linked OpenSSL from openmls_dart's inventory, and no mechanical rule tells such a crate apart from a pure build tool. **`--locked`**, because without it a stale `Cargo.lock` lets cargo re-resolve the graph, so the same commit could produce different inventories on different machines. **The file is not declared under `flutter: assets:`**, because a package-declared asset is bundled into every consuming application whether used or not; README documents the two lines an app needs to surface it itself. Licence discovery goes three directories deep, so licences shipped beside vendored code are found (SQLCipher's, the Dart SDK headers', the Unicode tables'), and walks up to the repository root for git dependencies, which keep their licence there rather than in the member directory. For a crate that ships no licence file of its own, the canonical text of the licence it declares is supplied from `spdx_license_texts.dart`: only invariant texts verbatim (Apache-2.0 and MPL-2.0 carry no per-crate copyright line), MIT composed from the crate's `authors` metadata and labelled as such in the output, and a licence whose copyright line cannot be recovered reported as SPDX-only rather than guessed at.
- **Notice regeneration wired into `make rust-update`, and verified in CI and both release stages** (`template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`, `template/.github/workflows/build-{{ package_name }}.yml.jinja`, `template/scripts/src/release.dart.jinja`, `template/scripts/src/release_frb.dart.jinja`) — the inventory is derived from the dependency graph, so any lockfile change invalidates it. Regenerating inside `rust-update` means the scheduled update workflow, which already calls that target, refreshes the notices in the same PR instead of landing a stale file and failing its own CI. `test-reusable.yml` verifies it once on the Linux x86_64 leg (the generator unions every release target regardless of host), and `build-<package>.yml` verifies it in `check-release`, before the build matrix starts — every archive it produces embeds the file alongside `LICENSE`, and a hand-pushed tag skips the release script's own gate. Both release stages call `assertNoticesCurrent()` in preflight, ahead of anything irreversible: a pushed tag and a published pub.dev version cannot be taken back. Adopting this in an existing project requires generating and committing the file once — see the breaking-change entry above.
- **Write ordering and durability stated as a requirement in the FRB store-callback guidance** (`template/.claude/skills/frb-patterns/SKILL.md.jinja`) — the `DartFn` store-callback example already had the correct shape (`storage_write(key, value).await;` before `Ok(result)`), but nothing said that the `.await` is load-bearing rather than incidental style, so there was no reason for a reader to preserve it. A new *Write Ordering and Durability* section states the two rules a wrapper that delegates state persistence to Dart must satisfy: **(1)** every write callback is awaited before the operation's result is returned — a fire-and-forget write, or one awaited after `Ok(...)` is built, lets the caller act on output whose state may never be stored; **(2)** the Dart callback must not resolve its future until the write is durable — resolving once the value sits in a map, an unflushed file or a write-behind queue satisfies rule 1 while still losing the write to a crash. The split matters because the two obligations sit on different sides: rule 1 is the wrapper's and holds by construction once every callback is awaited, while rule 2 is the application's and **cannot be inferred from the callback signature**, so the wrapper has to state it explicitly or consumers will not know it exists. What a lost or rolled-back write actually costs is protocol-specific, so the section defers that to the generated package's own `SECURITY.md` rather than asserting anything cryptographic here. Extracted from libsignal_dart, where the price is concrete: message keys are derived deterministically from stored state with no per-message nonce guard, so a lost or rolled-back session write makes the next send reuse a message key and IV — confirmed there by restoring an earlier session record and observing a byte-identical AES-CBC body.
- **DartFn callbacks documented as non-failable** (`template/.claude/skills/frb-patterns/SKILL.md.jinja`) — a `DartFnFuture<T>` has no error channel, so a Dart closure that throws does not reach the Rust side as a `Result`: FRB panics the worker thread with `Dart throws exception but Rust side assume it is not failable: <the error>`. The skill documented only the opposite direction (`Result<T, String>` → Dart exception, under *Error Handling*), which invites the assumption that the two are symmetric. They are not, nothing in the callback signature says so, and nothing fails at compile time — the first sign is a panicking worker at runtime. A new *Callbacks Are Not Failable* section states the two consequences: **(1)** the Dart-facing interface has to document that implementations must not throw, since the implementer is the one who has to honour it; **(2)** a callback cannot act as a veto — to let the Dart side reject something, give the callback a return type that expresses rejection (`DartFnFuture<bool>`, not `DartFnFuture<()>`) so the Rust side branches on it. The section also notes that a write-back callback invoked *after* the operation's real work is done cannot abort that work whatever it returns, so a check that must be able to stop an operation has to run before it — usually a read callback rather than a write one. *Error Handling* gains a cross-reference so the asymmetry is visible from either side. Found in libsignal_dart while widening a store callback to its upstream argument list: the upstream trait documents that the store should "produce an error" when it sees a replayed pre-key combination, and a store implementing that literally by throwing would have panicked the worker instead of failing the decryption.
- **`make rust-test` and a CI step that runs it** (`template/Makefile.jinja`, `template/.github/workflows/test-reusable.yml.jinja`) — the crate's own `#[cfg(test)]` tests were never executed anywhere in CI. That matters beyond coverage: projects routinely cite a specific unit test as the reachability justification for an advisory ignore in `.cargo/audit.toml` / `rust/deny.toml` (openmls_dart cites `classical_ops_do_not_init_libcrux` for six libcrux RUSTSEC entries), and that justification was going unverified on every run. Runs on the Linux x86_64 matrix leg only, same rationale as clippy.
- **A project with a custom tag prefix asserts that the default `v` shape is rejected** (`template/test/scripts/check_updates_test.dart.jinja`) — `rejects a bare version without the configured prefix` only covered a version with no prefix at all. `v` is the copier default, so a `vX.Y.Z` tag is the likeliest wrong thing to reach a project that overrides the prefix — from a copied command line, or from a sibling repo. Rendered only when `version_tag_prefix != 'v'`, where the tag genuinely belongs to a different upstream naming scheme; for a default-prefix project `vX.Y.Z` is valid and asserting otherwise would be wrong. Ported from openmls_dart, which had carried the assertion locally.
- **The update-template skill points at the template repository** (`template/.claude/skills/update-template/SKILL.md`) — the Resources list named only the copier documentation, and the `.copier-answers.yml` example showed a placeholder `_src_path: https://github.com/...`. Both now name this template, and the CHANGELOG link is marked as the thing to read before running `copier update`. Ported from libsignal_dart.
- **freezed toolchain preinstalled with working version bounds** (`template/pubspec.yaml.jinja`) — the first data-carrying enum/struct in the FRB API makes codegen emit freezed sealed classes and fail with `MissingDep: Please add freezed to your dev_dependencies`. The template now ships `freezed_annotation ^3.0.0` (dependencies) plus `freezed >=3.0.0 <3.2.6` and `build_runner >=2.4.0 <2.6.0` (dev_dependencies). The upper bounds are load-bearing: pub resolves `freezed ^3.0.0` to the `3.2.6-dev.1` prerelease, which fails flutter_rust_bridge_codegen's dependency version check, and `build_runner >=2.6` AOT-compiles builders via `dart compile`, which refuses to run in packages using native build hooks (`hook/build.dart`) — both discovered while wiring enigma_dart's typed `EnigmaError`.

### Changed

- **Update workflows detect a crashed checker by what it wrote, not by its exit code** (`template/.github/workflows/check-{{ package_name }}-updates.yml.jinja`, `template/.github/workflows/check-template-updates.yml.jinja`) — both checkers exit 0 when up to date, 1 when an update is available and 2 on failure, but the workflows ran them under `|| true`, making a crashed checker indistinguishable from "no updates available". That is precisely what hid the tag-validation bug above behind green scheduled runs. Discriminating on the exit code cannot work here, and an earlier revision of this change assumed it could: the checkers are invoked through `make`, and **GNU make collapses any non-zero recipe status into its own exit 2** (verified: a recipe exiting 1 makes `make` exit 2), so an `exit_code > 1` guard fires on the ordinary "update available" path and would have failed the workflow on exactly the event it exists to serve — no update PR or notification would ever be opened again. The gate is the artefact instead: the checker writes `needs_update=` to its outputs file *before* signalling, and writes nothing at all when it throws, so a missing `needs_update=` line means it failed, and the step fails with an `::error::` that tells the reader not to interpret it as "up to date". Manual `target_version` input is additionally validated in the workflow shell — it is interpolated into `ARGS` and reaches a shell before the Dart checker ever sees it — using a pattern built from `{{ version_tag_prefix }}`.
- **The test workflow triggers on `hook/`, `scripts/` and `Makefile` changes** (`template/.github/workflows/test.yml.jinja`) — edits to the build hook, tooling scripts and the Makefile previously ran no tests at all, even though `test/hook/` and `test/scripts/` cover exactly those. Workflow files are now watched on pull requests too, not only on pushes. `THIRD_PARTY_NOTICES.txt` and `.gitattributes` are watched as well, because `make verify-third-party-notices` runs in this workflow: the notices file is the artefact being checked, and `.gitattributes` decides which bytes a checkout materialises for it. Without them the one commit that can break — or fix — that check was also the one commit that did not run it, so a stale inventory reached `main` unverified and surfaced only in the release preflight of both stages. Found the hard way in openmls_dart: the commit that repaired its `.gitattributes` handling of that very file triggered no run at all and had to be dispatched by hand.
- **GitHub Actions moved to their current majors** (`template/.github/workflows/*.jinja`, `template/.github/actions/setup-fvm/action.yml.jinja`) — `actions/checkout` v4→v7, `actions/upload-artifact` v4→v7, `actions/download-artifact` v4→v8, `actions/cache` v4→v6, `actions/create-github-app-token` v2→v3, `android-actions/setup-android` v3.2.2→v4.0.1 and `schneegans/dynamic-badges-action` v1.7.0→v1.9.0. Most of the majors are the Node 20→24 runtime migration, which requires nothing on GitHub-hosted runners (it needs runner ≥2.327.1, so a self-hosted runner would have to be updated first). Three carry behaviour worth knowing. `download-artifact` v8 now **fails** a run on an artifact digest mismatch instead of logging a warning — a welcome hardening of `build-<package>.yml`'s release job, which is exactly the step that packages the native archives consumers download, and recoverable by re-dispatching because it fails before the GitHub Release is created. `checkout` v7 refuses to check out a fork PR under `pull_request_target`/`workflow_run`; no checkout in the template passes an explicit `ref`, so all of them resolve to the base or default branch and are unaffected. `setup-android` v4 defaults to cmdline-tools 20.0 and still reads `ANDROID_SDK_ROOT` from the environment, which is what `build-<package>.yml` interpolates into `ANDROID_NDK_HOME`. The two SHA-pinned third-party actions were verified against their upstream tag refs before bumping. Note that Dependabot cannot see these files — `*.yml.jinja` is not a manifest it scans — so template action pins are bumped by hand, from the PR Dependabot opens in a generated project.
- **A rejected upstream tag says which input it came from** (`template/scripts/src/check_updates.dart.jinja`, `template/test/scripts/check_updates_test.dart.jinja`) — `validateUpstreamTag` guards three inputs (the GitHub API response, the maintainer's `--version` argument, and the tag recorded in `rust/Cargo.toml`) and threw the same `Refusing unexpected upstream tag format` for all of them, so the message never said where to look. The three fail for different reasons and the fix differs: a typo in a dispatch input, a stale pin, or upstream changing its tag scheme. A `source` parameter now names the input; it defaults to the previous wording, so a call site that does not pass one is unchanged. Ported from liboqs_dart, which is not copier-managed but shares this script's lineage.
- **The changelog AI is told that a wrapper binds a subset of its upstream** (`template/scripts/src/update_changelog.dart.jinja`) — the prompt asked for "2-7 bullet points summarizing key changes", which invites the model to present upstream features the package does not bind or expose as if they were this package's own. Ported from libsignal_dart, where the failure was observed on real update PRs and where a project-specific version of this prompt has been in use since: out-of-scope upstream changes are now collapsed into a single bullet ending "— none of which this library exposes", only changes reaching the package's own API get their own bullet, and "nothing this package exposes changed" — the common case — must be stated outright instead of padded into a list. The rules that name a specific package's exposed surface deliberately stay in that package: the template cannot know it, and a copier question would freeze evolving prose in an answers file. The file header now also records that this step never bumps the `{{ crate_name }}` crate version, which is a deliberate `make release-frb` step, so update PRs can accumulate on `main` without publishing a native binary per bump.

### Fixed

- **One crashing fuzz target no longer cancels every target after it** (`template/.github/workflows/fuzz.yml.jinja`) — targets ran sequentially in one job, `for target in $(cargo +nightly fuzz list); do cargo +nightly fuzz run "$target" …; done`. `cargo fuzz run` exits non-zero when libFuzzer finds a crash, and the step is a plain `bash -e` script, so the loop aborted at the first crash: targets after it never ran, and the workflow reported one failure where there might have been several. The job is now a `fail-fast: false` matrix, one job per target, so every target runs to completion and reports independently, and a crash uploads a per-target artifact (`fuzz-artifacts-<target>`) instead of one shared directory. Targets stay dynamically discovered — a new `discover` job reads the `[[bin]]` names out of `rust/fuzz/Cargo.toml`, which is where cargo-fuzz itself gets them, so it needs neither a toolchain nor a build (verified: the parser reproduces libsignal_dart's hand-maintained six-target list exactly, and openmls_dart's two). An empty list is a valid state, so the fan-out is guarded with `if: needs.discover.outputs.targets != '[]'` rather than letting GitHub error on an empty matrix. This costs runner minutes: setup now repeats per target instead of once. `cargo install cargo-fuzz` amortises (rust-cache v2.9.1 caches `~/.cargo/bin`), but the seed-corpus build does not, so expect a visible increase on the weekly cron in exchange for never losing a target's coverage to another target's crash.
- **`LICENSE` no longer renders a broken copyright line** (`template/LICENSE.jinja`, `copier.yml`) — the file interpolated `{{ current_year }}`, which was never defined as a question, so Jinja rendered it empty and every fresh MIT/BSD project got `Copyright (c) -present <package> authors`. Replaced with a new `copyright_year` answer (four-digit validator, default `2026`). It is a stored answer rather than a rendered "now" on purpose: the notice must keep naming the year of first publication, so re-rendering it in a later year must not move it.
- **`LICENSE` no longer starts with a blank line** (`template/LICENSE.jinja`) — `{%- if license == … %}` strips whitespace *before* the tag but emits the newline after it, so every generated licence began with an empty line. Each branch now opens with its first line of licence text on the tag's own line; `-%}` would have been wrong here, as it would also eat the leading indentation that centres the AGPL and Apache headings.
- **The rendered `check_updates_test.dart` is `dart format`-clean** (`template/test/scripts/check_updates_test.dart.jinja`) — one `expect(…)` rendered to 82 columns, so `dart format` rewrote it and generated projects shipped a file their own `make format-check` rejects. Nothing on that line is interpolated by Jinja, so it was 82 columns for every project. This is the second time an over-long line reached a generated project through a `.jinja` file the template's own CI cannot format-check; the line now carries a comment saying why it stays wrapped.
- **Upstream tag validation is derived from `version_tag_prefix` instead of a hardcoded `v?`** (`template/scripts/src/check_updates.dart.jinja`) — the guard added in v3.0.0 rejected anything not matching `^v?\d+\.\d+\.\d+$`, but the prefix itself is a template variable, so every project generated with a non-default prefix failed its own scheduled update check on the first step with `Refusing unexpected upstream tag_name format`. The workflow's blanket `|| true` (fixed below) kept the run green, so the breakage stayed invisible — a real upstream release would simply never have been picked up. openmls_dart (`version_tag_prefix: "openmls-v"`) had been in that state since adopting v3.0.0. The pattern is now built from `RegExp.escape(_tagPrefix)` and applied to all three untrusted inputs: the API response, manual `--version` input (previously not validated at all), and the tag recorded in `rust/Cargo.toml`. The no-`upstream_crates` branch is deliberately excluded — `getCrateVersion()` returns the crate's own unprefixed version, which is not a tag and must not be validated as one. New `template/test/scripts/check_updates_test.dart.jinja` guards the regression, building its fixtures from the configured prefix so a project with a custom prefix exercises its own format.
- **The build hook no longer re-runs on every single build** (`template/hook/build.dart.jinja`) — `output.dependencies.add(skipMarkerUri)` ran unconditionally, including when `.skip_<package>_hook` does not exist, which is the normal state for every consumer. `hooks_runner` classifies a declared-but-missing file as modified during the build and forces a redundant second hook pass, on every build, for everyone. Measured on a real project with an instrumented hook: 1→2→3 invocations across three consecutive builds before, 1→1→1 after. The marker is now declared only inside the `existsSync()` branch; invalidation is unaffected, because removing an existing marker makes the declared dependency disappear and drops the cached skip result (verified through a full codegen cycle: marker present → hook skips → marker removed → hook re-runs → library registered).
- **`description` is quoted and escaped in generated manifests** (`template/pubspec.yaml.jinja`, `template/rust/Cargo.toml.jinja`) — the description was emitted as an unquoted YAML plain scalar, so any value containing `": "` (e.g. `"messaging: 1:1"`) produced an unparseable `pubspec.yaml` and killed the post-generation `flutter create` tasks, leaving a half-generated project with `.git` already initialized. Both manifests now emit a double-quoted string with `\` and `"` escaped (the same escaping is valid for YAML and TOML). Found while generating enigma_dart.
- **Freshly generated projects pass `make analyze`** (`template/test/{{ package_name }}_test.dart.jinja`) — the two imports were emitted in a fixed order (`package:test` first), but the `directives_ordering` lint wants package imports sorted by URI, so the correct order depends on how `package_name` compares to `"test"` (e.g. `package:enigma` must come first, `package:zebra` last). The template now orders the imports conditionally on the package name.
- **`cargo check` / `make rust-check` work before the first codegen run** (`template/rust/src/frb_generated.rs`) — `lib.rs` declares `mod frb_generated;` but the file only existed after `make codegen`, so a freshly generated project failed `cargo check` with E0583. A placeholder file (overwritten by codegen) ships with the template.
- **Dependabot can rebase and clean up its own branches** (`template/.github/rulesets/signing-commit.json`, `template/.github/rulesets/delete-branches.json`, `template/.github/rulesets/README.md.jinja`) — both rulesets target `~ALL` branches and `signing-commit.json` has an empty `bypass_actors`, so `non_fast_forward` applied to every branch with no exemption for anyone, not even an admin. Dependabot refreshes an open PR by force-pushing a rewritten commit, so its grouped `github-actions` PR could never be rebased onto a moved `main`: on the first scheduled run after the Dependabot config shipped in v3.0.0, it commented *"Dependabot attempted to update this pull request, but because the branch … is protected it was unable to do so"* and left the PR frozen at the state it was opened in. `deletion` from `delete-branches.json` blocked `@dependabot recreate` and post-merge branch cleanup for the same reason. Observed in openmls_dart and true by construction of every project generated since v3.0.0. Both rulesets now exclude `refs/heads/dependabot/**/*` — the trailing `/*` is load-bearing, because these are `fnmatch` patterns in pathname mode where a bare `**` does not cross a `/`, so `refs/heads/dependabot/**` matches only a one-segment `dependabot/foo` and misses the `dependabot/github_actions/github-actions-<hash>` shape Dependabot actually generates (deeper still when a config scopes updates to a directory); confirmed against the live evaluation endpoint, `gh api repos/<slug>/rules/branches/<url-encoded-branch>`, for one-, two- and five-segment names plus an unrelated branch and `main` as controls. The fix is deliberately a `ref_name.exclude` rather than an `Integration` bypass actor: the rulesets target `~ALL`, so a bypass actor would be exempt on `main` as well, which is strictly worse. Nothing is weakened by the exclusion — Dependabot's commits carry a valid GitHub signature regardless of the rule, and they still have to pass `main`'s own `pull_request` gate and `required_signatures` to land. The runbook documents the reasoning, and the "add a bypass actor for your bot" note now warns that a force-push or delete need is scoped with `exclude`, not with a bypass. The rulesets are committed JSON applied by hand, so an existing project picks the exclusions up only when it re-runs `make setup-repo-protections` — until then its Dependabot PRs stay frozen exactly as before. Branches from `peter-evans/create-pull-request` (`update-{{ package_name }}-*`, `update-template-*`) are intentionally left in scope: those PRs are recreated per version rather than refreshed in place, so the force-push path has not been exercised.
- **The FVM cache in CI never saved anything** (`template/.github/actions/setup-fvm/action.yml.jinja`) — the cache pointed at `~/.fvm`, but fvm keeps installed SDKs in `~/fvm/versions` (`kAppDirHome` = user home + `/fvm`, joined with `versions`; the user home is `USERPROFILE` on Windows and `HOME` elsewhere, confirmed against fvm 4.1.2, the version `dart pub global activate fvm` currently resolves to). `~/.fvm` is the *per-project* directory fvm symlinks inside a checkout, not the global cache, so the cached path existed on no runner. A missing path is not an error to `actions/cache`: it warns in the post step and reports success, which is why this survived unnoticed in every generated project — the step is green, the job summary shows nothing wrong, and the only trace is a `Path Validation Error` warning buried in the post-step log plus a repository that holds no `fvm-*` entry at all. Measured in openmls_dart: `fvm install` takes 71 s on Linux and sits inside a 163 s setup step on Windows, paid by all four matrix legs on every single run. Three further changes ride along. The key now carries `runner.arch`, because Linux x86_64 and Linux ARM64 both report `runner.os == 'Linux'` and were emitting one byte-identical key (`fvm-Linux-<hash>` in both legs' logs) — harmless only while nothing saved, but the moment saving works one leg restores the other architecture's `bin/cache/dart-sdk`, which Flutter then keeps rather than redownloads, because its revision stamp matches, and fails to execute. `restore-keys` is dropped: a near-miss restored the previous SDK and then installed the new one beside it, so the entry grew by a full SDK on every Flutter bump, whereas an outright miss costs one reinstall. fvm itself is now pinned (`dart pub global activate fvm 4.1.2`, exposed as the action's `fvm-version` input) rather than resolved to whatever is latest that day: this action hardcodes where fvm stores SDKs, so an unannounced major that relocated them would break every job in every generated project at once, including a release in progress. Dependabot cannot see that pin — `dart pub global activate` is not a manifest it scans — so it is bumped by hand, deliberately, after confirming the new version still resolves its cache to `$FVM_CACHE_PATH/versions`. `FVM_CACHE_PATH` is set explicitly instead of inherited for the same reason, making the cached path a contract rather than a guess; the value matches fvm's own default, so nothing relocates today. And a new `Verify FVM cache layout` step asserts the directory is populated after `fvm install`, converting the silent-warning failure mode into a job that fails pointing at the action — this is the actual defect class here, not the typo. It fails rather than annotates because annotate-and-continue is exactly the mode that hid the bug for months: it is not the safe option, it is the broken one with a louder log line. The cost of that choice is bounded — the version pin means fvm cannot move on its own, and the check sits before anything irreversible in both release stages (`publish.yml` calls setup-fvm before `Publish to pub.dev` and `gh release create`; `build-<package>.yml` calls it in `check-release`, its first job, before the build matrix), so a failure costs a re-run rather than a broken release. The step also prints the SDK size (~2.5 GB per version uncompressed), keeping the cache budget visible — the 10 GB per-repository limit is shared with the Rust caches and evicted LRU across all of them, and in openmls_dart those already occupy 8.8 GB, so the first runs will show what the trade actually costs.
- **CI was blind to changes in its own workflows and composite actions** (`template/.github/workflows/test.yml.jinja`) — the path filters named `test.yml` and `test-reusable.yml` but never `.github/actions/**`, so a PR touching `setup-fvm`, `setup-rust`, `setup-make` or `setup-protoc` ran no tests, and the release-only workflows (`publish`, `build-<package>`) were unwatched as well — they execute once, at a moment when a failure is expensive. Compounding it, the job skipped every PR whose author was a bot, which swept in Dependabot's grouped action bumps and the template update PRs: exactly the PRs that change what CI executes. In openmls_dart the Dependabot PR bumping seven actions completed as `skipped` in one second and would have merged with no signal at all. The filters now carry `.github/**` on both `push` and `pull_request` (the FVM cache fix above is itself only reachable in review because of this), and the skip is narrowed from "any bot" to the `update-{{ package_name }}-*` branches that `check-{{ package_name }}-updates.yml` opens for itself, which move `native_version` ahead of the released binaries. `github.head_ref` is empty outside `pull_request`, so push, dispatch and `workflow_run` runs are unaffected. This works because a `pull_request` run resolves reusable workflows and local actions from the merge ref: the PR's own versions are what execute, so an action bump is genuinely exercised before it lands.
- **A native-update entry lands at the top of `[Unreleased]`, not below `### For Contributors`** (`template/scripts/src/update_changelog.dart.jinja`, `template/test/scripts/update_changelog_test.dart.jinja`) — `insertChangelogEntry` created its `### For Users` block at the point where the `[Unreleased]` section *ends*, so whenever the accumulated changes were CI or tooling only — the section then holds `### For Contributors` and nothing else, which is its normal shape between feature work — the user-facing highlight was filed underneath them, the reverse of the order every released section uses. It also emitted a second `### For Users` heading when the section already had one that ran to the end of `[Unreleased]` with no `#### ✨ Highlights` / `#### Changed` under it. The insertion point is now the top of the section (the index of the `## [Unreleased]` heading is tracked while scanning), and an existing `### For Users` is extended rather than duplicated. Found while restructuring liboqs_dart's `[Unreleased]` to the For Users / For Contributors shape this function expects.
- **A native-library bump is filed under `#### Changed`, never under `#### Changed (Breaking)`** (`template/scripts/src/update_changelog.dart.jinja`, `template/test/scripts/update_changelog_test.dart.jinja`) — the subsection was matched with `startsWith('#### Changed')`, which also matches `#### Changed (Breaking)`. Two things followed, both reproduced against openmls_dart's real `[Unreleased]`, whose `### For Users` opens with a breaking subsection: the routine bump was announced as a **breaking change**, and because the branch fires once per matching heading without consulting `insertedChanged`, it was then filed a **second** time under the real `#### Changed` — the same bullet in two places, one of them wrong. The match is exact now. Two placement rules follow from it. A missing `#### ✨ Highlights` is no longer created inline before whichever `#### Changed` was found — that put it after the breaking subsection — but spliced at the top of the `### For Users` block, where the documented order (Highlights → Changed (Breaking) → Changed → Security → Fixed) wants it. A missing `#### Changed` is created just before the first subsection that follows it in that order (`#### Security`, `#### Fixed`, …), or at the end of the block when there is none, rather than at the point of discovery. Creating only what is actually missing also removes a duplicate `#### ✨ Highlights` heading that the end-of-block fallback emitted whenever `### For Users` had Highlights but no Changed.
- **The `[Unreleased]` regression test the template ships is `dart format`-clean** (`template/test/scripts/update_changelog_test.dart.jinja`) — the test added above carried an 81-character line, one past the default `page_width`, and it contains no template variables, so it renders identically everywhere: `make format-check` would have failed in **every** generated project on the first run after `copier update`, on a file the project never wrote. Caught by porting the fix into openmls_dart, where `dart format` rewrapped exactly that line and nothing else in the repository (83 files, 1 changed) — which also confirms no other rendered Dart file is affected. The line is pre-wrapped in the template now.
- **A locally built native library invalidates the hook when it changes or disappears** (`template/hook/build.dart.jinja`) — the local-build branch declared `rust/Cargo.toml` as its only dependency, never the library it had just registered. `_findLocalBuild` returns that path precisely because the file exists, so declaring it follows the same declare-only-while-it-exists rule as the skip marker above. Without it the cached hook result outlives the file it points at, in both directions: rebuilding the crate without touching `Cargo.toml` keeps serving the previous binary, and removing the build (`make clean`, or switching to the downloaded release) leaves the cached asset pointing at nothing, so the next `dart test` / `dart run` aborts with `PathNotFoundException: Cannot copy file to .dart_tool/lib/lib<crate>.<ext>` before a single test runs. Hit in openmls_dart while running the script tests after a clean; the recovery is deleting the stale `.dart_tool/hooks_runner/<package>/<hash>` entry, which is not something the error points at.

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

[Unreleased]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.6.0...HEAD
[4.6.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.5.0...v4.6.0
[4.5.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.4.0...v4.5.0
[4.4.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.3.0...v4.4.0
[4.3.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.2.0...v4.3.0
[4.2.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.1.0...v4.2.0
[4.1.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v4.0.0...v4.1.0
[4.0.0]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v3.0.3...v4.0.0
[3.0.3]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v3.0.2...v3.0.3
[3.0.2]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v3.0.1...v3.0.2
[3.0.1]: https://github.com/djx-y-z/copier-dart-frb-wrapper/compare/v3.0.0...v3.0.1
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
