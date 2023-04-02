import dataclasses
import importlib
from typing import Self


def getClassName(cls: type):
    return f"{cls.__module__}:{cls.__name__}"


def getClassType(name: str):
    module, name = name.split(":")
    module = importlib.import_module(module)
    cls = getattr(module, name)
    assert isinstance(cls, type)
    return cls


def dumpValue(value):
    if isinstance(value, Serializable):
        return value.dump()
    if isinstance(value, list):
        return [dumpValue(v) for v in value]
    if isinstance(value, dict):
        return {k: dumpValue(v) for k, v in value.items()}
    if isinstance(value, set):
        return {"__type__": "set",
                "__raw__": [dumpValue(v) for v in value]}
    return value


def loadValue(raw: dict | list | object):
    if isinstance(raw, list):
        return [loadValue(v) for v in raw]
    if isinstance(raw, dict):
        type = raw.pop("__type__", None)
        if type == "set":
            rlist = raw.pop("__raw__")
            assert isinstance(rlist, list) and len(raw) == 0
            return {loadValue(v) for v in rlist}
        if not type:
            return {k: loadValue(v) for k, v in raw.items()}
        cls = getClassType(type)
        assert issubclass(cls, Serializable)
        value = cls()
        value.load(raw)
        return value
    else:
        return raw


class Serializable:
    def dump(self) -> dict:
        result = {}
        for field in dataclasses.fields(self):
            if not field.init:
                continue
            value = dumpValue(getattr(self, field.name))
            result[field.name] = value
        if isinstance(self, dict):
            result["__dict__"] = dumpValue(
                {k: dumpValue(v) for k, v in self.items()})
        if isinstance(self, list):
            result["__list__"] = dumpValue([dumpValue(v) for v in self])
        if isinstance(self, set):
            result["__set__"] = dumpValue([dumpValue(v) for v in self])
        result["__type__"] = getClassName(self.__class__)
        return result

    def load(self, raw: dict):
        for field in dataclasses.fields(self):
            if not field.init:
                continue
            value = raw.get(field.name)
            setattr(self, field.name, loadValue(value))            
        if isinstance(self, dict):
            rdict = raw.pop("__dict__")
            assert isinstance(rdict, dict)
            for k, v in rdict.items():
                self[k] = loadValue(v)
        if isinstance(self, list):
            rlist = raw.pop("__list__")
            assert isinstance(rlist, list)
            for v in rlist:
                self.append(loadValue(v))
        if isinstance(self, set):
            rlist = raw.pop("__set__")
            assert isinstance(rlist, list)
            for v in rlist:
                self.add(loadValue(v))
        postinit = getattr(self, "__post_init__", None)
        if postinit:
            postinit()

    def copy(self) -> Self:
        result = self.__class__()
        result.load(self.dump())
        return result
