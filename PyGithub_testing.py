import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from dotenv import load_dotenv
    import os
    import matplotlib.pyplot as plt

    load_dotenv()
    return mo, os, plt


@app.cell
def _(mo, os):
    from github import Github
    from github import Auth

    token = os.getenv("github_pat")
    mo.stop(
        not token,
        mo.callout(
            "Set `github_pat` in `.env` before running this notebook.",
            kind="warn",
        ),
    )

    auth = Auth.Token(token)
    g = Github(auth=auth)
    return auth, g


@app.cell
def _(auth):
    auth.token_type
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Connect to PyOpenSci submissions
    Connect an object to PyOpenSci submissions to get metadata for a submission
    """)
    return


@app.cell
def _(g):
    pyopensci_repo = g.get_repo("PyOpenSci/software-submission")
    commits_list_pyopensci = list(pyopensci_repo.get_issues())
    return commits_list_pyopensci, pyopensci_repo


@app.cell
def _(commits_list_pyopensci):
    commits_list_pyopensci[0].raw_data
    return


@app.cell
def _(pyopensci_repo):
    for sub in pyopensci_repo.get_issues():
        print(sub.labels)
    return


@app.cell
def _(pyopensci_repo):
    pyopensci_accepted_packages = [sub for sub in pyopensci_repo.get_issues(labels=["6/pyOS-approved"], state='closed')]
    print(pyopensci_accepted_packages)
    return (pyopensci_accepted_packages,)


@app.cell
def _(pyopensci_accepted_packages):
    swiftgalaxy_issue = next(
        (issue for issue in pyopensci_accepted_packages if "swiftgalaxy" in issue.title),
        None
    )
    return (swiftgalaxy_issue,)


@app.cell
def _(swiftgalaxy_issue):
    swiftgalaxy_github_name = ('/').join(swiftgalaxy_issue.body.split('\n')[4].split('/')[-2:])
    swiftgalaxy_pyopensci_acceptance = swiftgalaxy_issue.closed_at
    return swiftgalaxy_github_name, swiftgalaxy_pyopensci_acceptance


@app.cell
def _(swiftgalaxy_issue):
    swiftgalaxy_issue.get_comments()[0]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Example Package
    How can I use PyGithub to explore the git history of a python package
    """)
    return


@app.cell(hide_code=True)
def _(g, swiftgalaxy_github_name):
    repo_ = g.get_repo(swiftgalaxy_github_name)
    return (repo_,)


@app.cell
def _(repo_):
    commits_list = list(repo_.get_commits())
    return (commits_list,)


@app.cell
def _(swiftgalaxy_pyopensci_acceptance):
    swiftgalaxy_pyopensci_acceptance
    return


@app.cell
def _(
    commits_list,
    plt,
    swiftgalaxy_github_name,
    swiftgalaxy_pyopensci_acceptance,
):
    # Grab dates for commits
    commit_dates = [
        commit.commit.author.date
        for commit in commits_list
        if commit.commit.author.date is not None
    ]
    # Check out distribution of commits
    fig, ax = plt.subplots()
    ax.hist(commit_dates, bins=100)
    ax.axvline(
        swiftgalaxy_pyopensci_acceptance,
        color="red",
        linestyle="--",
        label="pyOpenSci acceptance",
    )
    ax.set(
        title=f"Commit history for {swiftgalaxy_github_name}",
        xlabel="Commit date",
        ylabel="Number of commits",
    )
    fig.autofmt_xdate()
    fig.legend()
    fig
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Compute the amount of time it takes to get the first maintainer reponse to a PR
    """)
    return


@app.function
# Function to compute the time to a first maintainer reponse for all types of PR comments
def time_to_first_maintainer_response(pr):
    maintainer_roles = {"OWNER", "MEMBER", "COLLABORATOR"}
    response_dates = []

    # General PR conversation comments
    for comment in pr.get_issue_comments():
        if comment.author_association in maintainer_roles:
            response_dates.append(comment.created_at)

    # Inline code review comments
    for comment in pr.get_review_comments():
        if comment.author_association in maintainer_roles:
            response_dates.append(comment.created_at)

    # Submitted PR reviews
    for review in pr.get_reviews():
        if (
            review.author_association in maintainer_roles
            and review.submitted_at is not None
            and review.state != "PENDING"
            and review.body
        ):
            response_dates.append(review.submitted_at)

    if not response_dates:
        return None

    first_response = min(response_dates)
    return (first_response - pr.created_at).total_seconds() / 86400


@app.cell
def _(repo_):
    # Apply to the whole repo
    import pandas as pd

    results = []

    for pr in repo_.get_pulls(state="all"):
        results.append({
            "number": pr.number,
            "title": pr.title,
            "created_at": pr.created_at,
            "time_to_first_response_days": time_to_first_maintainer_response(pr),
        })

    df = pd.DataFrame(results)
    return df, pd


@app.cell
def _(df, plt):
    def _():
        # Check out distribution
        fig, ax = plt.subplots()

        ax.hist(
            df["time_to_first_response_days"].dropna(),
            bins=30
        )
        return ax.set(
            xlabel="Time to first maintainer response (days)",
            ylabel="Number of PRs",
            title="Maintainer response times"
        )


    _()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now the PRs after acceptance
    """)
    return


@app.cell
def _(pd, repo_, swiftgalaxy_pyopensci_acceptance):

    results_post_acceptance = []

    for pr_a in repo_.get_pulls(state="all"):
        # Only consider PRs opened after pyOpenSci acceptance
        if pr_a.created_at <= swiftgalaxy_pyopensci_acceptance:
            continue

        results_post_acceptance.append({
            "number": pr_a.number,
            "title": pr_a.title,
            "created_at": pr_a.created_at,
            "merged_at": pr_a.merged_at,
            "time_to_first_response_days": time_to_first_maintainer_response(pr_a),
        })

    df_post_acceptance = pd.DataFrame(results_post_acceptance)
    return (df_post_acceptance,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Summary stats
    """)
    return


@app.cell
def _(df_post_acceptance):
    response_times = df_post_acceptance["time_to_first_response_days"]

    print(f"PRs after acceptance: {len(df_post_acceptance)}")
    print(f"PRs with maintainer response: {response_times.notna().sum()}")
    print(f"Median response time: {response_times.median():.2f} days")
    print(f"Mean response time: {response_times.mean():.2f} days")
    print(f"75th percentile: {response_times.quantile(0.75):.2f} days")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Compare before and after acceptance
    """)
    return


@app.cell
def _(pd, repo_, swiftgalaxy_pyopensci_acceptance):
    def _():
        results = []

        for pr in repo_.get_pulls(state="all"):
            results.append({
                "number": pr.number,
                "created_at": pr.created_at,
                "period": (
                    "After acceptance"
                    if pr.created_at > swiftgalaxy_pyopensci_acceptance
                    else "Before acceptance"
                ),
                "response_days": time_to_first_maintainer_response(pr),
            })

        df = pd.DataFrame(results)
        return df

    _()
    return


@app.function
def get_pr_closer(pr):
    # Only consider currently closed PRs
    if pr.closed_at is None:
        return None

    # Get the event corresponding to the current closure
    events = [
        event
        for event in pr.get_issue_timeline()
        if event.event in {"closed", "merged"}
        and event.actor is not None
        and event.created_at <= pr.closed_at
    ]

    if not events:
        return None

    event = max(events, key=lambda e: e.created_at)
    return event.actor.login


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
