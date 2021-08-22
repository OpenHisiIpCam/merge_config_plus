from .lexer import MCPLexer
from .parser import MCPParser
from .ast import MCPAst
from .format import MCPFormat

from . import __version__
from . import __url__
from . import __license__

import argparse
import os
import sys

import pprint
import logging

# Logger
class CustomFormatter(logging.Formatter):
    white = "\033[36;1m"
    grey = "\033[37;1m"
    yellow = "\033[33;1m"
    red = "\033[31;1m"
    bold_red = "\033[41;1m"
    reset = "\033[0m"

    format = "%(name)s [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: white + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def hierarchy_print(items, base_dir, level=0):
    # first level is stored in revetsed order
    if level == 0:
        files = items[::-1]
    else:
        files = items

    for item in files:
        f = os.path.relpath(item[0], start=base_dir)
        if item[2] != "":
            print(
                "#" + "".join(level * "  "), "*", f, "(", item[2], ")", file=args.output
            )
        else:
            print("#" + "".join(level * "  "), "*", f, file=args.output)
        hierarchy_print(item[1], base_dir, level + 1)


def hierarchy_flat(items, base_dir):
    r = list()
    for item in items:
        f = os.path.relpath(item[0], start=base_dir)
        r.append(f)
        r.extend(hierarchy_flat(item[1], base_dir))
    return r


# Cmd options
argparser = argparse.ArgumentParser(
    prog="merge_config_plus.py",
    description="Kconfig preprocessor {version} license {license} ({url}).".format(
        version=__version__, url=__url__, license=__license__
    ),
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

argparser.add_argument(
    "-v",
    "--version",
    action="version",
    version="%(prog)s {version}".format(version=__version__),
)

argparser.add_argument("-d", "--debug", action="store_true", help="Show debug log")

argparser.add_argument(
    "--mode",
    choices=["normal", "debug-lexer", "debug-parser", "dependencies"],
    default="normal",
    help="debug modes",
)

argparser.add_argument(
    "-o", "--output", type=argparse.FileType("w"), default="-", help="output to file"
)
argparser.add_argument(
    "-t",
    "--tmp-dir",
    type=str,
    help="temporary dir TODO",
)
argparser.add_argument(
    "-b",
    "--base-dir",
    type=str,
    help="base dir TODO",
)
argparser.add_argument(
    "-f",
    "--files",
    metavar="F",
    type=argparse.FileType("r"),
    nargs="+",
    help="input files list",
)
argparser.add_argument(
    "-a",
    "--append",
    type=str,
    default="",
    help="data as string, append after files",
)
argparser.add_argument(
    "-p",
    "--prepend",
    type=str,
    default="",
    help="data as string, prepend before files",
)
argparser.add_argument(
    "--strip-history", action="store_true", help="Drop detailed var history from output"
)

args = argparser.parse_args()

logger = logging.getLogger("mcp")
ch = logging.StreamHandler()
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

if args.debug:
    logger.setLevel(logging.DEBUG)
    ch.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)
    ch.setLevel(logging.INFO)

lexer = MCPLexer()
parser = MCPParser()

interactive = True

if args.files and len(args.files) > 0:
    # files should be added in reversed order
    for file in args.files[::-1]:
        text = file.read()
        lexer.textAdd(text, os.path.abspath(file.name), "from cmd line")
        logger.debug("File '{path}' added".format(path=file.name))
    interactive = False

if args.mode == "debug-lexer":
    if not interactive:
        pprint.PrettyPrinter().pprint(
            list(lexer.tokenize2(prepend=args.prepend, append=args.append))
        )

    else:
        print("Press CTRL+D to exit")

        while True:
            try:
                text = input("lexer > ")
            except EOFError:
                break
            if text:
                pprint.PrettyPrinter().pprint(list(lexer.tokenize(text)))
        print("")
    exit(0)

if args.mode == "debug-parser":
    if not interactive:
        ast = parser.parse(lexer.tokenize2(prepend=args.prepend, append=args.append))
        pprint.PrettyPrinter().pprint(ast)
    else:
        print("Press CTRL+D to exit")

        while True:
            try:
                text = input("parser > ")
            except EOFError:
                break
            if text:
                ast = parser.parse(lexer.tokenize(text))
                pprint.PrettyPrinter().pprint(ast)
        print("")
    exit(0)

if args.files and len(args.files) == 0:
    print("No input")
    exit(1)

if args.base_dir:
    base_dir = os.path.abspath(args.base_dir)
else:
    # if not set, than same as first input file dir
    base_dir = os.path.dirname(os.path.abspath(args.files[0].name))

if args.tmp_dir:
    tmp_dir = os.path.abspath(args.tmp_dir)
else:
    tmp_dir = base_dir

if args.mode == "dependencies":
    # list needed, as tokenize2() returns generator
    list(lexer.tokenize2(prepend=args.prepend, append=args.append))
    deps = hierarchy_flat(lexer.hierarchy, base_dir)
    print(" ".join(deps))
    exit(0)

# Normal mode
ast = MCPAst()

ast.configAdd("LOCAL_BASE", "string", base_dir, 0, "/")
ast.configAdd("LOCAL_TMP", "string", tmp_dir, 0, "/")

ast.process(parser.parse(lexer.tokenize2(prepend=args.prepend, append=args.append)))

# Output
print("# This file was generated by merge_config_plus", file=args.output)

if True:
    print("# Files include structure:", file=args.output)
    if args.prepend:
        print("# *", "prepend data", file=args.output)
    hierarchy_print(lexer.hierarchy, base_dir)
    if args.append:
        print("# *", "append data", file=args.output)
    print("", file=args.output)

strip_prev = False
if args.strip_history:
    strip_prev = True

format = MCPFormat(args.output, base_dir, strip_prev=strip_prev)
format.output(ast.configs)

num_errors = 0
num_errors += lexer.num_errors
num_errors += parser.num_errors
num_errors += ast.num_errors

if num_errors > 0:
    logger.warning(
        "Processing to '{out}' done, but there were {num} warnings/errors".format(
            out=args.output.name, num=num_errors
        )
    )
    exit(1)
else:
    logger.info("Processing to '{out}' done".format(out=args.output.name))
    exit(0)
