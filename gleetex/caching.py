"""This module contains the ImageCache, which caches formulas which have already
been converted. Only with this mechanism, a formula which occurs multiple times
can be reused, even across several runs of GladTeX.

Cache format:

    { # dict of formulas
        'some formula': # formula as key into dictionary
            { # list of display math / inline maths variants
                True: # displaymath = True
                    { # dictionary of values describing formula
                        'path': 'some/path'
                        'pos': { # positioning within the HTML document
                            'height': ..., 'width':..., 'depth:....
                        }
                    }
                    }
            }
    }

Formulas are `normalized`, so spacing is unified to detect possibly equal
formulas more easyly.
"""

import json
import os

CACHE_VERSION = '2.0'

def normalize_formula(formula):
    """This function normalizes a formula. This e.g. means that multiple white
    spaces are squeezed into one and a tab will be replaced by a space. With
    this it is more realistic that a recurring formula in a document is detected
    as such, even though if it might have been written with different spacing.
    Empty braces ({}) are removed as well."""
    return formula.replace('{}', ' ').replace('\t', ' ').replace('  ', ' '). \
        rstrip().lstrip()

def recover_bools(object):
    """After JSon is read from disk, keys as False or True have been serialized
    to 'false' and 'true', but they're not recovered by the json parser. This
    function alters converts these keys back to booleans; note: it only works
    with references, so this function doesn't return anything."""
    if isinstance(object, dict):
        for key in ['false', 'true']:
            if key in object:
                val = object[key] # store value
                object[key == 'true'] = val # safe it with boolean representation
                del object[key] # remove string key
        # iterate recursively through dict
        for value in object.values():
            recover_bools(value)
    if isinstance(object, list):
        for item in object:
            recover_bools(item)

class JsonParserException(Exception):
    """Specialized exception class for handling errors while parsing the JSON
    cache."""
    pass

class ImageCache:
    """
    This cache stores formulas which have been converted already and don't need
    to be converted again. This is both a disk usage and performance
    improvement. The cache can be written and read from disk.

    If the argument keep_old_cache is True, the cache will raise a
    JsonParserException if
    that file could not be read (i.e. incompatible GladTeX version). If set to
    False, it'll discard the cache along with all eqn* files and start with a
    clean cache.

    cache = ImageCache()
    c.add_formula('\\tau', # the formulas
        {'height': 1, 'depth': 2, 'width='3'}, # the positioning information for the output document
        'eqn042.png', displaymath=True):
    assert len(cache) == 1 # one entry
    c.write()
    assert os.path.exists('gladtex.cache')
    """
    VERSION_STR = 'GladTeX__cache__version'

    def __init__(self, path='gladtex.cache', keep_old_cache=True):
        self.__cache = {}
        self.__set_version(CACHE_VERSION)
        self.__path = path
        if os.path.exists(path):
            try:
                self._read()
            except JsonParserException:
                if keep_old_cache:
                    raise
                else:
                    self._remove_old_cache_and_files()

    def __len__(self):
        """Return number of formulas in the cache."""
        # ignore version
        return len(self.__cache) - 1

    def __set_version(self, version):
        """Set version of cache (data structure format)."""
        self.__cache[ImageCache.VERSION_STR] = version

    def write(self):
        """Write cache to disk. The file name will be the one configured during
        initialisation of the cache."""
        if len(self.__cache) == 0:
            return
        with open(self.__path, 'w', encoding='UTF-8') as file:
            file.write(json.dumps(self.__cache))

    def _read(self):
        """Read Json from disk into cache, if file exists.
        :raises JsonParserException if json could not be parsed"""
        def raise_error(msg):
            raise JsonParserException(msg + "\nPlease delete the cache (and" + \
                        " the images) and rerun the program.")
        if os.path.exists(self.__path):
            #pylint: disable=broad-except
            try:
                with open(self.__path, 'r', encoding='utf-8') as file:
                    self.__cache = json.load(file)
            except Exception as e:
                msg = "error while reading cache from %s: " % os.path.abspath(self.__path)
                if isinstance(e, (ValueError, OSError)):
                    msg += str(e.args[0])
                elif isinstance(e, UnicodeDecodeError):
                    msg += 'expected UTF-8 encoding, erroneous byte ' + \
                            '{0} at {1}:{2} ({3})'.format(*(e.args[1:]))
                else:
                    msg += str(e.args[0])
                raise_error(msg)
        if not isinstance(self.__cache, dict):
            raise_error("Decoded Json is not a dictionary.")
        if not self.__cache.get(ImageCache.VERSION_STR):
            self.__set_version(CACHE_VERSION)
        cur_version = self.__cache.get(ImageCache.VERSION_STR)
        if cur_version != CACHE_VERSION:
            raise_error("Cache in %s has version %s, expected %s." % \
                    (self.__path, cur_version, CACHE_VERSION))
        recover_bools(self.__cache)

    def _remove_old_cache_and_files(self):
        os.remove(self.__path)
        directory = os.path.split(self.__path)[0]
        if not directory:
            directory = '.'
        # remove all files starting with eqn*
        for file in os.listdir(directory):
            if not file.startswith('eqn'):
                continue
            file = os.path.join(directory, file)
            if os.path.isfile(file):
                os.remove(file)

    def add_formula(self, formula, pos, file_path, displaymath=False):
        """Add formula to cache. The pos argument contains the positioning
        info for the output document and is a dict with 'height', 'width' and
        'depth'.
        Keep in mind that formulas set with displaymath are not the same as
        those set iwth inlinemath.
        This method raises OSError if specified image doesn't exist or if it got
        an absolute file_path."""
        if not pos or not formula or not file_path:
            raise ValueError("the supplied arguments may not be empty/none")
        if not isinstance(displaymath, bool):
            raise ValueError("displaymath must be a boolean")
        if os.path.isabs(file_path):
            raise OSError("The file path to the image may NOT be an absolute path")
        if '\\' in file_path:
            file_path = file_path.replace('\\', '/')
        if not os.path.exists(file_path):
            # could be that the current working directory is different
            test_path = os.path.join(os.path.split(self.__path)[0],
                    os.path.split(file_path)[1])
            if not os.path.exists(test_path):
                raise OSError("cannot add %s to the cache: doesn't exist" %
                    file_path)
        formula = normalize_formula(formula)
        if not formula in self.__cache:
            self.__cache[formula] = {}
        val = self.__cache[formula]
        if not displaymath in val:
            val[displaymath] = {'pos' : pos, 'path' : file_path}

    def remove_formula(self, formula, displaymath):
        """This method removes the given formula from the cache. A KeyError is
        raised, if the formula did not exist. Internally, formulas are
        normalized to detect similarities."""
        formula = normalize_formula(formula)
        if not formula in self.__cache:
            raise KeyError("key %s not in cache" % formula)
        else:
            value = self.__cache[formula]
            if displaymath in value:
                del self.__cache[formula]
            else:
                raise KeyError("key %s (%s) not in cache" % (formula, displaymath))

    def contains(self, formula, displaymath):
        """Check whether a formula was already cached and return True if
        found."""
        try:
            return bool(self.get_data_for(formula, displaymath))
        except KeyError:
            return False


    def get_data_for(self, formula, displaymath):
        """
        Retrieve meta data about a formula from the cache.

        The meta information is used to embed the formula in the HTML document.
        It is a dictionary with the keys 'pos' and 'path'. The positioning info
        is described in the documentation of this class.
        This method raises a KeyError if the formula wasn't found."""
        formula = normalize_formula(formula)
        if not formula in self.__cache:
            raise KeyError(formula, displaymath)
        else:
            # check whether file still exists
            value = self.__cache[formula]
            if displaymath in value.keys():
                if not os.path.exists(value[displaymath]['path']):
                    del self.__cache[formula]
                    raise KeyError((formula, displaymath))
                else:
                    return value[displaymath]
            else:
                raise KeyError((formula, displaymath))

