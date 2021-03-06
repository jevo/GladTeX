GladTeX
=======

GladTeX is a preprocessor that enables the use of LaTeX formulas within HTML
files. The formulas, embedded in <eq>...</eq> tags, as if within $$..$$ in LaTeX,
is fed through latex and replaced by images.

Additionally all images get an alt-tag for alternative texts that contains the
LaTeX-equivalent of the image. This is handy for text-mode browsers or blind
people.

This is a complete rewrite of the old GladTeX which was implemented in Perl and
in C. The old version was not easily portable across platforms. The
new version is purely implemented in Python, gets rid of the Ghostscript
dependency and additionally offers the GladTeX functionality in a Python module
called gleetex.  to be embedded in other applications.

License
-------

_Copyright:_

About the old perl version:

- (C) 1999-2010 Martin G. Gulbrandsen
- (C) 2011-2013 Jonathan Daugherty (especially release 1.3)
- (C) 2013-2015 Sebastian Humenda

Credits go to

- 2013 Patrick Spendrin (patches for cmake and eqn2img to build it on Windows)



About the rewritten (current) version:

-   (c) 2015-2017 Sebastian Humenda
    -   credits go to Martin G. Gulbrandsen who had the idea in the first place

This program is distributed under the LGPL-3, or at your option, any later
version of the license; for details see the accompanying file COPYING.

The official project homepage is at <http://humenda.github.io/GladTeX>

Installation
============

### Debian/Ubuntu

On all derivatives of Debian (as Ubuntu/Mint, etc.), installing GladTeX is as
easy as

    # apt-get install gladtex

### Windows

If you want to use the program without the Python library, you should download a
pre-compiled binary from <https://github.com/humenda/GladTeX/releases>.

Just unzip the archive and move the files to a directory within `%PATH%`.

### OS X

If you want to use GladTex you have to install LaTeX on your system. 
The installation of GladTex was tested with ![MacTex](http://www.tug.org/mactex/).
Afterwards you can installed GladTex from github.
The following steps require Python >= 3.4

The commands are:

'''
$ git clone https://github.com/humenda/GladTeX.git

$ cd GladTex

$ python setup.py install

'''

Now you can use GladTex on your Mac.

### From Source

The following is required for installing GladTeX:

-   Python >= 3.4
-   LaTeX (2e), dvipng
-   the LaTeX package preview.sty

On Debian/Ubuntu systems the following commands will satisfy the dependencies:

    # apt-get install python3-all texlive-fonts-recommended texlive-latex-recommended preview-latex-style dvipng
    
The package can then be installed using

    # python3 setup.py install

Note: If your system ships `python` as the command for Python3 you have to use
`python in` the above command instead.

### Compilation On Windows

To compile GladTeX on Windows, yu need a Python3 installation. Assumed is
python3.4, newer versions should work fine as well. Only the paths need to be
adjusted

Install py2exe:

    c:\python34\scripts\pip.exe install py2exe

Given that GladTeX is located in c:\users\user\gladtex:

    cd c:\users\user\gladtex
    c:\python34\python.exe setup.py install

That will install GladTeX as a library to `c:\python34\lib` and the script to
`c:\python34\scripts`. It also allows py2exe to find the gleetex module. Now the
executable can be build:

    c:\python34\scripts\build_exe.exe -b 0 -c gladtex.py

That'll create a `dist/` folder containing the executable. If you have other
python applications in your project it is useful to read about the `-b` switch
to share some python components included in the just-built executable.

Documentation
-------------

Please use `man gladtex` for further instructions.

