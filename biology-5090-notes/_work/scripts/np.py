# note-patching helpers used from short python heredocs:  from np import *
from state import *
class PatchError(Exception): pass
FAILED = []
def _rw(sec, f):
    t = notes(sec)
    try:
        t2 = f(t)
    except PatchError as e:
        FAILED.append(str(e)); print("!!!!!!!! PATCH FAILED:", e); raise
    if t2 == t:
        print("!!!!!!!! NO CHANGE in", sec); raise PatchError("no change")
    save_notes(sec, t2); log("notes %s patched (%+d chars)" % (sec, len(t2) - len(t)))
def sub(sec, old, new):
    def f(t):
        if t.count(old) != 1: raise PatchError("sub: %r occurs %d times in %s" % (old[:50], t.count(old), sec))
        return t.replace(old, new)
    _rw(sec, f); print("sub ok", sec)
def after(sec, anchor, line):
    """insert a new line after the (unique) line containing anchor"""
    def f(t):
        L = t.split("\n"); idx = [i for i, l in enumerate(L) if anchor in l]
        if len(idx) != 1: raise PatchError("after: %r matches %d lines in %s" % (anchor[:50], len(idx), sec))
        L.insert(idx[0] + 1, line); return "\n".join(L)
    _rw(sec, f); print("after ok", sec)
def under(sec, heading, line):
    """append line at the end of the block that follows the given sub-heading line"""
    def f(t):
        L = t.split("\n"); idx = [i for i, l in enumerate(L) if l.strip() == heading]
        if len(idx) != 1: raise PatchError("under: heading %r matches %d lines in %s" % (heading, len(idx), sec))
        j = idx[0] + 1
        while j < len(L) and L[j].strip() != "": j += 1
        L.insert(j, line); return "\n".join(L)
    _rw(sec, f); print("under ok", sec)
def newblock(sec, heading, lines, before=None):
    """add a new sub-heading block at the end of the section (or before an existing heading)"""
    def f(t):
        blk = "\n" + heading + "\n" + "\n".join(lines) + "\n"
        if before:
            L = t.split("\n"); idx = [i for i, l in enumerate(L) if l.strip() == before]
            if len(idx) != 1: raise PatchError("newblock: before %r matches %d" % (before, len(idx)))
            return "\n".join(L[:idx[0]]).rstrip("\n") + "\n" + blk + "\n" + "\n".join(L[idx[0]:])
        return t.rstrip("\n") + "\n" + blk
    _rw(sec, f); print("newblock ok", sec)
def heads(sec):
    return [l for l in notes(sec).split("\n") if l.strip() and not l.startswith("- ") and not l.startswith("    ") and not l.startswith("Context")]

def _safe(fn):
    def g(*a, **k):
        try: return fn(*a, **k)
        except PatchError: return None
    return g
sub = _safe(sub); after = _safe(after); under = _safe(under); newblock = _safe(newblock)
