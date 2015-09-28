import argparse
import gleetex
import os
import re
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
        parser.add_argument('-b', dest='background_color',
                help="Set background color for resulting images (default transparent)")
        parser.add_argument('-c', dest='foreground_color',
                help="Set foreground color for resulting images (default 0,0,0)")
        parser.add_argument('-d', dest='directory', help="Directory in which to" +
                " store generated images in (relative path)")
        parser.add_argument('-E', dest='encoding', default="UTF-8",
                help="Overwrite encoding to use (default UTF-8)")
        parser.add_argument('-o', metavar='FILENAME', dest='output',
                help=("set output file name; '-' will print text to stdout (by"
                    "default input file name is used and .htex ending changed "
                    "to .html)"))
        parser.add_argument('-r', metavar='DPI', dest='dpi', default=100, type=int,
                help="set resolution (size of images) to 'dpi' (100 by " + \
                    "default)")
        parser.add_argument("-u", metavar="URL", dest='url',
                help="url to image files (relative links are default)")
        parser.add_argument('input', help="input .htex file with LaTeX " +
                "formulas")
        return parser.parse_args(args)

    def exit(self, status):
        """Exit function. Could be used to register any clean up action."""
        sys.exit(status)

    def validate_options(self, opts):
        """Validate certain arguments suppliedon the command line."""
        color_regex = re.compile(r"^\d(?:\.\d+)?,\d(?:\.\d+)?,\d(?:\.\d+)?")
        if opts.background_color and not color_regex.match(opts.background_color):
            print("Option -b requires a string in the format " +
                        "num,num,num where num is a broken decimal between 0 " +
                        "and 1.")
            sys.exit(12)
        if opts.foreground_color and not color_regex.match(opts.foreground_color):
            print("Option -c requires a string in the format " +
                        "num,num,num where num is a broken decimal between 0 " +
                        "and 1.")
            sys.exit(13)

    def get_input_output(self, options):
        """Return input document as string and determine, base directory and
        output file name. If -o is supplied, the output file name is not
        altered. If document is read from stdin and no -o option is specified,
        standard output will be used (denoted by -). If an ordinary input file
        is given and no output file name, the same file with .html endingin
        (instead of .htex) is used."""
        data = None
        base_path = ''
        output = '-'
        if options.input == '-':
            data = sys.stdin.read()
        else:
            with open(options.input, 'r', encoding=options.encoding) as file:
                data = file.read()
            base_path = os.path.split(options.input)[0]
        # check which output file name to use
        if options.output:
            base_path = os.path.split(options.output)[0]
            output = options.output
        else:
            if options.input != '-':
                base_path = os.path.split(options.input)[0]
                output = os.path.splitext(options.input)[0] + '.html'
        if options.directory:
            base_path = os.path.join(base_path, options.directory)
        return (data, base_path, output)


    def run(self, args):
        options = self._parse_args(args[1:])
        self.validate_options(options)
        self.__encoding = options.encoding
        docparser = gleetex.htmlhandling.EqnParser()
        doc, base_path, output = self.get_input_output(options)
        try:
            docparser.feed(doc)
        except gleetex.htmlhandling.ParseException as e:
            print('Error while parsing {}: {}', options.input, (str(e[0])
                if len(e) > 0 else str(e)))
            self.exit(5)
        doc = docparser.get_data()
        processed = self.convert_images(doc, base_path, options)
        img_fmt = gleetex.htmlhandling.HtmlImageFormatter(encoding = \
                self.__encoding)
        img_fmt.set_exclude_long_formulas(True)
        if options.url:
            img_fmt.set_url(options.url)

        if output == '-':
            self.write_data(sys.stdout, processed, img_fmt)
        else:
            with open(output, 'w', encoding=self.__encoding) as file:
                self.write_data(file, processed, img_fmt)

    def write_data(self, file, processed, formatter):
        """Write back altered HTML file with given formatter."""
        # write data back
        for chunk in processed:
            if isinstance(chunk, (list, tuple)):
                file.write(formatter.format(*chunk))
            else:
                file.write(chunk)

    def convert_images(self, parsed_htex_document, base_path, options):
        """Convert all formulas to images and store file path and equation in a
        list to be processed later on."""
        base_path = ('' if not base_path or base_path == '.' else base_path)
        result = []
        conv = gleetex.convenience.CachedConverter(base_path)
        options_to_query = ['dpi']
        for option_str in options_to_query:
            option = getattr(options, option_str)
            if option:
                conv.set_option(option_str, option)
        # colors need special handling
        for option_str in ['foreground_color', 'background_color']:
            option = getattr(options, option_str)
            if option:
                conv.set_option(option_str, tuple(map(float, option.split(','))))
        for chunk in parsed_htex_document:
            # two types of chunks: a) str (uninteresting), b) list: formula
            if isinstance(chunk, list):
                equation = chunk[2]
                try:
                    pos, path = conv.convert(equation)
                    # add data for formatting to `result`
                    result.append((pos, equation, path))
                except SubprocessError as e:
                    print(("Error while converting the formula: %s at line %d"
                            " pos %d") % (equation, chunk[0][0], chunk[0][1]))
                    print("Error: %s" % e.args[0])
                    self.exit(91)
            else:
                result.append(chunk)
        return result


if __name__ == '__main__':
    m = Main()
    m.run(sys.argv)
