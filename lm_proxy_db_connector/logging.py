"""
lm_proxy_db_connector - Minimalistic database connector for LM Proxy
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import sqlalchemy
from microcore.utils import resolve_callable
from sqlalchemy.exc import SQLAlchemyError
from lm_proxy.loggers import AbstractLogWriter
from . import db_session, db_engine


TYPE_MAP = {
    "id": sqlalchemy.Integer,
    "integer": sqlalchemy.Integer,
    "string": sqlalchemy.String,
    "text": sqlalchemy.Text,
    "json": sqlalchemy.JSON,
    "datetime": sqlalchemy.DateTime,
    "float": sqlalchemy.Float,
}

DEFAULT_COLUMNS = {
    "id": {"type": "id", "primary_key": True, "autoincrement": True},
    "request": {"type": "json", "nullable": False},
    "response": {"type": "text", "nullable": True},
    "error": {"type": "text", "nullable": True},
    "group": {"type": "string", "length": 255, "nullable": True},
    "connection": {"type": "string", "length": 255, "nullable": True},
    "api_key_id": {"type": "string", "length": 255, "nullable": True},
    "remote_addr": {"type": "string", "length": 255, "nullable": True},
    "created_at": {"type": "datetime", "default": "now"},
    "duration": {"type": "float", "nullable": True},
    #
    "prompt_tokens": {"type": "integer", "nullable": True},
    "completion_tokens": {"type": "integer", "nullable": True},
}


@dataclass
class DBLogWriter(AbstractLogWriter):
    table_name: str
    schema: Optional[str] = None
    columns: Optional[Dict[str, Dict[str, Any]]] = None
    create_table: bool = field(default=True)
    _table: sqlalchemy.Table = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.columns is None:
            self.columns = DEFAULT_COLUMNS

        metadata = sqlalchemy.MetaData(schema=self.schema)
        engine = db_engine()
        dialect = engine.dialect.name
        # Build columns
        cols = []
        for name, spec in self.columns.items():
            if spec["type"] not in TYPE_MAP:
                col_type = resolve_callable(spec["type"])
            else:
                col_type = TYPE_MAP[spec["type"]]
            length = spec.get("length")
            if length is not None:
                col_type = col_type(length)
            elif spec["type"] == "string" and dialect == "mysql":
                col_type = col_type(255)
            kwargs = {
                k: v
                for k, v in spec.items()
                if k not in ("type", "length")
            }
            if "default" in kwargs and kwargs["default"] == "now":
                kwargs["default"] = sqlalchemy.func.now()
            cols.append(sqlalchemy.Column(name, col_type, **kwargs))

        self._table = sqlalchemy.Table(self.table_name, metadata, *cols)
        if self.create_table:
            metadata.create_all(engine, checkfirst=True)

    def __call__(self, logged_data: dict):
        db = db_session()
        try:
            stmt = self._table.insert().values(**logged_data)
            db.execute(stmt)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise
