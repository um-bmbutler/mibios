"""
Utilities module
"""
import logging


class PrintLikeLogging(logging.LoggerAdapter):
    """
    Adapter to log just like print
    """
    def log(self, level, *msg, sep=' ', **kwargs):
        """
        Adapter to log just like print

        Except end, file, and flush keyword args are not to be used
        """
        super().log(level, sep.join([str(i) for i in msg]), **kwargs)


def getLogger(name):
    """
    Wrapper around logging.getLogger()
    """
    return PrintLikeLogging(logging.getLogger(name), {})


class DeepRecord():
    """
    Dict-of-dict / tree like datastructure to hold a multi-table record

    Helps loading complex table
    """
    def __init__(self, init={}, sep='__'):
        self._ = {}
        self.sep = sep
        for k, v in init.items():
            self.add(k, v)

    @classmethod
    def from_accessors(cls, accessors, sep='__'):
        """
        Make a deep template dict for the model(s)
        """
        return cls(init={i: {} for i in accessors}, sep=sep)

    def split(self, key):
        """
        ensure key is in split format and valid for other methods
        """
        if isinstance(key, str):
            key = key.split(self.sep)
        return key

    def __getitem__(self, key):
        """
        Get method for dict for dicts / a.k.a. deep model template

        key can be a __-separated string (django lookup style) or a list
        of dict keys
        """
        cur = self._
        key = self.split(key)

        for i in key:
            try:
                cur = cur[i]
            except (KeyError, TypeError):
                raise LookupError('Invalid key: {}'.format(key))
        return cur

    def __delitem__(self, key):
        """
        Del method for dict for dicts / a.k.a. deep model template

        key can be a __-separated string (django lookup style) or a list
        of dict keys
        """
        # FIXME: has currently no users
        cur = self._
        key = self.split(key)

        prev = cur
        for i in key:
            prev = cur
            try:
                cur = cur[i]
            except (KeyError, TypeError):
                raise KeyError('Invalid key for template: {}'.format(key))

        del prev[i]

    def add(self, key, value={}):
        """
        Add a new key with optional value

        Adds a new key with optional value. Key can be a __-separated string
        (django lookup style) or a list of dict keys
        """
        self.__setitem__(key, value)

    def __contains__(self, key):
        """
        Contains method for dict for dicts / a.k.a. deep model template

        Key can be a __-separated string (django lookup
        style) or a list
        of dict keys
        """
        # FIXME: at this point dicts of dict should really get their own class
        cur = self._
        key = self.split(key)

        for i in key:
            try:
                cur = cur[i]
            except (KeyError, TypeError):
                return False
        return True

    def __setitem__(self, key, value):
        """
        Set method for dict for dicts / a.k.a. deep model template

        The key must exist.  Key can be a __-separated string (django lookup
        style) or a list
        of dict keys
        """
        cur = self._
        prev = None
        key = self.split(key)

        for i in key:
            prev = cur
            try:
                cur = cur[i]
            except KeyError:
                # extend key space
                cur[i] = {}
                cur = cur[i]
            except TypeError:
                # value at cur already set
                print('THE BORK\n', self)
                raise KeyError('Invalid key: {}, a value has already been set:'
                               ' {}'.format(key, cur))

        prev[i] = value

    def keys(self, key=(), leaves_first=False, leaves_only=False):
        """
        Return (sorted) list of keys
        """
        ret = []
        cur = self[key]
        if isinstance(cur, dict):
            if key:
                if not (cur and leaves_only):
                    ret.append(key)
            for k, v in cur.items():
                ret += self.keys(
                    key + (k,),
                    leaves_first=leaves_first,
                    leaves_only=leaves_only,
                )
        else:
            if key:
                ret.append(key)

        if leaves_first:
            ret = sorted(ret, key=lambda x: -len(x))

        return ret

    def items(self, **kwargs):
        return [(i, self[i]) for i in self.keys(**kwargs)]

    def update(self, *args, **kwargs):
        for i in args:
            for k, v in i.items():
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def __iter__(self):
        return iter(self.keys(leaves_first=True))

    def pretty(self, indent=(0, 2)):
        """
        Pretty-print object
        """
        if len(indent) == 2:
            offset, indent = indent
        elif len(indent) == 1:
            offset = 0
        else:
            raise ValueError('bad value for indent parameter: {}'
                             ''.format(indent))
        lines = []
        for k, v in self.items():
            line = '{}{}{}:'.format(
                ' ' * offset,
                ' ' * indent * (len(k) - 1),
                k[-1],
            )
            if isinstance(v, dict):
                if not v:
                    # empty leaf
                    line += ' -'
            else:
                line += '[{}] "{}"'.format(type(v).__name__, v)
            lines.append(line)
        return '\n'.join(lines)

    def __str__(self):
        return str(self._)
