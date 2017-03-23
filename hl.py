#!/usr/bin/python -u

import argparse
import glob
import re
import sys

__version__ = '1.0.0'

parser = argparse.ArgumentParser(description='Highlight keywords in a file or stdin with different specified colors')
parser.add_argument('files', nargs='*', help='File path', default=None)
parser.add_argument('--grep', dest='grep_words', action='append', help='Filter lines with words in log messages. The words are delimited with \'|\', where each word can be tailed with a color initialed with \'\\\'. If no color is specified, \'RED\' will be the default color. For example, option --grep=\"word1|word2\\CYAN\" means to filter out all lines containing either word1 or word2, and word1 will appear in default color \'RED\' while word2 will be in the specified color \'CYAN\'. Supported colors (case ignored): {BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, BG_BLACK, BG_RED, BG_GREEN, BG_YELLOW, BG_BLUE, BG_MAGENTA, BG_CYAN, BG_WHITE}. The color with prefix \'BG_\' is background color. You can have multiple \'--grep\' options in the command line, and if so, the command will grep all of the key words in all \'--grep\' options. Escape \'|\' with \'\\|\', and \'\\\' with \'\\\\\'.')
parser.add_argument('--hl', dest='highlight_words', action='append', help='Words to highlight in log messages. Unlike --grep option, this option will only highlight the specified words with specified color but does not filter any lines. Except this, the format and supported colors are the same as \'--grep\'. You can have multiple \'--hl\' options in the command line, and if so, the command will highlight all of the key words in all \'--hl\' options')
parser.add_argument('--grepv', dest='grepv_words', action='append', help='Exclude lines with words from log messages. The format and supported colors are the same as \'--grep\'. Note that if both \'--grepv\' and \'--grep\' are provided and they contain the same word, the line will always show, which means \'--grep\' overwrites \'--grepv\' for the same word they both contain. You can have multiple \'--grepv\' options in the command line, and if so, the command will exclude the lines containing any keywords in all \'--grepv\' options')
parser.add_argument('--igrep', dest='igrep_words', action='append', help='The same as \'--grep\', just ignore case')
parser.add_argument('--ihl', dest='ihighlight_words', action='append', help='The same as \'--hl\', just ignore case')
parser.add_argument('--igrepv', dest='igrepv_words', action='append', help='The same as \'--grepv\', just ignore case')
parser.add_argument('--wrap-indent', dest='wrap_indent_width', type=int, default=0, help='If this option is provided, each wrapped line will be added an extra indent. This option implicitly enables \'--wrap\' option, however, please NOTE that when running in pipe mode, you have to use \'--wrap\' option explicitly to specify the terminal width by just adding \'--wrap=`tput cols`\'. For example, \'cat file.txt | hl.py --grep="test" --wrap=`tput cols`\'')
parser.add_argument('--wrap', dest='terminal_width', type=int, default=-1, help='When running in pipe mode (like \'cat file.txt | hl.py --grep="test" --wrap=`tput cols`\'), if you want to wrap each line width specified width, you need to give terminal width as the value, just put \"`tput cols`\" here. When this option is provided, every line will be wrapped based on the \'terminal_width\' specified, where each line will be limited to the area with this width')
parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, help='Print the version number and exit')

args = parser.parse_args()

file_paths = []
for path in args.files:
    file_paths += glob.glob(path)

if len(sys.argv) <= 1:
    parser.print_help()
    sys.exit(0)

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

color_dict = {'BLACK': BLACK, 'RED': RED, 'GREEN': GREEN, 'YELLOW': YELLOW, 'BLUE': BLUE, 'MAGENTA': MAGENTA, 'CYAN': CYAN, 'WHITE': WHITE}
contrast_color_dict = {BLACK: WHITE, RED: WHITE, GREEN: BLACK, YELLOW: BLACK, BLUE: WHITE, MAGENTA: WHITE, CYAN: BLACK, WHITE: BLACK}


RESET = '\033[0m'
EOL = '\033[K'


def termcolor(fg=None, bg=None, ul=False):
    codes = []
    if fg is not None:
        codes.append('3%d' % fg)
    if bg is not None:
        codes.append('10%d' % bg)
    return '\033[%s%sm' % ('4;' if ul else '', ';'.join(codes) if codes else '')


def colorize(message, fg=None, bg=None, ul=False):
    return termcolor(fg, bg, ul) + message + RESET


def print_error(error_msg):
    print('\n' + colorize(error_msg, fg=WHITE, bg=RED, ul=True) + '\n')


def extract_color_from_word(word):
    w = word
    c = RED
    bg = False
    delimiter = '\\'
    index = word.rfind(delimiter)
    if index is not -1:
        w = word[0:index]
        w.replace('\|', '|')
        w.replace('\\\\', '\\')
        raw_color_word = word[index + len(delimiter):]
        try:
            color_word = raw_color_word.upper()
            if color_word[:3] == 'BG_':
                bg = True
                color_word = color_word[3:]
            c = color_dict[color_word]
        except KeyError:
            print_error('Wrong color name: \'' + raw_color_word + '\'')
            c = RED
            bg = False
    return w, c, bg


def parse_words_with_color(words):
    words_with_color = []
    for word in words:
        words_with_color.append(extract_color_from_word(word))
    return words_with_color


def empty(vector):
    return vector is None or len(vector) <= 0


def parse_keywords(keyword_str_list):
    if empty(keyword_str_list):
        return None
    else:
        res = []
        for words in keyword_str_list:
            res += parse_words_with_color(words.split('|'))
        return res


grep_words_with_color = parse_keywords(args.grep_words)
highlight_words_with_color = parse_keywords(args.highlight_words)
excluded_words = parse_keywords(args.grepv_words)
igrep_words_with_color = parse_keywords(args.igrep_words)
ihighlight_words_with_color = parse_keywords(args.ihighlight_words)
iexcluded_words = parse_keywords(args.igrepv_words)


def does_match_grep(message, grep_words_with_color, ignore_case):
    if not empty(grep_words_with_color):
        for word, color, bg in grep_words_with_color:
            if len(word) > 0 and ((not ignore_case and word in message) or (ignore_case and word.upper() in message.upper())):
                return True
    return False


def does_match_grepv(message, grepv_words, ignore_case):
    if not empty(grepv_words):
        for word, color, bg in grepv_words:
            if len(word) > 0 and ((not ignore_case and word in message) or (ignore_case and word.upper() in message.upper())):
                return True
    return False


def colorize_substr(str, start_index, end_index, color, bg):
    fg_color = None
    bg_color = None
    ul = False
    if bg:
        bg_color = color
        try:
            fg_color = contrast_color_dict[color]
        except KeyError:
            pass
    else:
        fg_color = color
        ul = True
    colored_word = colorize(str[start_index:end_index], fg_color, bg_color, ul=ul)
    return str[:start_index] + colored_word + str[end_index:], start_index + len(colored_word)


def highlight(line, words_to_color, ignore_case=False, prev_line=None, next_line=None):
    for word, color, bg in words_to_color:
        if len(word) > 0:
            index = 0
            while True:
                try:
                    if ignore_case:
                        index = line.upper().index(word.upper(), index)
                    else:
                        index = line.index(word, index)
                except ValueError:
                    break
                line, index = colorize_substr(line, index, index + len(word), color, bg)

            if not empty(prev_line):
                for i in range(1, len(word)):
                    wrapped_word = prev_line[-i:] + line[:len(word) - i]
                    if (not ignore_case and word == wrapped_word) or (ignore_case and word.upper() == wrapped_word.upper()):
                        line, index = colorize_substr(line, 0, len(word) - i, color, bg)
                        break

            if not empty(next_line):
                for i in range(1, len(word)):
                    wrapped_word = line[-i:] + next_line[:len(word) - i]
                    if (not ignore_case and word == wrapped_word) or (ignore_case and word.upper() == wrapped_word.upper()):
                        line, index = colorize_substr(line, len(line) - i, len(line), color, bg)
                        break

    return line


ANSI_ESC_PATTERN = r'\x1b\[([0-9,A-Z]{1,2}(;[0-9]{1,2})*(;[0-9]{3})?)?[m|K]'


def split_to_lines(message, total_width, initial_indent_width=0, subsequent_indent_width=0):
    if total_width == -1:
        return message
    message = message.replace('\t', ' ' * 4)
    lines = []

    current_indent = initial_indent_width
    current_line = ''
    current_esc = RESET
    current_line_stripped_len = 0
    idx = 0
    while idx < len(message):
        matches = re.match(ANSI_ESC_PATTERN, message[idx:])
        if matches:
            current_esc = message[idx + matches.start():idx + matches.end()]
            current_line += current_esc
            idx += matches.end()
        else:
            current_line += message[idx]
            current_line_stripped_len += 1
            if current_line_stripped_len >= total_width - current_indent:
                if current_line[-len(RESET):] != RESET:
                    current_line += RESET
                lines.append(current_line)
                current_indent = subsequent_indent_width
                if current_esc == RESET:
                    current_line = ''
                else:
                    current_line = current_esc
                current_line_stripped_len = 0
            idx += 1
    if len(current_line) > 0:
        lines.append(current_line)
    return lines


def run(input_src, file_path):
    while True:
        try:
            line = input_src.readline().decode('utf-8')
            if not line:
                break
        except UnicodeDecodeError:
            print_error('Can\'t decode line as utf-8 for file \'' + file_path + '\'')
            continue

        matches_grep = does_match_grep(line, grep_words_with_color, False)
        matches_igrep = does_match_grep(line, igrep_words_with_color, True)

        matches_grepv = does_match_grepv(line, excluded_words, False)
        matches_igrepv = does_match_grepv(line, iexcluded_words, True)

        if matches_grep or matches_igrep:
            pass
        elif matches_grepv or matches_igrepv:
            continue
        else:
            if empty(grep_words_with_color) and empty(igrep_words_with_color):
                pass
            else:
                continue

        words_to_color = []
        if grep_words_with_color is not None:
            words_to_color += grep_words_with_color
        if highlight_words_with_color is not None:
            words_to_color += highlight_words_with_color

        iwords_to_color = []
        if igrep_words_with_color is not None:
            iwords_to_color += igrep_words_with_color
        if ihighlight_words_with_color is not None:
            iwords_to_color += ihighlight_words_with_color

        line = highlight(line, words_to_color, ignore_case=False)
        line = highlight(line, iwords_to_color, ignore_case=True)

        if args.terminal_width != -1 or args.wrap_indent_width != 0:

            width = args.terminal_width
            if width == -1:
                try:
                    # Get the current terminal width
                    import fcntl
                    import termios
                    import struct
                    h, width = struct.unpack('hh', fcntl.ioctl(0, termios.TIOCGWINSZ, struct.pack('hh', 0, 0)))
                except:
                    width = 100
                    print_error('PLEASE SPECIFY TERMINAL WIDTH !!! It looks the script is running in pipe mode. '
                        'Please just provide \'--wrap=`tput cols`\' as an option')

            indent = args.wrap_indent_width
            lines = split_to_lines(line, width, 0, indent)
            linebuf = ('\n' + ' ' * indent).join(lines)
        else:
            linebuf = line

        sys.stdout.write(linebuf.encode('utf-8'))
    return 0


if empty(file_paths) or empty(file_paths[0]):
    run(sys.stdin, 'stdin')
else:
    for path in file_paths:
        if not empty(path):
            try:
                f = open(path, 'r')
            except (OSError, IOError) as e:
                print_error('Can\'t open file \'' + path + '\'!!')
                continue
            try:
                res = run(f, path)
                f.close()
            except KeyboardInterrupt:
                f.close()
                print(RESET + EOL + '\n')
                print('KeyboardInterrupt\n')
