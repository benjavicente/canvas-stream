"API -> DB objects"

from datetime import datetime
from typing import Any, Mapping
from .db import Course, ExternalUrl, File, Folder


def naive_datetime(dt_str: str):
    return datetime.fromisoformat(dt_str.strip("Z")).replace(tzinfo=None)


def courses(element: Mapping[str, Any]):
    return Course(
        element["_id"],
        naive_datetime(element["updatedAt"]),
        element["name"],
        element["term"]["name"],
        element["courseCode"],
        False,
    )


def folder(element: Mapping[str, Any], course_id: int):
    return Folder(
        element["id"],
        naive_datetime(element["updated_at"]),
        element["full_name"].replace("course files/", ""),
        element["files_count"],
        course_id,
        element["parent_folder_id"],
    )


def file(element: Mapping[str, Any], course_id: int):
    return File(
        element["id"],
        naive_datetime(element["updated_at"]),
        None,
        element["filename"].strip(),
        element["url"],
        element["folder_id"],
        course_id,
    )


def file_gql(element: Mapping[str, Any], course_id: int):
    return File(
        element["_id"],
        naive_datetime(element["updatedAt"]),
        None,
        element["displayName"],
        element["url"],
        None,
        course_id,
    )


def ext_url(element: Mapping[str, Any], course_id: int):
    return ExternalUrl(
        element["_id"],
        naive_datetime(element["updatedAt"]),
        None,
        element["url"],
        element["title"],
        course_id,
    )
