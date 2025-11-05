from __future__ import annotations

import copy
import datetime as dt
import json
from enum import Enum
from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar, Union, get_args, get_origin

try:  # Prefer the real pydantic package when it is available.
    from pydantic import BaseModel as RealBaseModel  # type: ignore
    from pydantic import Field as RealField  # type: ignore
except (ModuleNotFoundError, ImportError):  # pragma: no cover - fallback implementation

    class FieldInfo:
        __slots__ = ("default", "default_factory")

        def __init__(self, default: Any = ..., default_factory: Callable[[], Any] | None = None) -> None:
            self.default = default
            self.default_factory = default_factory

    def Field(*, default: Any = ..., default_factory: Callable[[], Any] | None = None) -> FieldInfo:
        if default is not ... and default_factory is not None:
            raise ValueError("Specify either default or default_factory, not both")
        return FieldInfo(default=default, default_factory=default_factory)

    class BaseModelMeta(type):
        def __new__(mcls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]):
            annotations: Dict[str, Any] = {}
            for base in reversed(bases):
                base_annotations = getattr(base, "__annotations__", {})
                for key, value in base_annotations.items():
                    if key.startswith("_"):
                        continue
                    annotations[key] = value
            class_annotations = namespace.get("__annotations__", {})
            if class_annotations:
                for key, value in class_annotations.items():
                    if key.startswith("_"):
                        continue
                    annotations[key] = value

            field_infos: Dict[str, FieldInfo] = {}
            class_defaults: Dict[str, Any] = {}
            for attr, value in list(namespace.items()):
                if isinstance(value, FieldInfo):
                    field_infos[attr] = value
                    namespace.pop(attr)
                elif attr in class_annotations and not attr.startswith("_"):
                    class_defaults[attr] = value

            cls = super().__new__(mcls, name, bases, namespace)

            base_fields: Dict[str, Dict[str, Any]] = {}
            for base in reversed(cls.__mro__[1:]):
                base_fields.update(getattr(base, "__fields__", {}))

            fields: Dict[str, Dict[str, Any]] = {}
            for field_name, field_type in annotations.items():
                default = ...
                default_factory = None
                if field_name in field_infos:
                    info = field_infos[field_name]
                    default = info.default
                    default_factory = info.default_factory
                elif field_name in class_defaults:
                    default = class_defaults[field_name]
                elif field_name in base_fields:
                    default = base_fields[field_name]["default"]
                    default_factory = base_fields[field_name]["default_factory"]
                fields[field_name] = {
                    "type": field_type,
                    "default": default,
                    "default_factory": default_factory,
                }
            cls.__fields__ = fields
            return cls

    TModel = TypeVar("TModel", bound="BaseModel")

    class BaseModel(metaclass=BaseModelMeta):
        __fields__: Dict[str, Dict[str, Any]]

        def __init__(self, **data: Any) -> None:
            values: Dict[str, Any] = {}
            remaining = dict(data)
            for field_name, info in self.__fields__.items():
                if field_name in remaining:
                    raw_value = remaining.pop(field_name)
                else:
                    if info["default_factory"] is not None:
                        raw_value = info["default_factory"]()
                    elif info["default"] is not ...:
                        raw_value = copy.deepcopy(info["default"])
                    else:
                        raise TypeError(f"Missing required field: {field_name}")
                values[field_name] = self._convert_value(info["type"], raw_value)
            if remaining:
                raise TypeError(f"Unexpected fields: {', '.join(remaining)}")
            self.__dict__.update(values)

        @classmethod
        def _convert_value(cls, field_type: Any, value: Any) -> Any:
            if value is None:
                return None
            origin = get_origin(field_type)
            if origin is Union:
                args = [arg for arg in get_args(field_type) if arg is not type(None)]
                if not args:
                    return value
                return cls._convert_value(args[0], value)
            if origin in (list, List):
                (item_type,) = get_args(field_type) if get_args(field_type) else (Any,)
                return [cls._convert_value(item_type, item) for item in value]
            if origin in (dict, Dict):
                args = get_args(field_type)
                value_type = args[1] if len(args) == 2 else Any
                return {key: cls._convert_value(value_type, item) for key, item in value.items()}
            if isinstance(field_type, type):
                if issubclass(field_type, BaseModel):
                    if isinstance(value, field_type):
                        return value
                    if isinstance(value, dict):
                        return field_type(**value)
                if issubclass(field_type, Enum):
                    if isinstance(value, field_type):
                        return value
                    return field_type(value)
                if field_type is dt.date:
                    if isinstance(value, dt.date):
                        return value
                    return dt.date.fromisoformat(value)
                if field_type is dt.datetime:
                    if isinstance(value, dt.datetime):
                        return value
                    return dt.datetime.fromisoformat(value)
            return value

        def model_dump(self, *, mode: str = "python") -> Dict[str, Any]:
            result: Dict[str, Any] = {}
            for field_name in self.__fields__:
                value = getattr(self, field_name, None)
                result[field_name] = self._dump_value(value, mode=mode)
            return result

        @classmethod
        def _dump_value(cls, value: Any, *, mode: str) -> Any:
            if isinstance(value, BaseModel):
                return value.model_dump(mode=mode)
            if isinstance(value, list):
                return [cls._dump_value(item, mode=mode) for item in value]
            if isinstance(value, dict):
                return {key: cls._dump_value(item, mode=mode) for key, item in value.items()}
            if mode == "json":
                if isinstance(value, dt.datetime):
                    return value.isoformat()
                if isinstance(value, dt.date):
                    return value.isoformat()
                if isinstance(value, Enum):
                    return value.value
            return value

        @classmethod
        def model_validate_json(cls: Type[TModel], json_str: str) -> TModel:
            data = json.loads(json_str)
            return cls.model_validate(data)

        @classmethod
        def model_validate(cls: Type[TModel], data: Dict[str, Any]) -> TModel:
            return cls(**data)

        def __repr__(self) -> str:  # pragma: no cover - debugging helper
            fields = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.__fields__)
            return f"{self.__class__.__name__}({fields})"

    __all__ = ["BaseModel", "Field"]

else:  # pragma: no cover - when pydantic is installed we re-export it
    BaseModel = RealBaseModel  # type: ignore
    Field = RealField  # type: ignore
    __all__ = ["BaseModel", "Field"]
