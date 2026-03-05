import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MoveDeltaPanel } from '../MoveDeltaPanel';
import { useGameStore } from '../../../store/gameStore';

// Mock zustand store
vi.mock('../../../store/gameStore', () => ({
    useGameStore: vi.fn(),
}));

// Mock recharts to avoid rendering issues in jsdom
vi.mock('recharts', async () => {
    const OriginalModule = await vi.importActual<any>('recharts');
    return {
        ...OriginalModule,
        ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
        BarChart: () => <div data-testid="barchart"></div>,
        RadarChart: () => <div data-testid="radarchart"></div>,
        LineChart: () => <div data-testid="linechart"></div>,
    };
});

const mockGameState = {
    winner: 'RED',
    game_history: [
        {
            board_state: [],
            action: { piece_id: 1, orientation: 0, anchor_row: 0, anchor_col: 0 },
            player_to_move: 'RED',
            telemetry: {
                ply: 1,
                moverId: 'RED',
                deltaSelf: { frontierSize: 5, mobility: 10, deadSpace: 0 },
                deltaOppTotal: { frontierSize: -2, mobility: -5, deadSpace: 4 },
                deltaOppByPlayer: {
                    BLUE: { frontierSize: -1, mobility: -2, deadSpace: 2 },
                    YELLOW: { frontierSize: 0, mobility: -1, deadSpace: 1 },
                    GREEN: { frontierSize: -1, mobility: -2, deadSpace: 1 },
                },
                impactScore: 12.5,
                before: [
                    { playerId: 'RED', metrics: { frontierSize: 0, mobility: 0, deadSpace: 0 } },
                    { playerId: 'BLUE', metrics: { frontierSize: 5, mobility: 10, deadSpace: 0 } }
                ],
                after: [
                    { playerId: 'RED', metrics: { frontierSize: 5, mobility: 10, deadSpace: 0 } },
                    { playerId: 'BLUE', metrics: { frontierSize: 4, mobility: 8, deadSpace: 2 } }
                ]
            }
        }
    ]
};

describe('MoveDeltaPanel', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders empty state when no game is active', () => {
        (useGameStore as any).mockImplementation((selector: any) => selector({ gameState: null, setBoardOverlay: vi.fn() }));
        render(<MoveDeltaPanel />);
        expect(screen.getByText('No game active.')).toBeInTheDocument();
    });

    it('renders empty state when history has no telemetry', () => {
        (useGameStore as any).mockImplementation((selector: any) => selector({
            gameState: { game_history: [{ board_state: [] }] },
            setBoardOverlay: vi.fn()
        }));
        render(<MoveDeltaPanel />);
        expect(screen.getByText('Play some moves to see Move Delta Telemetry.')).toBeInTheDocument();
    });

    it('renders the Move Impact Delta panel with telemetry', () => {
        (useGameStore as any).mockImplementation((selector: any) => selector({
            gameState: mockGameState,
            setBoardOverlay: vi.fn()
        }));
        render(<MoveDeltaPanel />);

        expect(screen.getByText('Move Impact Delta')).toBeInTheDocument();
        expect(screen.getByText("RED's Move")).toBeInTheDocument();
        expect(screen.getByText('Ply 1 · Piece 1')).toBeInTheDocument();

        // Check if charts are rendered via mocks
        expect(screen.getAllByTestId('barchart').length).toBeGreaterThan(0);
        expect(screen.getAllByTestId('radarchart').length).toBeGreaterThan(0);
        expect(screen.getAllByTestId('linechart').length).toBeGreaterThan(0);
    });
});
