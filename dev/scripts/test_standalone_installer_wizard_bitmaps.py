"""Host-free regression test for the Inno Setup wizard bitmaps (#3758).

Setup passes a wizard image's DIB header and pixels, without any trailing data,
to GDI ``CreateDIBSection``. When the BMP uses a ``BITMAPV5HEADER`` with an
embedded colour profile, Windows reads the profile past the end of that buffer
and Setup intermittently dies with an access violation in ``ucrtbase.dll``.
Wizard bitmaps must therefore use a plain ``BITMAPINFOHEADER``.
"""

import glob
import os
import re
import struct
import unittest


TEST_ENVIRONMENT = "HostFree"
TEST_LEVEL = "Integration"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RELEASE_DIR = os.path.join(REPO_ROOT, "release")
BITMAP_INFO_HEADER_SIZE = 40
BI_RGB = 0
WIZARD_DIRECTIVE = re.compile(
    r"^Wizard(?:Small)?ImageFile\s*=\s*(?P<path>.+?)\s*$", re.MULTILINE
)


def _wizard_bitmaps():
    bitmaps = {}
    for script in sorted(glob.glob(os.path.join(RELEASE_DIR, "*.iss"))):
        with open(script, encoding="utf-8-sig") as handle:
            for match in WIZARD_DIRECTIVE.finditer(handle.read()):
                relative = match.group("path").replace("\\", os.sep)
                path = os.path.normpath(os.path.join(RELEASE_DIR, relative))
                bitmaps.setdefault(path, []).append(os.path.basename(script))
    return bitmaps


class WizardBitmapTests(unittest.TestCase):
    def test_installer_scripts_reference_wizard_bitmaps(self):
        self.assertGreaterEqual(len(_wizard_bitmaps()), 3)

    def test_wizard_bitmaps_use_plain_info_header(self):
        for path, scripts in _wizard_bitmaps().items():
            with self.subTest(bitmap=os.path.basename(path), scripts=scripts):
                with open(path, "rb") as handle:
                    data = handle.read()
                self.assertEqual(data[:2], b"BM")
                (header_size,) = struct.unpack_from("<I", data, 14)
                self.assertEqual(
                    header_size,
                    BITMAP_INFO_HEADER_SIZE,
                    "re-save the bitmap with a BITMAPINFOHEADER and no colour space",
                )

    def test_wizard_bitmaps_have_no_trailing_data(self):
        for path in _wizard_bitmaps():
            with self.subTest(bitmap=os.path.basename(path)):
                with open(path, "rb") as handle:
                    data = handle.read()
                (pixel_offset,) = struct.unpack_from("<I", data, 10)
                width, height, _, bits_per_pixel, compression = struct.unpack_from(
                    "<iiHHI", data, 18
                )
                self.assertEqual(compression, BI_RGB)
                row_stride = (width * bits_per_pixel + 31) // 32 * 4
                self.assertEqual(len(data), pixel_offset + row_stride * abs(height))


if __name__ == "__main__":
    unittest.main()
