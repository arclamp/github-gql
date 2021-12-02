# issueup
Utilities for using GitHub's GraphQL API. Issue up your beta projects!

## Motivation

GitHub's new [beta projects](https://docs.github.com/en/issues/trying-out-the-new-projects-experience/about-projects) are awesome. But there's no way to rig them up so that new issues opened in a given repository (or repositories) are also filed in a given project. This script uses the GitHub GraphQL API to automate the adding of issues to a beta project that aren't there yet.

You can run this script by hand, or rig an automated system (like GitHub Actions) to run it for you periodically.

## Building and Running

The project is built using Python Poetry. To build:

```bash
$ poetry install
```

To run:

```bash
$ poetry run python issueup.py
```

or

```bash
$ poetry shell
$ python run issueup.py
```