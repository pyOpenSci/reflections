# Maintenance of pyOpenSci-accepted packages

> Working draft. This narrative will be developed incrementally as the analysis
> and data collection mature.

## Emerging finding

Across the metrics examined so far, package activity generally decreases
following pyOpenSci acceptance. Some decrease is expected: preparing a package
for submission and responding to peer review require concentrated work, making
the period leading up to acceptance an unusually active phase. By the time a
package is accepted, it has also been brought into closer alignment with
pyOpenSci's standards and may require less intensive corrective work. Lower
post-acceptance activity therefore should not, by itself, be interpreted as a
loss of maintenance. The observed decline is not precipitous, and substantial
activity continues after acceptance. Commit, issue, pull-request, star, and
maintainer activity collectively suggest that accepted packages remain
actively maintained rather than becoming dormant after review.

We are working from the hypothesis that pyOpenSci review and acceptance may
contribute to sustained package maintenance. The current analysis cannot test
that causal claim: it describes how activity changes around acceptance, but it
cannot distinguish the effects of pyOpenSci participation from package
maturity, maintainer capacity, broader community trends, or other factors. A
future comparison with a carefully selected control group of packages that
have not undergone pyOpenSci review will help evaluate whether the observed
patterns are distinctive to the pyOpenSci cohort.

These findings should also be interpreted in light of the available sample.
Commit, star, and maintainer measurements currently cover much of the
accepted-package cohort, while the issue and pull-request datasets contain
fewer repositories and should be treated as preliminary. The analysis can be
updated as collection becomes more complete.

## Cohort profile

As of November 20, 2026, the collected cohort contains 71 packages accepted
by pyOpenSci. Seventy are hosted on GitHub and form the analytic cohort for
the GitHub-derived measures in this report; one GitLab-hosted package is not
included in those measures. Acceptance dates for the GitHub cohort range from
August 6, 2019 to November 16, 2026. The mean time since acceptance is 2.37
years and the median is 1.99 years.

The GitHub-hosted submission records contain 127 maintainer listings representing 124
unique GitHub accounts. Packages have a mean of 1.82 listed maintainers and a
median of one listed maintainer. These values describe the maintainers named
in the available submission records; they may not capture subsequent changes
to project teams.

| Cohort characteristic | Value |
| --- | ---: |
| Accepted packages | 71 |
| GitHub-hosted analytic cohort | 70 |
| Earliest acceptance | August 6, 2019 |
| Most recent acceptance | November 16, 2026 |
| Mean time since acceptance | 2.37 years |
| Median time since acceptance | 1.99 years |
| Mean submission-to-acceptance time | 280 days |
| Median submission-to-acceptance time | 229 days |
| Submission-to-acceptance interquartile range | 126–391 days |
| Mean current GitHub repository age | 5.81 years |
| Median current GitHub repository age | 5.17 years |
| Repository-age interquartile range | 3.32–8.01 years |
| Maintainer listings | 127 |
| Unique listed GitHub accounts | 124 |
| Mean listed maintainers per package | 1.82 |
| Median listed maintainers per package | 1 |

The mean time between opening a submission and acceptance is 280 days, while
the median is 229 days. The interquartile range is 126 to 391 days, indicating
substantial variation in the duration of the submission and review process.

At the time of collection, the mean age of the associated GitHub repositories
is 5.81 years and the median is 5.17 years. Repository age is only a proxy for
package age: a package may predate its current GitHub repository, and a
repository transfer or recreation can alter the recorded creation date.

The median package has received a commit on its default branch within the
previous 1.85 months. The distribution is strongly right-skewed: the mean is
8.99 months and the interquartile range is 0.23 to 9.83 months.

![Months since the latest default-branch commit](../figures/cohort/cohort_last_commit_recency.png)

*Figure 1. Distribution of time since the latest commit on each package's
default branch, measured at the cohort metadata snapshot. The vertical line
marks the cohort median of 1.85 months. All 70 GitHub-hosted repositories had
an available default-branch commit timestamp.*

## Cohort and comparison

The study cohort consists of packages accepted into pyOpenSci through its
peer-review process. For each package, the acceptance date serves as the
temporal reference point. Repository activity is then organized relative to
that date, allowing us to compare activity before and after acceptance across
packages with different review timelines.

The available observation period differs by metric. Commit activity is
compared within matched 90-day periods before and after acceptance, and
packages must have at least 90 days of post-acceptance follow-up to be
included. Pull-request, issue, and star measurements use longer observation
periods where sufficient data are available. Monthly summaries account for
the number of repositories observable at each point in time. Maintainer
activity provides a current snapshot of public GitHub activity rather than a
direct before-and-after comparison.

Because data availability varies, the number of packages contributing to each
metric is not always the same. Results are therefore presented with
metric-specific sample sizes, and findings based on the smaller pull-request
and issue datasets should be considered preliminary.

## Early results

### Commit activity decreases but generally continues

Commit activity declines following acceptance, but the dominant pattern is a
reduction in activity rather than a complete cessation of development. Across
59 repositories with commits in the matched observation window, the median
number of default-branch commits decreased from 61 in the 90 days before
acceptance to 21 in the 90 days after acceptance. Forty-nine repositories had
fewer commits after acceptance and 10 had more.

![Monthly default-branch commit activity relative to acceptance](../figures/cohort/commits_monthly_activity.png)

*Figure 2. Monthly default-branch commit activity relative to pyOpenSci
acceptance. The line shows the median across repositories, the shaded region
shows the interquartile range, and the dashed line marks acceptance. Only
repositories with at least 90 days of post-acceptance observation are included.*

Despite the overall decline, 50 of the 59 repositories (84.7%) recorded at
least one default-branch commit during the 90 days after acceptance. The
distribution of within-repository changes also shows that the size of the
decline varies considerably across the cohort.

![Change in default-branch commits after acceptance](../figures/cohort/commits_change.png)

*Figure 3. Change in default-branch commits for each repository, calculated as
the number of commits in the 90 days after acceptance minus the number in the
90 days before acceptance. The dashed line indicates no change, and the solid
line marks the cohort median change of −24 commits.*

Taken together, these results are consistent with a post-acceptance reduction
in development intensity, but not with widespread abandonment of accepted
packages. Commit activity alone does not establish whether other forms of
maintenance—such as responding to users, reviewing contributions, or issuing
releases—continued over the same period. Those behaviors are considered using
the other available metrics.
