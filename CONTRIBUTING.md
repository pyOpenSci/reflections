# Contributing to reflections

We welcome bug reports, documentation improvements, new tests, and focused
changes to the data collection and analysis tools.

For substantial changes, please open an issue first so that the approach can
be discussed with the maintainers. Small fixes can be submitted directly as a
pull request.

## Development setup

Fork and clone the repository, then create a branch for your work. Install the
locked development environment with:

```console
uv sync --extra analysis --group test
```

Run the test suite before opening a pull request:

```console
uv run pytest -q
```

Pull requests also run these tests automatically on the oldest Python version
supported by the project and a newer Python version. Please include tests for
new behavior where practical and keep commits focused enough to review.

By participating, you agree to follow the [pyOpenSci Code of
Conduct](CODE_OF_CONDUCT.md). Contributions are accepted under the terms of
the project's [MIT license](LICENSE).
