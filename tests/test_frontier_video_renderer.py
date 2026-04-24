import unittest

from analytics.heatmap.renderer import compute_frontier_cells


class TestFrontierVideoRenderer(unittest.TestCase):
    def test_red_frontier_starts_at_corner_before_first_move(self):
        grid = [[0] * 20 for _ in range(20)]

        frontier = compute_frontier_cells(grid, player_id=1)

        self.assertEqual(frontier, [(0, 0)])

    def test_red_frontier_after_single_corner_piece(self):
        grid = [[0] * 20 for _ in range(20)]
        grid[0][0] = 1

        frontier = compute_frontier_cells(grid, player_id=1)

        self.assertEqual(frontier, [(1, 1)])

    def test_red_frontier_excludes_orthogonally_adjacent_cells(self):
        grid = [[0] * 20 for _ in range(20)]
        grid[0][0] = 1
        grid[0][1] = 1

        frontier = compute_frontier_cells(grid, player_id=1)

        self.assertEqual(frontier, [(1, 2)])


if __name__ == "__main__":
    unittest.main()
