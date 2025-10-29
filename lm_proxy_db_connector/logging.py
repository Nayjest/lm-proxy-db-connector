"""
lm_proxy_db_connector - Minimalistic database connector for LM Proxy
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

import sqlalchemy
from microcore.utils import resolve_callable
from lm_proxy.loggers import AbstractLogWriter, BaseLogger, LogEntryTransformer
from lm_proxy.base_types import RequestContext

from . import db, db_session


TYPE_MAP = {
    "id": sqlalchemy.Integer,
    "integer": sqlalchemy.Integer,
    "string": sqlalchemy.String,
    "text": sqlalchemy.Text,
    "json": sqlalchemy.JSON,
    "datetime": sqlalchemy.DateTime,
    "float": sqlalchemy.Float,
}

_DEFAULT_COLUMNS = {
    "id": {"type": "string", "primary_key": True, "length": 36},
    "request": {"type": "json", "nullable": False},
    "response": {"type": "text", "nullable": True},
    "error": {"type": "text", "nullable": True},
    "group": {"type": "string", "length": 255, "nullable": True},
    "connection": {"type": "string", "length": 255, "nullable": True},
    "api_key_id": {"type": "string", "length": 255, "nullable": True},
    "remote_addr": {"type": "string", "length": 255, "nullable": True},
    "created_at": {"type": "datetime", "default": "now"},
    "duration": {"type": "float", "nullable": True},
    "user_info": {"type": "json", "nullable": True},
    "extra": {"type": "json", "nullable": True},
}


@dataclass
class DBLogWriter(AbstractLogWriter):
    """
    Database log writer that writes logged data into a specified table.
    Creates the table if it does not exist and if create_table is True.
    """
    table_name: str
    schema: Optional[str] = None
    columns: Optional[Dict[str, Dict[str, Any]]] = None
    create_table: bool = field(default=True)
    _table: sqlalchemy.Table = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.columns is None:
            self.columns = _DEFAULT_COLUMNS

        metadata = sqlalchemy.MetaData(schema=self.schema)
        engine = db().engine
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
                kwargs["default"] = sqlalchemy.func.now()  # pylint: disable=not-callable
            cols.append(sqlalchemy.Column(name, col_type, **kwargs))

        self._table = sqlalchemy.Table(self.table_name, metadata, *cols)
        if self.create_table:
            metadata.create_all(engine, checkfirst=True)

    def __call__(self, logged_data: dict):
        with db_session() as s:
            stmt = self._table.insert().values(**logged_data)
            s.execute(stmt)


@dataclass
class DBLogger:
    """
    Database-backed LLM request logger.
    This class combines LogEntryTransformer and DBLogWriter
    allowing to simplify logger configuration and avoid listing fields twice.
    The `columns` parameter defines both the database table schema
    and the mapping from RequestContext to logged attributes (column.src field).
    """
    table_name: str = "llm_requests"
    schema: Optional[str] = None
    columns: Optional[Dict[str, Dict[str, Any]]] = None
    create_table: bool = field(default=True)
    _logger: BaseLogger = field(init=False, repr=False)

    def __post_init__(self):
        mapping = {}
        for col_name, col_spec in self.columns.items():
            mapping[col_name] = col_spec.pop("src", col_name)
        log_writer = DBLogWriter(
            table_name=self.table_name,
            schema=self.schema,
            columns=self.columns,
            create_table=self.create_table,
        )
        log_transformer = LogEntryTransformer(**mapping)
        self._logger = BaseLogger(
            log_writer=log_writer,
            entry_transformer=log_transformer,
        )

    def __call__(self, request_context: RequestContext):
        self._logger(request_context)
