"""
This module takes care of the actual image creation process.
"""
import distutils.dir_util
import os
import re
import shutil
import subprocess
import sys

def remove_all(*files):
    """Guarded remove of files (rm -f); no exception is thrown if a file
    couldn't be removed."""
    try:
        for file in files:
            os.remove(file)
    except OSError:
        pass


def proc_call(cmd, cwd=None):
    """Execute cmd (list of arguments) as a subprocess. Returned is a tuple with
    stdout and stderr, decoded if not None. If the return value is not equal 0, a
    subprocess error is raised. Timeouts will happen after 20 seconds."""
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=1, universal_newlines=False, cwd=cwd) as proc:
        data = []
        try:
            data = [d.decode(sys.getdefaultencoding(), errors="surrogateescape")
                    for d in proc.communicate(timeout=20) if d]
            if proc.wait():
                raise subprocess.SubprocessError("Error while executing %s\n%s\n" %
                    (' '.join(cmd), '\n'.join(data)))
        except subprocess.TimeoutExpired as e:
            proc.kill()
            note = 'Subprocess expired with time out: ' + str(cmd) + '\n'
            poll = proc.poll()
            if poll:
                note += str(poll) + '\n'
            if data:
                raise subprocess.SubprocessError(str(data + '\n' + note))
            else:
                raise subprocess.SubprocessError('execution timed out after ' +
                        str(e.args[1]) + ' s: ' + ' '.join(e.args[0]))
        except KeyboardInterrupt as e:
            sys.stderr.write("\nInterrupted; ")
            import traceback
            traceback.print_exc(file=sys.stderr)
        if isinstance(data, list):
            return '\n'.join(data)
        else:
            return data


class Tex2img:
    """
    Convert a TeX document string into a png file.
    This class interacts with the LaTeX and dvipng sub processes. Upon error
    the methods throw a SubprocessError with all necessary information to fix
    the issue.
    The background of the PNG files will be transparent by default.
    """
    call = proc_call
    DVIPNG_REGEX = re.compile(r"^ depth=(-?\d+) height=(\d+) width=(\d+)")
    def __init__(self, tex_document, output_fn, encoding="UTF-8"):
        """tex_document should be either a full TeX document as a string or a
        class which implements the __str__ method."""
        self.tex_document = tex_document
        self.output_name = output_fn
        self.__encoding = encoding
        self.__parsed_data = None
        self.__dpi = 100
        self.__background = 'transparent'
        self.__foreground = 'rgb 0 0 0'
        self.__keep_latex_source = False
        # create directory for image if that doesn't exist
        base_name = os.path.split(output_fn)[0]
        if base_name and not os.path.exists(base_name):
            distutils.dir_util.mkpath(base_name)


    def set_dpi(self, dpi):
        """Set output resolution for formula images."""
        if not isinstance(dpi, (int, float)):
            raise TypeError("Dpi must be an integer or floating point number")
        self.__dpi = int(dpi)

    def set_transparency(self, flag):
        """Set whether or not the background of an image is transparent."""
        if not isinstance(flag, bool):
            raise ValueError("Argument must be of type bool!")
        self.__background = ('transparent' if flag else 'rgb 1 1 1')

    def __check_rgb(self, rgb_list):
        """Check whether a list of RGB colors is correct. It must contain three
        broken decimals with 0 <= x <= 1."""
        if not isinstance(rgb_list, (list, tuple)) or len(rgb_list) != 3:
            raise ValueError("A list with three broken decimals between 0 and 1 expected.")
        if not all(map((lambda x: x >= 0 and x <= 1), rgb_list)):
            raise ValueError("RGB values must between 0 and 1")

    def set_background_color(self, rgb_list):
        """set_background_color(rgb_values)
        The list rgb_values must contain three broken decimals between 0 and 1."""
        self.__check_rgb(rgb_list)
        self.__background = 'rgb {0[0]} {0[1]} {0[2]}'.format(rgb_list)

    def set_foreground_color(self, rgb_list):
        """set_background_color(rgb_values)
        The list rgb_values must contain three broken decimals between 0 and 1."""
        self.__check_rgb(rgb_list)
        self.__foreground = 'rgb {0[0]} {0[1]} {0[2]}'.format(rgb_list)

    def set_keep_latex_source(self, flag):
        """Set whether LaTeX source document should be kept."""
        if not isinstance(flag, bool):
            raise TypeError("boolean object required, got %s." % repr(flag))
        self.__keep_latex_source = flag


    def create_dvi(self, dvi_fn):
        """
        Call LaTeX to produce a dvi file with the given LaTeX document.
        Temporary files will be removed, even in the case of a LaTeX error.
        This method raises a SubprocessError with the helpful part of LaTeX's
        error output."""
        path = os.path.dirname(dvi_fn)
        if not path:
            path = os.getcwd()
        new_extension = lambda x: os.path.splitext(dvi_fn)[0] + '.' + x

        tex_fn = new_extension('tex')
        aux_fn = new_extension('aux')
        log_fn = new_extension('log')
        cmd = None
        cmd = ['latex', '-halt-on-error', os.path.basename(tex_fn)]
        encoding = self.__encoding
        with open(tex_fn, mode='w', encoding=encoding) as tex:
            tex.write(str(self.tex_document))
        try:
            Tex2img.call(cmd, cwd=path)
        except subprocess.SubprocessError as e:
            remove_all(dvi_fn)
            msg = ''
            if e.args:
                data = self.parse_log(e.args[0])
                if data:
                    msg += data
                else:
                    msg += str(e.args[0])
            raise subprocess.SubprocessError(msg) # propagate subprocess error
        except FileNotFoundError:
            # `latex` is missing, give suggestions on how to install it
            text = "Command `%s` not found." % cmd[0]
            if shutil.which('dpkg'):
                text += ' Install it using `sudo apt install texlive-latex-recommended preview-latex-style`'
            else:
                text += ' Install a TeX distribution of your choice, e.g. MikTeX or TeXlive.'
                raise subprocess.SubprocessError(text)
        finally:
            if self.__keep_latex_source:
                remove_all(aux_fn, log_fn)
            else:
                remove_all(tex_fn, aux_fn, log_fn)

    def create_png(self, dvi_fn):
        """Create a PNG file from a given dvi file. The side effect is the PNG
        file being written to disk.
        :param dvi_fn   Dvi file name
        :return dimensions for embedding into an HTML document
        :raises ValueError raised whenever dvipng output coudln't be parsed
        """
        cmd = ['dvipng', '-q*', '-D', str(self.__dpi),
                # colors
                '-bg', self.__background, '-fg', self.__foreground,
                '--height*', '--depth*', '--width*', # print information for embedding
                '-o', self.output_name, dvi_fn]
        data = None
        try:
            data = Tex2img.call(cmd)
        except subprocess.SubprocessError:
            remove_all(self.output_name)
            raise
        except FileNotFoundError:
            # `dvipng` is missing, give suggestions on how to install it
            text = "Command `%s` not found." % cmd[0]
            if shutil.which('dpkg'):
                text += ' Install it using `sudo apt install dvipng`'
            else:
                text += ' Install a TeX distribution of your choice, e.g. MikTeX or TeXlive.'
            raise subprocess.SubprocessError(text)
        finally:
            remove_all(dvi_fn)
        for line in data.split('\n'):
            found = Tex2img.DVIPNG_REGEX.search(line)
            if found:
                return dict(zip(['depth', 'height', 'width'], found.groups()))
        raise ValueError("Could not parse dvi output: " + repr(data))

    def convert(self):
        """Convert the TeX document into an image.
        This calls create_dvi and create_png but will not return anything. Thre
        result should be retrieved using get_positioning_info()."""
        dvi = os.path.join(os.path.splitext(self.output_name)[0] + '.dvi')
        try:
            self.create_dvi(dvi)
            self.__parsed_data = self.create_png(dvi)
        except OSError:
            remove_all(self.output_name)
            raise

    def get_positioning_info(self):
        """Return positioning information to position created image in the HTML
        page."""
        return self.__parsed_data

    def parse_log(self, logdata):
        """Parse the LaTeX error output and return the relevant part of it."""
        if not logdata:
            return None
        line = None
        for line in logdata.split('\n'):
            if line.startswith('! '):
                line = line[2:]
                break
        if line: # try to remove LaTeX line numbers
            lineno = re.search(r'\s*on input line \d+', line)
            if lineno:
                line = line[:lineno.span()[0]] + line[lineno.span()[1]:]
            return line

def fontsize2dpi(size_pt):
    """This function calculates the DPI for the resulting image. Depending on
    the font size, a different resolution needs to be used. According to the
    dvipng manual page, the formula is:
    <dpi> = <font_px> * 72.27 / 10 [px * TeXpt/in / TeXpt]"""
    size_px = size_pt * 1.3333333 # and more 3s!
    return size_px * 72.27 / 10

