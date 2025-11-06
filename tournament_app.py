import streamlit as st
import pandas as pd
from collections import deque
import math
try:
    import graphviz
    HAS_GRAPHVIZ = True
except ImportError:
    HAS_GRAPHVIZ = False

# --- C Structs -> Python Classes ---
# This is a literal translation of your C structs into Python classes.

class Player:
    """Replaces the C 'Player' struct."""
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.wins = 0
        self.losses = 0
        self.seed = 0
        self.score_for = 0
        self.score_against = 0
    
    def get_pd(self):
        """Helper for point differential."""
        return self.score_for - self.score_against
    
    def __repr__(self):
        return f"<Player {self.id}: {self.name}>"

class Match:
    """Replaces the C 'Match' struct."""
    def __init__(self, match_id, round_num=0):
        self.match_id = match_id
        self.player1 = None  # Player object
        self.player2 = None  # Player object
        self.winner = None   # Player object
        self.initial_player1 = None
        self.initial_player2 = None
        self.round = round_num
        self.is_from_losers = False
        self.is_leaf = False
        self.player1_score = 0
        self.player2_score = 0
    
    def __repr__(self):
        p1 = self.player1.name if self.player1 else "TBD"
        p2 = self.player2.name if self.player2 else "TBD"
        return f"<Match {self.match_id}: {p1} vs {p2}>"

class MatchNode:
    """Replaces the C 'MatchNode' struct (the tree structure)."""
    def __init__(self, match):
        self.match = match  # Match object
        self.left = None    # Child MatchNode
        self.right = None   # Child MatchNode

class QueueNode:
    """Replaces the C 'QueueNode' struct."""
    def __init__(self, match_ptr):
        self.match_ptr = match_ptr # This will be a MatchNode
        self.next = None

class Queue:
    """Replaces the C 'Queue' struct and its functions."""
    def __init__(self):
        self.front = None
        self.rear = None
    
    def is_empty(self):
        return self.front is None
        
    def enqueue(self, match_ptr):
        """(Port of C: enqueue)"""
        if not match_ptr:
            return
        n = QueueNode(match_ptr)
        if self.rear is None:
            self.front = self.rear = n
        else:
            self.rear.next = n
            self.rear = n
    
    def dequeue_front(self):
        """(Port of C: dequeue_front)"""
        if self.front is None:
            return None
        tmp = self.front
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        return tmp.match_ptr # Return the MatchNode

    def iter_nodes(self):
        """Helper to iterate through the queue."""
        cur = self.front
        while cur:
            yield cur.match_ptr
            cur = cur.next

class PrintQueueNode:
    """Replaces the C 'PrintQueueNode' struct."""
    def __init__(self, match_ptr):
        self.match_ptr = match_ptr
        self.next = None

class PrintQueue:
    """Replaces the C 'PrintQueue' struct and its functions."""
    def __init__(self):
        self.front = None
        self.rear = None
    
    def is_empty(self):
        return self.front is None
        
    def enqueue(self, match_ptr):
        """(Port of C: pq_enqueue)"""
        n = PrintQueueNode(match_ptr)
        if self.rear is None:
            self.front = self.rear = n
        else:
            self.rear.next = n
            self.rear = n
    
    def dequeue(self):
        """(Port of C: pq_dequeue)"""
        if self.front is None:
            return None
        tmp = self.front
        match_ptr = tmp.match_ptr
        self.front = self.front.next
        if self.front is None:
            self.rear = None
        return match_ptr

class AVLNode:
    """Replaces the C 'AVLNode' struct."""
    def __init__(self, key, match_ptr):
        self.key = key
        self.match_ptr = match_ptr
        self.left = None
        self.right = None
        self.height = 1

# --- C Globals -> Streamlit Session State ---
def initialize_state():
    """(Replaces C Globals)"""
    if 'mode' not in st.session_state:
        st.session_state.mode = "None" # Replaces TournamentMode
        
    if 'players' not in st.session_state:
        st.session_state.players = [] # Replaces player_list_head (as a list)
        
    if 'player_index_by_name' not in st.session_state:
        st.session_state.player_index_by_name = {} # Replaces getPlayerByName
        
    if 'next_player_id' not in st.session_state:
        st.session_state.next_player_id = 1000
        
    if 'next_match_id' not in st.session_state:
        st.session_state.next_match_id = 100
        
    if 'bracket_root' not in st.session_state:
        st.session_state.bracket_root = None # Replaces bracket_root
        
    if 'winners_root' not in st.session_state:
        st.session_state.winners_root = None # Replaces winners_root
        
    if 'match_queue' not in st.session_state:
        st.session_state.match_queue = Queue() # Our ported Queue class
        
    if 'match_avl_root' not in st.session_state:
        st.session_state.match_avl_root = None # Replaces match_avl_root
        
    if 'losers_fifo' not in st.session_state:
        # We can use deque here as it's a simple FIFO
        st.session_state.losers_fifo = deque()
        
    if 'rr_advancement_count' not in st.session_state:
        st.session_state.rr_advancement_count = 0
        
    if 'rr_matches_completed' not in st.session_state:
        st.session_state.rr_matches_completed = 0
        
    if 'rr_num_edges' not in st.session_state:
        st.session_state.rr_num_edges = 0
        
    if 'total_matches_played' not in st.session_state:
        st.session_state.total_matches_played = 0

# --- Helper Functions (Replaced C utilities) ---

def get_player_by_name(name):
    """(Replaces C: getPlayerByName)"""
    return st.session_state.player_index_by_name.get(name)

# --- AVL Tree Functions (Ported from C) ---

def avl_height(node):
    """(Port of C: avlHeight)"""
    return node.height if node else 0

def avl_balance(node):
    """(Port of C: avlBalance)"""
    return avl_height(node.left) - avl_height(node.right) if node else 0

def avl_right_rotate(y):
    """(Port of C: avlRightRotate)"""
    x = y.left
    T2 = x.right
    x.right = y
    y.left = T2
    y.height = 1 + max(avl_height(y.left), avl_height(y.right))
    x.height = 1 + max(avl_height(x.left), avl_height(x.right))
    return x

def avl_left_rotate(x):
    """(Port of C: avlLeftRotate)"""
    y = x.right
    T2 = y.left
    y.left = x
    x.right = T2
    x.height = 1 + max(avl_height(x.left), avl_height(x.right))
    y.height = 1 + max(avl_height(y.left), avl_height(y.right))
    return y

def avl_insert(node, key, match_ptr):
    """(Port of C: avlInsert)"""
    if not node:
        return AVLNode(key, match_ptr)
    
    if key < node.key:
        node.left = avl_insert(node.left, key, match_ptr)
    elif key > node.key:
        node.right = avl_insert(node.right, key, match_ptr)
    else:
        return node # Duplicate keys not allowed

    node.height = 1 + max(avl_height(node.left), avl_height(node.right))
    balance = avl_balance(node)

    # Left Left
    if balance > 1 and key < node.left.key:
        return avl_right_rotate(node)
    # Right Right
    if balance < -1 and key > node.right.key:
        return avl_left_rotate(node)
    # Left Right
    if balance > 1 and key > node.left.key:
        node.left = avl_left_rotate(node.left)
        return avl_right_rotate(node)
    # Right Left
    if balance < -1 and key < node.right.key:
        node.right = avl_right_rotate(node.right)
        return avl_left_rotate(node)
    
    return node

def avl_search_by_key(node, key):
    """(Port of C: avlSearchByKey)"""
    if not node:
        return None
    if node.key == key:
        return node
    if key < node.key:
        return avl_search_by_key(node.left, key)
    return avl_search_by_key(node.right, key)

# --- C Logic -> Python Functions ---

def create_match_node(round_num=0):
    """(Port of C: createMatchNode)"""
    new_id = st.session_state.next_match_id
    st.session_state.next_match_id += 1
    
    new_match = Match(match_id=new_id, round_num=round_num)
    new_node = MatchNode(new_match)
    
    # Add to our AVL index
    st.session_state.match_avl_root = avl_insert(
        st.session_state.match_avl_root, 
        new_id, 
        new_node
    )
    return new_node

def register_player(name):
    """(Port of C: registerPlayer)"""
    if not name:
        st.error("Player name cannot be empty.")
        return
    if st.session_state.mode != "None":
        st.error("Cannot register players after tournament has started.")
        return
    if get_player_by_name(name):
        st.warning(f"Player '{name}' is already registered.")
        return
    
    new_id = st.session_state.next_player_id
    st.session_state.next_player_id += 1
    
    new_player = Player(id=new_id, name=name)
    
    st.session_state.players.append(new_player)
    st.session_state.player_index_by_name[name] = new_player
    
    st.success(f"Registered Player: ID {new_id}, Name: {name}")

def create_bracket_recursive(participants, start, end):
    """(Port of C: createBracketRecursive)"""
    if start == end:
        leaf_node = create_match_node(round_num=1)
        leaf_node.match.is_leaf = True
        leaf_node.match.player1 = participants[start]
        leaf_node.match.initial_player1 = participants[start]
        return leaf_node
    
    mid = start + (end - start) // 2
    
    left_child = create_bracket_recursive(participants, start, mid)
    right_child = create_bracket_recursive(participants, mid + 1, end)
    
    parent_node = create_match_node()
    parent_node.left = left_child
    parent_node.right = right_child
    parent_node.match.round = 1 # Will be fixed later
    
    if left_child.match.is_leaf and right_child.match.is_leaf:
        parent_node.match.player1 = left_child.match.player1
        parent_node.match.player2 = right_child.match.player1 # C code had .player1
        parent_node.match.initial_player1 = left_child.match.player1
        parent_node.match.initial_player2 = right_child.match.player1
        st.session_state.match_queue.enqueue(parent_node)
    
    return parent_node

def get_max_depth(node):
    """(Port of C: getMaxDepth)"""
    if not node:
        return 0
    l = get_max_depth(node.left)
    r = get_max_depth(node.right)
    return 1 + max(l, r)

def fix_bracket_rounds(root_node):
    """Helper to fix round numbers"""
    if not root_node:
        return
    
    max_depth = get_max_depth(root_node)
    if max_depth > 1:
        max_depth -= 1 # C logic
        
    def adjust_rounds(node, current_depth):
        if not node:
            return
        if not node.match.is_leaf:
            node.match.round = max_depth - current_depth
            adjust_rounds(node.left, current_depth + 1)
            adjust_rounds(node.right, current_depth + 1)

    adjust_rounds(root_node, 0)
    
    # Fix first round matches
    q = deque([root_node])
    while q:
        node = q.popleft()
        if not node:
            continue
        if node.left and node.left.match.is_leaf and node.right and node.right.match.is_leaf:
            node.match.round = 1
        if node.left:
            q.append(node.left)
        if node.right:
            q.append(node.right)


def generate_knockout_bracket():
    """(Port of C: generateKnockoutBracket)"""
    participants = st.session_state.players
    num_players = len(participants)
    
    if num_players < 2:
        st.error("Need at least 2 players.")
        return
    
    st.session_state.match_queue = Queue() # Reset queue
    st.session_state.bracket_root = create_bracket_recursive(participants, 0, num_players - 1)
    fix_bracket_rounds(st.session_state.bracket_root)
    
    st.session_state.mode = "Knockout"
    st.success(f"Knockout bracket generated for {num_players} players.")

# --- Leaderboard Logic (Ported from C) ---
def is_player_better(p1, p2):
    """(Port of C: isPlayerBetter)"""
    if not p1: return False
    if not p2: return True
    
    if p1.wins > p2.wins: return True
    if p1.wins < p2.wins: return False
    
    if p1.losses < p2.losses: return True
    if p1.losses > p2.losses: return False
    
    p1_diff = p1.get_pd()
    p2_diff = p2.get_pd()
    if p1_diff > p2_diff: return True
    if p1_diff < p2_diff: return False
    
    if p1.id < p2.id: return True
    return False

def max_heapify(arr, n, i):
    """(Port of C: maxHeapify)"""
    largest = i
    l = 2 * i + 1
    r = 2 * i + 2
    
    if l < n and is_player_better(arr[l], arr[largest]):
        largest = l
    if r < n and is_player_better(arr[r], arr[largest]):
        largest = r
    if largest != i:
        arr[i], arr[largest] = arr[largest], arr[i] # Swap
        max_heapify(arr, n, largest)

def heap_sort(arr):
    """(Port of C: heapSort)"""
    n = len(arr)
    for i in range(n // 2 - 1, -1, -1):
        max_heapify(arr, n, i)
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0] # Swap
        max_heapify(arr, i, 0)
    return arr # Returns sorted list (ascending)

def display_leaderboard():
    """(Port of C: displayLeaderboard)"""
    if not st.session_state.players:
        st.info("No players registered yet.")
        return

    # Create a copy of the list to sort
    players_copy = list(st.session_state.players)
    
    # Sort using our ported heap_sort
    sorted_players_asc = heap_sort(players_copy)
    
    # Reverse for descending order
    sorted_players_desc = sorted_players_asc[::-1]
    
    player_data = []
    for i, p in enumerate(sorted_players_desc):
        player_data.append({
            "Rank": i + 1,
            "ID": p.id,
            "Name": p.name,
            "Wins": p.wins,
            "Losses": p.losses,
            "PD": p.get_pd(),
            "For": p.score_for,
            "Against": p.score_against,
        })

    df = pd.DataFrame(player_data)
    st.dataframe(df, hide_index=True)
    
# --- Round Robin and Double Elim (Ported from C) ---

def generate_round_robin_schedule(advancement_count):
    """(Port of C: generateRoundRobinSchedule)"""
    participants = st.session_state.players
    num_players = len(participants)
    
    if num_players < 2:
        st.error("Need at least 2 players.")
        return
        
    st.session_state.match_queue = Queue()
    st.session_state.rr_num_edges = 0
    st.session_state.rr_matches_completed = 0
    
    for i in range(num_players):
        for j in range(i + 1, num_players):
            p1 = participants[i]
            p2 = participants[j]
            
            node = create_match_node(round_num=1)
            node.match.player1 = p1
            node.match.player2 = p2
            node.match.initial_player1 = p1
            node.match.initial_player2 = p2
            
            st.session_state.match_queue.enqueue(node)
            st.session_state.rr_num_edges += 1
            
    st.session_state.mode = "Round-Robin"
    st.session_state.rr_advancement_count = advancement_count
    
    st.success(f"Round-Robin schedule created with {st.session_state.rr_num_edges} matches.")
    if advancement_count > 0:
        st.info(f"Top {advancement_count} players will advance to Knockout.")

def generate_double_elimination():
    """(Port of C: generateDoubleElimination)"""
    participants = st.session_state.players
    num_players = len(participants)
    
    if num_players < 2:
        st.error("Need at least 2 players.")
        return
    
    st.session_state.match_queue = Queue()
    st.session_state.losers_fifo = deque()
    
    for p in participants:
        p.losses = 0
        p.wins = 0
    
    st.session_state.winners_root = create_bracket_recursive(participants, 0, num_players - 1)
    fix_bracket_rounds(st.session_state.winners_root)
    
    st.session_state.mode = "Double-Elim"
    st.success(f"Double Elimination (Winners Bracket) generated for {num_players} players.")

# --- Match Update Logic (Ported from C) ---

def find_and_update_match_generic(node, match_id, winner, winner_score, loser_score):
    """(Port of C: findAndUpdateMatchGeneric)"""
    if not node:
        return False, None
        
    if node.match.match_id == match_id:
        if node.match.winner:
            st.error(f"Match {match_id} already has winner: {node.match.winner.name}")
            return True, None
        if not node.match.player1 or not node.match.player2:
            st.error(f"Match {match_id} not fully scheduled.")
            return True, None
        
        if node.match.player1.name == winner.name or node.match.player2.name == winner.name:
            node.match.winner = winner
            winner.wins += 1
            st.session_state.total_matches_played += 1
            
            loser = node.match.player2 if node.match.player1 == winner else node.match.player1
            
            winner.score_for += winner_score
            winner.score_against += loser_score
            
            if loser:
                loser.losses += 1
                loser.score_for += loser_score
                loser.score_against += winner_score
            
            if node.match.player1 == winner:
                node.match.player1_score = winner_score
                node.match.player2_score = loser_score
            else:
                node.match.player1_score = loser_score
                node.match.player2_score = winner_score
                
            st.success(f"Match {match_id} result: {winner.name} wins ({winner_score} - {loser_score})")
            return True, loser
        else:
            st.error(f"Player {winner.name} did not play in Match {match_id}")
            return True, None
    
    found, loser = find_and_update_match_generic(node.left, match_id, winner, winner_score, loser_score)
    if found:
        return True, loser
    
    found, loser = find_and_update_match_generic(node.right, match_id, winner, winner_score, loser_score)
    if found:
        return True, loser
    
    return False, None

def update_next_round_generic(node):
    """(Port of C: updateNextRoundGeneric)"""
    if not node or node.match.is_leaf:
        return
    
    if node.left and node.right and node.left.match.winner and node.right.match.winner:
        if not node.match.player1 or not node.match.player2:
            node.match.player1 = node.left.match.winner
            node.match.player2 = node.right.match.winner
            st.info(f"✨ Scheduled Match {node.match.match_id}: {node.match.player1.name} vs {node.match.player2.name}")
            st.session_state.match_queue.enqueue(node)

def check_and_schedule_generic(node):
    """(Port of C: checkAndScheduleGeneric)"""
    if not node:
        return
    if not node.match.is_leaf:
        check_and_schedule_generic(node.left)
        check_and_schedule_generic(node.right)
        update_next_round_generic(node)

def handle_double_elim_loss(loser):
    """(Port of C: handleDoubleElimLoss)"""
    if not loser: return
    # Loss is incremented in find_and_update
    if loser.losses >= 2:
        st.info(f"⛔ {loser.name} has been eliminated (2 losses).")
    else:
        st.info(f"🔽 {loser.name} moves to Losers FIFO (losses={loser.losses}).")
        st.session_state.losers_fifo.append(loser)

def schedule_losers_from_fifo():
    """(Port of C: scheduleLosersFromFIFO)"""
    while len(st.session_state.losers_fifo) >= 2:
        p1 = st.session_state.losers_fifo.popleft()
        p2 = st.session_state.losers_fifo.popleft()
        
        node = create_match_node()
        node.match.player1 = p1
        node.match.player2 = p2
        node.match.is_from_losers = True
        
        st.info(f"🔁 Scheduled Losers Match {node.match.match_id}: {p1.name} vs {p2.name}")
        st.session_state.match_queue.enqueue(node)

def schedule_grand_final_if_ready():
    """(Port of C: scheduleGrandFinalIfReady)"""
    if not st.session_state.winners_root or not st.session_state.winners_root.match.winner:
        return # Winners bracket not finished
        
    if len(st.session_state.losers_fifo) == 1:
        # Check if all other loser matches are done
        other_loser_matches_pending = False
        for node in st.session_state.match_queue.iter_nodes():
            if node.match.is_from_losers:
                other_loser_matches_pending = True
                break
        
        if not other_loser_matches_pending:
            losers_champion = st.session_state.losers_fifo.popleft()
            winners_champion = st.session_state.winners_root.match.winner
            
            node = create_match_node(round_num=99) # 99 = Grand Final
            node.match.player1 = winners_champion
            node.match.player2 = losers_champion
            
            st.info(f"🏁 GRAND FINAL: {winners_champion.name} (W) vs {losers_champion.name} (L)")
            st.session_state.match_queue.enqueue(node)

def find_and_update_match_in_all(match_id, winner, winner_score, loser_score):
    """(Port of C: findAndUpdateMatchInAll)"""
    mode = st.session_state.mode
    
    if mode == "Double-Elim":
        # 1. Check Winners Bracket
        found, loser = find_and_update_match_generic(st.session_state.winners_root, match_id, winner, winner_score, loser_score)
        if found:
            if loser:
                handle_double_elim_loss(loser)
            return True, loser
        
        # 2. Check Losers Bracket (via AVL replacement)
        avl_node = avl_search_by_key(st.session_state.match_avl_root, match_id)
        if avl_node:
            match_node = avl_node.match_ptr
            m = match_node.match
            
            if m.is_from_losers and not m.winner and \
               ((m.player1 and m.player1.name == winner.name) or \
                (m.player2 and m.player2.name == winner.name)):
                
                m.winner = winner
                winner.wins += 1
                st.session_state.total_matches_played += 1
                
                loser = m.player2 if m.player1 == winner else m.player1
                
                winner.score_for += winner_score
                winner.score_against += loser_score
                if loser:
                    loser.losses += 1
                    loser.score_for += loser_score
                    loser.score_against += winner_score
                
                if m.player1 == winner:
                    m.player1_score, m.player2_score = winner_score, loser_score
                else:
                    m.player1_score, m.player2_score = loser_score, winner_score
                
                st.success(f"Match {match_id} result: {winner.name} wins ({winner_score} - {loser_score})")
                
                # Handle loser and advancing winner
                if loser:
                    st.info(f"⛔ {loser.name} has been eliminated (2 losses).")
                st.session_state.losers_fifo.append(winner)
                return True, loser
            elif m.round == 99: # Grand Final
                return find_and_update_match_generic(avl_node.match_ptr, match_id, winner, winner_score, loser_score)
                
    elif mode == "Round-Robin":
        avl_node = avl_search_by_key(st.session_state.match_avl_root, match_id)
        if avl_node:
            match_node = avl_node.match_ptr
            m = match_node.match
            if not m.winner and \
               ((m.player1 and m.player1.name == winner.name) or \
                (m.player2 and m.player2.name == winner.name)):
                
                m.winner = winner
                winner.wins += 1
                st.session_state.total_matches_played += 1
                
                loser = m.player2 if m.player1 == winner else m.player1
                
                winner.score_for += winner_score
                winner.score_against += loser_score
                if loser:
                    loser.losses += 1
                    loser.score_for += loser_score
                    loser.score_against += winner_score
                
                if m.player1 == winner:
                    m.player1_score, m.player2_score = winner_score, loser_score
                else:
                    m.player1_score, m.player2_score = loser_score, winner_score
                
                st.success(f"Match {match_id} result: {winner.name} wins ({winner_score} - {loser_score})")
                st.session_state.rr_matches_completed += 1
                return True, loser
            elif m.winner:
                st.error(f"Match {match_id} already has winner: {m.winner.name}")
                return False, None
    
    elif mode == "Knockout":
        return find_and_update_match_generic(st.session_state.bracket_root, match_id, winner, winner_score, loser_score)

    return False, None # Match not found or not updated

def update_match_result(match_node, winner_name, winner_score, loser_score):
    """(Port of C: updateMatchResult)"""
    winner = get_player_by_name(winner_name)
    if not winner:
        st.error(f"Player '{winner_name}' not found.")
        return

    match_id = match_node.match.match_id
    
    success, loser = find_and_update_match_in_all(match_id, winner, winner_score, loser_score)
    
    if success:
        # Remove from playable queue
        # This is tricky with our C queue, we'll just leave it
        # and filter it in the UI
        
        mode = st.session_state.mode
        
        if mode == "Knockout":
            check_and_schedule_generic(st.session_state.bracket_root)
            if st.session_state.bracket_root.match.winner:
                st.balloons()
                st.success(f"👑 CHAMPION: {st.session_state.bracket_root.match.winner.name}")
        
        elif mode == "Double-Elim":
            check_and_schedule_generic(st.session_state.winners_root)
            schedule_losers_from_fifo()
            schedule_grand_final_if_ready()
            
            if match_node.match.round == 99:
                st.balloons()
                st.success(f"👑👑 GRAND CHAMPION: {winner.name} 👑👑")

        elif mode == "Round-Robin":
            count = st.session_state.rr_advancement_count
            if count > 0 and st.session_state.rr_matches_completed == st.session_state.rr_num_edges:
                st.info("🎉 All Round-Robin matches complete! Transitioning to Knockout...")
                
                # --- Port of generateKnockoutFromRR ---
                all_players = list(st.session_state.players)
                # Sort using our ported heap_sort
                sorted_asc = heap_sort(all_players)
                participants = sorted_asc[::-1][:count] # Top N
                
                st.session_state.match_queue = Queue()
                st.session_state.bracket_root = create_bracket_recursive(participants, 0, len(participants) - 1)
                fix_bracket_rounds(st.session_state.bracket_root)

                st.session_state.mode = "Knockout"
                st.success(f"New Knockout bracket generated for top {count} players.")

# --- UI Display Functions ---

def show_scheduled_matches():
    """(Port of C: showScheduledMatches)"""
    st.subheader("Upcoming Scheduled Matches")
    if st.session_state.match_queue.is_empty():
        st.info("No matches scheduled.")
        return
    
    match_list = []
    for match_node in st.session_state.match_queue.iter_nodes():
        m = match_node.match
        p1_name = m.player1.name if m.player1 else "TBD"
        p2_name = m.player2.name if m.player2 else "TBD"
        
        round_name = f"Round {m.round}"
        if m.round == 99: round_name = "GRAND FINAL"
        
        if not m.winner: # Only show matches that are not complete
            match_list.append({
                "ID": m.match_id,
                "Match": f"{p1_name} vs {p2_name}",
                "Round": round_name,
                "Bracket": "Losers" if m.is_from_losers else "Winners",
            })
    
    if not match_list:
        st.info("No matches scheduled.")
    else:
        st.dataframe(pd.DataFrame(match_list), hide_index=True)

def get_bracket_level_order(root_node):
    """(Port of C: printBracketLevelOrder)"""
    if not root_node:
        return ["Bracket not generated yet."]

    output = []
    q = PrintQueue() # Use our ported PrintQueue
    q.enqueue(root_node)
    q.enqueue(None)
    
    max_depth = get_max_depth(root_node)
    if max_depth > 1:
        max_depth -= 1
    current_round_label = max_depth

    if current_round_label == 1:
        output.append(f"\nRound 1 (Final):")
    else:
        output.append(f"\nRound {current_round_label} (Final):")
    current_round_label -= 1

    while not q.is_empty():
        cur = q.dequeue()
        
        if cur is None:
            if not q.is_empty():
                if current_round_label > 0:
                    output.append(f"\nRound {current_round_label}:")
                    current_round_label -= 1
                q.enqueue(None)
        else:
            if cur.match.is_leaf:
                continue
                
            p1 = cur.match.player1.name if cur.match.player1 else "TBD"
            p2 = cur.match.player2.name if cur.match.player2 else "TBD"
            
            line = f"  [M{cur.match.match_id}] {p1} vs {p2}"
            if cur.match.winner:
                line += f" -> Winner: {cur.match.winner.name} ({cur.match.player1_score}-{cur.match.player2_score})"
            output.append(line)
            
            if cur.left:
                q.enqueue(cur.left)
            if cur.right:
                q.enqueue(cur.right)
                
    return output

def display_losers_matches():
    """(Port of C: printLosersMatches and avlCollectLosers)"""
    output = ["\n--- Losers' Bracket Matches ---"]
    found_matches = []
    
    def collect_losers(node):
        if not node:
            return
        collect_losers(node.left)
        m = node.match_ptr.match
        if m.is_from_losers:
            p1 = m.player1.name if m.player1 else "TBD"
            p2 = m.player2.name if m.player2 else "TBD"
            line = f"  [M{m.match_id}] {p1} vs {p2}"
            if m.winner:
                line += f" -> Winner: {m.winner.name} ({m.player1_score}-{m.player2_score})"
            found_matches.append(line)
        collect_losers(node.right)

    collect_losers(st.session_state.match_avl_root)
    
    if not found_matches:
        output.append("No losers' matches scheduled yet.")
    else:
        output.extend(found_matches)
        
    return output

def display_statistics_page():
    """(Port of C: displayStatistics)"""
    st.header("3. Leaderboard & Stats")
    
    st.subheader("Leaderboard")
    display_leaderboard()
    
    st.subheader("Overall Tournament Stats")
    col1, col2 = st.columns(2)
    col1.metric("Total Players Registered", len(st.session_state.players))
    col2.metric("Total Matches Completed", st.session_state.total_matches_played)
    
    st.subheader("Player Specific Stats")
    player_names = [p.name for p in st.session_state.players]
    if not player_names:
        st.info("Register players to see stats.")
        return
        
    selected_player_name = st.selectbox("Select Player", player_names)
    p1 = get_player_by_name(selected_player_name)
    
    if p1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Wins", p1.wins)
        c2.metric("Losses", p1.losses)
        c3.metric("Score For", p1.score_for)
        c4.metric("Score Against", p1.score_against)
        total_played = p1.wins + p1.losses
        win_rate = (p1.wins / total_played * 100) if total_played > 0 else 0
        st.metric(f"Win Rate ({total_played} matches)", f"{win_rate:.1f}%")

    st.subheader("Head-to-Head History")
    col1, col2 = st.columns(2)
    p1_name = col1.selectbox("Select Player 1", player_names, key="h2h_p1")
    p2_name = col2.selectbox("Select Player 2", player_names, key="h2h_p2", index=min(1, len(player_names)-1))
    
    p1 = get_player_by_name(p1_name)
    p2 = get_player_by_name(p2_name)
    
    if st.button("Find H2H Matches"):
        if not p1 or not p2 or p1 == p2:
            st.error("Select two different players.")
        else:
            st.write(f"Searching match history for {p1.name} vs {p2.name}...")
            
            found_matches = []
            def find_h2h_recursive(node):
                """(Port of C: findHeadToHeadRecursive)"""
                if not node:
                    return
                find_h2h_recursive(node.left)
                m = node.match_ptr.match
                if ((m.player1 == p1 and m.player2 == p2) or (m.player1 == p2 and m.player2 == p1)):
                    line = f"  [M{m.match_id}] {p1.name} vs {p2.name}"
                    if m.winner:
                        if m.player1 == p1:
                            line += f" ({m.player1_score} - {m.player2_score})"
                        else:
                            line += f" ({m.player2_score} - {m.player1_score})"
                        line += f" -> Winner: {m.winner.name}"
                    else:
                        line += " (Not yet played)"
                    found_matches.append(line)
                find_h2h_recursive(node.right)
            
            find_h2h_recursive(st.session_state.match_avl_root)
            
            if not found_matches:
                st.info(f"No matches found between {p1.name} and {p2.name}.")
            else:
                st.code("\n".join(found_matches))

# --- NEW HELPER: Graphviz Drawing ---
def draw_bracket_graphviz(root_node):
    """Generates a Graphviz digraph for the tournament bracket."""
    if not root_node: return None
    
    g = graphviz.Digraph(comment='Tournament Bracket')
    g.attr(rankdir='LR', bgcolor='transparent') # Left-to-Right layout
    g.attr('node', shape='box', style='filled', color='#464b5d', fontname='sans-serif', fontcolor='white')
    g.attr('edge', color='#a6a9b6')

    def add_nodes_edges(node):
        if not node: return
        m = node.match
        p1 = m.player1.name if m.player1 else "?"
        p2 = m.player2.name if m.player2 else "?"
        
        label = f"M{m.match_id}\n{p1} vs {p2}"
        fillcolor = '#262730' # Default dark
        if m.winner:
            fillcolor = '#0e3311' # Dark green for finished
            label += f"\n🏆 {m.winner.name}"
        elif m.player1 and m.player2:
             fillcolor = '#5e3c0a' # Dark orange for ready to play

        g.node(str(m.match_id), label=label, fillcolor=fillcolor)

        if node.left:
            add_nodes_edges(node.left)
            g.edge(str(node.left.match.match_id), str(m.match_id))
        if node.right:
            add_nodes_edges(node.right)
            g.edge(str(node.right.match.match_id), str(m.match_id))

    add_nodes_edges(root_node)
    return g

# --- Main Application UI (Replaces C main()) ---

initialize_state()

st.set_page_config(layout="wide", page_title="Tournament Manager")
st.title("🏆 Tournament Bracket Manager")
st.caption("A Streamlit app (Literal C Port)")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", 
    [
        "1. Setup & Registration", 
        "2. Run Tournament", 
        "3. Leaderboard & Stats",
        "4. View Bracket (Text)",
        "5. Full Tree Visualisation", # <--- ADDED NEW OPTION
        "6. (Debug) View State"
    ]
)
st.sidebar.info(f"**Mode:** `{st.session_state.mode}`")
if st.sidebar.button("RESET TOURNAMENT"):
    st.session_state.clear()
    st.rerun()

if page == "1. Setup & Registration":
    st.header("1. Setup & Registration")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Register Player")
        with st.form("register_form", clear_on_submit=True):
            name = st.text_input("Player Name")
            submit = st.form_submit_button("Register")
        if submit:
            register_player(name)
        
        st.subheader("Current Players")
        if st.session_state.players:
            names = [f"- {p.name} (ID: {p.id})" for p in st.session_state.players]
            st.markdown("\n".join(names))
        else:
            st.info("No players registered.")
            
    with col2:
        st.subheader("Choose Mode & Generate")
        if st.session_state.mode != "None":
            st.warning(f"Tournament already in progress ({st.session_state.mode}). Reset to start a new one.")
        else:
            mode = st.selectbox("Select Tournament Mode", ["Knockout", "Round-Robin", "Double Elimination"])
            rr_adv_count = 0
            if mode == "Round-Robin":
                rr_adv_count = st.number_input(
                    "Players to Advance (N)? (0 for RR-only)", 
                    min_value=0, max_value=len(st.session_state.players), 
                    step=2
                )
            
            if st.button("Generate Bracket"):
                if len(st.session_state.players) < 2:
                    st.error("Need at least 2 players to generate a bracket.")
                else:
                    if mode == "Knockout":
                        generate_knockout_bracket()
                    elif mode == "Round-Robin":
                        generate_round_robin_schedule(rr_adv_count)
                    elif mode == "Double Elimination":
                        generate_double_elimination()
                    st.rerun()

elif page == "2. Run Tournament":
    st.header("2. Run Tournament")
    if st.session_state.mode == "None":
        st.warning("Please generate a bracket on the 'Setup' page first.")
    else:
        st.subheader("Update Match Result")
        
        schedulable_matches = []
        for node in st.session_state.match_queue.iter_nodes():
            if node.match.player1 and node.match.player2 and not node.match.winner:
                schedulable_matches.append(node)

        if not schedulable_matches:
            st.info("No matches are currently ready to be played (or tournament is complete).")
        else:
            match_options = {
                f"M{node.match.match_id}: {node.match.player1.name} vs {node.match.player2.name}": node
                for node in schedulable_matches
            }
            
            selected_match_str = st.selectbox("Choose Match to Update", match_options.keys())
            
            if selected_match_str:
                selected_match_node = match_options[selected_match_str]
                m = selected_match_node.match
                
                winner_name = st.radio("Winner", [m.player1.name, m.player2.name], horizontal=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    winner_score = st.number_input("Winner's Score", min_value=0, step=1, key=f"w_{m.match_id}")
                with col2:
                    loser_score = st.number_input("Loser's Score", min_value=0, step=1, key=f"l_{m.match_id}")
                
                if st.button("Submit Result"):
                    update_match_result(
                        selected_match_node, 
                        winner_name, 
                        winner_score, 
                        loser_score
                    )
                    st.rerun()
        
        show_scheduled_matches()

elif page == "3. Leaderboard & Stats":
    display_statistics_page()

elif page == "4. View Bracket (Text)":
    st.header("4. View Bracket (Text-Based)")
    mode = st.session_state.mode
    
    if mode == "Knockout":
        output_lines = get_bracket_level_order(st.session_state.bracket_root)
        st.code("\n".join(output_lines))
        
    elif mode == "Double-Elim":
        st.subheader("Winners Bracket")
        output_lines_w = get_bracket_level_order(st.session_state.winners_root)
        st.code("\n".join(output_lines_w))
        
        st.subheader("Losers Bracket")
        output_lines_l = display_losers_matches()
        st.code("\n".join(output_lines_l))
        
    elif mode == "Round-Robin":
        st.info("No bracket view for Round-Robin. See 'Run Tournament' for match list.")
    else:
        st.info("No bracket generated yet.")

# --- NEW SECTION: FULL TREE VISUALISATION ---
elif page == "5. Full Tree Visualisation":
    st.header("5. Full Tree Visualisation")
    
    # Only works for Knockout currently as it's a single tree
    if st.session_state.mode == "Knockout" and st.session_state.bracket_root:
        if not HAS_GRAPHVIZ:
             st.error("Graphviz is not installed on this server.")
             st.warning("If you are deployed on Streamlit Cloud, add 'graphviz' to packages.txt")
             # Fallback to text so user is not left with nothing
             st.text(get_bracket_level_order(st.session_state.bracket_root))
        else:
            try:
                graph = draw_bracket_graphviz(st.session_state.bracket_root)
                st.graphviz_chart(graph, use_container_width=True)
            except Exception as e:
                st.error(f"Visualisation failed to render: {e}")
                st.info("Falling back to text view:")
                st.code("\n".join(get_bracket_level_order(st.session_state.bracket_root)))
                
    elif st.session_state.mode == "Double-Elim" and st.session_state.winners_root:
         st.subheader("Winners Bracket")
         if HAS_GRAPHVIZ:
             st.graphviz_chart(draw_bracket_graphviz(st.session_state.winners_root), use_container_width=True)
         else:
             st.error("Graphviz missing for visual chart.")

    elif st.session_state.mode == "Round-Robin":
        st.info("Tree visualisation is not applicable for Round-Robin format.")
    else:
        st.info("Bracket not generated yet. Go to 'Setup' first.")

elif page == "6. (Debug) View State":
    st.header("Debug: Session State")
    st.info("This is the 'memory' of your application, equivalent to your C global variables.")
    
    debug_state = {}
    for k, v in st.session_state.items():
        if k == 'players':
            debug_state[k] = [p.name for p in v]
        elif k == 'player_index_by_name':
            debug_state[k] = {name: player.id for name, player in v.items()}
        elif k in ['bracket_root', 'winners_root', 'match_avl_root']:
            debug_state[k] = f"<{k} root object (Omitted)>"
        elif k == 'match_queue':
            debug_state[k] = f"<Queue object with {len(list(v.iter_nodes()))} items>"
        elif k == 'losers_fifo':
            debug_state[k] = f"<deque object with {len(v)} items>"
        else:
            debug_state[k] = v
            

    st.json(debug_state)
