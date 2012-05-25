"""
testkit.data
~~~~~~~~~~~~

Various Data Test Tools
"""
import random

NUMBERS = "0123456789"
SYMBOLS = """!@#$%^&*()_+=-[]\;',./{}|:"<>?~`"""
ALPHAS_LOWER = "abcdefghijklmnopqrstuvwxyz"
ALPHAS_UPPER = ALPHAS_LOWER.upper()
ALL_ALPHAS = ALPHAS_LOWER + ALPHAS_UPPER
ALPHA_NUMERIC = ALL_ALPHAS + NUMBERS
ALL_CHARS = SYMBOLS + ALPHA_NUMERIC

def random_string(length, chars=ALL_CHARS):
    """Generates a random string of length"""
    array = []
    for i in xrange(length):
        c = random.choice(chars)
        array.append(c)
    return "".join(array)

def dict_to_object(d):
    return type('DictAsObject', (object,), d)
    
