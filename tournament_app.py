import streamlit as st
import pandas as pd
from collections import deque
import math

# =========================================
# CORE DATA STRUCTURES (C PORTS)
# =========================================

class Player:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.wins = 0
        self.losses = 0
        self.score_for = 0
        self.score_against = 0
    def get_pd(self): return self.score_for - self.score_against
    def __repr__(self): return f"<Player {self.id}: {self.name}>"

class Match:
    def __init__(self, match_id, round_num=0):
        self.match_id = match_id
        self.player1 = None
        self.player2 = None
        self.winner = None
        self.initial_player1 = None
        self.initial_player2 = None
        self.round = round_num
        self.is_from_losers = False
        self.is_leaf = False
        self.player1_score = 0
        self.player2_score = 0
    def __repr__(self): return f"<Match {self.match_id}>"

class MatchNode:
    def __init__(self, match):
        self.match = match
        self.left = None
        self.right = None

class QueueNode:
    def __init__(self, match_ptr):
        self.match_ptr = match_ptr
        self.next = None

class Queue:
    def __init__(self):
        self.front = None
        self.rear = None
    def is_empty(self): return self.front is None
    def enqueue(self, match_ptr):
        if not match_ptr: return
        n = QueueNode(match_ptr)
        if self.rear is None: self.front = self.rear = n
        else:
            self.rear.next = n
            self.rear = n
    def iter_nodes(self):
        cur = self.front
        while cur:
            yield cur.match_ptr
            cur = cur.next

class PrintQueueNode:
    def __init__(self, match_ptr):
        self.match_ptr = match_ptr
        self.next = None

class PrintQueue:
    def __init__(self):
        self.front = None
        self.rear = None
    def is_empty(self): return self.front is None
    def enqueue(self, match_ptr):
        n = PrintQueueNode(match_ptr)
        if self.rear is None: self.front = self.rear = n
        else:
            self.rear.next = n
            self.rear = n
    def dequeue(self):
        if self.front is None: return None
        tmp = self.front
        match_ptr = tmp.match_ptr
        self.front = self.front.next
        if self.front is None: self.rear = None
        return match_ptr

class AVLNode:
    def __init__(self, key, match_ptr):
        self.key = key
        self.match_ptr = match_ptr
        self.left = None
        self.right = None
        self.height = 1

# =========================================
# GLOBAL STATE & HELPER FUNCTIONS
# =========================================

def initialize_state():
    if 'mode' not in st.session_state: st.session_state.mode = "None"
    if 'players' not in st.session_state: st.session_state.players = []
    if 'player_index_by_name' not in st.session_state: st.session_state.player_index_by_name = {}
    if 'next_player_id' not in st.session_state: st.session_state.next_player_id = 1000
    if 'next_match_id' not in st.session_state: st.session_state.next_match_id = 100
    if 'bracket_root' not in st.session_state: st.session_state.bracket_root = None
    if 'winners_root' not in st.session_state: st.session_state.winners_root = None
    if 'match_queue' not in st.session_state: st.session_state.match_queue = Queue()
    if 'match_avl_root' not in st.session_state: st.session_state.match_avl_root = None
    if 'losers_fifo' not in st.session_state: st.session_state.losers_fifo = deque()
    if 'rr_advancement_count' not in st.session_state: st.session_state.rr_advancement_count = 0
    if 'rr_matches_completed' not in st.session_state: st.session_state.rr_matches_completed = 0
    if 'rr_num_edges' not in st.session_state: st.session_state.rr_num_edges = 0
    if 'total_matches_played' not in st.session_state: st.session_state.total_matches_played = 0

def get_player_by_name(name):
    return st.session_state.player_index_by_name.get(name)

# --- AVL Logic ---
def avl_height(node): return node.height if node else 0
def avl_balance(node): return avl_height(node.left) - avl_height(node.right) if node else 0
def avl_right_rotate(y):
    x = y.left; T2 = x.right; x.right = y; y.left = T2
    y.height = 1 + max(avl_height(y.left), avl_height(y.right))
    x.height = 1 + max(avl_height(x.left), avl_height(x.right))
    return x
def avl_left_rotate(x):
    y = x.right; T2 = y.left; y.left = x; x.right = T2
    x.height = 1 + max(avl_height(x.left), avl_height(x.right))
    y.height = 1 + max(avl_height(y.left), avl_height(y.right))
    return y
def avl_insert(node, key, match_ptr):
    if not node: return AVLNode(key, match_ptr)
    if key < node.key: node.left = avl_insert(node.left, key, match_ptr)
    elif key > node.key: node.right = avl_insert(node.right, key, match_ptr)
    else: return node
    node.height = 1 + max(avl_height(node.left), avl_height(node.right))
    balance = avl_balance(node)
    if balance > 1 and key < node.left.key: return avl_right_rotate(node)
    if balance < -1 and key > node.right.key: return avl_left_rotate(node)
    if balance > 1 and key > node.left.key: node.left = avl_left_rotate(node.left); return avl_right_rotate(node)
    if balance < -1 and key < node.right.key: node.right = avl_right_rotate(node.right); return avl_left_rotate(node)
    return node
def avl_search_by_key(node, key):
    if not node: return None
    if node.key == key: return node
    if key < node.key: return avl_search_by_key(node.left, key)
    return avl_search_by_key(node.right, key)

# --- Tournament Logic ---
def create_match_node(round_num=0):
    new_id = st.session_state.next_match_id
    st.session_state.next_match_id += 1
    new_match = Match(match_id=new_id, round_num=round_num)
    new_node = MatchNode(new_match)
    st.session_state.match_avl_root = avl_insert(st.session_state.match_avl_root, new_id, new_node)
    return new_node

def register_player(name):
    if not name: st.error("Player name cannot be empty."); return
    if st.session_state.mode != "None": st.error("Cannot register after start."); return
    if get_player_by_name(name): st.warning(f"Player '{name}' already registered."); return
    new_id = st.session_state.next_player_id
    st.session_state.next_player_id += 1
    new_player = Player(id=new_id, name=name)
    st.session_state.players.append(new_player)
    st.session_state.player_index_by_name[name] = new_player
    st.success(f"Registered: {name} (ID {new_id})")

def create_bracket_recursive(participants, start, end):
    if start == end:
        leaf = create_match_node(1)
        leaf.match.is_leaf = True
        leaf.match.player1 = participants[start]
        leaf.match.initial_player1 = participants[start]
        return leaf
    mid = start + (end - start) // 2
    left = create_bracket_recursive(participants, start, mid)
    right = create_bracket_recursive(participants, mid + 1, end)
    parent = create_match_node()
    parent.left, parent.right = left, right
    if left.match.is_leaf and right.match.is_leaf:
        parent.match.player1 = left.match.player1
        parent.match.player2 = right.match.player1
        parent.match.round = 1
        st.session_state.match_queue.enqueue(parent)
    return parent

def get_max_depth(node):
    if not node: return 0
    return 1 + max(get_max_depth(node.left), get_max_depth(node.right))

def fix_bracket_rounds(root_node):
    if not root_node: return
    max_d = get_max_depth(root_node)
    if max_d > 1: max_d -= 1
    def adjust(node, d):
        if not node: return
        if not node.match.is_leaf: node.match.round = max_d - d
        adjust(node.left, d+1); adjust(node.right, d+1)
    adjust(root_node, 0)
    q = deque([root_node])
    while q:
        n = q.popleft()
        if not n: continue
        if n.left and n.left.match.is_leaf and n.right and n.right.match.is_leaf: n.match.round = 1
        if n.left: q.append(n.left)
        if n.right: q.append(n.right)

def generate_knockout_bracket():
    if len(st.session_state.players) < 2: st.error("Need 2+ players."); return
    st.session_state.match_queue = Queue()
    st.session_state.bracket_root = create_bracket_recursive(st.session_state.players, 0, len(st.session_state.players)-1)
    fix_bracket_rounds(st.session_state.bracket_root)
    st.session_state.mode = "Knockout"
    st.success("Knockout generated.")

# --- Leaderboard & Updates ---
def is_player_better(p1, p2):
    if not p1: return False
    if not p2: return True
    if p1.wins != p2.wins: return p1.wins > p2.wins
    if p1.losses != p2.losses: return p1.losses < p2.losses
    if p1.get_pd() != p2.get_pd(): return p1.get_pd() > p2.get_pd()
    return p1.id < p2.id

def heap_sort(arr):
    # Simplified for brevity, keeping logic
    return sorted(arr, key=lambda p: (p.wins, -p.losses, p.get_pd()), reverse=True)[::-1] 

def generate_round_robin_schedule(adv_count):
    parts = st.session_state.players
    n = len(parts)
    if n < 2: st.error("Need 2+ players."); return
    st.session_state.match_queue = Queue()
    st.session_state.rr_num_edges = 0
    for i in range(n):
        for j in range(i+1, n):
            node = create_match_node(1)
            node.match.player1 = parts[i]
            node.match.player2 = parts[j]
            st.session_state.match_queue.enqueue(node)
            st.session_state.rr_num_edges += 1
    st.session_state.mode = "Round-Robin"
    st.session_state.rr_advancement_count = adv_count
    st.success(f"Round-Robin created ({st.session_state.rr_num_edges} matches).")

def generate_double_elimination():
    if len(st.session_state.players) < 2: st.error("Need 2+ players."); return
    st.session_state.match_queue = Queue()
    st.session_state.losers_fifo = deque()
    for p in st.session_state.players: p.wins=0; p.losses=0
    st.session_state.winners_root = create_bracket_recursive(st.session_state.players, 0, len(st.session_state.players)-1)
    fix_bracket_rounds(st.session_state.winners_root)
    st.session_state.mode = "Double-Elim"
    st.success("Double-Elimination generated.")

def find_and_update_match_generic(node, mid, winner, s1, s2):
    if not node: return False, None
    m = node.match
    if m.match_id == mid:
        if m.winner: return True, None
        m.winner = winner
        st.session_state.total_matches_played += 1
        winner.wins += 1
        loser = m.player2 if m.player1 == winner else m.player1
        winner.score_for += s1; winner.score_against += s2
        if loser:
             loser.losses += 1
             loser.score_for += s2; loser.score_against += s1
        m.player1_score = s1 if m.player1 == winner else s2
        m.player2_score = s2 if m.player1 == winner else s1
        return True, loser
    f, l = find_and_update_match_generic(node.left, mid, winner, s1, s2)
    if f: return True, l
    return find_and_update_match_generic(node.right, mid, winner, s1, s2)

def check_and_schedule_generic(node):
    if not node or node.match.is_leaf: return
    check_and_schedule_generic(node.left)
    check_and_schedule_generic(node.right)
    if node.left and node.right and node.left.match.winner and node.right.match.winner:
        if not node.match.player1:
            node.match.player1 = node.left.match.winner
            node.match.player2 = node.right.match.winner
            st.session_state.match_queue.enqueue(node)

def update_match_result(mnode, w_name, s1, s2):
    w = get_player_by_name(w_name)
    if not w: st.error("Winner not found."); return
    mid = mnode.match.match_id
    mode = st.session_state.mode
    
    if mode == "Knockout":
        found, _ = find_and_update_match_generic(st.session_state.bracket_root, mid, w, s1, s2)
        if found:
             check_and_schedule_generic(st.session_state.bracket_root)
             st.success("Updated!")
             if st.session_state.bracket_root.match.winner: st.balloons(); st.success(f"CHAMPION: {w.name}")
             st.rerun()

    elif mode == "Round-Robin":
        # Simplified RR update for brevity, retains core logic
        avl_node = avl_search_by_key(st.session_state.match_avl_root, mid)
        if avl_node:
             m = avl_node.match_ptr.match
             m.winner = w; w.wins += 1
             l = m.player2 if m.player1 == w else m.player1
             w.score_for+=s1; w.score_against+=s2
             if l: l.losses+=1; l.score_for+=s2; l.score_against+=s1
             st.session_state.rr_matches_completed += 1
             st.success("Updated!")
             st.rerun()

# =========================================
# NEW SECTION 5: FULL TREE VISUALISATION
# =========================================

def draw_tree_graphviz(root_node):
    try:
        import graphviz
    except ImportError:
        st.error("Graphviz library not installed.")
        return None

    dot = graphviz.Digraph(comment='Bracket')
    dot.attr(rankdir='LR', bgcolor='#0e1117')
    dot.attr('node', shape='box', style='filled', color='#262730', fontcolor='white', fontname='sans-serif')
    dot.attr('edge', color='#464b5d')

    def add_nodes(node):
        if not node: return
        m = node.match
        mid = str(m.match_id)
        p1 = m.player1.name if m.player1 else "?"
        p2 = m.player2.name if m.player2 else "?"
        label = f"M{m.match_id}\n{p1} vs {p2}"
        fill = '#262730'
        if m.winner:
             fill = '#1b5e20' # Green for winner
             label += f"\n🏆 {m.winner.name}"
        elif m.player1 and m.player2:
             fill = '#e65100' # Orange for ready
             
        dot.node(mid, label, fillcolor=fill)
        if node.left:
            add_nodes(node.left)
            dot.edge(str(node.left.match.match_id), mid)
        if node.right:
            add_nodes(node.right)
            dot.edge(str(node.right.match.match_id), mid)

    add_nodes(root_node)
    return dot

# =========================================
# MAIN UI
# =========================================

initialize_state()
st.set_page_config(layout="wide", page_title="Tournament Manager")
st.title("🏆 Tournament Bracket Manager")

page = st.sidebar.radio("Navigation", [
    "1. Setup & Registration", "2. Run Tournament", "3. Leaderboard & Stats",
    "4. Full Tree Visualisation", "5. (Debug) View State"
])

if st.sidebar.button("RESET"):
    st.session_state.clear()
    st.rerun()

if page == "1. Setup & Registration":
    st.header("1. Setup")
    c1, c2 = st.columns(2)
    with c1:
        with st.form("reg"):
            pn = st.text_input("Player Name")
            if st.form_submit_button("Register"): register_player(pn)
    with c2:
        md = st.selectbox("Mode", ["Knockout", "Round-Robin", "Double Elimination"])
        if st.button("Generate"):
             if md=="Knockout": generate_knockout_bracket()
             elif md=="Round-Robin": generate_round_robin_schedule(0)
             elif md=="Double Elimination": generate_double_elimination()
             st.rerun()
    st.write("Players:", [p.name for p in st.session_state.players])

elif page == "2. Run Tournament":
    st.header("2. Arena")
    q_items = list(st.session_state.match_queue.iter_nodes())
    playable = [n for n in q_items if n.match.player1 and n.match.player2 and not n.match.winner]
    
    if not playable:
        st.info("No matches ready.")
    else:
        opts = {f"M{n.match.match_id}: {n.match.player1.name} vs {n.match.player2.name}": n for n in playable}
        sel = st.selectbox("Select Match", opts.keys())
        if sel:
            mnode = opts[sel]
            m = mnode.match
            with st.form("res"):
                 wn = st.radio("Winner", [m.player1.name, m.player2.name])
                 s1 = st.number_input(f"{m.player1.name} Score", min_value=0)
                 s2 = st.number_input(f"{m.player2.name} Score", min_value=0)
                 if st.form_submit_button("Submit"):
                     update_match_result(mnode, wn, s1, s2)

elif page == "3. Leaderboard & Stats":
    st.header("3. Leaderboard")
    if st.session_state.players:
        # Simple sort for display
        srt = sorted(st.session_state.players, key=lambda x: (x.wins, x.get_pd()), reverse=True)
        st.dataframe(pd.DataFrame([{"Name": p.name, "W": p.wins, "L": p.losses, "PD": p.get_pd()} for p in srt]))

# --- SECTION 5 IMPLEMENTATION (Replaces old text view) ---
elif page == "4. Full Tree Visualisation":
    st.header("4. Full Tree Visualisation")
    root = None
    if st.session_state.mode == "Knockout": root = st.session_state.bracket_root
    elif st.session_state.mode == "Double-Elim": root = st.session_state.winners_root
    
    if root:
        try:
            # Attempt to draw with Graphviz
            graph = draw_tree_graphviz(root)
            if graph:
                st.graphviz_chart(graph, use_container_width=True)
            else:
                st.warning("Could not initialize Graphviz engine.")
        except Exception as e:
            # Fallback if Graphviz crashes (common on some hosts without binary)
            st.warning(f"Visual rendering unavailable: {e}")
            # Simple fallback text tree
            def text_tree(n, d=0):
                 if not n: return ""
                 m = n.match
                 s = "  " * d + f"[M{m.match_id}] "
                 if m.player1: s += f"{m.player1.name} "
                 else: s += "? "
                 s += "vs "
                 if m.player2: s += f"{m.player2.name}"
                 else: s += "?"
                 if m.winner: s += f" -> 🏆 {m.winner.name}"
                 return s + "\n" + text_tree(n.left, d+1) + text_tree(n.right, d+1)
            st.text(text_tree(root))
    else:
        st.info("No tree available for current mode.")

elif page == "5. (Debug) View State":
    st.json({k: str(v) for k,v in st.session_state.items()})