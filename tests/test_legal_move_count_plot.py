import unittest

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator
from scripts.plot_legal_move_counts import reconstruct_board_from_turn_data


class TestLegalMoveCountPlot(unittest.TestCase):
    def test_reconstructed_board_matches_legal_move_counts(self):
        board = Board()
        generator = LegalMoveGenerator()

        # Play two deterministic opening moves so the snapshot is non-trivial.
        for _ in range(2):
            player = board.current_player
            move = generator.get_legal_moves(board, player)[0]
            orientations = generator.piece_orientations_cache[move.piece_id]
            positions = move.get_positions(orientations)
            self.assertTrue(board.place_piece(positions, player, move.piece_id))

        turn_data = {
            "turn": board.move_count + 1,
            "player": board.current_player.value,
            "board_grid": board.grid.tolist(),
            "used_pieces": {
                str(player.value): sorted(board.player_pieces_used[player])
                for player in Player
            },
        }

        reconstructed = reconstruct_board_from_turn_data(turn_data)

        for player in Player:
            original_count = len(generator.get_legal_moves(board, player))
            reconstructed_count = len(generator.get_legal_moves(reconstructed, player))
            self.assertEqual(original_count, reconstructed_count)


if __name__ == "__main__":
    unittest.main()
