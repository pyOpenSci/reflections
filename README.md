# reflections

Tracking maintenance and community adoption of pyOpenSci-accepted packages.

This project provides reusable data collection and analysis tools for studying
how open source projects develop over time. It is currently an early proof of
concept being developed by the pyOpenSci community.

## Set up the project

Install the locked development environment:

```console
uv sync
```

Some data sources require authentication. For GitHub, set a token in your
environment or create a `.env` file containing:

```dotenv
GITHUB_TOKEN=your-token
```

The token is optional for public data, but anonymous GitHub API requests have
a much lower rate limit. `.env` files are ignored by Git.

## Test

Run the test suite with:

```console
uv run python -m unittest discover -s tests -v
```
