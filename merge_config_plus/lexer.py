from .sly import Lexer

import re
import os
import sys
import logging
import pprint


class MCPLexer(Lexer):
    tokens = {
        INCLUDE,
        COMMENT,
        DEFINE,
        ENDEF,
        FUNC,
        IF,
        COMMA,
        CBRACKET,
        DOT,
        ELSE,
        ENDIF,
        VAR,
        ASSIGN,
        UNSET,
        STATE,
        INT,
        HEX,
        VAL,
        STRING,
    }

    def __init__(self):
        self.logger = logging.getLogger("mcp.lexer")
        self.includes = list()
        self.hierarchy = list()
        self.num_errors = 0

    def textAdd(self, text, path, comment=""):
        self.includes.append(tuple((text, 1, 0, os.path.abspath(path))))
        self.hierarchy.append(tuple((os.path.abspath(path), [], comment)))

    ignore = " \t"

    _re_include = (
        r"%\(\s*include\s*(\"([a-zA-Z0-9-_./]*)\"|\'([a-zA-Z0-9-_./]*)\')\s*\)"
    )

    @_(_re_include)
    def INCLUDE(self, t):
        m = re.match(self._re_include, t.value)
        if m.group(2) != None:
            t.value = m.group(2)
        else:
            t.value = m.group(3)

        if t.value[0] != "/":
            if self.file == "/":  # TODO
                self.logger.error(
                    "Append and prepend data can't have relative path includes"
                )
                self.num_errors += 1
                return t  # None
            t.value = os.path.join(os.path.dirname(self.file), t.value)

        # Skip if there will be recusrion
        if t.value == self.file:
            self.logger.error("'{file}' is recursive include".format(file=t.value))
            self.num_errors += 1
            return t  # None
        for include in self.includes:
            if include[3] == t.value:
                self.logger.error("'{file}' is recursive include:".format(file=t.value))
                self.num_errors += 1
                return None

        if os.path.isfile(t.value):
            if not self.hierarchyAdd(self.hierarchy, t.value, ""):
                self.logger.critical("Internal error!")
                exit(1)

            data = open(t.value, "r").read()
            # push current file with position right after include
            self.includes.append(tuple((self.text, self.lineno, self.index, self.file)))
            # push next file, that will be taken by tokenize2
            self.includes.append(tuple((data, 1, 0, t.value)))
            # force end tokenize
            self.index = len(self.text)
        else:
            self.logger.error("'{file}' doesn't exist".format(file=t.value))
            self.num_errors += 1
            return t  # None
        return t

    @_(r"(\?=|\+=|=\+|-=|=)")
    def ASSIGN(self, t):
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"[ymn]")
    def STATE(self, t):
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r",")
    def COMMA(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"\)")
    def CBRACKET(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"\.")
    def DOT(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    _re_unset = r"\#\s([A-Z][a-zA-Z0-9_]*)\sis\snot\sset"

    @_(_re_unset)
    def UNSET(self, t):
        t.value = re.match(self._re_unset, t.value).group(1)
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"0[xX][a-fA-F0-9][a-fA-F0-9]*")
    def HEX(self, t):
        t.value = int(t.value, 16)
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"-?[0-9]+")
    def INT(self, t):
        t.value = int(t.value, 10)
        self.logger.debug(pprint.pformat(t))
        return t

    _re_var = r"([A-Z][a-zA-Z0-9_]*)"

    @_(_re_var)
    def VAR(self, t):
        t.value = re.match(self._re_var, t.value).group(1)
        self.logger.debug(pprint.pformat(t))
        return t

    _re_val = r"%\(\s*([A-Z][a-zA-Z0-9_]*)\s*\)"

    @_(_re_val)
    def VAL(self, t):
        t.value = re.match(self._re_val, t.value).group(1)
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"(\"[^\"]*\"|\'[^\']*\')")
    def STRING(self, t):
        t.value = self.remove_quotes(t.value).replace("\\\n", "").replace("\\n", "\n")
        self.logger.debug(pprint.pformat(t))
        return t

    ### Conditional
    @_(r"%\(\s*else\s*\)")
    def ELSE(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"%\(\s*endif\s*\)")
    def ENDIF(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    _re_if = r"%\(\s*if(eq|neq)\s*"

    @_(_re_if)
    def IF(self, t):
        t.value = re.match(self._re_if, t.value).group(1)
        self.logger.debug(pprint.pformat(t))
        return t

    ## Define
    _re_define = r"%\(\s*define\s*(\"([a-zA-Z0-9_]*)\"|\'([a-zA-Z0-9_]*)\')\s*\)"

    @_(_re_define)
    def DEFINE(self, t):
        m = re.match(self._re_define, t.value)
        if m.group(2) != None:
            t.value = m.group(2)
        else:
            t.value = m.group(3)
        self.logger.debug(pprint.pformat(t))
        return t

    @_(r"%\(\s*endef\s*\)")
    def ENDEF(self, t):
        t.value = None
        self.logger.debug(pprint.pformat(t))
        return t

    ### Function
    _re_func = r"%\(\s*([a-z][a-z0-9_]*)"

    @_(_re_func)
    def FUNC(self, t):
        t.value = re.match(self._re_func, t.value).group(1)
        self.logger.debug(pprint.pformat(t))
        return t

    # Ignore comments from # untill \n
    @_(r"\#(.*)")
    def COMMENT(self, t):
        t.value = t.value[1:]
        self.logger.debug(pprint.pformat(t))
        return t

    # Ignored pattern
    ignore_newline = r"\n+"

    # Extra action for newlines
    def ignore_newline(self, t):
        self.lineno += t.value.count("\n")

    # Error handle TODO
    def error(self, t):
        self.logger.error("Illegal character '{char}'".format(char=t.value[0]))
        self.index += 1
        self.num_errors += 1

    # Misc
    def remove_quotes(self, text: str):
        if text.startswith('"') or text.startswith("'"):
            return text[1:-1]
        return text

    def hierarchyAdd(self, hierarchy, target, comment):
        for item in hierarchy:
            if item[0] == self.file:
                item[1].append(tuple((target, [], comment)))
                self.logger.debug(
                    "'{target}' added to '{parent}' hierarchy".format(
                        target=target, parent=item[0]
                    )
                )
                return True
            else:
                r = self.hierarchyAdd(item[1], target, comment)
                if r:
                    return True
        return False

    # Lexer's tokenize() wrapper
    def tokenize2(self, prepend="", append=""):
        if prepend:
            self.logger.debug("Added prepend data")
            self.includes.insert(0, tuple((prepend, 1, 0, "/")))

        if append:
            self.logger.debug("Added append data")
            self.includes.append(tuple((append, 1, 0, "/")))

        while len(self.includes) > 0:
            include = self.includes.pop()
            toks = self.tokenize(
                include[0], lineno=include[1], index=include[2], file=include[3]
            )
            while True:
                try:
                    tok = next(toks)
                    yield tok
                except StopIteration:
                    break
