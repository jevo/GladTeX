"""This script auto-generates gleetex/unicode_data.py. The purpose is to provide a
table with mappings from unicode points to their LaTeX equivalent. This way,
formulas can be converted using LaTeX2e, but the end-user can still use unicode
in it's formulas. The unicode version can also be used to make the alternative
text more readable."""

import collections
import enum
import os
import urllib.request
import xml.etree.ElementTree as ET

# URL to XML file, which is used to generate the python source file
UNICODE_TABLE_URL = "https://raw.githubusercontent.com/w3c/xml-entities/gh-pages/unicode.xml"
# a list of commands to replace, if found
BAD_COMMANDS = {'\\minus': '-'}

class LaTeXMode(enum.Enum):
    """Represent either math or text mode. Math mode in LaTeX is e.g.
    everything between $ and $."""
    textmode = 0
    mathmode = 1


def get_unicode_table_xml():
    with urllib.request.urlopen(UNICODE_TABLE_URL) as u:
        return ET.fromstring(u.read())

def create_unicode_latex_table(root):
    """This function iterates over the XML tree and extracts all characters for
    the unicode table. The resulting table will have the decimal unicode point
    as key. The value is again a dict with the possible keys from LaTeX and the
    LaTeX commands as string.
    Certain unicode points are ignored, to prevent replacing normal or control
    characters."""
    unicode_table = {}
    for character in root.find('charlist').iterfind('character'):
        childtags = set(node.tag for node in character.getchildren())
        # skip characters without LaTeX alternative
        if 'latex' not in childtags and 'AMS' not in childtags and \
                'mathlatex' not in childtags:
            continue # skip this character
        attr = character.attrib
        # if no mode (text or math) was specified, ignore character
        if attr.get('mode') not in ('text', 'math', 'mixed', 'other'):
            continue

        # a defined character may have multiple codepoints (called ids); add
        # each of the ids as a separate entry to the table
        ids = tuple(map(int, attr['dec'].split('-')))
        if any(elem for elem in ids if elem < 161):
            continue # ignore characters from ascii and a few unicode control characters

        # extract textmode, mathmode and AMS commands:
        commands = {}
        if 'latex' in childtags:
            commands[LaTeXMode.textmode] =\
                    next(character.iterfind('latex')).text
        if 'AMS' in childtags:
            commands[LaTeXMode.mathmode] = next(character.iterfind('AMS')).text
        # only take LaTeX command from <mathlatex/>, if no AMS tag present and
        # no set was specified. A `set` is a attempt to specify the LaTeX
        # package which needs to be loaded.
        if 'mathlatex' in childtags and LaTeXMode.mathmode not in commands:
            mathnode = next(character.iterfind('mathlatex'))
            if 'set' not in mathnode.attrib:
                commands[LaTeXMode.mathmode] = mathnode.text

        if commands: # if a usable textmode and a mathmode without unicode-math found:
            # replace bad commands
            for mode in commands:
                if commands[mode] in BAD_COMMANDS:
                    commands[mode] = BAD_COMMANDS[commands[mode]]
            for item in ids:
                unicode_table[item] = commands
    return unicode_table

def serialize_table(table):
    """Serialize the given unicode table to a python table, which could be
    directly executed by eval. The decimal code points, serving as a key in the
    dictionary, are sorted for the output."""
    ordered_table = collections.OrderedDict()
    for key in sorted(table.keys()):
        ordered_table[key] = table[key]
    python_string = ['unicode_table = {']
    reprmode = lambda m, v: 'LaTeXMode.%s: %s' % (m.name, repr(v[m]))
    for code_point, replacements in ordered_table.items():
        # serialize by hand to have a fixed order of items; helpful for a
        # minimal git diff
        commands = ''
        if LaTeXMode.textmode in replacements:
            commands = reprmode(LaTeXMode.textmode, replacements)
        if LaTeXMode.mathmode in replacements:
            if commands:
                commands += ', '
            commands += reprmode(LaTeXMode.mathmode, replacements)
        python_string.append('%s: {%s},' % (code_point, commands))
    return '\n    '.join(python_string) + '\n    }\n'

def generate_python_src_file(table, python_table):
    """Generate a fully importable python source file, by dumping the enum
    declarations, python imports, doc strings and the given python string with
    the unicode table into the source and returning it as a whole string."""
    enum_def = 'class LaTeXMode(enum.Enum):\n    """%s"""\n    ' % LaTeXMode.__doc__
    enum_values = tuple(e for e in dir(LaTeXMode)  if not e.startswith('_'))
    enum_def += '\n    '.join('%s = %s' % (name, getattr(LaTeXMode, name).value)
            for name in enum_values)
    return """\"\"\"
DO NOT ALTER THIS FILE IN ANY WAY, IT IS GENERATED AUTOMATICALLY. SEE THE SCRIPT
`update_unicode_table.py` FOR MORE INFORMATION.

This file contains a table of unicode code point to LaTeX command mapping. It
has %s entries and was derived from
<%s>.\"\"\"
#pylint: disable=too-many-lines,missing-docstring\n\n
import enum\n
%s\n\n%s\n""" % (len(table), UNICODE_TABLE_URL, enum_def, python_table)


def main():
    if not os.path.exists('gleetex'):
        print("Error: Generator script must be run from GladTeX source root.")
    table = create_unicode_latex_table(get_unicode_table_xml())
    python_table = serialize_table(table)
    with open('gleetex/unicode.py', 'w', encoding='utf-8') as f:
        f.write(generate_python_src_file(table, python_table))

if __name__ == '__main__':
    main()

