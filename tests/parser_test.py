import pytest

from merge_config_plus import MCPLexer
from merge_config_plus import MCPParser

test_var_assign = [
    ("TEST=1", [("config", "TEST", "=", ("int", 1))]),
    ("TEST=0", [("config", "TEST", "=", ("int", 0))]),
    ("TEST=0x0", [("config", "TEST", "=", ("hex", 0))]),
    ("TEST=0xf", [("config", "TEST", "=", ("hex", 0xF))]),
    ("TEST=y", [("config", "TEST", "=", ("state", "y"))]),
    ("TEST=m", [("config", "TEST", "=", ("state", "m"))]),
    ("TEST=n", [("config", "TEST", "=", ("state", "n"))]),
    ("# TEST is not set", [("config", "TEST", "=", ("state", "n"))]),
    ("TEST='abc'", [("config", "TEST", "=", ("string", [("str", "abc")]))]),
    ("TEST=%(VAR1)", [("config", "TEST", "=", ("val", "VAR1"))]),
]

test_string = [
    (
        "S='a'.'b'.'c'",
        [("config", "S", "=", ("string", [("str", "a"), ("str", "b"), ("str", "c")]))],
    ),
    ("S=%(VAR).'a'.'b'", [()]),
    ("S=%'a'.%(VAR).'b'", [()]),
    ("S='a'.%(VAR)", [()]),
    ("S=%(func '')", [()]),
    ("S=%(func '').'abc'.%(VAR)", [()]),
    ("", [()]),
    ("", [()]),
    ("", [()]),
]

test_function = [
    ("%(func)", [()]),
    ("%(func '1')", [()]),
    ("%(func '1','2','3','4','5')", [()]),
    ("%(func %(VAR), %(func2 '1'), '3'.%(VAR2))", [()]),
]

test_define = [
    ("%(define 'chunk1') TEST1=y %(endef)", [()]),
]

test_condition = [
    ("", [()]),
    ("", [()]),
    ("", [()]),
    ("", [()]),
    ("", [()]),
    ("", [()]),
]

test_all = list()

test_all.extend(test_var_assign)
test_all.extend(test_string)
# test_all.extend(test_function)
# test_all.extend(test_define)
# test_all.extend(test_condition)
# test_all.extend()
# test_all.extend()
# test_all.extend()


@pytest.mark.parametrize("data,tarr", test_all)
def test_parser(data, tarr):
    lexer = MCPLexer()
    parser = MCPParser()

    ast = parser.parse(lexer.tokenize2(data))

    counter = 0
    for item in ast:
        assert item[:-1] == tarr[counter]
        counter += 1

    assert counter == len(tarr)
