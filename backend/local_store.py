"""In-memory stand-in for the Mongo collections used by server.py.

Only exists so the app can boot and be demoed where MongoDB is not reachable
(local dev, CI, screenshot runs). When MONGO_URL points at a real server the
real motor client is used and this module is never touched.

Implements exactly the subset of the motor API that server.py calls:
find_one / find().to_list() / insert_one / update_one(upsert) / count_documents.
"""
from typing import Any, Dict, List, Optional


def _matches(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for key, want in (query or {}).items():
        if isinstance(want, dict):
            if "$regex" in want:
                import re as _re
                flags = _re.I if "i" in want.get("$options", "") else 0
                if not _re.search(want["$regex"], str(doc.get(key, "")), flags):
                    return False
                continue
            return False
        if doc.get(key) != want:
            return False
    return True


def _project(doc: Dict[str, Any], projection: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    out = dict(doc)
    for key, keep in (projection or {}).items():
        if not keep:
            out.pop(key, None)
    return out


class _Cursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._docs[:length] if length else list(self._docs)


class _Collection:
    def __init__(self) -> None:
        self._docs: List[Dict[str, Any]] = []

    async def find_one(self, query=None, projection=None):
        for doc in self._docs:
            if _matches(doc, query or {}):
                return _project(doc, projection)
        return None

    def find(self, query=None, projection=None) -> _Cursor:
        return _Cursor([_project(d, projection) for d in self._docs if _matches(d, query or {})])

    async def insert_one(self, doc: Dict[str, Any]):
        self._docs.append(dict(doc))
        return type("Result", (), {"inserted_id": doc.get("_id") or doc.get("id")})()

    async def update_one(self, query, update, upsert: bool = False):
        target = None
        for doc in self._docs:
            if _matches(doc, query or {}):
                target = doc
                break
        if target is None:
            if not upsert:
                return type("Result", (), {"matched_count": 0, "modified_count": 0})()
            target = dict(query or {})
            self._docs.append(target)
        target.update(update.get("$set", {}))
        for key, delta in update.get("$inc", {}).items():
            target[key] = target.get(key, 0) + delta
        return type("Result", (), {"matched_count": 1, "modified_count": 1})()

    async def count_documents(self, query=None) -> int:
        return sum(1 for d in self._docs if _matches(d, query or {}))


class LocalDatabase:
    """Mimics `client[db_name]` — attribute access returns a collection."""

    def __init__(self) -> None:
        self._collections: Dict[str, _Collection] = {}

    def __getattr__(self, name: str) -> _Collection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._collections.setdefault(name, _Collection())

    def __getitem__(self, name: str) -> _Collection:
        return self._collections.setdefault(name, _Collection())


class LocalClient:
    def __init__(self) -> None:
        self._db = LocalDatabase()

    def __getitem__(self, _name: str) -> LocalDatabase:
        return self._db

    def close(self) -> None:
        pass
