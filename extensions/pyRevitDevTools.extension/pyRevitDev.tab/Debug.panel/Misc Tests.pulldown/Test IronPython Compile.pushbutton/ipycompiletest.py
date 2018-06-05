class CompiledType(object):
    def __init__(self, message):
        print(message)


def compile_test(message):
    print(message)


compile_test("Compiled module level code works.")
