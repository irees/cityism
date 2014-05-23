"""Utils."""

# Just some useful filter functions.
def valueattr(items, key, minvalue=None):
    """Return filtered attr values"""
    if minvalue is not None:
        return [getattr(i, key, None) for i in items if getattr(i, key, None) > minvalue]
    return [getattr(i, key, None) for i in items if getattr(i, key, None)]

def valuekey(items, key, minvalue=None):
    """Return filtered key values"""
    if minvalue is not None:
        return [i.get(key) for i in items if i.get(key) > minvalue]
    return [i.get(key) for i in items if i.get(key)]

def filterattr(items, key, minvalue=None):
    """Filter objects by attr"""
    if minvalue is not None:
        return [i for i in items if getattr(i, key, None) > minvalue]
    return [i for i in items if getattr(i, key, None)]

def filterkey(items, key, minvalue=None):
    """Filter objects by key"""
    if minvalue is not None:
        return [i for i in items if i.get(key) > minvalue]
    return [i for i in items if i.get(key)]

def acsrange(base, start=None, end=None, cols=None, weight=1.0):
    """ACS table column range."""
    if start is not None:
        cols = range(start, (end or start)+1)
    elif cols:
        cols = cols
    else:
        raise Exception("Need start, end, or cols")
    ret = []
    for i in cols:
        i = ACSWeight(acstable='%s_%03d'%(base, i), weight=weight)
        ret.append(i)
    return ret

class ACSWeight(object):
    def __init__(self, acstable, weight):
        self.acstable = acstable
        self.weight = weight

