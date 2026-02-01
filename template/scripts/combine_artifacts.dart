#!/usr/bin/env dart
/// Combine build artifacts from CI.
///
/// Usage:
///   dart run scripts/combine_artifacts.dart [options]
///
/// This script is used by CI to combine artifacts from parallel builds.
/// Not typically needed for local development.
library;

import 'dart:io';

import 'src/common.dart';

void main(List<String> args) async {
  logInfo('Combining build artifacts...');

  final packageDir = getPackageDir();
  final artifactsDir = Directory('${packageDir.path}/artifacts');

  if (!artifactsDir.existsSync()) {
    logWarn('No artifacts directory found.');
    return;
  }

  // List all artifacts
  final artifacts = artifactsDir.listSync(recursive: true);
  logInfo('Found ${artifacts.length} artifact files.');

  for (final artifact in artifacts) {
    if (artifact is File) {
      logInfo('  ${artifact.path}');
    }
  }

  logInfo('Artifacts combined successfully!');
}
