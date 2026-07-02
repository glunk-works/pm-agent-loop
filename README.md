# pm-agent-loop

-----

## Table of Contents

- [Installation](#installation)
- [Setup](#setup)
- [Usage](#usage)
- [Security](#security)
- [License](#license)

## Installation

```console
pip install pm-agent-loop
```

Or, from a local checkout of this repository:

```console
hatch build
pip install dist/pm_agent_loop-*.whl
```

## Setup

`pm-agent-loop` calls the Anthropic API to run the PM and Critic personas. Before your
first session, store your Anthropic API key in your OS-native credential store:

```console
pm-agent-loop configure-key
```

You'll be prompted for the key with hidden input; it's stored via `keyring` and is
never printed, logged, or written to any spec file.

## Usage

Start a new spec from a raw, unstructured idea:

```console
pm-agent-loop run --idea "A CLI that tracks daily habits and streaks" --output ./docs/project_spec.json
```

Or start from an existing artifact (an issue, doc, or partial spec) that needs gaps
filled in:

```console
pm-agent-loop run --artifact-path ./notes/habit-tracker-draft.md --output ./docs/project_spec.json
```

The PM persona interviews you one question at a time until every required checklist
field is answered or explicitly marked `N/A`. You can end the interview early at any
point by typing `that's enough` or `generate the spec` — anything left unanswered is
recorded in the spec's `open_questions_for_architect` field rather than silently
dropped. Once a draft passes the Critic's review (or the revision cycle cap is
reached), you're asked to explicitly sign off before anything is written to disk.

## Security

- The Anthropic API key is retrieved from the OS keyring at call time and is never
  logged, printed to stdout/stderr, or written into `project_spec.json` or any of its
  versioned `project_spec.v{N}.json` siblings.
- All CLI logging passes through a redacting formatter that strips API-key-shaped
  strings before they're emitted, even from unexpected error messages.
- If a session is interrupted (Ctrl-C) or hits an unexpected error, no partial or
  corrupt spec is written — any pre-existing output file at that path is left
  untouched.

## License

`pm-agent-loop` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
