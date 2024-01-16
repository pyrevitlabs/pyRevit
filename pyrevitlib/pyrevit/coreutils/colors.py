#pylint: disable=C0302
"""Colors constants.

Provide RGB color constants and a colors dictionary with
elements formatted: COLORS[colorname] = CONSTANT.

Examples:
    ```python
    from pyrevit.coreutils import colors
    colors.COLORS['black']
    ```
    <RGB #000000>
    ```python
    colors.BLACK
    ```
    <RGB #000000>

"""
from collections import OrderedDict


class RGB(object):
    """RGB named color object.

    Attributes:
        name (str): color name
        red (int): value for red component (0-255)
        green (int): value for green component (0-255)
        blue (int): value for blue component (0-255)
    """
    def __init__(self, name='default', red=0, green=0, blue=0):
        self.name = name
        self.red, self.green, self.blue = red, green, blue

    def __str__(self):
        return self.hex_color

    def __repr__(self):
        return '<RGB {}>'.format(self.hex_color)

    @property
    def hex_color(self):
        """Return color in hex format."""
        return '#{:02X}{:02X}{:02X}'.format(self.red, self.green, self.blue)

    @property
    def luminance(self):
        """Return color luminance (preceived)."""
        return 0.299*self.red + 0.587*self.green + 0.114*self.blue

    @property
    def safe_text_color(self):
        """Return text color that is safe to overlap this color."""
        return '#FFFFFF' if self.luminance < 128 else '#000000'


COLORS = {}


# color consts
ALICEBLUE = RGB(name='aliceblue', red=240, green=248, blue=255)
ANTIQUEWHITE = RGB(name='antiquewhite', red=250, green=235, blue=215)
ANTIQUEWHITE1 = RGB(name='antiquewhite1', red=255, green=239, blue=219)
ANTIQUEWHITE2 = RGB(name='antiquewhite2', red=238, green=223, blue=204)
ANTIQUEWHITE3 = RGB(name='antiquewhite3', red=205, green=192, blue=176)
ANTIQUEWHITE4 = RGB(name='antiquewhite4', red=139, green=131, blue=120)
AQUA = RGB(name='aqua', red=0, green=255, blue=255)
AQUAMARINE1 = RGB(name='aquamarine1', red=127, green=255, blue=212)
AQUAMARINE2 = RGB(name='aquamarine2', red=118, green=238, blue=198)
AQUAMARINE3 = RGB(name='aquamarine3', red=102, green=205, blue=170)
AQUAMARINE4 = RGB(name='aquamarine4', red=69, green=139, blue=116)
AZURE1 = RGB(name='azure1', red=240, green=255, blue=255)
AZURE2 = RGB(name='azure2', red=224, green=238, blue=238)
AZURE3 = RGB(name='azure3', red=193, green=205, blue=205)
AZURE4 = RGB(name='azure4', red=131, green=139, blue=139)
BANANA = RGB(name='banana', red=227, green=207, blue=87)
BEIGE = RGB(name='beige', red=245, green=245, blue=220)
BISQUE1 = RGB(name='bisque1', red=255, green=228, blue=196)
BISQUE2 = RGB(name='bisque2', red=238, green=213, blue=183)
BISQUE3 = RGB(name='bisque3', red=205, green=183, blue=158)
BISQUE4 = RGB(name='bisque4', red=139, green=125, blue=107)
BLACK = RGB(name='black', red=0, green=0, blue=0)
BLANCHEDALMOND = RGB(name='blanchedalmond', red=255, green=235, blue=205)
BLUE = RGB(name='blue', red=0, green=0, blue=255)
BLUE2 = RGB(name='blue2', red=0, green=0, blue=238)
BLUE3 = RGB(name='blue3', red=0, green=0, blue=205)
BLUE4 = RGB(name='blue4', red=0, green=0, blue=139)
BLUEVIOLET = RGB(name='blueviolet', red=138, green=43, blue=226)
BRICK = RGB(name='brick', red=156, green=102, blue=31)
BROWN = RGB(name='brown', red=165, green=42, blue=42)
BROWN1 = RGB(name='brown1', red=255, green=64, blue=64)
BROWN2 = RGB(name='brown2', red=238, green=59, blue=59)
BROWN3 = RGB(name='brown3', red=205, green=51, blue=51)
BROWN4 = RGB(name='brown4', red=139, green=35, blue=35)
BURLYWOOD = RGB(name='burlywood', red=222, green=184, blue=135)
BURLYWOOD1 = RGB(name='burlywood1', red=255, green=211, blue=155)
BURLYWOOD2 = RGB(name='burlywood2', red=238, green=197, blue=145)
BURLYWOOD3 = RGB(name='burlywood3', red=205, green=170, blue=125)
BURLYWOOD4 = RGB(name='burlywood4', red=139, green=115, blue=85)
BURNTSIENNA = RGB(name='burntsienna', red=138, green=54, blue=15)
BURNTUMBER = RGB(name='burntumber', red=138, green=51, blue=36)
CADETBLUE = RGB(name='cadetblue', red=95, green=158, blue=160)
CADETBLUE1 = RGB(name='cadetblue1', red=152, green=245, blue=255)
CADETBLUE2 = RGB(name='cadetblue2', red=142, green=229, blue=238)
CADETBLUE3 = RGB(name='cadetblue3', red=122, green=197, blue=205)
CADETBLUE4 = RGB(name='cadetblue4', red=83, green=134, blue=139)
CADMIUMORANGE = RGB(name='cadmiumorange', red=255, green=97, blue=3)
CADMIUMYELLOW = RGB(name='cadmiumyellow', red=255, green=153, blue=18)
CARROT = RGB(name='carrot', red=237, green=145, blue=33)
CHARTREUSE1 = RGB(name='chartreuse1', red=127, green=255, blue=0)
CHARTREUSE2 = RGB(name='chartreuse2', red=118, green=238, blue=0)
CHARTREUSE3 = RGB(name='chartreuse3', red=102, green=205, blue=0)
CHARTREUSE4 = RGB(name='chartreuse4', red=69, green=139, blue=0)
CHOCOLATE = RGB(name='chocolate', red=210, green=105, blue=30)
CHOCOLATE1 = RGB(name='chocolate1', red=255, green=127, blue=36)
CHOCOLATE2 = RGB(name='chocolate2', red=238, green=118, blue=33)
CHOCOLATE3 = RGB(name='chocolate3', red=205, green=102, blue=29)
CHOCOLATE4 = RGB(name='chocolate4', red=139, green=69, blue=19)
COBALT = RGB(name='cobalt', red=61, green=89, blue=171)
COBALTGREEN = RGB(name='cobaltgreen', red=61, green=145, blue=64)
COLDGREY = RGB(name='coldgrey', red=128, green=138, blue=135)
CORAL = RGB(name='coral', red=255, green=127, blue=80)
CORAL1 = RGB(name='coral1', red=255, green=114, blue=86)
CORAL2 = RGB(name='coral2', red=238, green=106, blue=80)
CORAL3 = RGB(name='coral3', red=205, green=91, blue=69)
CORAL4 = RGB(name='coral4', red=139, green=62, blue=47)
CORNFLOWERBLUE = RGB(name='cornflowerblue', red=100, green=149, blue=237)
CORNSILK1 = RGB(name='cornsilk1', red=255, green=248, blue=220)
CORNSILK2 = RGB(name='cornsilk2', red=238, green=232, blue=205)
CORNSILK3 = RGB(name='cornsilk3', red=205, green=200, blue=177)
CORNSILK4 = RGB(name='cornsilk4', red=139, green=136, blue=120)
CRIMSON = RGB(name='crimson', red=220, green=20, blue=60)
CYAN2 = RGB(name='cyan2', red=0, green=238, blue=238)
CYAN3 = RGB(name='cyan3', red=0, green=205, blue=205)
CYAN4 = RGB(name='cyan4', red=0, green=139, blue=139)
DARKGOLDENROD = RGB(name='darkgoldenrod', red=184, green=134, blue=11)
DARKGOLDENROD1 = RGB(name='darkgoldenrod1', red=255, green=185, blue=15)
DARKGOLDENROD2 = RGB(name='darkgoldenrod2', red=238, green=173, blue=14)
DARKGOLDENROD3 = RGB(name='darkgoldenrod3', red=205, green=149, blue=12)
DARKGOLDENROD4 = RGB(name='darkgoldenrod4', red=139, green=101, blue=8)
DARKGRAY = RGB(name='darkgray', red=169, green=169, blue=169)
DARKGREEN = RGB(name='darkgreen', red=0, green=100, blue=0)
DARKKHAKI = RGB(name='darkkhaki', red=189, green=183, blue=107)
DARKOLIVEGREEN = RGB(name='darkolivegreen', red=85, green=107, blue=47)
DARKOLIVEGREEN1 = RGB(name='darkolivegreen1', red=202, green=255, blue=112)
DARKOLIVEGREEN2 = RGB(name='darkolivegreen2', red=188, green=238, blue=104)
DARKOLIVEGREEN3 = RGB(name='darkolivegreen3', red=162, green=205, blue=90)
DARKOLIVEGREEN4 = RGB(name='darkolivegreen4', red=110, green=139, blue=61)
DARKORANGE = RGB(name='darkorange', red=255, green=140, blue=0)
DARKORANGE1 = RGB(name='darkorange1', red=255, green=127, blue=0)
DARKORANGE2 = RGB(name='darkorange2', red=238, green=118, blue=0)
DARKORANGE3 = RGB(name='darkorange3', red=205, green=102, blue=0)
DARKORANGE4 = RGB(name='darkorange4', red=139, green=69, blue=0)
DARKORCHID = RGB(name='darkorchid', red=153, green=50, blue=204)
DARKORCHID1 = RGB(name='darkorchid1', red=191, green=62, blue=255)
DARKORCHID2 = RGB(name='darkorchid2', red=178, green=58, blue=238)
DARKORCHID3 = RGB(name='darkorchid3', red=154, green=50, blue=205)
DARKORCHID4 = RGB(name='darkorchid4', red=104, green=34, blue=139)
DARKSALMON = RGB(name='darksalmon', red=233, green=150, blue=122)
DARKSEAGREEN = RGB(name='darkseagreen', red=143, green=188, blue=143)
DARKSEAGREEN1 = RGB(name='darkseagreen1', red=193, green=255, blue=193)
DARKSEAGREEN2 = RGB(name='darkseagreen2', red=180, green=238, blue=180)
DARKSEAGREEN3 = RGB(name='darkseagreen3', red=155, green=205, blue=155)
DARKSEAGREEN4 = RGB(name='darkseagreen4', red=105, green=139, blue=105)
DARKSLATEBLUE = RGB(name='darkslateblue', red=72, green=61, blue=139)
DARKSLATEGRAY = RGB(name='darkslategray', red=47, green=79, blue=79)
DARKSLATEGRAY1 = RGB(name='darkslategray1', red=151, green=255, blue=255)
DARKSLATEGRAY2 = RGB(name='darkslategray2', red=141, green=238, blue=238)
DARKSLATEGRAY3 = RGB(name='darkslategray3', red=121, green=205, blue=205)
DARKSLATEGRAY4 = RGB(name='darkslategray4', red=82, green=139, blue=139)
DARKTURQUOISE = RGB(name='darkturquoise', red=0, green=206, blue=209)
DARKVIOLET = RGB(name='darkviolet', red=148, green=0, blue=211)
DEEPPINK1 = RGB(name='deeppink1', red=255, green=20, blue=147)
DEEPPINK2 = RGB(name='deeppink2', red=238, green=18, blue=137)
DEEPPINK3 = RGB(name='deeppink3', red=205, green=16, blue=118)
DEEPPINK4 = RGB(name='deeppink4', red=139, green=10, blue=80)
DEEPSKYBLUE1 = RGB(name='deepskyblue1', red=0, green=191, blue=255)
DEEPSKYBLUE2 = RGB(name='deepskyblue2', red=0, green=178, blue=238)
DEEPSKYBLUE3 = RGB(name='deepskyblue3', red=0, green=154, blue=205)
DEEPSKYBLUE4 = RGB(name='deepskyblue4', red=0, green=104, blue=139)
DIMGRAY = RGB(name='dimgray', red=105, green=105, blue=105)
DIMGRAY = RGB(name='dimgray', red=105, green=105, blue=105)
DODGERBLUE1 = RGB(name='dodgerblue1', red=30, green=144, blue=255)
DODGERBLUE2 = RGB(name='dodgerblue2', red=28, green=134, blue=238)
DODGERBLUE3 = RGB(name='dodgerblue3', red=24, green=116, blue=205)
DODGERBLUE4 = RGB(name='dodgerblue4', red=16, green=78, blue=139)
EGGSHELL = RGB(name='eggshell', red=252, green=230, blue=201)
EMERALDGREEN = RGB(name='emeraldgreen', red=0, green=201, blue=87)
FIREBRICK = RGB(name='firebrick', red=178, green=34, blue=34)
FIREBRICK1 = RGB(name='firebrick1', red=255, green=48, blue=48)
FIREBRICK2 = RGB(name='firebrick2', red=238, green=44, blue=44)
FIREBRICK3 = RGB(name='firebrick3', red=205, green=38, blue=38)
FIREBRICK4 = RGB(name='firebrick4', red=139, green=26, blue=26)
FLESH = RGB(name='flesh', red=255, green=125, blue=64)
FLORALWHITE = RGB(name='floralwhite', red=255, green=250, blue=240)
FORESTGREEN = RGB(name='forestgreen', red=34, green=139, blue=34)
GAINSBORO = RGB(name='gainsboro', red=220, green=220, blue=220)
GHOSTWHITE = RGB(name='ghostwhite', red=248, green=248, blue=255)
GOLD1 = RGB(name='gold1', red=255, green=215, blue=0)
GOLD2 = RGB(name='gold2', red=238, green=201, blue=0)
GOLD3 = RGB(name='gold3', red=205, green=173, blue=0)
GOLD4 = RGB(name='gold4', red=139, green=117, blue=0)
GOLDENROD = RGB(name='goldenrod', red=218, green=165, blue=32)
GOLDENROD1 = RGB(name='goldenrod1', red=255, green=193, blue=37)
GOLDENROD2 = RGB(name='goldenrod2', red=238, green=180, blue=34)
GOLDENROD3 = RGB(name='goldenrod3', red=205, green=155, blue=29)
GOLDENROD4 = RGB(name='goldenrod4', red=139, green=105, blue=20)
GRAY = RGB(name='gray', red=128, green=128, blue=128)
GRAY1 = RGB(name='gray1', red=3, green=3, blue=3)
GRAY10 = RGB(name='gray10', red=26, green=26, blue=26)
GRAY11 = RGB(name='gray11', red=28, green=28, blue=28)
GRAY12 = RGB(name='gray12', red=31, green=31, blue=31)
GRAY13 = RGB(name='gray13', red=33, green=33, blue=33)
GRAY14 = RGB(name='gray14', red=36, green=36, blue=36)
GRAY15 = RGB(name='gray15', red=38, green=38, blue=38)
GRAY16 = RGB(name='gray16', red=41, green=41, blue=41)
GRAY17 = RGB(name='gray17', red=43, green=43, blue=43)
GRAY18 = RGB(name='gray18', red=46, green=46, blue=46)
GRAY19 = RGB(name='gray19', red=48, green=48, blue=48)
GRAY2 = RGB(name='gray2', red=5, green=5, blue=5)
GRAY20 = RGB(name='gray20', red=51, green=51, blue=51)
GRAY21 = RGB(name='gray21', red=54, green=54, blue=54)
GRAY22 = RGB(name='gray22', red=56, green=56, blue=56)
GRAY23 = RGB(name='gray23', red=59, green=59, blue=59)
GRAY24 = RGB(name='gray24', red=61, green=61, blue=61)
GRAY25 = RGB(name='gray25', red=64, green=64, blue=64)
GRAY26 = RGB(name='gray26', red=66, green=66, blue=66)
GRAY27 = RGB(name='gray27', red=69, green=69, blue=69)
GRAY28 = RGB(name='gray28', red=71, green=71, blue=71)
GRAY29 = RGB(name='gray29', red=74, green=74, blue=74)
GRAY3 = RGB(name='gray3', red=8, green=8, blue=8)
GRAY30 = RGB(name='gray30', red=77, green=77, blue=77)
GRAY31 = RGB(name='gray31', red=79, green=79, blue=79)
GRAY32 = RGB(name='gray32', red=82, green=82, blue=82)
GRAY33 = RGB(name='gray33', red=84, green=84, blue=84)
GRAY34 = RGB(name='gray34', red=87, green=87, blue=87)
GRAY35 = RGB(name='gray35', red=89, green=89, blue=89)
GRAY36 = RGB(name='gray36', red=92, green=92, blue=92)
GRAY37 = RGB(name='gray37', red=94, green=94, blue=94)
GRAY38 = RGB(name='gray38', red=97, green=97, blue=97)
GRAY39 = RGB(name='gray39', red=99, green=99, blue=99)
GRAY4 = RGB(name='gray4', red=10, green=10, blue=10)
GRAY40 = RGB(name='gray40', red=102, green=102, blue=102)
GRAY42 = RGB(name='gray42', red=107, green=107, blue=107)
GRAY43 = RGB(name='gray43', red=110, green=110, blue=110)
GRAY44 = RGB(name='gray44', red=112, green=112, blue=112)
GRAY45 = RGB(name='gray45', red=115, green=115, blue=115)
GRAY46 = RGB(name='gray46', red=117, green=117, blue=117)
GRAY47 = RGB(name='gray47', red=120, green=120, blue=120)
GRAY48 = RGB(name='gray48', red=122, green=122, blue=122)
GRAY49 = RGB(name='gray49', red=125, green=125, blue=125)
GRAY5 = RGB(name='gray5', red=13, green=13, blue=13)
GRAY50 = RGB(name='gray50', red=127, green=127, blue=127)
GRAY51 = RGB(name='gray51', red=130, green=130, blue=130)
GRAY52 = RGB(name='gray52', red=133, green=133, blue=133)
GRAY53 = RGB(name='gray53', red=135, green=135, blue=135)
GRAY54 = RGB(name='gray54', red=138, green=138, blue=138)
GRAY55 = RGB(name='gray55', red=140, green=140, blue=140)
GRAY56 = RGB(name='gray56', red=143, green=143, blue=143)
GRAY57 = RGB(name='gray57', red=145, green=145, blue=145)
GRAY58 = RGB(name='gray58', red=148, green=148, blue=148)
GRAY59 = RGB(name='gray59', red=150, green=150, blue=150)
GRAY6 = RGB(name='gray6', red=15, green=15, blue=15)
GRAY60 = RGB(name='gray60', red=153, green=153, blue=153)
GRAY61 = RGB(name='gray61', red=156, green=156, blue=156)
GRAY62 = RGB(name='gray62', red=158, green=158, blue=158)
GRAY63 = RGB(name='gray63', red=161, green=161, blue=161)
GRAY64 = RGB(name='gray64', red=163, green=163, blue=163)
GRAY65 = RGB(name='gray65', red=166, green=166, blue=166)
GRAY66 = RGB(name='gray66', red=168, green=168, blue=168)
GRAY67 = RGB(name='gray67', red=171, green=171, blue=171)
GRAY68 = RGB(name='gray68', red=173, green=173, blue=173)
GRAY69 = RGB(name='gray69', red=176, green=176, blue=176)
GRAY7 = RGB(name='gray7', red=18, green=18, blue=18)
GRAY70 = RGB(name='gray70', red=179, green=179, blue=179)
GRAY71 = RGB(name='gray71', red=181, green=181, blue=181)
GRAY72 = RGB(name='gray72', red=184, green=184, blue=184)
GRAY73 = RGB(name='gray73', red=186, green=186, blue=186)
GRAY74 = RGB(name='gray74', red=189, green=189, blue=189)
GRAY75 = RGB(name='gray75', red=191, green=191, blue=191)
GRAY76 = RGB(name='gray76', red=194, green=194, blue=194)
GRAY77 = RGB(name='gray77', red=196, green=196, blue=196)
GRAY78 = RGB(name='gray78', red=199, green=199, blue=199)
GRAY79 = RGB(name='gray79', red=201, green=201, blue=201)
GRAY8 = RGB(name='gray8', red=20, green=20, blue=20)
GRAY80 = RGB(name='gray80', red=204, green=204, blue=204)
GRAY81 = RGB(name='gray81', red=207, green=207, blue=207)
GRAY82 = RGB(name='gray82', red=209, green=209, blue=209)
GRAY83 = RGB(name='gray83', red=212, green=212, blue=212)
GRAY84 = RGB(name='gray84', red=214, green=214, blue=214)
GRAY85 = RGB(name='gray85', red=217, green=217, blue=217)
GRAY86 = RGB(name='gray86', red=219, green=219, blue=219)
GRAY87 = RGB(name='gray87', red=222, green=222, blue=222)
GRAY88 = RGB(name='gray88', red=224, green=224, blue=224)
GRAY89 = RGB(name='gray89', red=227, green=227, blue=227)
GRAY9 = RGB(name='gray9', red=23, green=23, blue=23)
GRAY90 = RGB(name='gray90', red=229, green=229, blue=229)
GRAY91 = RGB(name='gray91', red=232, green=232, blue=232)
GRAY92 = RGB(name='gray92', red=235, green=235, blue=235)
GRAY93 = RGB(name='gray93', red=237, green=237, blue=237)
GRAY94 = RGB(name='gray94', red=240, green=240, blue=240)
GRAY95 = RGB(name='gray95', red=242, green=242, blue=242)
GRAY97 = RGB(name='gray97', red=247, green=247, blue=247)
GRAY98 = RGB(name='gray98', red=250, green=250, blue=250)
GRAY99 = RGB(name='gray99', red=252, green=252, blue=252)
GREEN = RGB(name='green', red=0, green=128, blue=0)
GREEN1 = RGB(name='green1', red=0, green=255, blue=0)
GREEN2 = RGB(name='green2', red=0, green=238, blue=0)
GREEN3 = RGB(name='green3', red=0, green=205, blue=0)
GREEN4 = RGB(name='green4', red=0, green=139, blue=0)
GREENYELLOW = RGB(name='greenyellow', red=173, green=255, blue=47)
HONEYDEW1 = RGB(name='honeydew1', red=240, green=255, blue=240)
HONEYDEW2 = RGB(name='honeydew2', red=224, green=238, blue=224)
HONEYDEW3 = RGB(name='honeydew3', red=193, green=205, blue=193)
HONEYDEW4 = RGB(name='honeydew4', red=131, green=139, blue=131)
HOTPINK = RGB(name='hotpink', red=255, green=105, blue=180)
HOTPINK1 = RGB(name='hotpink1', red=255, green=110, blue=180)
HOTPINK2 = RGB(name='hotpink2', red=238, green=106, blue=167)
HOTPINK3 = RGB(name='hotpink3', red=205, green=96, blue=144)
HOTPINK4 = RGB(name='hotpink4', red=139, green=58, blue=98)
INDIANRED = RGB(name='indianred', red=176, green=23, blue=31)
INDIANRED = RGB(name='indianred', red=205, green=92, blue=92)
INDIANRED1 = RGB(name='indianred1', red=255, green=106, blue=106)
INDIANRED2 = RGB(name='indianred2', red=238, green=99, blue=99)
INDIANRED3 = RGB(name='indianred3', red=205, green=85, blue=85)
INDIANRED4 = RGB(name='indianred4', red=139, green=58, blue=58)
INDIGO = RGB(name='indigo', red=75, green=0, blue=130)
IVORY1 = RGB(name='ivory1', red=255, green=255, blue=240)
IVORY2 = RGB(name='ivory2', red=238, green=238, blue=224)
IVORY3 = RGB(name='ivory3', red=205, green=205, blue=193)
IVORY4 = RGB(name='ivory4', red=139, green=139, blue=131)
IVORYBLACK = RGB(name='ivoryblack', red=41, green=36, blue=33)
KHAKI = RGB(name='khaki', red=240, green=230, blue=140)
KHAKI1 = RGB(name='khaki1', red=255, green=246, blue=143)
KHAKI2 = RGB(name='khaki2', red=238, green=230, blue=133)
KHAKI3 = RGB(name='khaki3', red=205, green=198, blue=115)
KHAKI4 = RGB(name='khaki4', red=139, green=134, blue=78)
LAVENDER = RGB(name='lavender', red=230, green=230, blue=250)
LAVENDERBLUSH1 = RGB(name='lavenderblush1', red=255, green=240, blue=245)
LAVENDERBLUSH2 = RGB(name='lavenderblush2', red=238, green=224, blue=229)
LAVENDERBLUSH3 = RGB(name='lavenderblush3', red=205, green=193, blue=197)
LAVENDERBLUSH4 = RGB(name='lavenderblush4', red=139, green=131, blue=134)
LAWNGREEN = RGB(name='lawngreen', red=124, green=252, blue=0)
LEMONCHIFFON1 = RGB(name='lemonchiffon1', red=255, green=250, blue=205)
LEMONCHIFFON2 = RGB(name='lemonchiffon2', red=238, green=233, blue=191)
LEMONCHIFFON3 = RGB(name='lemonchiffon3', red=205, green=201, blue=165)
LEMONCHIFFON4 = RGB(name='lemonchiffon4', red=139, green=137, blue=112)
LIGHTBLUE = RGB(name='lightblue', red=173, green=216, blue=230)
LIGHTBLUE1 = RGB(name='lightblue1', red=191, green=239, blue=255)
LIGHTBLUE2 = RGB(name='lightblue2', red=178, green=223, blue=238)
LIGHTBLUE3 = RGB(name='lightblue3', red=154, green=192, blue=205)
LIGHTBLUE4 = RGB(name='lightblue4', red=104, green=131, blue=139)
LIGHTCORAL = RGB(name='lightcoral', red=240, green=128, blue=128)
LIGHTCYAN1 = RGB(name='lightcyan1', red=224, green=255, blue=255)
LIGHTCYAN2 = RGB(name='lightcyan2', red=209, green=238, blue=238)
LIGHTCYAN3 = RGB(name='lightcyan3', red=180, green=205, blue=205)
LIGHTCYAN4 = RGB(name='lightcyan4', red=122, green=139, blue=139)
LIGHTGOLDENROD1 = RGB(name='lightgoldenrod1', red=255, green=236, blue=139)
LIGHTGOLDENROD2 = RGB(name='lightgoldenrod2', red=238, green=220, blue=130)
LIGHTGOLDENROD3 = RGB(name='lightgoldenrod3', red=205, green=190, blue=112)
LIGHTGOLDENROD4 = RGB(name='lightgoldenrod4', red=139, green=129, blue=76)
LIGHTGOLDENRODYELLOW = \
    RGB(name='lightgoldenrodyellow', red=250, green=250, blue=210)
LIGHTGREY = RGB(name='lightgrey', red=211, green=211, blue=211)
LIGHTPINK = RGB(name='lightpink', red=255, green=182, blue=193)
LIGHTPINK1 = RGB(name='lightpink1', red=255, green=174, blue=185)
LIGHTPINK2 = RGB(name='lightpink2', red=238, green=162, blue=173)
LIGHTPINK3 = RGB(name='lightpink3', red=205, green=140, blue=149)
LIGHTPINK4 = RGB(name='lightpink4', red=139, green=95, blue=101)
LIGHTSALMON1 = RGB(name='lightsalmon1', red=255, green=160, blue=122)
LIGHTSALMON2 = RGB(name='lightsalmon2', red=238, green=149, blue=114)
LIGHTSALMON3 = RGB(name='lightsalmon3', red=205, green=129, blue=98)
LIGHTSALMON4 = RGB(name='lightsalmon4', red=139, green=87, blue=66)
LIGHTSEAGREEN = RGB(name='lightseagreen', red=32, green=178, blue=170)
LIGHTSKYBLUE = RGB(name='lightskyblue', red=135, green=206, blue=250)
LIGHTSKYBLUE1 = RGB(name='lightskyblue1', red=176, green=226, blue=255)
LIGHTSKYBLUE2 = RGB(name='lightskyblue2', red=164, green=211, blue=238)
LIGHTSKYBLUE3 = RGB(name='lightskyblue3', red=141, green=182, blue=205)
LIGHTSKYBLUE4 = RGB(name='lightskyblue4', red=96, green=123, blue=139)
LIGHTSLATEBLUE = RGB(name='lightslateblue', red=132, green=112, blue=255)
LIGHTSLATEGRAY = RGB(name='lightslategray', red=119, green=136, blue=153)
LIGHTSTEELBLUE = RGB(name='lightsteelblue', red=176, green=196, blue=222)
LIGHTSTEELBLUE1 = RGB(name='lightsteelblue1', red=202, green=225, blue=255)
LIGHTSTEELBLUE2 = RGB(name='lightsteelblue2', red=188, green=210, blue=238)
LIGHTSTEELBLUE3 = RGB(name='lightsteelblue3', red=162, green=181, blue=205)
LIGHTSTEELBLUE4 = RGB(name='lightsteelblue4', red=110, green=123, blue=139)
LIGHTYELLOW1 = RGB(name='lightyellow1', red=255, green=255, blue=224)
LIGHTYELLOW2 = RGB(name='lightyellow2', red=238, green=238, blue=209)
LIGHTYELLOW3 = RGB(name='lightyellow3', red=205, green=205, blue=180)
LIGHTYELLOW4 = RGB(name='lightyellow4', red=139, green=139, blue=122)
LIMEGREEN = RGB(name='limegreen', red=50, green=205, blue=50)
LINEN = RGB(name='linen', red=250, green=240, blue=230)
MAGENTA = RGB(name='magenta', red=255, green=0, blue=255)
MAGENTA2 = RGB(name='magenta2', red=238, green=0, blue=238)
MAGENTA3 = RGB(name='magenta3', red=205, green=0, blue=205)
MAGENTA4 = RGB(name='magenta4', red=139, green=0, blue=139)
MANGANESEBLUE = RGB(name='manganeseblue', red=3, green=168, blue=158)
MAROON = RGB(name='maroon', red=128, green=0, blue=0)
MAROON1 = RGB(name='maroon1', red=255, green=52, blue=179)
MAROON2 = RGB(name='maroon2', red=238, green=48, blue=167)
MAROON3 = RGB(name='maroon3', red=205, green=41, blue=144)
MAROON4 = RGB(name='maroon4', red=139, green=28, blue=98)
MEDIUMORCHID = RGB(name='mediumorchid', red=186, green=85, blue=211)
MEDIUMORCHID1 = RGB(name='mediumorchid1', red=224, green=102, blue=255)
MEDIUMORCHID2 = RGB(name='mediumorchid2', red=209, green=95, blue=238)
MEDIUMORCHID3 = RGB(name='mediumorchid3', red=180, green=82, blue=205)
MEDIUMORCHID4 = RGB(name='mediumorchid4', red=122, green=55, blue=139)
MEDIUMPURPLE = RGB(name='mediumpurple', red=147, green=112, blue=219)
MEDIUMPURPLE1 = RGB(name='mediumpurple1', red=171, green=130, blue=255)
MEDIUMPURPLE2 = RGB(name='mediumpurple2', red=159, green=121, blue=238)
MEDIUMPURPLE3 = RGB(name='mediumpurple3', red=137, green=104, blue=205)
MEDIUMPURPLE4 = RGB(name='mediumpurple4', red=93, green=71, blue=139)
MEDIUMSEAGREEN = RGB(name='mediumseagreen', red=60, green=179, blue=113)
MEDIUMSLATEBLUE = RGB(name='mediumslateblue', red=123, green=104, blue=238)
MEDIUMSPRINGGREEN = RGB(name='mediumspringgreen', red=0, green=250, blue=154)
MEDIUMTURQUOISE = RGB(name='mediumturquoise', red=72, green=209, blue=204)
MEDIUMVIOLETRED = RGB(name='mediumvioletred', red=199, green=21, blue=133)
MELON = RGB(name='melon', red=227, green=168, blue=105)
MIDNIGHTBLUE = RGB(name='midnightblue', red=25, green=25, blue=112)
MINT = RGB(name='mint', red=189, green=252, blue=201)
MINTCREAM = RGB(name='mintcream', red=245, green=255, blue=250)
MISTYROSE1 = RGB(name='mistyrose1', red=255, green=228, blue=225)
MISTYROSE2 = RGB(name='mistyrose2', red=238, green=213, blue=210)
MISTYROSE3 = RGB(name='mistyrose3', red=205, green=183, blue=181)
MISTYROSE4 = RGB(name='mistyrose4', red=139, green=125, blue=123)
MOCCASIN = RGB(name='moccasin', red=255, green=228, blue=181)
NAVAJOWHITE1 = RGB(name='navajowhite1', red=255, green=222, blue=173)
NAVAJOWHITE2 = RGB(name='navajowhite2', red=238, green=207, blue=161)
NAVAJOWHITE3 = RGB(name='navajowhite3', red=205, green=179, blue=139)
NAVAJOWHITE4 = RGB(name='navajowhite4', red=139, green=121, blue=94)
NAVY = RGB(name='navy', red=0, green=0, blue=128)
OLDLACE = RGB(name='oldlace', red=253, green=245, blue=230)
OLIVE = RGB(name='olive', red=128, green=128, blue=0)
OLIVEDRAB = RGB(name='olivedrab', red=107, green=142, blue=35)
OLIVEDRAB1 = RGB(name='olivedrab1', red=192, green=255, blue=62)
OLIVEDRAB2 = RGB(name='olivedrab2', red=179, green=238, blue=58)
OLIVEDRAB3 = RGB(name='olivedrab3', red=154, green=205, blue=50)
OLIVEDRAB4 = RGB(name='olivedrab4', red=105, green=139, blue=34)
ORANGE = RGB(name='orange', red=255, green=128, blue=0)
ORANGE1 = RGB(name='orange1', red=255, green=165, blue=0)
ORANGE2 = RGB(name='orange2', red=238, green=154, blue=0)
ORANGE3 = RGB(name='orange3', red=205, green=133, blue=0)
ORANGE4 = RGB(name='orange4', red=139, green=90, blue=0)
ORANGERED1 = RGB(name='orangered1', red=255, green=69, blue=0)
ORANGERED2 = RGB(name='orangered2', red=238, green=64, blue=0)
ORANGERED3 = RGB(name='orangered3', red=205, green=55, blue=0)
ORANGERED4 = RGB(name='orangered4', red=139, green=37, blue=0)
ORCHID = RGB(name='orchid', red=218, green=112, blue=214)
ORCHID1 = RGB(name='orchid1', red=255, green=131, blue=250)
ORCHID2 = RGB(name='orchid2', red=238, green=122, blue=233)
ORCHID3 = RGB(name='orchid3', red=205, green=105, blue=201)
ORCHID4 = RGB(name='orchid4', red=139, green=71, blue=137)
PALEGOLDENROD = RGB(name='palegoldenrod', red=238, green=232, blue=170)
PALEGREEN = RGB(name='palegreen', red=152, green=251, blue=152)
PALEGREEN1 = RGB(name='palegreen1', red=154, green=255, blue=154)
PALEGREEN2 = RGB(name='palegreen2', red=144, green=238, blue=144)
PALEGREEN3 = RGB(name='palegreen3', red=124, green=205, blue=124)
PALEGREEN4 = RGB(name='palegreen4', red=84, green=139, blue=84)
PALETURQUOISE1 = RGB(name='paleturquoise1', red=187, green=255, blue=255)
PALETURQUOISE2 = RGB(name='paleturquoise2', red=174, green=238, blue=238)
PALETURQUOISE3 = RGB(name='paleturquoise3', red=150, green=205, blue=205)
PALETURQUOISE4 = RGB(name='paleturquoise4', red=102, green=139, blue=139)
PALEVIOLETRED = RGB(name='palevioletred', red=219, green=112, blue=147)
PALEVIOLETRED1 = RGB(name='palevioletred1', red=255, green=130, blue=171)
PALEVIOLETRED2 = RGB(name='palevioletred2', red=238, green=121, blue=159)
PALEVIOLETRED3 = RGB(name='palevioletred3', red=205, green=104, blue=137)
PALEVIOLETRED4 = RGB(name='palevioletred4', red=139, green=71, blue=93)
PAPAYAWHIP = RGB(name='papayawhip', red=255, green=239, blue=213)
PEACHPUFF1 = RGB(name='peachpuff1', red=255, green=218, blue=185)
PEACHPUFF2 = RGB(name='peachpuff2', red=238, green=203, blue=173)
PEACHPUFF3 = RGB(name='peachpuff3', red=205, green=175, blue=149)
PEACHPUFF4 = RGB(name='peachpuff4', red=139, green=119, blue=101)
PEACOCK = RGB(name='peacock', red=51, green=161, blue=201)
PINK = RGB(name='pink', red=255, green=192, blue=203)
PINK1 = RGB(name='pink1', red=255, green=181, blue=197)
PINK2 = RGB(name='pink2', red=238, green=169, blue=184)
PINK3 = RGB(name='pink3', red=205, green=145, blue=158)
PINK4 = RGB(name='pink4', red=139, green=99, blue=108)
PLUM = RGB(name='plum', red=221, green=160, blue=221)
PLUM1 = RGB(name='plum1', red=255, green=187, blue=255)
PLUM2 = RGB(name='plum2', red=238, green=174, blue=238)
PLUM3 = RGB(name='plum3', red=205, green=150, blue=205)
PLUM4 = RGB(name='plum4', red=139, green=102, blue=139)
POWDERBLUE = RGB(name='powderblue', red=176, green=224, blue=230)
PURPLE = RGB(name='purple', red=128, green=0, blue=128)
PURPLE1 = RGB(name='purple1', red=155, green=48, blue=255)
PURPLE2 = RGB(name='purple2', red=145, green=44, blue=238)
PURPLE3 = RGB(name='purple3', red=125, green=38, blue=205)
PURPLE4 = RGB(name='purple4', red=85, green=26, blue=139)
RASPBERRY = RGB(name='raspberry', red=135, green=38, blue=87)
RAWSIENNA = RGB(name='rawsienna', red=199, green=97, blue=20)
RED1 = RGB(name='red1', red=255, green=0, blue=0)
RED2 = RGB(name='red2', red=238, green=0, blue=0)
RED3 = RGB(name='red3', red=205, green=0, blue=0)
RED4 = RGB(name='red4', red=139, green=0, blue=0)
ROSYBROWN = RGB(name='rosybrown', red=188, green=143, blue=143)
ROSYBROWN1 = RGB(name='rosybrown1', red=255, green=193, blue=193)
ROSYBROWN2 = RGB(name='rosybrown2', red=238, green=180, blue=180)
ROSYBROWN3 = RGB(name='rosybrown3', red=205, green=155, blue=155)
ROSYBROWN4 = RGB(name='rosybrown4', red=139, green=105, blue=105)
ROYALBLUE = RGB(name='royalblue', red=65, green=105, blue=225)
ROYALBLUE1 = RGB(name='royalblue1', red=72, green=118, blue=255)
ROYALBLUE2 = RGB(name='royalblue2', red=67, green=110, blue=238)
ROYALBLUE3 = RGB(name='royalblue3', red=58, green=95, blue=205)
ROYALBLUE4 = RGB(name='royalblue4', red=39, green=64, blue=139)
SALMON = RGB(name='salmon', red=250, green=128, blue=114)
SALMON1 = RGB(name='salmon1', red=255, green=140, blue=105)
SALMON2 = RGB(name='salmon2', red=238, green=130, blue=98)
SALMON3 = RGB(name='salmon3', red=205, green=112, blue=84)
SALMON4 = RGB(name='salmon4', red=139, green=76, blue=57)
SANDYBROWN = RGB(name='sandybrown', red=244, green=164, blue=96)
SAPGREEN = RGB(name='sapgreen', red=48, green=128, blue=20)
SEAGREEN1 = RGB(name='seagreen1', red=84, green=255, blue=159)
SEAGREEN2 = RGB(name='seagreen2', red=78, green=238, blue=148)
SEAGREEN3 = RGB(name='seagreen3', red=67, green=205, blue=128)
SEAGREEN4 = RGB(name='seagreen4', red=46, green=139, blue=87)
SEASHELL1 = RGB(name='seashell1', red=255, green=245, blue=238)
SEASHELL2 = RGB(name='seashell2', red=238, green=229, blue=222)
SEASHELL3 = RGB(name='seashell3', red=205, green=197, blue=191)
SEASHELL4 = RGB(name='seashell4', red=139, green=134, blue=130)
SEPIA = RGB(name='sepia', red=94, green=38, blue=18)
SGIBEET = RGB(name='sgibeet', red=142, green=56, blue=142)
SGIBRIGHTGRAY = RGB(name='sgibrightgray', red=197, green=193, blue=170)
SGICHARTREUSE = RGB(name='sgichartreuse', red=113, green=198, blue=113)
SGIDARKGRAY = RGB(name='sgidarkgray', red=85, green=85, blue=85)
SGIGRAY12 = RGB(name='sgigray12', red=30, green=30, blue=30)
SGIGRAY16 = RGB(name='sgigray16', red=40, green=40, blue=40)
SGIGRAY32 = RGB(name='sgigray32', red=81, green=81, blue=81)
SGIGRAY36 = RGB(name='sgigray36', red=91, green=91, blue=91)
SGIGRAY52 = RGB(name='sgigray52', red=132, green=132, blue=132)
SGIGRAY56 = RGB(name='sgigray56', red=142, green=142, blue=142)
SGIGRAY72 = RGB(name='sgigray72', red=183, green=183, blue=183)
SGIGRAY76 = RGB(name='sgigray76', red=193, green=193, blue=193)
SGIGRAY92 = RGB(name='sgigray92', red=234, green=234, blue=234)
SGIGRAY96 = RGB(name='sgigray96', red=244, green=244, blue=244)
SGILIGHTBLUE = RGB(name='sgilightblue', red=125, green=158, blue=192)
SGILIGHTGRAY = RGB(name='sgilightgray', red=170, green=170, blue=170)
SGIOLIVEDRAB = RGB(name='sgiolivedrab', red=142, green=142, blue=56)
SGISALMON = RGB(name='sgisalmon', red=198, green=113, blue=113)
SGISLATEBLUE = RGB(name='sgislateblue', red=113, green=113, blue=198)
SGITEAL = RGB(name='sgiteal', red=56, green=142, blue=142)
SIENNA = RGB(name='sienna', red=160, green=82, blue=45)
SIENNA1 = RGB(name='sienna1', red=255, green=130, blue=71)
SIENNA2 = RGB(name='sienna2', red=238, green=121, blue=66)
SIENNA3 = RGB(name='sienna3', red=205, green=104, blue=57)
SIENNA4 = RGB(name='sienna4', red=139, green=71, blue=38)
SILVER = RGB(name='silver', red=192, green=192, blue=192)
SKYBLUE = RGB(name='skyblue', red=135, green=206, blue=235)
SKYBLUE1 = RGB(name='skyblue1', red=135, green=206, blue=255)
SKYBLUE2 = RGB(name='skyblue2', red=126, green=192, blue=238)
SKYBLUE3 = RGB(name='skyblue3', red=108, green=166, blue=205)
SKYBLUE4 = RGB(name='skyblue4', red=74, green=112, blue=139)
SLATEBLUE = RGB(name='slateblue', red=106, green=90, blue=205)
SLATEBLUE1 = RGB(name='slateblue1', red=131, green=111, blue=255)
SLATEBLUE2 = RGB(name='slateblue2', red=122, green=103, blue=238)
SLATEBLUE3 = RGB(name='slateblue3', red=105, green=89, blue=205)
SLATEBLUE4 = RGB(name='slateblue4', red=71, green=60, blue=139)
SLATEGRAY = RGB(name='slategray', red=112, green=128, blue=144)
SLATEGRAY1 = RGB(name='slategray1', red=198, green=226, blue=255)
SLATEGRAY2 = RGB(name='slategray2', red=185, green=211, blue=238)
SLATEGRAY3 = RGB(name='slategray3', red=159, green=182, blue=205)
SLATEGRAY4 = RGB(name='slategray4', red=108, green=123, blue=139)
SNOW1 = RGB(name='snow1', red=255, green=250, blue=250)
SNOW2 = RGB(name='snow2', red=238, green=233, blue=233)
SNOW3 = RGB(name='snow3', red=205, green=201, blue=201)
SNOW4 = RGB(name='snow4', red=139, green=137, blue=137)
SPRINGGREEN = RGB(name='springgreen', red=0, green=255, blue=127)
SPRINGGREEN1 = RGB(name='springgreen1', red=0, green=238, blue=118)
SPRINGGREEN2 = RGB(name='springgreen2', red=0, green=205, blue=102)
SPRINGGREEN3 = RGB(name='springgreen3', red=0, green=139, blue=69)
STEELBLUE = RGB(name='steelblue', red=70, green=130, blue=180)
STEELBLUE1 = RGB(name='steelblue1', red=99, green=184, blue=255)
STEELBLUE2 = RGB(name='steelblue2', red=92, green=172, blue=238)
STEELBLUE3 = RGB(name='steelblue3', red=79, green=148, blue=205)
STEELBLUE4 = RGB(name='steelblue4', red=54, green=100, blue=139)
TAN = RGB(name='tan', red=210, green=180, blue=140)
TAN1 = RGB(name='tan1', red=255, green=165, blue=79)
TAN2 = RGB(name='tan2', red=238, green=154, blue=73)
TAN3 = RGB(name='tan3', red=205, green=133, blue=63)
TAN4 = RGB(name='tan4', red=139, green=90, blue=43)
TEAL = RGB(name='teal', red=0, green=128, blue=128)
THISTLE = RGB(name='thistle', red=216, green=191, blue=216)
THISTLE1 = RGB(name='thistle1', red=255, green=225, blue=255)
THISTLE2 = RGB(name='thistle2', red=238, green=210, blue=238)
THISTLE3 = RGB(name='thistle3', red=205, green=181, blue=205)
THISTLE4 = RGB(name='thistle4', red=139, green=123, blue=139)
TOMATO1 = RGB(name='tomato1', red=255, green=99, blue=71)
TOMATO2 = RGB(name='tomato2', red=238, green=92, blue=66)
TOMATO3 = RGB(name='tomato3', red=205, green=79, blue=57)
TOMATO4 = RGB(name='tomato4', red=139, green=54, blue=38)
TURQUOISE = RGB(name='turquoise', red=64, green=224, blue=208)
TURQUOISE1 = RGB(name='turquoise1', red=0, green=245, blue=255)
TURQUOISE2 = RGB(name='turquoise2', red=0, green=229, blue=238)
TURQUOISE3 = RGB(name='turquoise3', red=0, green=197, blue=205)
TURQUOISE4 = RGB(name='turquoise4', red=0, green=134, blue=139)
TURQUOISEBLUE = RGB(name='turquoiseblue', red=0, green=199, blue=140)
VIOLET = RGB(name='violet', red=238, green=130, blue=238)
VIOLETRED = RGB(name='violetred', red=208, green=32, blue=144)
VIOLETRED1 = RGB(name='violetred1', red=255, green=62, blue=150)
VIOLETRED2 = RGB(name='violetred2', red=238, green=58, blue=140)
VIOLETRED3 = RGB(name='violetred3', red=205, green=50, blue=120)
VIOLETRED4 = RGB(name='violetred4', red=139, green=34, blue=82)
WARMGREY = RGB(name='warmgrey', red=128, green=128, blue=105)
WHEAT = RGB(name='wheat', red=245, green=222, blue=179)
WHEAT1 = RGB(name='wheat1', red=255, green=231, blue=186)
WHEAT2 = RGB(name='wheat2', red=238, green=216, blue=174)
WHEAT3 = RGB(name='wheat3', red=205, green=186, blue=150)
WHEAT4 = RGB(name='wheat4', red=139, green=126, blue=102)
WHITE = RGB(name='white', red=255, green=255, blue=255)
WHITESMOKE = RGB(name='whitesmoke', red=245, green=245, blue=245)
WHITESMOKE = RGB(name='whitesmoke', red=245, green=245, blue=245)
YELLOW1 = RGB(name='yellow1', red=255, green=255, blue=0)
YELLOW2 = RGB(name='yellow2', red=238, green=238, blue=0)
YELLOW3 = RGB(name='yellow3', red=205, green=205, blue=0)
YELLOW4 = RGB(name='yellow4', red=139, green=139, blue=0)

# create colors dict
COLORS[ALICEBLUE.name] = ALICEBLUE
COLORS[ANTIQUEWHITE.name] = ANTIQUEWHITE
COLORS[ANTIQUEWHITE1.name] = ANTIQUEWHITE1
COLORS[ANTIQUEWHITE2.name] = ANTIQUEWHITE2
COLORS[ANTIQUEWHITE3.name] = ANTIQUEWHITE3
COLORS[ANTIQUEWHITE4.name] = ANTIQUEWHITE4
COLORS[AQUA.name] = AQUA
COLORS[AQUAMARINE1.name] = AQUAMARINE1
COLORS[AQUAMARINE2.name] = AQUAMARINE2
COLORS[AQUAMARINE3.name] = AQUAMARINE3
COLORS[AQUAMARINE4.name] = AQUAMARINE4
COLORS[AZURE1.name] = AZURE1
COLORS[AZURE2.name] = AZURE2
COLORS[AZURE3.name] = AZURE3
COLORS[AZURE4.name] = AZURE4
COLORS[BANANA.name] = BANANA
COLORS[BEIGE.name] = BEIGE
COLORS[BISQUE1.name] = BISQUE1
COLORS[BISQUE2.name] = BISQUE2
COLORS[BISQUE3.name] = BISQUE3
COLORS[BISQUE4.name] = BISQUE4
COLORS[BLACK.name] = BLACK
COLORS[BLANCHEDALMOND.name] = BLANCHEDALMOND
COLORS[BLUE.name] = BLUE
COLORS[BLUE2.name] = BLUE2
COLORS[BLUE3.name] = BLUE3
COLORS[BLUE4.name] = BLUE4
COLORS[BLUEVIOLET.name] = BLUEVIOLET
COLORS[BRICK.name] = BRICK
COLORS[BROWN.name] = BROWN
COLORS[BROWN1.name] = BROWN1
COLORS[BROWN2.name] = BROWN2
COLORS[BROWN3.name] = BROWN3
COLORS[BROWN4.name] = BROWN4
COLORS[BURLYWOOD.name] = BURLYWOOD
COLORS[BURLYWOOD1.name] = BURLYWOOD1
COLORS[BURLYWOOD2.name] = BURLYWOOD2
COLORS[BURLYWOOD3.name] = BURLYWOOD3
COLORS[BURLYWOOD4.name] = BURLYWOOD4
COLORS[BURNTSIENNA.name] = BURNTSIENNA
COLORS[BURNTUMBER.name] = BURNTUMBER
COLORS[CADETBLUE.name] = CADETBLUE
COLORS[CADETBLUE1.name] = CADETBLUE1
COLORS[CADETBLUE2.name] = CADETBLUE2
COLORS[CADETBLUE3.name] = CADETBLUE3
COLORS[CADETBLUE4.name] = CADETBLUE4
COLORS[CADMIUMORANGE.name] = CADMIUMORANGE
COLORS[CADMIUMYELLOW.name] = CADMIUMYELLOW
COLORS[CARROT.name] = CARROT
COLORS[CHARTREUSE1.name] = CHARTREUSE1
COLORS[CHARTREUSE2.name] = CHARTREUSE2
COLORS[CHARTREUSE3.name] = CHARTREUSE3
COLORS[CHARTREUSE4.name] = CHARTREUSE4
COLORS[CHOCOLATE.name] = CHOCOLATE
COLORS[CHOCOLATE1.name] = CHOCOLATE1
COLORS[CHOCOLATE2.name] = CHOCOLATE2
COLORS[CHOCOLATE3.name] = CHOCOLATE3
COLORS[CHOCOLATE4.name] = CHOCOLATE4
COLORS[COBALT.name] = COBALT
COLORS[COBALTGREEN.name] = COBALTGREEN
COLORS[COLDGREY.name] = COLDGREY
COLORS[CORAL.name] = CORAL
COLORS[CORAL1.name] = CORAL1
COLORS[CORAL2.name] = CORAL2
COLORS[CORAL3.name] = CORAL3
COLORS[CORAL4.name] = CORAL4
COLORS[CORNFLOWERBLUE.name] = CORNFLOWERBLUE
COLORS[CORNSILK1.name] = CORNSILK1
COLORS[CORNSILK2.name] = CORNSILK2
COLORS[CORNSILK3.name] = CORNSILK3
COLORS[CORNSILK4.name] = CORNSILK4
COLORS[CRIMSON.name] = CRIMSON
COLORS[CYAN2.name] = CYAN2
COLORS[CYAN3.name] = CYAN3
COLORS[CYAN4.name] = CYAN4
COLORS[DARKGOLDENROD.name] = DARKGOLDENROD
COLORS[DARKGOLDENROD1.name] = DARKGOLDENROD1
COLORS[DARKGOLDENROD2.name] = DARKGOLDENROD2
COLORS[DARKGOLDENROD3.name] = DARKGOLDENROD3
COLORS[DARKGOLDENROD4.name] = DARKGOLDENROD4
COLORS[DARKGRAY.name] = DARKGRAY
COLORS[DARKGREEN.name] = DARKGREEN
COLORS[DARKKHAKI.name] = DARKKHAKI
COLORS[DARKOLIVEGREEN.name] = DARKOLIVEGREEN
COLORS[DARKOLIVEGREEN1.name] = DARKOLIVEGREEN1
COLORS[DARKOLIVEGREEN2.name] = DARKOLIVEGREEN2
COLORS[DARKOLIVEGREEN3.name] = DARKOLIVEGREEN3
COLORS[DARKOLIVEGREEN4.name] = DARKOLIVEGREEN4
COLORS[DARKORANGE.name] = DARKORANGE
COLORS[DARKORANGE1.name] = DARKORANGE1
COLORS[DARKORANGE2.name] = DARKORANGE2
COLORS[DARKORANGE3.name] = DARKORANGE3
COLORS[DARKORANGE4.name] = DARKORANGE4
COLORS[DARKORCHID.name] = DARKORCHID
COLORS[DARKORCHID1.name] = DARKORCHID1
COLORS[DARKORCHID2.name] = DARKORCHID2
COLORS[DARKORCHID3.name] = DARKORCHID3
COLORS[DARKORCHID4.name] = DARKORCHID4
COLORS[DARKSALMON.name] = DARKSALMON
COLORS[DARKSEAGREEN.name] = DARKSEAGREEN
COLORS[DARKSEAGREEN1.name] = DARKSEAGREEN1
COLORS[DARKSEAGREEN2.name] = DARKSEAGREEN2
COLORS[DARKSEAGREEN3.name] = DARKSEAGREEN3
COLORS[DARKSEAGREEN4.name] = DARKSEAGREEN4
COLORS[DARKSLATEBLUE.name] = DARKSLATEBLUE
COLORS[DARKSLATEGRAY.name] = DARKSLATEGRAY
COLORS[DARKSLATEGRAY1.name] = DARKSLATEGRAY1
COLORS[DARKSLATEGRAY2.name] = DARKSLATEGRAY2
COLORS[DARKSLATEGRAY3.name] = DARKSLATEGRAY3
COLORS[DARKSLATEGRAY4.name] = DARKSLATEGRAY4
COLORS[DARKTURQUOISE.name] = DARKTURQUOISE
COLORS[DARKVIOLET.name] = DARKVIOLET
COLORS[DEEPPINK1.name] = DEEPPINK1
COLORS[DEEPPINK2.name] = DEEPPINK2
COLORS[DEEPPINK3.name] = DEEPPINK3
COLORS[DEEPPINK4.name] = DEEPPINK4
COLORS[DEEPSKYBLUE1.name] = DEEPSKYBLUE1
COLORS[DEEPSKYBLUE2.name] = DEEPSKYBLUE2
COLORS[DEEPSKYBLUE3.name] = DEEPSKYBLUE3
COLORS[DEEPSKYBLUE4.name] = DEEPSKYBLUE4
COLORS[DIMGRAY.name] = DIMGRAY
COLORS[DIMGRAY.name] = DIMGRAY
COLORS[DODGERBLUE1.name] = DODGERBLUE1
COLORS[DODGERBLUE2.name] = DODGERBLUE2
COLORS[DODGERBLUE3.name] = DODGERBLUE3
COLORS[DODGERBLUE4.name] = DODGERBLUE4
COLORS[EGGSHELL.name] = EGGSHELL
COLORS[EMERALDGREEN.name] = EMERALDGREEN
COLORS[FIREBRICK.name] = FIREBRICK
COLORS[FIREBRICK1.name] = FIREBRICK1
COLORS[FIREBRICK2.name] = FIREBRICK2
COLORS[FIREBRICK3.name] = FIREBRICK3
COLORS[FIREBRICK4.name] = FIREBRICK4
COLORS[FLESH.name] = FLESH
COLORS[FLORALWHITE.name] = FLORALWHITE
COLORS[FORESTGREEN.name] = FORESTGREEN
COLORS[GAINSBORO.name] = GAINSBORO
COLORS[GHOSTWHITE.name] = GHOSTWHITE
COLORS[GOLD1.name] = GOLD1
COLORS[GOLD2.name] = GOLD2
COLORS[GOLD3.name] = GOLD3
COLORS[GOLD4.name] = GOLD4
COLORS[GOLDENROD.name] = GOLDENROD
COLORS[GOLDENROD1.name] = GOLDENROD1
COLORS[GOLDENROD2.name] = GOLDENROD2
COLORS[GOLDENROD3.name] = GOLDENROD3
COLORS[GOLDENROD4.name] = GOLDENROD4
COLORS[GRAY.name] = GRAY
COLORS[GRAY1.name] = GRAY1
COLORS[GRAY10.name] = GRAY10
COLORS[GRAY11.name] = GRAY11
COLORS[GRAY12.name] = GRAY12
COLORS[GRAY13.name] = GRAY13
COLORS[GRAY14.name] = GRAY14
COLORS[GRAY15.name] = GRAY15
COLORS[GRAY16.name] = GRAY16
COLORS[GRAY17.name] = GRAY17
COLORS[GRAY18.name] = GRAY18
COLORS[GRAY19.name] = GRAY19
COLORS[GRAY2.name] = GRAY2
COLORS[GRAY20.name] = GRAY20
COLORS[GRAY21.name] = GRAY21
COLORS[GRAY22.name] = GRAY22
COLORS[GRAY23.name] = GRAY23
COLORS[GRAY24.name] = GRAY24
COLORS[GRAY25.name] = GRAY25
COLORS[GRAY26.name] = GRAY26
COLORS[GRAY27.name] = GRAY27
COLORS[GRAY28.name] = GRAY28
COLORS[GRAY29.name] = GRAY29
COLORS[GRAY3.name] = GRAY3
COLORS[GRAY30.name] = GRAY30
COLORS[GRAY31.name] = GRAY31
COLORS[GRAY32.name] = GRAY32
COLORS[GRAY33.name] = GRAY33
COLORS[GRAY34.name] = GRAY34
COLORS[GRAY35.name] = GRAY35
COLORS[GRAY36.name] = GRAY36
COLORS[GRAY37.name] = GRAY37
COLORS[GRAY38.name] = GRAY38
COLORS[GRAY39.name] = GRAY39
COLORS[GRAY4.name] = GRAY4
COLORS[GRAY40.name] = GRAY40
COLORS[GRAY42.name] = GRAY42
COLORS[GRAY43.name] = GRAY43
COLORS[GRAY44.name] = GRAY44
COLORS[GRAY45.name] = GRAY45
COLORS[GRAY46.name] = GRAY46
COLORS[GRAY47.name] = GRAY47
COLORS[GRAY48.name] = GRAY48
COLORS[GRAY49.name] = GRAY49
COLORS[GRAY5.name] = GRAY5
COLORS[GRAY50.name] = GRAY50
COLORS[GRAY51.name] = GRAY51
COLORS[GRAY52.name] = GRAY52
COLORS[GRAY53.name] = GRAY53
COLORS[GRAY54.name] = GRAY54
COLORS[GRAY55.name] = GRAY55
COLORS[GRAY56.name] = GRAY56
COLORS[GRAY57.name] = GRAY57
COLORS[GRAY58.name] = GRAY58
COLORS[GRAY59.name] = GRAY59
COLORS[GRAY6.name] = GRAY6
COLORS[GRAY60.name] = GRAY60
COLORS[GRAY61.name] = GRAY61
COLORS[GRAY62.name] = GRAY62
COLORS[GRAY63.name] = GRAY63
COLORS[GRAY64.name] = GRAY64
COLORS[GRAY65.name] = GRAY65
COLORS[GRAY66.name] = GRAY66
COLORS[GRAY67.name] = GRAY67
COLORS[GRAY68.name] = GRAY68
COLORS[GRAY69.name] = GRAY69
COLORS[GRAY7.name] = GRAY7
COLORS[GRAY70.name] = GRAY70
COLORS[GRAY71.name] = GRAY71
COLORS[GRAY72.name] = GRAY72
COLORS[GRAY73.name] = GRAY73
COLORS[GRAY74.name] = GRAY74
COLORS[GRAY75.name] = GRAY75
COLORS[GRAY76.name] = GRAY76
COLORS[GRAY77.name] = GRAY77
COLORS[GRAY78.name] = GRAY78
COLORS[GRAY79.name] = GRAY79
COLORS[GRAY8.name] = GRAY8
COLORS[GRAY80.name] = GRAY80
COLORS[GRAY81.name] = GRAY81
COLORS[GRAY82.name] = GRAY82
COLORS[GRAY83.name] = GRAY83
COLORS[GRAY84.name] = GRAY84
COLORS[GRAY85.name] = GRAY85
COLORS[GRAY86.name] = GRAY86
COLORS[GRAY87.name] = GRAY87
COLORS[GRAY88.name] = GRAY88
COLORS[GRAY89.name] = GRAY89
COLORS[GRAY9.name] = GRAY9
COLORS[GRAY90.name] = GRAY90
COLORS[GRAY91.name] = GRAY91
COLORS[GRAY92.name] = GRAY92
COLORS[GRAY93.name] = GRAY93
COLORS[GRAY94.name] = GRAY94
COLORS[GRAY95.name] = GRAY95
COLORS[GRAY97.name] = GRAY97
COLORS[GRAY98.name] = GRAY98
COLORS[GRAY99.name] = GRAY99
COLORS[GREEN.name] = GREEN
COLORS[GREEN1.name] = GREEN1
COLORS[GREEN2.name] = GREEN2
COLORS[GREEN3.name] = GREEN3
COLORS[GREEN4.name] = GREEN4
COLORS[GREENYELLOW.name] = GREENYELLOW
COLORS[HONEYDEW1.name] = HONEYDEW1
COLORS[HONEYDEW2.name] = HONEYDEW2
COLORS[HONEYDEW3.name] = HONEYDEW3
COLORS[HONEYDEW4.name] = HONEYDEW4
COLORS[HOTPINK.name] = HOTPINK
COLORS[HOTPINK1.name] = HOTPINK1
COLORS[HOTPINK2.name] = HOTPINK2
COLORS[HOTPINK3.name] = HOTPINK3
COLORS[HOTPINK4.name] = HOTPINK4
COLORS[INDIANRED.name] = INDIANRED
COLORS[INDIANRED.name] = INDIANRED
COLORS[INDIANRED1.name] = INDIANRED1
COLORS[INDIANRED2.name] = INDIANRED2
COLORS[INDIANRED3.name] = INDIANRED3
COLORS[INDIANRED4.name] = INDIANRED4
COLORS[INDIGO.name] = INDIGO
COLORS[IVORY1.name] = IVORY1
COLORS[IVORY2.name] = IVORY2
COLORS[IVORY3.name] = IVORY3
COLORS[IVORY4.name] = IVORY4
COLORS[IVORYBLACK.name] = IVORYBLACK
COLORS[KHAKI.name] = KHAKI
COLORS[KHAKI1.name] = KHAKI1
COLORS[KHAKI2.name] = KHAKI2
COLORS[KHAKI3.name] = KHAKI3
COLORS[KHAKI4.name] = KHAKI4
COLORS[LAVENDER.name] = LAVENDER
COLORS[LAVENDERBLUSH1.name] = LAVENDERBLUSH1
COLORS[LAVENDERBLUSH2.name] = LAVENDERBLUSH2
COLORS[LAVENDERBLUSH3.name] = LAVENDERBLUSH3
COLORS[LAVENDERBLUSH4.name] = LAVENDERBLUSH4
COLORS[LAWNGREEN.name] = LAWNGREEN
COLORS[LEMONCHIFFON1.name] = LEMONCHIFFON1
COLORS[LEMONCHIFFON2.name] = LEMONCHIFFON2
COLORS[LEMONCHIFFON3.name] = LEMONCHIFFON3
COLORS[LEMONCHIFFON4.name] = LEMONCHIFFON4
COLORS[LIGHTBLUE.name] = LIGHTBLUE
COLORS[LIGHTBLUE1.name] = LIGHTBLUE1
COLORS[LIGHTBLUE2.name] = LIGHTBLUE2
COLORS[LIGHTBLUE3.name] = LIGHTBLUE3
COLORS[LIGHTBLUE4.name] = LIGHTBLUE4
COLORS[LIGHTCORAL.name] = LIGHTCORAL
COLORS[LIGHTCYAN1.name] = LIGHTCYAN1
COLORS[LIGHTCYAN2.name] = LIGHTCYAN2
COLORS[LIGHTCYAN3.name] = LIGHTCYAN3
COLORS[LIGHTCYAN4.name] = LIGHTCYAN4
COLORS[LIGHTGOLDENROD1.name] = LIGHTGOLDENROD1
COLORS[LIGHTGOLDENROD2.name] = LIGHTGOLDENROD2
COLORS[LIGHTGOLDENROD3.name] = LIGHTGOLDENROD3
COLORS[LIGHTGOLDENROD4.name] = LIGHTGOLDENROD4
COLORS[LIGHTGOLDENRODYELLOW.name] = LIGHTGOLDENRODYELLOW
COLORS[LIGHTGREY.name] = LIGHTGREY
COLORS[LIGHTPINK.name] = LIGHTPINK
COLORS[LIGHTPINK1.name] = LIGHTPINK1
COLORS[LIGHTPINK2.name] = LIGHTPINK2
COLORS[LIGHTPINK3.name] = LIGHTPINK3
COLORS[LIGHTPINK4.name] = LIGHTPINK4
COLORS[LIGHTSALMON1.name] = LIGHTSALMON1
COLORS[LIGHTSALMON2.name] = LIGHTSALMON2
COLORS[LIGHTSALMON3.name] = LIGHTSALMON3
COLORS[LIGHTSALMON4.name] = LIGHTSALMON4
COLORS[LIGHTSEAGREEN.name] = LIGHTSEAGREEN
COLORS[LIGHTSKYBLUE.name] = LIGHTSKYBLUE
COLORS[LIGHTSKYBLUE1.name] = LIGHTSKYBLUE1
COLORS[LIGHTSKYBLUE2.name] = LIGHTSKYBLUE2
COLORS[LIGHTSKYBLUE3.name] = LIGHTSKYBLUE3
COLORS[LIGHTSKYBLUE4.name] = LIGHTSKYBLUE4
COLORS[LIGHTSLATEBLUE.name] = LIGHTSLATEBLUE
COLORS[LIGHTSLATEGRAY.name] = LIGHTSLATEGRAY
COLORS[LIGHTSTEELBLUE.name] = LIGHTSTEELBLUE
COLORS[LIGHTSTEELBLUE1.name] = LIGHTSTEELBLUE1
COLORS[LIGHTSTEELBLUE2.name] = LIGHTSTEELBLUE2
COLORS[LIGHTSTEELBLUE3.name] = LIGHTSTEELBLUE3
COLORS[LIGHTSTEELBLUE4.name] = LIGHTSTEELBLUE4
COLORS[LIGHTYELLOW1.name] = LIGHTYELLOW1
COLORS[LIGHTYELLOW2.name] = LIGHTYELLOW2
COLORS[LIGHTYELLOW3.name] = LIGHTYELLOW3
COLORS[LIGHTYELLOW4.name] = LIGHTYELLOW4
COLORS[LIMEGREEN.name] = LIMEGREEN
COLORS[LINEN.name] = LINEN
COLORS[MAGENTA.name] = MAGENTA
COLORS[MAGENTA2.name] = MAGENTA2
COLORS[MAGENTA3.name] = MAGENTA3
COLORS[MAGENTA4.name] = MAGENTA4
COLORS[MANGANESEBLUE.name] = MANGANESEBLUE
COLORS[MAROON.name] = MAROON
COLORS[MAROON1.name] = MAROON1
COLORS[MAROON2.name] = MAROON2
COLORS[MAROON3.name] = MAROON3
COLORS[MAROON4.name] = MAROON4
COLORS[MEDIUMORCHID.name] = MEDIUMORCHID
COLORS[MEDIUMORCHID1.name] = MEDIUMORCHID1
COLORS[MEDIUMORCHID2.name] = MEDIUMORCHID2
COLORS[MEDIUMORCHID3.name] = MEDIUMORCHID3
COLORS[MEDIUMORCHID4.name] = MEDIUMORCHID4
COLORS[MEDIUMPURPLE.name] = MEDIUMPURPLE
COLORS[MEDIUMPURPLE1.name] = MEDIUMPURPLE1
COLORS[MEDIUMPURPLE2.name] = MEDIUMPURPLE2
COLORS[MEDIUMPURPLE3.name] = MEDIUMPURPLE3
COLORS[MEDIUMPURPLE4.name] = MEDIUMPURPLE4
COLORS[MEDIUMSEAGREEN.name] = MEDIUMSEAGREEN
COLORS[MEDIUMSLATEBLUE.name] = MEDIUMSLATEBLUE
COLORS[MEDIUMSPRINGGREEN.name] = MEDIUMSPRINGGREEN
COLORS[MEDIUMTURQUOISE.name] = MEDIUMTURQUOISE
COLORS[MEDIUMVIOLETRED.name] = MEDIUMVIOLETRED
COLORS[MELON.name] = MELON
COLORS[MIDNIGHTBLUE.name] = MIDNIGHTBLUE
COLORS[MINT.name] = MINT
COLORS[MINTCREAM.name] = MINTCREAM
COLORS[MISTYROSE1.name] = MISTYROSE1
COLORS[MISTYROSE2.name] = MISTYROSE2
COLORS[MISTYROSE3.name] = MISTYROSE3
COLORS[MISTYROSE4.name] = MISTYROSE4
COLORS[MOCCASIN.name] = MOCCASIN
COLORS[NAVAJOWHITE1.name] = NAVAJOWHITE1
COLORS[NAVAJOWHITE2.name] = NAVAJOWHITE2
COLORS[NAVAJOWHITE3.name] = NAVAJOWHITE3
COLORS[NAVAJOWHITE4.name] = NAVAJOWHITE4
COLORS[NAVY.name] = NAVY
COLORS[OLDLACE.name] = OLDLACE
COLORS[OLIVE.name] = OLIVE
COLORS[OLIVEDRAB.name] = OLIVEDRAB
COLORS[OLIVEDRAB1.name] = OLIVEDRAB1
COLORS[OLIVEDRAB2.name] = OLIVEDRAB2
COLORS[OLIVEDRAB3.name] = OLIVEDRAB3
COLORS[OLIVEDRAB4.name] = OLIVEDRAB4
COLORS[ORANGE.name] = ORANGE
COLORS[ORANGE1.name] = ORANGE1
COLORS[ORANGE2.name] = ORANGE2
COLORS[ORANGE3.name] = ORANGE3
COLORS[ORANGE4.name] = ORANGE4
COLORS[ORANGERED1.name] = ORANGERED1
COLORS[ORANGERED2.name] = ORANGERED2
COLORS[ORANGERED3.name] = ORANGERED3
COLORS[ORANGERED4.name] = ORANGERED4
COLORS[ORCHID.name] = ORCHID
COLORS[ORCHID1.name] = ORCHID1
COLORS[ORCHID2.name] = ORCHID2
COLORS[ORCHID3.name] = ORCHID3
COLORS[ORCHID4.name] = ORCHID4
COLORS[PALEGOLDENROD.name] = PALEGOLDENROD
COLORS[PALEGREEN.name] = PALEGREEN
COLORS[PALEGREEN1.name] = PALEGREEN1
COLORS[PALEGREEN2.name] = PALEGREEN2
COLORS[PALEGREEN3.name] = PALEGREEN3
COLORS[PALEGREEN4.name] = PALEGREEN4
COLORS[PALETURQUOISE1.name] = PALETURQUOISE1
COLORS[PALETURQUOISE2.name] = PALETURQUOISE2
COLORS[PALETURQUOISE3.name] = PALETURQUOISE3
COLORS[PALETURQUOISE4.name] = PALETURQUOISE4
COLORS[PALEVIOLETRED.name] = PALEVIOLETRED
COLORS[PALEVIOLETRED1.name] = PALEVIOLETRED1
COLORS[PALEVIOLETRED2.name] = PALEVIOLETRED2
COLORS[PALEVIOLETRED3.name] = PALEVIOLETRED3
COLORS[PALEVIOLETRED4.name] = PALEVIOLETRED4
COLORS[PAPAYAWHIP.name] = PAPAYAWHIP
COLORS[PEACHPUFF1.name] = PEACHPUFF1
COLORS[PEACHPUFF2.name] = PEACHPUFF2
COLORS[PEACHPUFF3.name] = PEACHPUFF3
COLORS[PEACHPUFF4.name] = PEACHPUFF4
COLORS[PEACOCK.name] = PEACOCK
COLORS[PINK.name] = PINK
COLORS[PINK1.name] = PINK1
COLORS[PINK2.name] = PINK2
COLORS[PINK3.name] = PINK3
COLORS[PINK4.name] = PINK4
COLORS[PLUM.name] = PLUM
COLORS[PLUM1.name] = PLUM1
COLORS[PLUM2.name] = PLUM2
COLORS[PLUM3.name] = PLUM3
COLORS[PLUM4.name] = PLUM4
COLORS[POWDERBLUE.name] = POWDERBLUE
COLORS[PURPLE.name] = PURPLE
COLORS[PURPLE1.name] = PURPLE1
COLORS[PURPLE2.name] = PURPLE2
COLORS[PURPLE3.name] = PURPLE3
COLORS[PURPLE4.name] = PURPLE4
COLORS[RASPBERRY.name] = RASPBERRY
COLORS[RAWSIENNA.name] = RAWSIENNA
COLORS[RED1.name] = RED1
COLORS[RED2.name] = RED2
COLORS[RED3.name] = RED3
COLORS[RED4.name] = RED4
COLORS[ROSYBROWN.name] = ROSYBROWN
COLORS[ROSYBROWN1.name] = ROSYBROWN1
COLORS[ROSYBROWN2.name] = ROSYBROWN2
COLORS[ROSYBROWN3.name] = ROSYBROWN3
COLORS[ROSYBROWN4.name] = ROSYBROWN4
COLORS[ROYALBLUE.name] = ROYALBLUE
COLORS[ROYALBLUE1.name] = ROYALBLUE1
COLORS[ROYALBLUE2.name] = ROYALBLUE2
COLORS[ROYALBLUE3.name] = ROYALBLUE3
COLORS[ROYALBLUE4.name] = ROYALBLUE4
COLORS[SALMON.name] = SALMON
COLORS[SALMON1.name] = SALMON1
COLORS[SALMON2.name] = SALMON2
COLORS[SALMON3.name] = SALMON3
COLORS[SALMON4.name] = SALMON4
COLORS[SANDYBROWN.name] = SANDYBROWN
COLORS[SAPGREEN.name] = SAPGREEN
COLORS[SEAGREEN1.name] = SEAGREEN1
COLORS[SEAGREEN2.name] = SEAGREEN2
COLORS[SEAGREEN3.name] = SEAGREEN3
COLORS[SEAGREEN4.name] = SEAGREEN4
COLORS[SEASHELL1.name] = SEASHELL1
COLORS[SEASHELL2.name] = SEASHELL2
COLORS[SEASHELL3.name] = SEASHELL3
COLORS[SEASHELL4.name] = SEASHELL4
COLORS[SEPIA.name] = SEPIA
COLORS[SGIBEET.name] = SGIBEET
COLORS[SGIBRIGHTGRAY.name] = SGIBRIGHTGRAY
COLORS[SGICHARTREUSE.name] = SGICHARTREUSE
COLORS[SGIDARKGRAY.name] = SGIDARKGRAY
COLORS[SGIGRAY12.name] = SGIGRAY12
COLORS[SGIGRAY16.name] = SGIGRAY16
COLORS[SGIGRAY32.name] = SGIGRAY32
COLORS[SGIGRAY36.name] = SGIGRAY36
COLORS[SGIGRAY52.name] = SGIGRAY52
COLORS[SGIGRAY56.name] = SGIGRAY56
COLORS[SGIGRAY72.name] = SGIGRAY72
COLORS[SGIGRAY76.name] = SGIGRAY76
COLORS[SGIGRAY92.name] = SGIGRAY92
COLORS[SGIGRAY96.name] = SGIGRAY96
COLORS[SGILIGHTBLUE.name] = SGILIGHTBLUE
COLORS[SGILIGHTGRAY.name] = SGILIGHTGRAY
COLORS[SGIOLIVEDRAB.name] = SGIOLIVEDRAB
COLORS[SGISALMON.name] = SGISALMON
COLORS[SGISLATEBLUE.name] = SGISLATEBLUE
COLORS[SGITEAL.name] = SGITEAL
COLORS[SIENNA.name] = SIENNA
COLORS[SIENNA1.name] = SIENNA1
COLORS[SIENNA2.name] = SIENNA2
COLORS[SIENNA3.name] = SIENNA3
COLORS[SIENNA4.name] = SIENNA4
COLORS[SILVER.name] = SILVER
COLORS[SKYBLUE.name] = SKYBLUE
COLORS[SKYBLUE1.name] = SKYBLUE1
COLORS[SKYBLUE2.name] = SKYBLUE2
COLORS[SKYBLUE3.name] = SKYBLUE3
COLORS[SKYBLUE4.name] = SKYBLUE4
COLORS[SLATEBLUE.name] = SLATEBLUE
COLORS[SLATEBLUE1.name] = SLATEBLUE1
COLORS[SLATEBLUE2.name] = SLATEBLUE2
COLORS[SLATEBLUE3.name] = SLATEBLUE3
COLORS[SLATEBLUE4.name] = SLATEBLUE4
COLORS[SLATEGRAY.name] = SLATEGRAY
COLORS[SLATEGRAY1.name] = SLATEGRAY1
COLORS[SLATEGRAY2.name] = SLATEGRAY2
COLORS[SLATEGRAY3.name] = SLATEGRAY3
COLORS[SLATEGRAY4.name] = SLATEGRAY4
COLORS[SNOW1.name] = SNOW1
COLORS[SNOW2.name] = SNOW2
COLORS[SNOW3.name] = SNOW3
COLORS[SNOW4.name] = SNOW4
COLORS[SPRINGGREEN.name] = SPRINGGREEN
COLORS[SPRINGGREEN1.name] = SPRINGGREEN1
COLORS[SPRINGGREEN2.name] = SPRINGGREEN2
COLORS[SPRINGGREEN3.name] = SPRINGGREEN3
COLORS[STEELBLUE.name] = STEELBLUE
COLORS[STEELBLUE1.name] = STEELBLUE1
COLORS[STEELBLUE2.name] = STEELBLUE2
COLORS[STEELBLUE3.name] = STEELBLUE3
COLORS[STEELBLUE4.name] = STEELBLUE4
COLORS[TAN.name] = TAN
COLORS[TAN1.name] = TAN1
COLORS[TAN2.name] = TAN2
COLORS[TAN3.name] = TAN3
COLORS[TAN4.name] = TAN4
COLORS[TEAL.name] = TEAL
COLORS[THISTLE.name] = THISTLE
COLORS[THISTLE1.name] = THISTLE1
COLORS[THISTLE2.name] = THISTLE2
COLORS[THISTLE3.name] = THISTLE3
COLORS[THISTLE4.name] = THISTLE4
COLORS[TOMATO1.name] = TOMATO1
COLORS[TOMATO2.name] = TOMATO2
COLORS[TOMATO3.name] = TOMATO3
COLORS[TOMATO4.name] = TOMATO4
COLORS[TURQUOISE.name] = TURQUOISE
COLORS[TURQUOISE1.name] = TURQUOISE1
COLORS[TURQUOISE2.name] = TURQUOISE2
COLORS[TURQUOISE3.name] = TURQUOISE3
COLORS[TURQUOISE4.name] = TURQUOISE4
COLORS[TURQUOISEBLUE.name] = TURQUOISEBLUE
COLORS[VIOLET.name] = VIOLET
COLORS[VIOLETRED.name] = VIOLETRED
COLORS[VIOLETRED1.name] = VIOLETRED1
COLORS[VIOLETRED2.name] = VIOLETRED2
COLORS[VIOLETRED3.name] = VIOLETRED3
COLORS[VIOLETRED4.name] = VIOLETRED4
COLORS[WARMGREY.name] = WARMGREY
COLORS[WHEAT.name] = WHEAT
COLORS[WHEAT1.name] = WHEAT1
COLORS[WHEAT2.name] = WHEAT2
COLORS[WHEAT3.name] = WHEAT3
COLORS[WHEAT4.name] = WHEAT4
COLORS[WHITE.name] = WHITE
COLORS[WHITESMOKE.name] = WHITESMOKE
COLORS[WHITESMOKE.name] = WHITESMOKE
COLORS[YELLOW1.name] = YELLOW1
COLORS[YELLOW2.name] = YELLOW2
COLORS[YELLOW3.name] = YELLOW3
COLORS[YELLOW4.name] = YELLOW4

COLORS = OrderedDict(sorted(COLORS.items(), key=lambda t: t[0]))
