from .sly import Parser
from .lexer import MCPLexer

import logging
import pprint


class MCPParser(Parser):
    tokens = MCPLexer.tokens

    def __init__(self):
        self.logger = logging.getLogger("mcp.parser")
        self.names = {}
        self.num_errors = 0

    ### Root rule
    @_("config", "if0", "include", "function", "comment", "define")
    def all(self, p):
        r = list()
        r.append(p[0])
        self.logger.debug("Added to 'all'")
        return r

    @_(
        "all config",
        "all if0",
        "all function",
        "all include",
        "all comment",
        "all define",
    )
    def all(self, p):
        r = p[0]
        r.append(p[1])
        self.logger.debug("Added to 'all'")
        return r

    ### Include
    @_("INCLUDE")
    def include(self, p):
        r = tuple(("include", str(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    ### Comment
    @_("COMMENT")
    def comment(self, p):
        r = tuple(("comment", str(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    ### Config
    @_("UNSET")
    def config(self, p):
        r = tuple(
            ("config", str(p[0]), "=", tuple(("state", "n")), tuple((p.lineno, p.file)))
        )
        self.logger.debug(pprint.pformat(r))
        return r

    @_(
        "VAR ASSIGN int",
        "VAR ASSIGN state",
        "VAR ASSIGN hex",
        "VAR ASSIGN function",
        "VAR ASSIGN val",
        "VAR ASSIGN string",
    )
    def config(self, p):
        r = tuple(("config", str(p[0]), str(p[1]), p[2], tuple((p.lineno, p.file))))
        self.logger.debug(pprint.pformat(r))
        return r

    ### Basic types
    @_("STATE")
    def state(self, p):
        r = tuple(("state", str(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("INT")
    def int(self, p):
        r = tuple(("int", int(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("HEX")
    def hex(self, p):
        r = tuple(("hex", int(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("VAL")
    def val(self, p):
        r = tuple(("val", str(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    ### String
    @_("STRING")
    def str(self, p):
        r = tuple(("str", str(p[0])))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("str")
    def string(self, p):
        r = tuple(("string", [p[0]]))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("str DOT", "function DOT", "val DOT")
    def string0(self, p):
        r = tuple(("string", [p[0]]))
        self.logger.debug("Added to 'string0'")
        return r

    @_("string0 str DOT", "string0 function DOT", "string0 val DOT")
    def string0(self, p):
        r = p[0]
        r[1].append(p[1])
        self.logger.debug("Added to 'string0'")
        return r

    @_("string0 str", "string0 function", "string0 val")
    def string(self, p):
        r = p[0]
        r[1].append(p[1])
        self.logger.debug("Added to 'string'")
        return r

    ### Function
    @_("FUNC")
    def function0(self, p):
        r = tuple(("func", str(p[0]), [], tuple((p.lineno, p.file))))
        self.logger.debug(pprint.pformat(r))
        return r

    @_("function0 string COMMA", "function0 val COMMA", "function0 function COMMA")
    def function0(self, p):
        r = p[0]
        r[2].append(p[1])
        self.logger.debug("Added to 'function0'")
        return r

    @_(
        "function0 string CBRACKET",
        "function0 val CBRACKET",
        "function0 function CBRACKET",
        "function0 CBRACKET",
    )
    def function(self, p):
        r = p[0]
        if len(p) == 3:
            r[2].append(p[1])
        self.logger.debug("Added to 'function'")
        return r

    ### Conditional
    @_("IF string COMMA", "IF val COMMA", "IF function COMMA")
    def ifcondition0(self, p):
        r = tuple(("if", str(p[0]), p[1]))
        self.logger.debug(pprint.pformat(r))
        return r

    @_(
        "ifcondition0 string CBRACKET",
        "ifcondition0 val CBRACKET",
        "ifcondition0 function CBRACKET",
    )
    def ifcondition(self, p):
        r = p[0] + tuple((p[1], [], []))
        self.logger.debug(pprint.pformat(r))
        return r

    @_(
        "ifcondition",
        "ifbranch config",
        "ifbranch function",
        "ifbranch if0",
        "ifbranch include",
        "ifbranch comment",
    )
    def ifbranch(self, p):
        r = p[0]
        if len(p) == 2:
            r[4].append(p[1])
        self.logger.debug("Added to 'ifbranch'")
        return r

    @_(
        "ifbranch ELSE",
        "else0 config",
        "else0 function",
        "else0 if0",
        "else0 include",
        "else0 comment",
    )
    def else0(self, p):
        r = p[0]
        if p[1]:
            r[5].append(p[1])
        self.logger.debug("Added to 'else0'")
        return r

    @_("else0 ENDIF", "ifbranch ENDIF")
    def if0(self, p):
        return p[0]

    ### Define
    @_("DEFINE")
    def define0(self, p):
        r = tuple(("define", str(p[0]), []))
        self.logger.debug(pprint.pformat(r))
        return r

    @_(
        "define0 config",
        "define0 function",
        "define0 if0",
        "define0 include",
        "define0 comment",
    )
    def define0(self, p):
        r = p[0]
        r[2].append(p[1])
        self.logger.debug("Added to 'define0'")
        return r

    @_("define0 ENDEF")
    def define(self, p):
        return p[0]

    def error(self, p):
        if p:
            self.logger.error(
                "Syntax error at {file}:{line}".format(line=p.lineno, file=p.file)
            )
            self.num_errors += 1
            # Just discard the token and tell the parser it's okay.
            self.errok()
        else:
            self.num_errors += 1
            self.logger.error("Syntax error at EOF")
