from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import PIL.Image

from tools.blueprint import Voxel
from tools.render import BACKGROUND, figure, front, portrait, side, sheet

RED = (200, 0, 0)
BLUE = (0, 0, 200)


def voxel(x, y, z, colour=RED):
    return Voxel(x, y, z, *colour, 0, 21)


class ProjectionTests(unittest.TestCase):
    def test_the_front_view_widens_on_x_and_heightens_on_y(self):
        grid = front([voxel(0, 0, 0), voxel(2, 1, 0)], size=(3, 2, 1))
        self.assertEqual(len(grid), 2)
        self.assertEqual(grid[0], [RED, None, None])   # row 0 is y = 0
        self.assertEqual(grid[1], [None, None, RED])   # row 1 is y = 1

    def test_the_nearest_voxel_wins_a_column(self):
        voxels = [voxel(0, 0, 4, BLUE), voxel(0, 0, 9, RED)]
        self.assertEqual(front(voxels, size=(1, 1, 10))[0][0], RED)
        self.assertEqual(front(voxels, size=(1, 1, 10), near="far")[0][0], BLUE)

    def test_the_side_view_widens_on_z_and_heightens_on_y(self):
        grid = side([voxel(0, 0, 0, RED), voxel(0, 1, 3, BLUE)], size=(1, 2, 4))
        self.assertEqual(grid[0], [RED, None, None, None])
        self.assertEqual(grid[1], [None, None, None, BLUE])

    def test_an_empty_model_projects_to_nothing(self):
        self.assertEqual(front([], size=(0, 0, 0)), [])
        self.assertEqual(side([], size=(0, 0, 0)), [])


class FigureTests(unittest.TestCase):
    def test_parts_compose_in_one_shared_bone_frame(self):
        """A part's `pos` is where its grid sits on the bone, so a figure is the union of
        every part placed at its own pos - the only way to see whether the set fits."""
        parts = [("torso", [voxel(0, 0, 0, RED)], (-1, 0, 0)), ("hand", [voxel(0, 0, 0, BLUE)], (1, 0, 0))]
        self.assertEqual(figure(parts), [[RED, None, BLUE]])

    def test_a_higher_part_sits_above(self):
        parts = [("hips", [voxel(0, 0, 0, RED)], (0, 0, 0)), ("torso", [voxel(0, 0, 0, BLUE)], (0, 3, 0))]
        self.assertEqual(figure(parts, view=front), [[RED], [None], [None], [BLUE]])

    def test_the_nearest_part_wins_where_two_parts_overlap(self):
        parts = [("a", [voxel(0, 0, 0, BLUE)], (0, 0, 0)), ("b", [voxel(0, 0, 0, RED)], (0, 0, 4))]
        self.assertEqual(figure(parts), [[RED]])

    def test_a_portrait_is_the_figure_front_then_side(self):
        parts = [("torso", [voxel(0, 0, 0, RED)], (-1, 0, 0)), ("hand", [voxel(0, 0, 0, BLUE)], (1, 0, 0))]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "figure.png"
            size = portrait(parts, target, scale=8)
            with PIL.Image.open(target) as opened:
                image = opened.convert("RGB")
            self.assertEqual(size, ((3 + 2 + 1) * 8, 8))   # 3 wide front, gap, 1 wide side
            self.assertEqual(image.getpixel((0, 0)), RED)
            self.assertEqual(image.getpixel((8, 0)), BACKGROUND)   # the empty column between them
            self.assertEqual(image.getpixel((16, 0)), BLUE)
            self.assertEqual(image.getpixel((40, 0)), BLUE)        # the side view, after the gap


class SheetTests(unittest.TestCase):
    def render(self, models=(), **options):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "preview.png"
            if not models:
                models = [("torso", [voxel(0, 0, 0)], (1, 1, 1))]
            size = sheet(models, target, **options)
            with PIL.Image.open(target) as image:
                pixels = image.convert("RGB")
            return size, pixels

    def test_a_cell_is_the_front_view_then_the_side_view_then_the_label(self):
        size, image = self.render(scale=6, label_height=10)
        self.assertEqual(size, (3 * 6, 1 * 6 + 10))   # 1 wide + 1 gap + 1 wide
        self.assertEqual(image.getpixel((3, 3)), RED)
        self.assertEqual(image.getpixel((2 * 6 + 3, 3)), RED)

    def test_the_label_strip_under_a_cell_holds_text(self):
        size, image = self.render(scale=6, label_height=12)
        strip = {image.getpixel((x, 6 + y)) for x in range(18) for y in range(12)}
        self.assertGreater(len(strip), 1)

    def test_an_emptied_part_is_a_blank_cell_not_a_crash(self):
        size, _ = self.render(models=[("shoulder", [], (0, 0, 0))], scale=6, label_height=10)
        self.assertEqual(size, (1 * 6, 10))

    def test_models_flow_into_rows_of_the_requested_width(self):
        models = [("m%d" % index, [voxel(0, 0, 0)], (1, 1, 1)) for index in range(5)]
        size, _ = self.render(models=models, scale=2, columns=2, label_height=4)
        self.assertEqual(size, (2 * (3 * 2), 3 * (1 * 2 + 4)))

    def test_a_small_part_stands_on_the_same_floor_as_a_tall_one(self):
        models = [("tall", [voxel(0, y, 0) for y in range(4)], (1, 4, 1)), ("short", [voxel(0, 0, 0, BLUE)], (1, 1, 1))]
        _, image = self.render(models=models, scale=2, columns=2, label_height=4)
        # Each cell is 4 voxels tall at scale 2, so the floor line is the pixel row y = 6.
        self.assertEqual(image.getpixel((0, 6)), RED)
        self.assertEqual(image.getpixel((6, 6)), BLUE)      # the next cell's front view
        self.assertEqual(image.getpixel((6, 0)), BACKGROUND)   # its empty rows are above, not below

    def test_the_background_is_the_gap_between_views(self):
        _, image = self.render(scale=6, label_height=10)
        self.assertEqual(image.getpixel((6, 3)), BACKGROUND)


if __name__ == "__main__":
    unittest.main()
