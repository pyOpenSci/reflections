import json
import typing as t
import urllib.request

from ._models import PyPIPackageData


class _Requester:
    """An ultra simple low-level HTTP client."""
    def get(self, url: str) -> t.Any:
        with urllib.request.urlopen(url) as conn:
            raw = conn.read()
        return json.loads(raw)


class PyPIClient:
    """
    A PyPI Client object, able to fetch projects and return object-modeled results.
    """

    _PYPI_PACKAGE_URL_FMT = "https://pypi.org/pypi/{package_name}/json"
    _PYPI_PACKAGE_VERSION_URL_FMT = (
        "https://pypi.org/pypi/{package_name}/{version}/json"
    )

    def __init__(self):
        self._requester = _Requester()

    def get_package(self, package_name: str) -> PyPIPackageData:
        return PyPIPackageData.from_dict(
            self._requester.get(
                self._PYPI_PACKAGE_URL_FMT.format(package_name=package_name)
            )
        )

    def get_package_version(self, package_name: str, version: str) -> PyPIPackageData:
        return PyPIPackageData.from_dict(
            self._requester.get(
                self._PYPI_PACKAGE_VERSION_URL_FMT.format(
                    package_name=package_name, version=version
                )
            )
        )
