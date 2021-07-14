"A basic implementation of a database object relationship mapping"

# TODO: make optional arguments work in a table object

import sqlite3

from datetime import datetime

import typing
from typing import Any, Iterable, Union

from dataclasses import make_dataclass


class SQLite3Adapter:
    "SQLite3 adapter"
    type_mapping: dict[type, str] = {
        str: "TEXT",
        int: "INTEGER",
        float: "REAL",
        datetime: "TEXT",
        bool: "INTEGER",
        type(None): "NULL",
    }

    @staticmethod
    def type_to_sql(python_type: type) -> tuple[str, set]:
        "Transform a python type to a SQLite type"
        origin = typing.get_origin(python_type)
        if origin:
            sub_arg = typing.get_args(python_type)
            if origin is Union and type(None) in sub_arg:
                # Is Optional[...]
                metadata = {"optional"}
                sub_arg = tuple(e for e in sub_arg if sub_arg is not None)
            else:
                raise TypeError(f"Unrecognized type origin: {repr(origin)}")

            if len(sub_arg) != 1:
                TypeError(f"Unexpected multiple types: {repr(sub_arg)}")

            sql_type, sub_metadata = SQLite3Adapter.type_to_sql(sub_arg[0])
            assert not sub_metadata
            return sql_type, metadata

        if python_type in SQLite3Adapter.type_mapping:
            return SQLite3Adapter.type_mapping[python_type], set()

        raise TypeError(f"Invalid argument type: {repr(python_type)}")

    @staticmethod
    def object_to_sql(python_object: object) -> str:
        if isinstance(python_object, datetime):
            return f"'{python_object.isoformat()}'"
        if isinstance(python_object, bool):
            return str(int(python_object))
        if python_object is None:
            return "NULL"
        if type(python_object) in SQLite3Adapter.type_mapping:
            return repr(python_object)
        raise TypeError(f"Unrecognized type of object: {type(python_object)}")

    @staticmethod
    def sql_to_object(sql_object: Any, to_type: type) -> object:
        origin = typing.get_origin(to_type)
        if origin:
            sub_arg = typing.get_args(to_type)
            if origin is Union and type(None) in sub_arg:
                # Is Optional[...]
                if not sql_object:
                    return None
            to_type = sub_arg[0]

        if isinstance(sql_object, to_type):
            return sql_object

        if to_type is datetime and isinstance(sql_object, str):
            try:
                return datetime.fromisoformat(sql_object)
            except ValueError as error:
                raise ValueError("Invalid date format") from error

        if to_type is bool and isinstance(sql_object, int):
            return sql_object != 0

        return type(sql_object)

    @staticmethod
    def create_table(
        name: str, pk_keys: Iterable[str], attrs: dict[str, type], exists_ok=True
    ) -> str:
        sql_attrs = map(SQLite3Adapter.type_to_sql, attrs.values())
        if_exists = "IF NOT EXISTS" if exists_ok else ""

        table_attributes = []
        for col_name, (col_type, meta) in zip(attrs.keys(), sql_attrs):
            base = f"{col_name} {col_type}"
            if not "optional" in meta:
                base += " NOT NULL"
            table_attributes.append(base)
        if pk_keys:
            table_attributes.append(f"PRIMARY KEY ({', '.join(pk_keys)})")

        return f"CREATE TABLE {if_exists} {name} ({', '.join(table_attributes)})"

    @staticmethod
    def upsert(table_name: str, conflict: Iterable[str], attrs: dict[str, Any]) -> str:
        "Saves the object to the DataBase"
        names = list(attrs.keys())
        values = [SQLite3Adapter.object_to_sql(v) for v in attrs.values()]
        to_update_attributes = (
            f"{n}={v}" for n, v in zip(names, values) if n not in conflict
        )
        statement = (
            f"INSERT INTO {table_name} ({', '.join(names)})"
            f" VALUES ({', '.join(values)})"
            f" ON CONFLICT ({', '.join(conflict)})"
            f" DO UPDATE SET {', '.join(to_update_attributes)}"
        )
        return statement

    @staticmethod
    def find_eq(table_name: str, attrs: Iterable[str], **eq: int):
        conditions = (f"{k}={SQLite3Adapter.object_to_sql(v)}" for k, v in eq.items())
        return (
            f"SELECT {', '.join(attrs)} FROM {table_name}"
            f"{(' WHERE ' + 'AND '.join(conditions)) if eq else ''}"
        )


class DataBase:
    "Database object"

    def __init__(self, database: str, addapter: SQLite3Adapter = SQLite3Adapter()):
        self.connection = sqlite3.connect(database)
        self.addapter = addapter

    def __process_table(self, cls: type, pk_keys: Iterable[str]) -> type:
        # Make the table
        annotations = cls.__dict__.get("__annotations__", {})
        ct_statement = self.addapter.create_table(cls.__name__, pk_keys, annotations)
        self.__execute(ct_statement)

        # Make a dataclass
        # TODO: make optional parameters work
        new_cls = make_dataclass(
            cls.__name__, annotations.items(), bases=(TableObject,)
        )
        setattr(new_cls, "__db__", self)
        setattr(new_cls, "__table_name__", cls.__name__)
        setattr(new_cls, "__pk_keys__", pk_keys)
        return new_cls

    def __execute(self, query):
        cursor = self.connection.cursor()
        cursor.execute(query)
        cursor.close()

    def commit(self):
        self.connection.commit()

    def table(self, cls: type = None, *, pk_keys: Iterable[str] = []):
        "Table class decorator"

        def wrap(cls: type):
            return self.__process_table(cls, pk_keys)

        if cls is None:
            return wrap
        return wrap(cls)

    def save(self, t_o: "TableObject"):
        "Saves a table object to the database"
        q = self.addapter.upsert(t_o.__table_name__, t_o.__pk_keys__, t_o.__dict__)
        self.__execute(q)

    def find_eq(self, t_c: type, **eq: Any) -> "ResultIterator":
        assert issubclass(t_c, TableObject)
        attrs = t_c.__annotations__.keys()
        statement = self.addapter.find_eq(t_c.__table_name__, attrs, **eq)
        cursor = self.connection.cursor()
        cursor.execute(statement)
        return ResultIterator(cursor, t_c, self.addapter)


class ResultIterator:
    "Wrapper around the cursor iterator that handles object mapping"

    def __init__(self, iterator: sqlite3.Cursor, table: type, addapter: SQLite3Adapter):
        self.__cursor = iterator
        self.__constructor = table
        self.__table_types = table.__annotations__.values()
        self.__adapter = addapter

    def __iter__(self):
        return self

    def __next__(self) -> Any:
        result = self.__cursor.fetchone()
        if not result:
            self.__cursor.close()
            raise StopIteration

        obj_arguments = []
        for value, to_type in zip(result, self.__table_types):
            obj_arguments.append(self.__adapter.sql_to_object(value, to_type))
        return self.__constructor(*obj_arguments)


class TableObject:
    "Abstract table class"
    __table_name__: str
    __db__: DataBase
    __pk_keys__: Iterable

    def __init__(self) -> None:
        raise NotADirectoryError

    def save(self):
        "Saves the object to the DataBase, class DB.save(self)"
        self.__db__.save(self)

    @classmethod
    def find_eq(cls, **eq) -> "ResultIterator":
        "Finds the objects with equal conditions"
        return cls.__db__.find_eq(cls, **eq)
