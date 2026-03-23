import re
import sys

def patch_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    
    # 1. Add compute_policy_entropy
    entropy_func = """
def compute_policy_entropy(visits: List[int]) -> float:
    total = sum(visits)
    if total <= 0:
        return 0.0
    import math
    entropy = 0.0
    for v in visits:
        if v > 0:
            p = v / total
            entropy -= p * math.log(p)
    return entropy

class FastMCTSNode:
"""
    content = content.replace("class FastMCTSNode:", entropy_func, 1)
    
    # 2. Add arguments to __init__
    init_old = """    def __init__(self,
                 iterations: int = 30,
                 time_limit: float = 0.5,
                 exploration_constant: float = 1.414,
                 seed: Optional[int] = None):"""
    init_new = """    def __init__(self,
                 iterations: int = 30,
                 time_limit: float = 0.5,
                 exploration_constant: float = 1.414,
                 seed: Optional[int] = None,
                 enable_diagnostics: bool = False,
                 diagnostics_sample_interval: int = 100):"""
    content = content.replace(init_old, init_new, 1)
    
    init_body_old = """        self.rng = random.Random(seed)
        self.move_generator = LegalMoveGenerator()"""
    init_body_new = """        self.rng = random.Random(seed)
        self.move_generator = LegalMoveGenerator()
        self.enable_diagnostics = enable_diagnostics
        self.diagnostics_sample_interval = diagnostics_sample_interval"""
    content = content.replace(init_body_old, init_body_new, 1)
    
    # 3. Modify think
    think_start_old = """        start_wall = time.perf_counter()
        root = FastMCTSNode()
        root.untried_moves = legal_moves.copy()

        # Run MCTS with strict time limit
        iteration = 0
        while (time.perf_counter() - start_wall < budget_s and
               iteration < self.iterations):
            self._fast_mcts_iteration(root, board, player)
            iteration += 1"""
    think_start_new = """        start_wall = time.perf_counter()
        root = FastMCTSNode()
        root.untried_moves = legal_moves.copy()

        max_depth = 0
        nodes_expanded = 0
        nodes_by_depth = {0: 1}
        best_move_trace = []

        # Run MCTS with strict time limit
        iteration = 0
        while (time.perf_counter() - start_wall < budget_s and
               iteration < self.iterations):
            depth, expanded = self._fast_mcts_iteration(root, board, player)
            
            if self.enable_diagnostics:
                if expanded:
                    nodes_expanded += 1
                    max_depth = max(max_depth, depth)
                    nodes_by_depth[depth] = nodes_by_depth.get(depth, 0) + 1
                
                if iteration > 0 and iteration % self.diagnostics_sample_interval == 0:
                    best_child = max(root.children, key=lambda c: c.visits) if root.children else None
                    if best_child and best_child.move:
                        bm = best_child.move
                        action_id = f"{bm.piece_id}-{bm.orientation}-{bm.anchor_row}-{bm.anchor_col}"
                        visits = [c.visits for c in root.children]
                        best_move_trace.append({
                            "sim": iteration,
                            "bestActionId": action_id,
                            "bestQMean": float(best_child.total_reward / best_child.visits) if best_child.visits > 0 else 0.0,
                            "entropy": float(compute_policy_entropy(visits))
                        })

            iteration += 1"""
    content = content.replace(think_start_old, think_start_new, 1)

    # 4. Modify return dict
    think_ret_old = """        best_move = root.get_best_move()
        top_moves = self._get_top_moves(root, top_n=10)
        time_spent_ms = int((time.perf_counter() - start_time) * 1000)
        # print(f"MCTS think: budget={time_budget_ms}ms, spent={time_spent_ms}ms, iterations={iteration}")
        return {
            "move": best_move if best_move else legal_moves[0],
            "stats": {
                "timeBudgetMs": time_budget_ms,
                "timeSpentMs": time_spent_ms,
                "nodesEvaluated": max(iteration, 1),
                "maxDepthReached": 2,
                "topMoves": top_moves,
            },
        }"""
    think_ret_new = """        best_move = root.get_best_move()
        top_moves = self._get_top_moves(root, top_n=10)
        time_spent_ms = int((time.perf_counter() - start_time) * 1000)
        
        policy_entropy = 0.0
        if self.enable_diagnostics and root.children:
            visits = [c.visits for c in root.children]
            policy_entropy = compute_policy_entropy(visits)

        return {
            "move": best_move if best_move else legal_moves[0],
            "stats": {
                "timeBudgetMs": time_budget_ms,
                "timeSpentMs": time_spent_ms,
                "nodesEvaluated": max(iteration, 1),
                "maxDepthReached": max_depth if self.enable_diagnostics else 2,
                "topMoves": top_moves,
                "diagnostics": {
                    "version": "v1",
                    "timeBudgetMs": int(time_budget_ms),
                    "timeSpentMs": int(time_spent_ms),
                    "simulations": max(iteration, 1),
                    "simsPerSec": int(max(iteration, 1) / (time_spent_ms / 1000.0)) if time_spent_ms > 0 else 0,
                    "rootLegalMoves": len(legal_moves),
                    "rootChildrenExpanded": len(root.children),
                    "rootPolicy": top_moves,
                    "policyEntropy": float(policy_entropy),
                    "maxDepthReached": int(max_depth),
                    "nodesExpanded": int(nodes_expanded),
                    "nodesByDepth": [{"depth": d, "nodes": n} for d, n in sorted(nodes_by_depth.items())],
                    "bestMoveTrace": best_move_trace,
                } if self.enable_diagnostics else None
            },
        }"""
    content = content.replace(think_ret_old, think_ret_new, 1)

    # 5. Modify _fast_mcts_iteration
    iter_old = """    def _fast_mcts_iteration(self, root: FastMCTSNode, board: Board, player: Player):
        \"\"\"Run one fast MCTS iteration without board copying.\"\"\"
        # Selection
        node = self._selection(root)

        # Expansion
        if not node.is_fully_expanded():
            legal_moves = self._get_cached_legal_moves(board, player)
            child = node.expand(legal_moves)
            if child is None:
                return
            node = child

        # Simulation (ultra-fast random rollout)
        reward = self._fast_rollout(board, player)

        # Backpropagation
        self._backpropagation(node, reward)"""
        
    iter_new = """    def _fast_mcts_iteration(self, root: FastMCTSNode, board: Board, player: Player):
        \"\"\"Run one fast MCTS iteration without board copying. Returns (depth, expanded_node).\"\"\"
        # Selection
        node = root
        depth = 0
        while not node.is_terminal():
            if not node.is_fully_expanded():
                break
            else:
                node = node.select_child(self.exploration_constant)
                depth += 1

        expanded = False
        # Expansion
        if not node.is_fully_expanded():
            legal_moves = self._get_cached_legal_moves(board, player)
            child = node.expand(legal_moves)
            if child is not None:
                expanded = True
                depth += 1
                node = child

        # Simulation (ultra-fast random rollout)
        reward = self._fast_rollout(board, player)

        # Backpropagation
        self._backpropagation(node, reward)

        return depth, expanded"""
    content = content.replace(iter_old, iter_new, 1)

    # Need to fix the use of _selection
    sel_old = """    def _selection(self, node: FastMCTSNode) -> FastMCTSNode:
        \"\"\"Selection phase with early termination.\"\"\"
        while not node.is_terminal():
            if not node.is_fully_expanded():
                return node
            else:
                node = node.select_child(self.exploration_constant)
        return node"""
    content = content.replace(sel_old, "", 1)


    with open(filename, 'w') as f:
        f.write(content)

patch_file("agents/fast_mcts_agent.py")
patch_file("browser_python/agents/fast_mcts_agent.py")

