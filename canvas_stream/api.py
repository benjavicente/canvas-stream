"A simple Canvas API Wrapper"

from __future__ import annotations

from pathlib import Path

import requests

# By default, Canvas REST API has a pagination of 10 items. This is
# customizable with the `per_page` parameter to a unspecified limit.
# The documentation recommends checking the `Link` header to avoid
# problems. GraphQL might have a similar problem.

# This module does not map the response to python types.


def _response_json(response: requests.Response):
    if not response.ok:
        raise requests.RequestException("Request returned: 401 - Unauthorized")
    return response.json()


def get_gql_query(file_name: str) -> str:
    "Gets a GQL query by it's file name"
    path = Path(__file__).parent.joinpath("gql", file_name).with_suffix(".gql")
    with path.open() as file:
        return file.read()


REST_ADDITIONAL_HEADERS = {"per_page": "50"}
REST_ENDPOINT = "/api/v1"
GQL_ENDPOINT = "/api/graphql"
GQL_COURSES_QUERY = get_gql_query("courses")
GQL_MODULES_AND_ITEMS_QUERY = get_gql_query("modules_items")


class CanvasAPI:
    "Canvas async API caller"

    def __init__(self, url: str, access_token: str):
        self.url = "https://" + url
        self.access_token = access_token
        self._header = {
            "Authorization": f"Bearer {access_token}",
        } | REST_ADDITIONAL_HEADERS

    def __repr__(self):
        return f"CanvasAPI({self.url})"

    def _get(self, route):
        url = self.url + REST_ENDPOINT + route
        response = requests.get(url=url, headers=self._header)
        try:
            return _response_json(response)
        except requests.RequestException as error:
            print(error)
            return []

    def _gql(self, query, variables=None):
        url = self.url + GQL_ENDPOINT
        data = {"query": query, "variables": variables if variables else {}}
        response = requests.post(url=url, json=data, headers=self._header)
        return _response_json(response)["data"]

    def get_favorites_courses(self):
        "REST call to `/users/self/favorites/courses`"
        return self._get("/users/self/favorites/courses")

    def get_all_courses(self):
        "GraphQL call with `GQL_COURSES_QUERY`"
        response = self._gql(GQL_COURSES_QUERY)
        return response["allCourses"]

    def get_modules_with_items(self, course_id):
        "GraphQL call with `GQL_MODULES_AND_ITEMS_QUERY`"
        response = self._gql(GQL_MODULES_AND_ITEMS_QUERY, {"course_id": course_id})
        return response["course"]["modulesConnection"]["nodes"]

    def get_folders(self, course_id):
        "REST call to `/courses/:course_id/folders`"
        return self._get(f"/courses/{course_id}/folders")

    def get_files(self, folder_id):
        "REST call to `/folders/:folder_id/files`"
        return self._get(f"/folders/{folder_id}/files")
