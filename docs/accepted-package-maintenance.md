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

These findings should also be interpreted in light of metric-specific data
coverage. The current analyses include between 59 and 70 of the 70
GitHub-hosted repositories, depending on eligibility, snapshot availability,
and whether a repository has events in the analysis window. Coverage and
exclusions are documented in the [data coverage audit](data-coverage.md).

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

Because data availability and eligibility vary, the number of packages
contributing to each metric is not always the same. Results are therefore
presented with metric-specific sample sizes and should be interpreted with the
coverage audit.

## Early results

### Commit activity decreases but generally continues

Commit activity declines following acceptance, but the dominant pattern is a
reduction in activity rather than a complete cessation of development. Across
59 repositories with commits in the matched observation window, the median
number of default-branch commits decreased from 61 in the 90 days before
acceptance to 21 in the 90 days after acceptance. Forty-nine repositories had
fewer commits after acceptance and 10 had more.

![Distribution of default-branch commits before and after acceptance](../figures/cohort/commits_coverage.png)

*Figure 2. Distribution of repository-level default-branch commit counts in
the matched 90-day windows before and after acceptance. Boxes show the median
and interquartile range, and points represent individual repositories.*

![Monthly default-branch commit activity relative to acceptance](../figures/cohort/commits_monthly_activity.png)

*Figure 3. Monthly default-branch commit activity relative to pyOpenSci
acceptance. The line shows the median across repositories, the shaded region
shows the interquartile range, and the dashed line marks acceptance. Only
repositories with at least 90 days of post-acceptance observation are included.*

Despite the overall decline, 50 of the 59 repositories (84.7%) recorded at
least one default-branch commit during the 90 days after acceptance. The
distribution of within-repository changes also shows that the size of the
decline varies considerably across the cohort.

![Change in default-branch commits after acceptance](../figures/cohort/commits_change.png)

*Figure 4. Change in default-branch commits for each repository, calculated as
the number of commits in the 90 days after acceptance minus the number in the
90 days before acceptance. The dashed line indicates no change, and the solid
line marks the cohort median change of −24 commits.*

Taken together, these results are consistent with a post-acceptance reduction
in development intensity, but not with widespread abandonment of accepted
packages. Commit activity alone does not establish whether other forms of
maintenance—such as responding to users, reviewing contributions, or issuing
releases—continued over the same period. Those behaviors are considered using
the other available metrics.

### Pull-request activity declines, while observed responses remain common

Pull-request volume follows a pattern similar to commit activity. Across 65
repositories represented in the matched windows, the median number of pull
requests decreased from 41 before acceptance to 12 after acceptance. This
comparison includes repositories with no pull requests in a period as zeros.

![Distribution of pull requests before and after acceptance](../figures/cohort/pull_requests_coverage.png)

*Figure 5. Distribution of repository-level pull-request counts in the
matched windows before and after acceptance. Boxes show the median and
interquartile range, and points represent individual repositories.*

The cumulative-response curves provide a complementary view of maintenance.
About 41% of pull requests opened after acceptance had an observed maintainer
response within 30 days, compared with about 33% before acceptance. This
descriptive difference does not establish that acceptance improved response
behavior, but it does show that the lower post-acceptance activity was not
accompanied by an absence of maintainer engagement.

![Cumulative share of pull requests with an observed maintainer response](../figures/cohort/pull_requests_cumulative_response.png)

*Figure 6. Cumulative share of pull requests with an observed maintainer
response during the first 30 days after opening. Line color and style
distinguish pull requests opened before and after acceptance.*

### Issue activity declines in the matched windows

The rebuilt issue dataset covers 68 repositories. The median number of issues
decreased from 20.5 before acceptance to 4.5 after acceptance, a pattern
consistent with the decline in commits and pull requests. Among repositories
with observations in both periods, the median change in time until an issue
was first addressed was 0.2 days across 35 repositories, while the median
change in issue close time was 6.8 days across 45 repositories. These timing
results describe observed issues and do not account for differences in issue
complexity or composition between periods.

![Distribution of issues before and after acceptance](../figures/cohort/issues_coverage.png)

*Figure 7. Distribution of repository-level issue counts in the matched
windows before and after acceptance. Sixty-eight repositories are represented,
and repositories without issues in a period are shown as zero.*

### Activity declines across 90-, 180-, and 365-day windows

The complete Tier 1 issue and pull-request indexes allow the analysis window
to be selected locally without querying GitHub again. We repeated the activity
and close-time summaries using symmetric 90-, 180-, and 365-day periods around
acceptance. A repository is eligible only when the snapshot provides at least
the selected number of post-acceptance days. Consequently, longer windows
contain more events but fewer eligible repositories: 64 at 90 days, 61 at 180
days, and 53 at 365 days. Repositories with no issues or pull requests in a
period are retained with a count of zero.

The direction of the activity result is consistent across the three windows.
Median issue and pull-request counts are lower after acceptance at every window
length. The larger absolute changes in longer windows are expected in part
because those windows accumulate more activity; they should not be interpreted
as evidence that the rate of decline accelerates over time.

| Window | Eligible repositories | Matched issues | Median issues, before → after | Median issue change | Matched PRs | Median PRs, before → after | Median PR change |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 90 days | 64 | 1,085 | 4.0 → 1.5 | −2.0 | 2,693 | 12 → 4 | −4.5 |
| 180 days | 61 | 2,181 | 11 → 3 | −5.0 | 5,417 | 20 → 7 | −7.0 |
| 365 days | 53 | 3,709 | 22 → 7 | −10.0 | 7,991 | 42 → 12 | −13.0 |

#### Activity-volume distributions

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Issue counts in 90-day windows](../figures/cohort/tier1_90_days/issues_coverage.png) | ![Issue counts in 180-day windows](../figures/cohort/tier1_180_days/issues_coverage.png) | ![Issue counts in 365-day windows](../figures/cohort/tier1_365_days/issues_coverage.png) |

*Figure 8. Repository-level issue-count distributions before and after
acceptance using 90-, 180-, and 365-day matched windows. Each panel includes
only repositories with sufficient follow-up for that window; eligible
repositories without issues in a period are represented by zero.*

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Pull-request counts in 90-day windows](../figures/cohort/tier1_90_days/pull_requests_coverage.png) | ![Pull-request counts in 180-day windows](../figures/cohort/tier1_180_days/pull_requests_coverage.png) | ![Pull-request counts in 365-day windows](../figures/cohort/tier1_365_days/pull_requests_coverage.png) |

*Figure 9. Repository-level pull-request-count distributions before and after
acceptance using 90-, 180-, and 365-day matched windows. The post-acceptance
distribution remains lower at each window length.*

#### Monthly activity trajectories

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Monthly issue activity in 90-day windows](../figures/cohort/tier1_90_days/issues_monthly_activity.png) | ![Monthly issue activity in 180-day windows](../figures/cohort/tier1_180_days/issues_monthly_activity.png) | ![Monthly issue activity in 365-day windows](../figures/cohort/tier1_365_days/issues_monthly_activity.png) |

*Figure 10. Monthly issue activity relative to acceptance across the three
matched-window lengths. Lines show repository medians, shaded regions show
interquartile ranges, and the dashed vertical line marks acceptance.*

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Monthly pull-request activity in 90-day windows](../figures/cohort/tier1_90_days/pull_requests_monthly_activity.png) | ![Monthly pull-request activity in 180-day windows](../figures/cohort/tier1_180_days/pull_requests_monthly_activity.png) | ![Monthly pull-request activity in 365-day windows](../figures/cohort/tier1_365_days/pull_requests_monthly_activity.png) |

*Figure 11. Monthly pull-request activity relative to acceptance across the
three matched-window lengths. Zero-event repository-months are retained in the
monthly distributions.*

Close-time comparisons also point in the same direction across windows, but
they require more caution. Only repositories with closed events in both
periods contribute to the paired close-time change. Open events are retained
in the underlying tables as censored observations but are not included in
these medians. The set of paired repositories changes with the window length.

| Window | Paired repositories, issue close time | Median issue close-time change | Paired repositories, PR close time | Median PR close-time change |
| ---: | ---: | ---: | ---: | ---: |
| 90 days | 31 | +1.31 days | 37 | +0.05 days |
| 180 days | 42 | +1.84 days | 46 | +0.06 days |
| 365 days | 39 | +8.36 days | 44 | +0.11 days |

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Issue close-time change in 90-day windows](../figures/cohort/tier1_90_days/issues_median_close_change.png) | ![Issue close-time change in 180-day windows](../figures/cohort/tier1_180_days/issues_median_close_change.png) | ![Issue close-time change in 365-day windows](../figures/cohort/tier1_365_days/issues_median_close_change.png) |

*Figure 12. Within-repository changes in median issue close time across the
three matched-window lengths. Positive values indicate longer observed close
times after acceptance.*

| 90 days | 180 days | 365 days |
| --- | --- | --- |
| ![Pull-request close-time change in 90-day windows](../figures/cohort/tier1_90_days/pull_requests_median_close_change.png) | ![Pull-request close-time change in 180-day windows](../figures/cohort/tier1_180_days/pull_requests_median_close_change.png) | ![Pull-request close-time change in 365-day windows](../figures/cohort/tier1_365_days/pull_requests_median_close_change.png) |

*Figure 13. Within-repository changes in median pull-request close time across
the three matched-window lengths. The median change is close to zero in all
three comparisons.*

These window comparisons strengthen the descriptive conclusion that issue and
pull-request activity is lower after acceptance without disappearing. They do
not resolve the causal limitations of the study. In addition, results across
window lengths are not based on an identical cohort because longer follow-up
requirements exclude more recently accepted packages.

### Maintainer responsiveness remains broadly stable as activity declines

> **Collection coverage:** Tier 2 collection is complete for 68 of 70
> repositories. MovingPandas is excluded because its repository issue-comment
> endpoint returned 404, and Astropy is excluded because GitHub stopped
> repository issue-comment pagination at its 30,000-record limit. Neither
> incomplete stream is treated as evidence of no response. Of the 68
> analysis-ready repositories, 62, 59, and 52 have sufficient follow-up for
> the 90-, 180-, and 365-day comparisons, respectively.

Tier 2 adds the timing and authorship of repository-wide comments to the Tier 1
issue and pull-request indexes. For issues, the response metric is the first
qualifying maintainer conversation comment. For pull requests, it is the first
qualifying conversation comment or inline review comment. A qualifying comment
must be associated with an owner, organization member, or repository
collaborator. Automated accounts and comments made by the person who opened the
item are excluded, as are comments made after the item closed.

This definition is narrower than all maintainer engagement. In particular,
formal submitted pull-request reviews and issue-management actions such as
labels or assignments require Tier 3 data. The present metric is therefore
described as *maintainer comment response*, not as the time until an item was
addressed.

Items without an observed qualifying comment are retained as censored
observations until closure or the common snapshot cutoff. Cumulative-response
curves use the complement of a Kaplan–Meier estimate so that short observed
follow-up is not silently treated as permanent nonresponse. The complementary
30-day repository summaries include an item only if it received a response by
30 days or was observable for at least 30 days. Median and mean response-time
summaries are conditional on an observed qualifying comment and consequently
answer a different question from the censoring-aware curves.

Across the substantially expanded Tier 2 sample, the probability of receiving
a qualifying maintainer comment within 30 days does not decline alongside the
lower volume of issues and pull requests. The estimated issue response is
higher after acceptance at all three window lengths, with differences of about
seven to nine percentage points. Pull-request response is modestly higher in
the 90- and 180-day comparisons and modestly lower in the 365-day comparison.
The long-window pull-request difference is less than two percentage points and
does not support a large change in either direction.

| Window | Eligible repositories | Matched issues | Issue response, before → after | Matched PRs | PR response, before → after |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 90 days | 62 | 938 | 34.4% → 43.0% | 2,036 | 48.4% → 51.4% |
| 180 days | 59 | 1,861 | 34.9% → 43.0% | 4,104 | 50.0% → 52.8% |
| 365 days | 52 | 3,709 | 34.7% → 41.6% | 7,991 | 56.1% → 54.2% |

Response speed among items with an observed qualifying comment is also
stable. Across the three window lengths, the median within-repository change
in response time ranges from approximately 0.04 days faster to 0.35 days
slower for issues, and from 0.53 days faster to effectively unchanged for pull
requests. These conditional response-time summaries should not be interpreted
separately from response probability because they exclude items without an
observed qualifying comment.

| Issue response curve | Issue-level 30-day response rates |
| --- | --- |
| ![Cumulative maintainer-comment response for issues](../figures/cohort/tier2_90_days/issues_cumulative_comment_response.png) | ![Thirty-day maintainer-comment response rates for issues](../figures/cohort/tier2_90_days/issues_comment_response_rate_30_days.png) |

*Figure 14. Issue comment-response results in matched 90-day
windows. The left panel estimates cumulative response while accounting for
censoring; the right panel shows repository-level 30-day response rates among
assessable issues. Only repositories with complete issue-comment streams are
included.*

| Pull-request response curve | Pull-request-level 30-day response rates |
| --- | --- |
| ![Cumulative maintainer-comment response for pull requests](../figures/cohort/tier2_90_days/pull_requests_cumulative_comment_response.png) | ![Thirty-day maintainer-comment response rates for pull requests](../figures/cohort/tier2_90_days/pull_requests_comment_response_rate_30_days.png) |

*Figure 15. Pull-request comment-response results in matched
90-day windows. Conversation and inline review comments are included, but
formal submitted reviews are not. Only repositories with both required
comment streams complete are included.*

Taken together, these results distinguish maintenance intensity from
maintainer responsiveness. Fewer issues and pull requests are opened after
acceptance, but the available evidence does not show a corresponding collapse
in engagement with the items that are opened. Issue-comment response is
consistently higher after acceptance, while pull-request response is broadly
comparable before and after acceptance. As with the activity results, these
before-and-after patterns remain descriptive and should not be interpreted as
effects caused by pyOpenSci acceptance.

### Star acquisition slows, while packages retain varied audiences

Star acquisition also generally slows after acceptance. Among the 66
repositories with comparable before-and-after measurements, the median
within-repository change was three fewer new stars after acceptance. Stars are
an imperfect measure of either use or maintenance, but they provide one signal
of continuing external attention to a package.

![Change in newly acquired stars after acceptance](../figures/cohort/stars_acquisition_change.png)

*Figure 16. Within-repository change in newly acquired stars, calculated as
the number after acceptance minus the number before acceptance. Each point is
a repository; the solid line marks the median change of −3 stars.*

The cohort spans a wide range of current audience sizes. Most repositories
have relatively modest star counts, while a small number of highly visible
projects create a strongly right-skewed distribution. This heterogeneity is
important when interpreting cohort averages and motivates retaining
repository-level distributions throughout the analysis.

![Distribution and ranking of current repository stars](../figures/cohort/stars_current_stargazers.png)

*Figure 17. Current repository stars at the snapshot date. The left panel
shows the cohort distribution on a logarithmic axis; the right panel shows
the 15 most-starred repositories.*

### Listed maintainers remain publicly active

The maintainer snapshot offers a current rather than before-and-after view.
For most packages with an available maintainer roster, all listed maintainers
had some observed public GitHub activity during the 365-day collection window.
This broad measure does not imply that every contribution was made to the
accepted package, but it indicates that the people associated with most
packages remain active in public software development.

![Package-level share of listed maintainers with public activity](../figures/cohort/maintainers_active_share.png)

*Figure 18. Distribution of the share of each package's listed maintainers
with observed public GitHub activity during the 365-day snapshot window.*

Recency provides a more direct view of that activity. Maintainers are grouped
by the time since their latest observed public contribution, with accounts
for which no activity was observed retained as a separate category. These
results should be interpreted as a snapshot of public GitHub activity: private
work and activity on other platforms are not observable through this measure.

![Recency of listed maintainer public GitHub activity](../figures/cohort/maintainers_activity_recency.png)

*Figure 19. Listed maintainers grouped by the number of days since their most
recent observed public GitHub contribution. Accounts without observed public
activity are shown separately.*
