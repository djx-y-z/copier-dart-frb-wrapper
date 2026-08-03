# Entry point for this repository's own tooling.
#
# This is the *template* repository, not a generated project: it ships a
# Makefile to every project it renders (template/Makefile.jinja), but had none
# of its own, so releasing it was a documented sequence of git commands. The
# targets here exist so that releasing the template is the same one-liner as
# releasing a generated package.
#
# Arguments go through ARGS, as in the generated projects:
#
#     make release ARGS="--version 4.3.0"
#
# Passing them directly does not work — `make release --version 4.3.0` makes
# `make` read `--version` as its own flag.

.PHONY: help release test

PYTHON ?= python3

help:
	@echo ""
	@echo "  copier-dart-frb-wrapper"
	@echo ""
	@echo "  Release:"
	@echo "    make release ARGS=\"--version X.Y.Z\"   - Finalize CHANGELOG, sign commit + tag, push"
	@echo "    make release ARGS=\"--version X.Y.Z --no-push\"  - Prepare locally, do not push"
	@echo ""
	@echo "  Checks:"
	@echo "    make test                              - Test the release script's pure decisions"
	@echo ""
	@echo "  Testing the template (render it into a scratch directory) is driven"
	@echo "  by the 'test-template' Claude skill; see .claude/skills/."
	@echo ""

# Finalizes `## [Unreleased]` into a dated version section, fixes the compare
# links, then signs a commit and a tag and pushes them. Pushing the tag is what
# triggers .github/workflows/release.yml to publish the GitHub Release.
#
# Interactive by design: the commit and tag are signed, so a passphrase prompt
# appears. A mistyped passphrase is retried rather than aborting the release,
# and an interrupted run is resumed by re-running the same command.
release:
	@$(PYTHON) scripts/release.py $(ARGS)

# Covers the release script's pure decisions — the resume predicate and the
# CHANGELOG rewrite. Stdlib unittest, no dependencies to install.
#
# Discovery is rooted at scripts/ because the tests import `release` as a
# top-level module. That means a test file placed anywhere else is not run and
# does not fail — it is simply invisible. Keep this repository's own tests in
# scripts/, or widen the root here. (Tests for the *generated* project live in
# template/test/ and run inside a generated project, not from here.)
test:
	@cd scripts && $(PYTHON) -m unittest discover -p 'test_*.py' $(ARGS)
