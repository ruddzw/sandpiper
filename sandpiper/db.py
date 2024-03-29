import pymongo

from sandpiper import _get_config


class Model(object):

    def __init__(self, *args, **kwargs):
        for i, arg in enumerate(args):
            setattr(self, self.fields[i], arg)
        for i, field in enumerate(self.fields):
            val = None
            if len(args) > i:
                val = args[i]
            elif field in kwargs:
                val = kwargs[field]
            elif field in self.defaults:
                val = self.defaults[field]
            setattr(self, field, val)

    @classmethod
    def from_dict(cls, d):
        args = [d[field] for field in cls.fields]
        return cls(*args)

    @classmethod
    def find(cls, **criteria):
        docs = _get_connection()[cls.collection].find(criteria)
        objs = [cls.from_dict(doc) for doc in docs]
        return objs

    @classmethod
    def get_by_key(cls, key):
        docs = _get_connection()[cls.collection].find({cls.key: key})
        if docs.count() == 1:
            return cls.from_dict(docs[0])
        else:
            return None

    def to_dict(self):
        d = {}
        for field in self.fields:
            d[field] = getattr(self, field)
        return d

    def save(self):
        _get_connection()[self.collection].update({self.key: getattr(self, self.key)}, self.to_dict(), True)


def _get_connection():
    return pymongo.Connection(host=_get_config('mongo_host'),
        port=int(_get_config('mongo_port')))[_get_config('mongo_db')]
