"""
Data models for the PyPI Data Source.

All data is as loaded from the PyPI JSON API, and subject to the modeling constraints of
that API.
See: https://docs.pypi.org/api/json/
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import functools
import typing as t

from packaging.utils import parse_sdist_filename, parse_wheel_filename
from packaging.version import Version


@dataclasses.dataclass(frozen=True)
class PyPIPackageData:
    """
    Data for a package, including some number of its releases (mapped by version).

    The `releases` are not guaranteed to be exhaustive, depending on whether a specific
    version was fetched vs all versions.
    """
    latest_release: PyPIReleaseData
    releases: t.Mapping[Version, PyPIReleaseData]
    ownership: PyPIPackageOwnership

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> t.Self:
        latest_release = PyPIReleaseData.from_array(data["urls"])
        if "releases" in data:
            releases = {
                Version(ver): PyPIReleaseData.from_array(dists)
                for ver, dists in data["releases"].items()
            }
        else:
            releases = {latest_release.package_version: latest_release}
        ownership = PyPIPackageOwnership.from_dict(data["ownership"])
        return cls(
            latest_release=latest_release, releases=releases, ownership=ownership
        )


@dataclasses.dataclass(frozen=True)
class PyPIPackageOwnership:
    """
    The ownership data for a package.
    """
    organization: str | None
    roles: tuple[PyPIPackageOwnershipRole]

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> t.Self:
        return cls(
            organization=data["organization"],
            roles=tuple(PyPIPackageOwnershipRole.from_dict(r) for r in data["roles"]),
        )


@dataclasses.dataclass(frozen=True)
class PyPIPackageOwnershipRole:
    role: str
    user: str

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> t.Self:
        return cls(role=data["role"], user=data["user"])


@dataclasses.dataclass(frozen=True)
class PyPIReleaseData:
    """
    A single release of a package.

    A release consists of multiple artifacts (distributions), from which some common
    data can be extracted.
    """
    #: the distributions (artifacts) for the release; must be non-empty
    dists: tuple[PyPIDistributionData, ...]

    @classmethod
    def from_array(cls, data: list[dict[str, t.Any]]) -> t.Self:
        """
        Convert an array, as loaded from the JSON API, to a data object.

        Typically loaded from the `urls` key in the top-level API response or one of the
        releases in the `releases` mapping.

        Fields are not thoroughly validated.
        """
        return cls(dists=tuple(PyPIDistributionData.from_dict(item) for item in data))


    @functools.cached_property
    def package_version(self) -> Version:
        # all dists are guaranteed to have the same version and we are guaranteed at
        # least one dist for a release
        return self.dists[0].package_version

    @functools.cached_property
    def requires_python_lower_bound(self) -> Version | None:
        """
        Get the lower bound for this release's `requires_python` data.
        If multiple dists have different values, the lowest one will be used.
        """
        candidates = [
            dist.requires_python_lower_bound for dist in self.dists
            if dist.requires_python_lower_bound is not None
        ]
        if not candidates:
            return None
        return min(candidates)


@dataclasses.dataclass(frozen=True)
class PyPIDistributionData:
    """
    A single distribution (artifact) for a release of a package.

    Not all fields from the API are included. e.g., Deprecated fields are not present.
    """

    comment_text: str
    filename: str
    packagetype: t.Literal["sdist", "bdist_wheel"]
    requires_python: str | None
    size: int
    upload_time: dt.datetime
    yanked: bool

    @classmethod
    def from_dict(cls, data: dict[str, t.Any]) -> t.Self:
        """
        Convert a dict, as loaded from the JSON API, to a data object.

        Fields are not thoroughly validated.
        """
        return cls(
            comment_text=data["comment_text"],
            filename=data["filename"],
            packagetype=data["packagetype"],
            requires_python=data["requires_python"],
            size=data["size"],
            upload_time=dt.datetime.fromisoformat(data["upload_time_iso_8601"]),
            yanked=data["yanked"],
        )

    @functools.cached_property
    def package_version(self) -> Version:
        if self.filename.endswith(".whl"):
            _name, version, _buildnum, _tags = parse_wheel_filename(self.filename)
            return version
        elif self.filename.endswith(".tar.gz"):
            _name, version = parse_sdist_filename(self.filename)
            return version
        else:
            raise ValueError(
                f"filename {self.filename!r} did not look like an sdist or wheel"
            )

    @functools.cached_property
    def requires_python_lower_bound(self) -> Version | None:
        """
        The lowest supported Python version number, as parsed from requires_python for
        ">=" bounds only.

        For example, `requires_python=">=3.10"` produces a lower bound of
        `<Version("3.10">`.
        """
        if self.requires_python is None:
            return None

        reqs = self.requires_python.split(",")
        lower_bounds = []
        for r in reqs:
            if r.startswith(">="):
                lower_bounds.append(r[2:])
            else:
                continue
        if len(lower_bounds) > 1:
            return min(Version(v) for v in lower_bounds)
        elif len(lower_bounds) == 0:
            return None
        else:
            return Version(lower_bounds[0])
