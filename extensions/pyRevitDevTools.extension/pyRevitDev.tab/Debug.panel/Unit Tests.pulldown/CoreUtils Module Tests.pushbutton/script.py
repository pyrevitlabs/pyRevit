"""Test Increment/Decrement Logic"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
from pyrevit import coreutils
from pyrevit import script

logger = script.get_logger()

TESTS = [
    # (step, tests)
    (1, [
        # (start str, result with refit, result wout refit)
        ("8", "9", "9"),
        ("9", "10", "0"),
        ("19", "20", "20"),
        ("99", "100", "00"),
        ("Y", "Z", "Z"),
        ("Z", "AA", "A"),
        ("ZZ", "AAA", "AA"),
        ("A1.13a", "A1.13b", "A1.13b"),
        ("S2.00Z", "S2.01A", "S2.01A"),
        ("99.Z", "100.A", "00.A"),
    ]),

    (2, [
        ("8", "10", "0"),
        ("9", "11", "1"),
        ("18", "20", "20"),
        ("99", "101", "01"),
    ]),

    (200, [
        ("8", "208", "8"),
    ]),
]


for shft in TESTS:
    step = shft[0]
    tests = shft[1]
    for test in tests:
        # test both refit options
        for fit in [False, True]:
            start = test[0]
            expected = test[1 if fit else 2]
            # test increment
            end = coreutils._inc_or_dec_string(
                str_id=start,
                shift=step,
                refit=fit,
                logger=logger)
            print("{result} {start} --{step}--> {end}={expected}".format(
                result=u"\u2713" if end == expected else " ",
                start=start,
                end=end,
                expected=expected,
                step=('[{}]' if fit else '{}').format(step)
                ))
            # test decrement
            end = coreutils._inc_or_dec_string(
                str_id=expected,
                shift=-step,
                refit=fit,
                logger=logger)
            print("{result} {expected}={end} <--{step}-- {start}".format(
                result=u"\u2713" if end == start else " ",
                start=expected,
                end=end,
                expected=start,
                step=('[{}]' if fit else '{}').format(step)
                ))
