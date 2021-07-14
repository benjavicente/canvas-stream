"Program database schema"

from typing import Optional
from datetime import datetime
from .db_api import DataBase

# DB = DataBase("example.db")
DB = DataBase("canvas-cache.db")


@DB.table(pk_keys=["id"])
class Course:
    id: int
    updated_at: datetime
    name: str
    term: str
    code: str
    is_favorite: bool


@DB.table(pk_keys=["id"])
class Folder:
    id: int
    updated_at: datetime
    full_name: str
    files_count: int
    course_id: int
    parent_id: Optional[int] = None


@DB.table(pk_keys=["id"])
class File:
    id: int
    updated_at: datetime
    dowloaded_at: Optional[datetime] = None
    filename: str
    download_url: str
    folder_id: Optional[int]
    course_id: int


@DB.table(pk_keys=["id"])
class ExternalUrl:
    id: int
    updated_at: datetime
    dowloaded_at: Optional[datetime] = None
    url: str
    title: str
    course_id: int
