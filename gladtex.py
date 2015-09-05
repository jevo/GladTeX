import argparse
import gleetex
import os
import sys
from subprocess import SubprocessError


class HelpfulCmdParser(argparse.ArgumentParser):
    """This variant of arg parser always prints the full help whenever an error
    occurs."""
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)



class Main:
    """This class parses command line arguments and deals with the
    conversion. Only the run method needs to be called."""
    def __init__(self):
        self.__encoding = "utf-8"
        self.__equations = []

    def _parse_args(self, args):
        """Parse command line arguments and return option instance."""
        parser = HelpfulCmdParser()
        parser.add_argument("-a", action="store_true", dest="exclusionfile", help="save text alternatives " +
                "for images which are too long for the alt attribute into a " +
                "single separate file and link images to it")
        parser.add_argument('-d', dest='directory', help="Directory in which to" +
                " store generated images in")
        parser.add_argument('-E', dest='encoding', default="UTF-8",
                help="Overwrite encoding to use (default UTF-8)")
        parser.add_argument('-r', metavar='DPI', dest='dpi', default=100,
                type=int, help="set resolution (size of images) to 'dpi' " + \
                "(100 by default)")
        parser.add_argument("-u", metavar="URL", dest='url',
                help="url to image files (relative links are default)")
        parser.add_argument('input', help="input .htex file with LaTeX " +
                "formulas")
        return parser.parse_args(args)

    def exit(self, status):
        """Exit function. Could be used to register any clean up action."""
        sys.exit(status)

    def run(self, args):
        options = self._parse_args(args[1:])
        self.__encoding = options.encoding
        doc = None
        with open(options.input, 'r', encoding=options.encoding) as file:
            docparser = gleetex.htmlhandling.EqnParser()
            try:
                docparser.feed(file.read())
            except gleetex.htmlhandling.ParseException as e:
                print('Error while parsing {}: {}', options.input, (str(e[0])
                    if len(e) > 0 else str(e)))
                self.exit(5)
            doc = docparser.get_data()
        # base name is the inut file name + an optional directory specified with
        # -d
        base_name = ('' if not options.directory else options.directory)
        base_name = os.path.join(os.path.split(options.input)[0], base_name)
        processed = self.convert_images(doc, base_name, options.dpi)
        img_fmt = gleetex.htmlhandling.HtmlImageFormatter(encoding = \
                self.__encoding)
        img_fmt.set_exclude_long_formulas(True)
        if options.url:
            img_fmt.set_url(options.url)

        html_fn = os.path.splitext(options.input)[0] + '.html'
        with open(html_fn, 'w', encoding=options.encoding) as f:
            for chunk in processed:
                if isinstance(chunk, (list, tuple)):
                    f.write(img_fmt.format(*chunk))

    def convert_images(self, parsed_htex_document, base_path, dpi):
        """Convert all formulas to images and store file path and equation in a
        list to be processed later on."""
        formula_number = 0
        base_path = (None if not base_path or base_path == '.' else base_path)
        result = []
        for chunk in parsed_htex_document:
            # two types of chunks: a) str (uninteresting), b) list: formula
            if isinstance(chunk, list):
                equation = chunk[2]
                latex = gleetex.document.LaTeXDocument(equation)
                formula_fn = 'eqn%03d.png' % formula_number
                if base_path:
                    formula_fn = os.path.join(base_path, formula_fn)
                conv = gleetex.image.Tex2img(latex, formula_fn)
                conv.set_dpi(dpi)
                try:
                    conv.convert()
                except SubprocessError as e:
                    print(("Error while converting the formula: %s at line %d"
                            " pos %d") % (equation, chunk[0][0], chunk[0][1]))
                    print("Error: %s" % e.args[0])
                    self.exit(91)
                # replace old chunk with formatted html string
                formula_number += 1
                result.append((conv.get_positioning_info(), equation, formula_fn))
            else:
                result.append(chunk)
        return result


if __name__ == '__main__':
    m = Main()
    m.run(sys.argv)
