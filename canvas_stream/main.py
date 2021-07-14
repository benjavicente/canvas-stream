from __future__ import annotations
from datetime import datetime

import sys

import time
from pathlib import Path

import toml

from . import api
from . import mappers
from .db import Course, DB, ExternalUrl, Folder, File
from .helpers import slugify, download


def _get_config(file_path=Path(Path(__file__).parent.parent, "config.toml")):
    config = toml.load(file_path)
    if "url" not in config or "access_token" not in config:
        raise Exception("Invalid config file: missing url or access_token")
    return config


# the `.save()` method updates or insets a new tuple
# if a tuple with the same `id` does not exists


class MainLoop:
    "MainLoop of the application"
    __slots__ = ["api_session", "sleep_time"]

    def __init__(self) -> None:
        config = _get_config()
        self.api_session = api.CanvasAPI(config["url"], config["access_token"])
        self.sleep_time = 60

    def run(self):
        "Runs the main loop"
        courses = [mappers.courses(c) for c in self.api_session.get_all_courses()]

        for favorite_course in self.api_session.get_favorites_courses():
            for course in courses:
                # For some reason, get_all_courses does
                # not return the json correct types
                if int(course.id) == favorite_course["id"]:
                    course.is_favorite = True
        try:
            while True:
                print("Runing...")
                self.__main_loop()
                print(f"Sleeping for {self.sleep_time} seconds. (zzz)")
                time.sleep(self.sleep_time)
        except KeyboardInterrupt:
            sys.exit(0)

    def __main_loop(self):
        # Get all courses
        courses = [mappers.courses(c) for c in self.api_session.get_all_courses()]
        for course in courses:
            if not course.is_favorite:
                continue

            cache_course = next(DB.find_eq(Course, id=course.id), None)
            # Check if the course has been updated

            if not cache_course or cache_course.updated_at < course.updated_at:
                # Gets the modules
                module_items = self.api_session.get_modules_with_items(course.id)
                for raw_module_items in module_items:
                    for item in raw_module_items["moduleItems"]:
                        if item["content"]:
                            content = item["content"]
                            if content["type"] == "ExternalUrl":
                                ext_url = mappers.ext_url(content, course.id)
                                ext_url.save()
                            elif content["type"] == "File":
                                file = mappers.file_gql(content, course.id)
                                file.save()

                # Gets the folders
                folders = [
                    mappers.folder(f, course.id)
                    for f in self.api_session.get_folders(course.id)
                ]

                # Save the folders
                for folder in folders:
                    cache_folder = next(DB.find_eq(Folder, id=folder.id), None)
                    if not cache_folder or cache_folder.updated_at < folder.updated_at:
                        files = [
                            mappers.file(f, course.id)
                            for f in self.api_session.get_files(folder.id)
                        ]
                        for file in files:
                            file.save()
                    folder.save()

            # Saves the course because it's have been updated
            course.save()
        DB.commit()

        # Update files
        for file in DB.find_eq(File):
            if not file.dowloaded_at or file.dowloaded_at < file.updated_at:
                course = next(DB.find_eq(Course, id=file.course_id))
                file_path = Path(slugify(file.filename))
                if file.folder_id:
                    folder = next(DB.find_eq(Folder, id=file.folder_id))
                    parent_path_parts = map(slugify, Path(folder.full_name).parts)
                    file_path = Path(*parent_path_parts, file_path)
                complete_path = Path("canvas", slugify(course.name), file_path)
                file.dowloaded_at = datetime.now()
                download(file.download_url, complete_path)
                file.save()
                DB.commit()

        for url_item in DB.find_eq(ExternalUrl):
            if not url_item.dowloaded_at or url_item.dowloaded_at < url_item.updated_at:
                course = next(DB.find_eq(Course, id=url_item.course_id))
                file_path = Path(
                    slugify(course.name), "modules", slugify(url_item.title)
                )
                print(file_path)


def main():
    main_loop = MainLoop()
    main_loop.run()


if __name__ == "__main__":
    main()
