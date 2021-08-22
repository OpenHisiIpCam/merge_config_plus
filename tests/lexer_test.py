import pytest

from merge_config_plus import MCPLexer


def check_token(token, typ, val):
    assert token.type == typ
    assert token.value == val


test_var = [
    ("A", [("VAR", "A")]),
    ("ABC", [("VAR", "ABC")]),
    ("ABC_ABC", [("VAR", "ABC_ABC")]),
    ("Aa", [("VAR", "Aa")]),
    ("ABC_abc", [("VAR", "ABC_abc")]),
    ("Abc_ABC", [("VAR", "Abc_ABC")]),
    ("AbCd", [("VAR", "AbCd")]),
]

test_comment = [
    ("#123", [("COMMENT", "123")]),
    ("###", [("COMMENT", "##")]),
    ("# ssss", [("COMMENT", " ssss")]),
]

test_int = [
    ("1", [("INT", 1)]),
    ("-1", [("INT", -1)]),
    ("090909", [("INT", 90909)]),
    ("-010101", [("INT", -10101)]),
    ("1234567890", [("INT", 1234567890)]),
    ("-1234567890", [("INT", -1234567890)]),
]

test_hex = [
    ("0x0", [("HEX", 0x0)]),
    ("0x1a", [("HEX", 0x1A)]),
    ("0xffff", [("HEX", 0xFFFF)]),
    ("0X0", [("HEX", 0x0)]),
    ("0X11", [("HEX", 0x11)]),
    ("0XFFFF", [("HEX", 0xFFFF)]),
]

test_string = [
    ("'abc'", [("STRING", "abc")]),
    ("'a\"b\"c'", [("STRING", 'a"b"c')]),
    ("'abc  abc'", [("STRING", "abc  abc")]),
    (
        """'abc
abc'""",
        [("STRING", "abc\nabc")],
    ),
    (
        """'abc\
abc'""",
        [("STRING", "abcabc")],
    ),
    ('"abc"', [("STRING", "abc")]),
    ("\"a'b'c\"", [("STRING", "a'b'c")]),
    ('"abc  abc"', [("STRING", "abc  abc")]),
    (
        '''"abc
abc"''',
        [("STRING", "abc\nabc")],
    ),
    (
        '''"abc\
abc"''',
        [("STRING", "abcabc")],
    ),
    (
        "'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&()*+,-./:;<=>?@[\\]^_`{|}~'",
        [
            (
                "STRING",
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&()*+,-./:;<=>?@[\\]^_`{|}~",
            )
        ],
    ),
    (
        '"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&()*+,-./:;<=>?@[\\]^_`{|}~"',
        [
            (
                "STRING",
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!#$%&()*+,-./:;<=>?@[\\]^_`{|}~",
            )
        ],
    ),
]

test_state = [
    ("y", [("STATE", "y")]),
    ("m", [("STATE", "m")]),
    ("n", [("STATE", "n")]),
]

test_assign = [
    ("=", [("ASSIGN", "=")]),
    ("+=", [("ASSIGN", "+=")]),
    ("=+", [("ASSIGN", "=+")]),
    ("-=", [("ASSIGN", "-=")]),
    ("?=", [("ASSIGN", "?=")]),
]

test_unset = [
    ("# TEST is not set", [("UNSET", "TEST")]),
    ("# Test is not set", [("UNSET", "Test")]),
    ("# TEST_ABC is not set", [("UNSET", "TEST_ABC")]),
    ("# Test_ABC is not set", [("UNSET", "Test_ABC")]),
    ("# Test_test is not set", [("UNSET", "Test_test")]),
]

test_val = [
    ("%(TEST)", [("VAL", "TEST")]),
    ("%(TEST_TEST)", [("VAL", "TEST_TEST")]),
    ("%(Test)", [("VAL", "Test")]),
    ("%(Test_TEST)", [("VAL", "Test_TEST")]),
    ("%(Test_test)", [("VAL", "Test_test")]),
    ("%(  TEST  )", [("VAL", "TEST")]),
    ("%( TEST_TEST)", [("VAL", "TEST_TEST")]),
    ("%(TEST   )", [("VAL", "TEST")]),
]

test_function = [
    ("%(func", [("FUNC", "func")]),
    ("%(   func", [("FUNC", "func")]),
    ("%(  func123   ", [("FUNC", "func123")]),
]

test_define = [
    ('%(define "aBc")', [("DEFINE", "aBc")]),
    ('%(  define "")', [("DEFINE", "")]),
    ('%(define  "BCab" )', [("DEFINE", "BCab")]),
    ('%(  define "123" )', [("DEFINE", "123")]),
    ("%(define 'aBcD')", [("DEFINE", "aBcD")]),
    ("%(  define '')", [("DEFINE", "")]),
    ("%(  define ''   )", [("DEFINE", "")]),
    ("%(endef)", [("ENDEF", None)]),
    ("%(  endef)", [("ENDEF", None)]),
    ("%(endef  )", [("ENDEF", None)]),
    ("%(   endef   )", [("ENDEF", None)]),
]

test_conditional = [
    ("%(ifeq", [("IF", "eq")]),
    ("%(ifneq", [("IF", "neq")]),
    ("%(else)", [("ELSE", None)]),
    ("%(  else)", [("ELSE", None)]),
    ("%(else  )", [("ELSE", None)]),
    ("%(   else   )", [("ELSE", None)]),
    ("%(endif)", [("ENDIF", None)]),
    ("%(  endif)", [("ENDIF", None)]),
    ("%(endif   )", [("ENDIF", None)]),
    ("%(   endif  )", [("ENDIF", None)]),
]

test_include = [
    ("%(include '/abc_1234/TEST.1')", [("INCLUDE", "/abc_1234/TEST.1")]),
    ("%(   include     'abc_1234/TEST.1'   )", [("INCLUDE", "abc_1234/TEST.1")]),
    ('%(include "./test123")', [("INCLUDE", "./test123")]),
    (
        '%(   include     "/soma/path/file.txt"   )',
        [("INCLUDE", "/soma/path/file.txt")],
    ),
]

test_misc = [
    (",", [("COMMA", None)]),
    (".", [("DOT", None)]),
    (")", [("CBRACKET", None)]),
]

test_all = list()
test_all.extend(test_var)
test_all.extend(test_comment)
test_all.extend(test_int)
test_all.extend(test_hex)
test_all.extend(test_string)
test_all.extend(test_state)
test_all.extend(test_assign)
test_all.extend(test_unset)
test_all.extend(test_val)
test_all.extend(test_function)
test_all.extend(test_define)
test_all.extend(test_conditional)
test_all.extend(test_include)
test_all.extend(test_misc)


@pytest.mark.parametrize("data,tarr", test_all)
def test_token(data, tarr):
    lexer = MCPLexer()

    counter = 0
    for tok in lexer.tokenize2(data):
        check_token(tok, tarr[counter][0], tarr[counter][1])
        counter += 1

    assert counter == len(tarr)
