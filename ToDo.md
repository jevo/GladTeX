To Do
=====

This list contains things to be implemented in GladTeX. If you have additions or
even feel like you want to do it, feel free to drop me an email: `shumenda |aT|
gmx //dot-- de`.

Uncategorized
-------------

-   introduce command line option which will check whether all all formulas in a
    cache are used and if not, remove the formula (only useful for caches
    corresponding to a single document)

Gettext
-------


Gettext should be integrated to localize messages (especially errors).

Compressed Cache
----------------

The cache stores the path, the formula and the positioning of an image. For
large documents, this might be quite big, hence it makes sense to compress them.

To make things easier, the cache should have a .gz extension.

