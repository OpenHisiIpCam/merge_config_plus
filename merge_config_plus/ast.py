from .lexer import MCPLexer
from .parser import MCPParser
from .format import MCPFormat

import os
import io
import subprocess
from subprocess import PIPE
from packaging.version import Version
import difflib
import logging
import pprint


class MCPAst:
    def __init__(self):
        self.logger = logging.getLogger("mcp.ast")
        self.reset()

    def reset(self):
        self.configs = list()
        self.defines = dict()
        self.num_errors = 0

    def configAdd(self, name, typ, value, lineno, file):
        for item in self.configs:
            if item[0] == "config" and item[1] == name:
                if item[2][-1][0] != typ:
                    self.logger.warning(
                        "{name} rewrited with type change ({old}->{new})".format(
                            name=name, old=item[2][-1][0], new=typ
                        )
                    )
                    self.num_errors += 1
                else:
                    self.logger.debug("Rewrited in configs:")

                new = tuple((str(typ), value, lineno, file))
                item[2].append(new)
                self.logger.debug(pprint.pformat(new))
                return

        append = tuple(("config", str(name), [tuple((str(typ), value, lineno, file))]))
        self.configs.append(append)
        self.logger.debug("Added to configs as config:")
        self.logger.debug(pprint.pformat(append))

    def configAddComment(self, comment):
        append = tuple(("comment", comment))
        self.configs.append(append)
        self.logger.debug("Added to configs as comment:")
        self.logger.debug(pprint.pformat(append))

    # third return param is config item exist in list or not
    def configValue(self, name, strict=True):
        r = None

        for item in self.configs:
            if item[0] == "config" and item[1] == name:
                tmp = item[2][-1]
                r = tuple((str(tmp[1]), str(tmp[0]), True))
                break

        if not r:
            r = "", "string", False
            # sometimes we care, sometimes not
            if strict:
                self.num_errors += 1
                self.logger.error("Can`t get value for '{var}'".format(var=name))

        self.logger.debug(r)

        return r

    # Functions

    # input text...
    def func_process(self, args, line, file):
        self.logger.debug("func_process:")
        self.logger.debug(pprint.pformat(args))

        base_dir = os.path.abspath(os.path.dirname(file))

        lexer = MCPLexer()
        parser = MCPParser()
        ast = MCPAst()

        text = ""
        for arg in args:
            text += arg + "\n"

        lexer.textAdd(text, os.path.abspath(file), "config that invoke supbrocess")

        self.logger.info("Process function starting sub processing...")
        ast.configAdd("LOCAL_BASE", "string", base_dir, 0, "/")
        ast.configAdd("LOCAL_TMP", "string", base_dir, 0, "/")
        
        local_generated, _, local_generated_exist = self.configValue("LOCAL_GENERATED")
        if local_generated_exist == False:
            local_generated = base_dir
        ast.configAdd("LOCAL_GENERATED", "string", local_generated, 0, "/")

        ast.process(parser.parse(lexer.tokenize2()))
        self.logger.info("Process function finished")

        num_errors = 0
        num_errors += lexer.num_errors
        num_errors += parser.num_errors
        num_errors += ast.num_errors

        if num_errors > 0:
            self.logger.warning("Sub processing finished, but there were {num} errors/warnings!".format(num=num_errors))
            self.num_errors += 1
        else:
            fake_file = io.StringIO()

            format = MCPFormat(fake_file, base_dir)
            format.output(ast.configs)

            return fake_file.getvalue().strip()

    def do_format(self, s, **kwargs):
        """Replaces missing keys with a pattern."""
        RET = "{{{}}}"
        try:
            return s.format(**kwargs)
        except KeyError as e:
            keyname = e.args[0]
            self.logger.warning(
                "Var '{key}' required by template, but not provided".format(key=keyname)
            )
            self.num_errors += 1
            return self.do_format(s, **{keyname: RET.format(keyname)}, **kwargs)

    # * template
    # * templating vars
    # * templating vars...
    def func_format(self, args, line, file):
        self.logger.debug("func_format:")
        self.logger.debug(pprint.pformat(args))

        template = ""
        raw = ""

        if len(args) > 0:
            template = args[0]

        for item in args[1:]:
            raw += item + "\n"

        lines = raw.splitlines()
        vars = dict()
        for line0 in lines:
            splited = line0.strip().split("=")
            if len(splited) != 2:
                self.logger.error(
                    "Format function can`t parse '{line0}' on {file}:{line}".format(
                        line0=line0, line=line, file=file
                    )
                )
                self.num_errors += 1
                continue
            vars[splited[0]] = str(splited[1]).strip()

        return self.do_format(template, **vars)

    def func_shell(self, args, line, file):
        self.logger.debug("func_shell:")
        self.logger.debug(pprint.pformat(args))

        if len(args) < 1:
            self.logger.error(
                "Shell function requires at least one argument on {file}:{line}".format(
                    line=line, file=file
                )
            )
            self.num_errors += 1
            return ""

        if args[0].strip() == "":
            self.logger.error(
                "Shell invoke to empty cmd on {file}:{line}".format(
                    line=line, file=file
                )
            )
            self.num_errors += 1
            return ""

        try:
            result = subprocess.run(
                args, timeout=5, stdout=PIPE, stderr=PIPE, check=False
            )

            if result.returncode != 0:
                self.logger.error(
                    "Shell '{name}' returns error {ret} on {file}:{line}".format(
                        name=args[0], ret=result.returncode, line=line, file=file
                    )
                )
                if result.stderr:
                    self.logger.error("Stderr below:")
                    for line in result.stderr.splitlines():
                        self.logger.error(line)
                    self.logger.error("-----")
                self.num_errors += 1

            return result.stdout
        except FileNotFoundError:
            self.logger.error(
                "Shell cmd '{name}' not found on {file}:{line}".format(
                    name=args[0], line=line, file=file
                )
            )
            self.num_errors += 1
        except subprocess.CalledProcessError as e:
            self.logger.critical("func_shell: internal error!")
            self.num_errors += 1
            print(e)
            exit(1)
        except Exception as e:
            self.logger.critical("func_shell: internal error!")
            self.num_errors += 1
            print(e)
            exit(1)

        return ""

    def func_strip(self, args, line, file):
        self.logger.debug("func_strip:")
        self.logger.debug(pprint.pformat(args))

        str = ""
        for arg in args:
            str += arg
        return str.strip()

    def func_diff(self, args, line, file):  # TODO
        self.logger.debug("func_diff:")
        self.logger.debug(pprint.pformat(args))

        if len(args) < 2:
            self.logger.error(
                "Diff function not enough arguments on {file}:{line}".format(
                    line=line, file=file
                )
            )
            self.num_errors += 1
            return ""

        # TODO maybe filter --- +++
        return "".join(
            list(difflib.unified_diff(args[0].split("\n"), args[1].split("\n"), n=6))
        )

    def func_call(self, args, line, file):
        self.logger.debug("func_call:")
        self.logger.debug(pprint.pformat(args))

        for arg in args:
            name = arg.strip()
            if name == "":
                self.logger.error(
                    "Call to unnamed define is ambiguous on {file}:{line}".format(
                        line=line, file=file
                    )
                )
                self.num_errors += 1
                continue

            if name in self.defines:
                self.ast_root(self.defines[name])
            else:
                self.logger.error(
                    "Call to unknown define '{define}' on {file}:{line}".format(
                        line=line, file=file, define=name
                    )
                )
                self.num_errors += 1
                continue

        return ""

    def func_file(self, args, line, file):
        self.logger.debug("func_file:")
        self.logger.debug(pprint.pformat(args))

        base_dir = os.path.dirname(file)

        r = ""

        for arg in args:
            if arg[0] == "/":
                path = arg
            else:
                path = base_dir + "/" + arg

            try:
                f = open(path, "r")
                r += f.read()
                f.close()
            except Exception as e:
                self.logger.error(
                    "{msg} on {file}:{line}".format(msg=e, line=line, file=file)
                )
                self.num_errors += 1

        return r

    def func_save(self, args, line, file):
        self.logger.debug("func_save:")
        self.logger.debug(pprint.pformat(args))

        base_dir = os.path.dirname(file)

        if len(args) < 1:
            self.logger.error(
                "Save function output file not set on {file}:{line}".format(
                    msg=e, line=line, file=file
                )
            )
            self.num_errors += 1
            return ""

        if len(args[0].strip()) == 0:
            self.logger.error(
                "Save function output file name empty on {file}:{line}".format(
                    msg=e, line=line, file=file
                )
            )
            self.num_errors += 1
            return ""

        if args[0][0] == "/":
            path = args[0]
        else:
            path = base_dir + "/" + args[0]
    
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            f = open(path, "w")
        except Exception as e:
            self.logger.error(
                "{msg} on {file}:{line}".format(msg=e, line=line, file=file)
            )
            self.num_errors += 1

        for arg in args[1:]:
            f.write(arg)

        f.close()

        return os.path.abspath(path)

    def func_fail(self, args, line, file):
        self.logger.debug("func_fail:")
        self.logger.debug(pprint.pformat(args))
        msg=""
        for arg in args:
            msg += msg + arg
        self.logger.critical("{msg} on {file}:{line}".format(msg=msg.strip(), line=line, file=file))
        return ""

    def func_comment(self, args, line, file):
        self.logger.debug("func_comment:")
        self.logger.debug(pprint.pformat(args))
        msg=""
        for arg in args:
            msg += msg + arg
        self.configAddComment(msg)
        return msg

    def func_major(self, args, line, file):
        self.logger.debug("func_major:")
        self.logger.debug(pprint.pformat(args))
        if len(args) < 1:
            self.logger.error(
                "Major function expect one arg {file}:{line}".format(
                    msg=e, line=line, file=file
                )
            )
            self.num_errors += 1
            return ""
        try:
            ver = Version(args[0])
            return str(ver.major)
        except Exception as e:
            self.logger.error("func_major: can't parse version string!")
            self.num_errors += 1
        return ""

    def func_minor(self, args, line, file):
        self.logger.debug("func_minor:")
        self.logger.debug(pprint.pformat(args))
        if len(args) < 1:
            self.logger.error(
                "Minor function expect one arg {file}:{line}".format(
                    msg=e, line=line, file=file
                )
            )
            self.num_errors += 1
            return ""
        try:
            ver = Version(args[0])
            return str(ver.minor)
        except Exception as e:
            self.logger.error("func_minor: can't parse version string!")
            self.num_errors += 1
        return ""

    def func_patch(self, args, line, file):
        self.logger.debug("func_patch:")
        self.logger.debug(pprint.pformat(args))
        if len(args) < 1:
            self.logger.error(
                "Patch function expect one arg {file}:{line}".format(
                    msg=e, line=line, file=file
                )
            )
            self.num_errors += 1
            return ""
        try:
            ver = Version(args[0])
            return str(ver.patch)
        except Exception as e:
            self.logger.error("func_patch: can't parse version string!")
            self.num_errors += 1
        return ""

    def func_relpath(self, args, line, file):
        self.logger.debug("func_relpath:")
        self.logger.debug(pprint.pformat(args))
        # TODO params check
        return os.path.relpath(args[0], start=args[1])

    # Ast processing

    def ast_root(self, items):
        self.logger.debug("ast_root:")

        if items == None:
            return

        for item in items:
            self.logger.debug(pprint.pformat(item))
            if item[0] == "include":
                continue
            elif item[0] == "define":
                self.ast_define(item)
            elif item[0] == "comment":
                self.configAddComment(item[1])
            elif item[0] == "config":
                self.ast_config(item)
            elif item[0] == "func":
                self.ast_func(item)
            elif item[0] == "if":
                self.ast_if(item)
            else:
                self.logger.critical("ast_root: unknown item!")
                exit(1)

    def ast_define(self, item):
        self.logger.debug("ast_define:")
        self.logger.debug(pprint.pformat(item))

        if item[1] in self.defines:
            self.logger.warning("define redefine TODO")
            self.num_errors += 1

        self.defines[item[1]] = item[2]

    def ast_config(self, item):
        self.logger.debug("ast_config:")
        self.logger.debug(pprint.pformat(item))

        t = item[3]

        val = ""
        typ = ""

        if t[0] == "state":
            val = t[1]
            typ = "state"
        elif t[0] == "string":
            val = self.ast_string(t)
            typ = "string"
        elif t[0] == "int":
            val = t[1]
            typ = "int"
        elif t[0] == "hex":
            val = t[1]
            typ = "hex"
        elif t[0] == "val":
            val, typ = self.ast_val(t)
        elif t[0] == "func":
            val = self.ast_func(t)
            typ = "string"
        else:
            self.logger.critical("ast_config: uknown item!")
            exit(1)

        if item[2] == "=":
            val
            typ
        elif item[2] == "?=":
            _, _, exist = self.configValue(item[1], strict=False)
            if exist == True:
                # dont save var if already exist
                return
            val
            typ
        elif item[2] in ["+=", "=+", "-="]:
            # strict false -> don`t warn if var is not exist
            cval, ctyp, _ = self.configValue(item[1], strict=False)
            if ctyp != "string":
                cval = str(cval)
            if typ != "string":
                val = str(val)

            if item[2] == "+=":
                val = cval + val
                typ = "string"
            elif item[2] == "=+":
                val = val + cval
                typ = "string"
            elif item[2] == "-=":
                val = cval.replace(val, "")
                typ = "string"
        else:
            self.logger.critical(
                "ast_config: uknown operation '{op}'!".format(op=item[2])
            )
            exit(1)

        self.configAdd(item[1], typ, val, item[4][0], item[4][1])

    def ast_val(self, item):
        self.logger.debug("ast_val:")
        self.logger.debug(pprint.pformat(item))
        val, typ, _ = self.configValue(item[1])
        return val, typ

    def ast_string(self, item):
        self.logger.debug("ast_string:")
        self.logger.debug(pprint.pformat(item))

        str0 = ""
        for part in item[1]:
            if part[0] == "str":
                str0 += part[1]
            elif part[0] == "val":
                val, _ = self.ast_val(part)
                str0 += str(val)
            elif part[0] == "func":
                str0 += self.ast_func(part)
            else:
                self.logger.critical("ast_string: unknown item!")
                exit(1)

        self.logger.debug("ast_string final:")
        self.logger.debug(pprint.pformat(str0))
        return str0

    def ast_if(self, item):
        self.logger.debug("ast_if:")
        self.logger.debug(pprint.pformat(item))

        left = self.ast_if_cond(item[2])
        right = self.ast_if_cond(item[3])

        branch = None

        if item[1] == "eq":
            if left == right:
                branch = 4
            else:
                branch = 5
        elif item[1] == "neq":
            if left == right:
                branch = 5
            else:
                branch = 4
        else:
            self.logger.critical("ast_if: internal error!")
            exit(1)

        self.ast_root(item[branch])

    def ast_if_cond(self, item):
        self.logger.debug("ast_if_cond:")
        self.logger.debug(pprint.pformat(item))

        if item[0] == "string":
            return self.ast_string(item)
        elif item[0] == "val":
            val, _ = self.ast_val(item)
            return str(val)
        elif item[0] == "func":
            return self.ast_func(item)
        else:
            self.logger.critical("ast_if_cond: internal error!")
            exit(1)

        return ""

    def ast_func(self, item):
        self.logger.debug("ast_func:")
        self.logger.debug(pprint.pformat(item))

        args = list()

        for arg in item[2]:
            if arg[0] == "string":
                r = self.ast_string(arg)
            elif arg[0] == "val":
                r, _ = self.ast_val(arg)
            elif arg[0] == "func":
                r = self.ast_func(arg)
            else:
                self.logger.critical("ast_func: internal error!")
                exit(1)

            args.append(str(r))

        line = item[3][0]
        file = item[3][1]

        r = ""

        if item[1] == "process":
            r = self.func_process(args, line, file)
        elif item[1] == "format":
            r = self.func_format(args, line, file)
        elif item[1] == "shell":
            r = self.func_shell(args, line, file)
        elif item[1] == "strip":
            r = self.func_strip(args, line, file)
        elif item[1] == "diff":
            r = self.func_diff(args, line, file)
        elif item[1] == "call":
            r = self.func_call(args, line, file)
        elif item[1] == "file":
            r = self.func_file(args, line, file)
        elif item[1] == "save":
            r = self.func_save(args, line, file)
        elif item[1] == "fail":
            r = self.func_fail(args, line, file)
        elif item[1] == "comment":
            r = self.func_comment(args, line, file)
        elif item[1] == "major":
            r = self.func_major(args, line, file)
        elif item[1] == "minor":
            r = self.func_minor(args, line, file)
        elif item[1] == "patch":
            r = self.func_patch(args, line, file)
        elif item[1] == "relpath":
            r = self.func_relpath(args, line, file)
        else:
            self.logger.error(
                "Function '{name}' not found on {file}:{line}".format(
                    name=item[1], file=file, line=line
                )
            )
            self.num_errors += 1

        return r

    def process(self, ast):
        self.ast_root(ast)
