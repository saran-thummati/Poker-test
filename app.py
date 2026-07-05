import streamlit as st
import random

# --- GLOBALS & POKER ENGINE ---
VALUES = '23456789TJQKA'
VAL_MAP = {v: i for i, v in enumerate(VALUES)}
CHIP_COLORS = ["White", "Red", "Blue", "Green", "Black"]
SUIT_MAP = {"Spades": "s", "Clubs": "c", "Hearts": "h", "Diamonds": "d"}
INV_SUIT_MAP = {v: k for k, v in SUIT_MAP.items()}

def format_card(c):
    return f"{c[0]} of {INV_SUIT_MAP[c[1]]}"

def evaluate_7_cards(cards):
    parsed = sorted([(VAL_MAP[c[0]], c[1]) for c in cards], reverse=True)
    suits = [c[1] for c in parsed]
    flush_suit = next((s for s in set(suits) if suits.count(s) >= 5), None)
            
    if flush_suit:
        flush_cards = [c[0] for c in parsed if c[1] == flush_suit]
        sf_score = check_straight(flush_cards)
        if sf_score: return (8, sf_score)
        return (5, flush_cards[:5])

    vals = [c[0] for c in parsed]
    counts = {v: vals.count(v) for v in set(vals)}
    sorted_counts = sorted(counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
    straight_high = check_straight(list(set(vals)))

    if sorted_counts[0][1] == 4:
        kicker = max([v for v in vals if v != sorted_counts[0][0]])
        return (7, (sorted_counts[0][0], kicker))
    if sorted_counts[0][1] == 3 and len(sorted_counts) > 1 and sorted_counts[1][1] >= 2:
        return (6, (sorted_counts[0][0], sorted_counts[1][0]))
    if straight_high: return (4, straight_high)
    if sorted_counts[0][1] == 3:
        kickers = [v for v in vals if v != sorted_counts[0][0]][:2]
        return (3, (sorted_counts[0][0], *kickers))
    if sorted_counts[0][1] == 2 and len(sorted_counts) > 1 and sorted_counts[1][1] == 2:
        kickers = [v for v in vals if v != sorted_counts[0][0] and v != sorted_counts[1][0]]
        return (2, (sorted_counts[0][0], sorted_counts[1][0], kickers[0] if kickers else 0))
    if sorted_counts[0][1] == 2:
        kickers = [v for v in vals if v != sorted_counts[0][0]][:3]
        return (1, (sorted_counts[0][0], *kickers))
    return (0, vals[:5])

def check_straight(unique_vals):
    unique_vals = sorted(unique_vals, reverse=True)
    if len(unique_vals) < 5:
        if 12 in unique_vals and set([0,1,2,3]).issubset(set(unique_vals)): return 3 
        return None
    for i in range(len(unique_vals) - 4):
        if unique_vals[i] - unique_vals[i+4] == 4: return unique_vals[i]
    if 12 in unique_vals and set([0,1,2,3]).issubset(set(unique_vals)): return 3
    return None

def calculate_multiplayer_equity(hole_cards, community_cards, num_players, playstyle, iterations=500):
    base_deck = [v+s for v in VALUES for s in ['s', 'c', 'h', 'd']]
    for c in hole_cards + community_cards:
        if c in base_deck: base_deck.remove(c)
            
    wins, ties = 0, 0
    for _ in range(iterations):
        deck = base_deck.copy()
        random.shuffle(deck)
        rem_board_count = 5 - len(community_cards)
        sim_board = community_cards + deck[:rem_board_count]
        my_score = evaluate_7_cards(hole_cards + sim_board)
        
        avail_opp_cards = deck[rem_board_count:]
        if playstyle == "Tight (Premium Hands only)":
            avail_opp_cards = [c for c in avail_opp_cards if c[0] in 'TJQKA']
            if len(avail_opp_cards) < (num_players - 1) * 2: avail_opp_cards = deck[rem_board_count:]
        elif playstyle == "Standard (Average Range)":
            avail_opp_cards = [c for c in avail_opp_cards if c[0] in '789TJQKA']
            if len(avail_opp_cards) < (num_players - 1) * 2: avail_opp_cards = deck[rem_board_count:]
                
        random.shuffle(avail_opp_cards)
        opp_scores = []
        cards_dealt = 0
        for _ in range(num_players - 1):
            opp_cards = avail_opp_cards[cards_dealt:cards_dealt+2]
            cards_dealt += 2
            opp_scores.append(evaluate_7_cards(opp_cards + sim_board))
            
        max_opp_score = max(opp_scores) if opp_scores else (0, [])
        if my_score > max_opp_score: wins += 1
        elif my_score == max_opp_score: ties += 1
            
    return (wins + (ties / num_players)) / iterations

def track_outs(hole_cards, community_cards):
    """Calculates active drawing outs for straight or flush draws on the Flop/Turn."""
    if len(community_cards) not in [3, 4]:
        return None, 0
        
    known_cards = hole_cards + community_cards
    full_deck = [v+s for v in VALUES for s in ['s', 'c', 'h', 'd']]
    remaining_deck = [c for c in full_deck if c not in known_cards]
    
    current_score = evaluate_7_cards(known_cards)
    
    # We only care about drawing if we don't already have a monster hand (Full House or better)
    if current_score[0] >= 6:
        return None, 0
        
    flush_outs = 0
    straight_outs = 0
    
    # Test every remaining card in the deck to see if it gives us a Flush or Straight
    for sim_card in remaining_deck:
        test_hand = known_cards + [sim_card]
        test_score = evaluate_7_cards(test_hand)
        
        if test_score[0] == 5 and current_score[0] < 5:
            flush_outs += 1
        elif test_score[0] == 4 and current_score[0] < 4:
            straight_outs += 1
            
    if flush_outs >= 8:
        return "Flush Draw", flush_outs
    if straight_outs >= 4:
        return "Straight Draw", straight_outs
    if flush_outs > 0 and straight_outs > 0:
        return "Combo Draw", (flush_outs + straight_outs)
        
    return "No Major Draw", 0

# --- STATE MANAGEMENT ---
if 'phase' not in st.session_state: st.session_state.phase = 'SETUP'
if 'hole_cards' not in st.session_state: st.session_state.hole_cards = []
if 'community_cards' not in st.session_state: st.session_state.community_cards = []
if 'total_chips' not in st.session_state: st.session_state.total_chips = 0
if 'num_players' not in st.session_state: st.session_state.num_players = 2
if 'playstyle' not in st.session_state: st.session_state.playstyle = "Standard (Average Range)"
if 'position' not in st.session_state: st.session_state.position = "Middle Position"
if 'chip_values' not in st.session_state: st.session_state.chip_values = {}

def next_phase(new_phase): st.session_state.phase = new_phase
def reset_hand():
    st.session_state.phase = 'SETUP'
    st.session_state.community_cards = []

# --- UI LAYOUT ---
st.set_page_config(page_title="Live Poker Assistant Pro", layout="centered")
st.title("♠️♥️ Pro Poker Assistant ♦️♣️")

# ==========================================
# PHASE 1: GAME SETUP
# ==========================================
if st.session_state.phase == 'SETUP':
    st.header("1. Game Setup")
    st.subheader("Your Chip Inventory")
    
    chip_totals = 0
    temp_chip_values = {}
    cols = st.columns(5)
    
    for i, color in enumerate(CHIP_COLORS):
        with cols[i]:
            st.markdown(f"**{color}**")
            val = st.number_input(f"Value", min_value=1, value=[1, 5, 10, 25, 100][i], key=f"val_{color}")
            count = st.number_input(f"Count", min_value=0, value=10, key=f"cnt_{color}")
            temp_chip_values[color] = val
            chip_totals += (val * count)
            
    st.info(f"**Your Total Stack Value:** {chip_totals}")
    st.markdown("---")
    
    st.subheader("Table & Hand Details")
    c1, c2 = st.columns(2)
    with c1:
        num_players = st.number_input("Total Players at Table", min_value=2, max_value=10, value=6)
        playstyle = st.selectbox("Opponent Playstyle", ["Loose (Plays anything)", "Standard (Average Range)", "Tight (Premium Hands only)"])
        position = st.selectbox("Your Table Position", ["Early Position (Disadvantage)", "Middle Position", "Late Position / Button (Advantage)"])
    with c2:
        st.write("Your Hole Cards")
        h1_val = st.selectbox("C1", list(VALUES), index=12, key="h1") 
        h1_suit = st.selectbox("Suit", list(SUIT_MAP.keys()), key="h1s", label_visibility="collapsed")
        h1 = h1_val + SUIT_MAP[h1_suit]
        
        h2_val = st.selectbox("C2", list(VALUES), index=11, key="h2") 
        h2_suit = st.selectbox("Suit", list(SUIT_MAP.keys()), key="h2s", label_visibility="collapsed")
        h2 = h2_val + SUIT_MAP[h2_suit]
    
    if st.button("Start Hand ➡️", type="primary"):
        if h1 == h2:
            st.error("Cards must be unique!")
        else:
            st.session_state.chip_values = temp_chip_values 
            st.session_state.total_chips = chip_totals
            st.session_state.num_players = num_players
            st.session_state.playstyle = playstyle
            st.session_state.position = position
            st.session_state.hole_cards = [h1, h2]
            next_phase('PRE-FLOP')
            st.rerun()

# ==========================================
# PHASE 2-5: STREET CALCULATOR
# ==========================================
def render_street_ui(street_name, expected_community_count, next_step, sim_iters):
    st.header(f"Current Phase: {street_name}")
    st.write(f"**Your Stack:** {st.session_state.total_chips} | **Opponents:** {st.session_state.num_players - 1} ({st.session_state.playstyle}) | **Pos:** {st.session_state.position}")
    
    formatted_hole = [format_card(c) for c in st.session_state.hole_cards]
    st.write(f"**Your Cards:** {formatted_hole[0]} | {formatted_hole[1]}")
    
    if expected_community_count > 0:
        formatted_board = [format_card(c) for c in st.session_state.community_cards]
        st.write(f"**Board:** {', '.join(formatted_board)}")
    st.markdown("---")
    
    new_cards = []
    if street_name == 'FLOP':
        st.subheader("Enter the Flop")
        cc1, cc2, cc3 = st.columns(3)
        with cc1: f1 = st.selectbox("F1", list(VALUES), key="f1") + SUIT_MAP[st.selectbox("Suit", list(SUIT_MAP.keys()), key="f1s")]
        with cc2: f2 = st.selectbox("F2", list(VALUES), key="f2") + SUIT_MAP[st.selectbox("Suit", list(SUIT_MAP.keys()), key="f2s")]
        with cc3: f3 = st.selectbox("F3", list(VALUES), key="f3") + SUIT_MAP[st.selectbox("Suit", list(SUIT_MAP.keys()), key="f3s")]
        new_cards = [f1, f2, f3]
    elif street_name == 'TURN':
        st.subheader("Enter the Turn")
        new_cards = [st.selectbox("Turn Card", list(VALUES), key="t1") + SUIT_MAP[st.selectbox("Suit", list(SUIT_MAP.keys()), key="t1s")]]
    elif street_name == 'RIVER':
        st.subheader("Enter the River")
        new_cards = [st.selectbox("River Card", list(VALUES), key="r1") + SUIT_MAP[st.selectbox("Suit", list(SUIT_MAP.keys()), key="r1s")]]

    # Pot and Call Inputs
    c1, c2 = st.columns(2)
    with c1: pot = st.number_input("Current Pot Size (Total in middle)", min_value=1, value=50, step=5)
    with c2: implied_odds = st.number_input("Implied Future Winnings (Guess)", min_value=0, value=0, step=5)
    
    st.subheader("The Bet to You (Count the chips required to call)")
    call_cols = st.columns(5)
    call_amt = 0
    for i, color in enumerate(CHIP_COLORS):
        with call_cols[i]:
            count = st.number_input(color, min_value=0, value=0, key=f"call_{color}_{street_name}")
            call_amt += (count * st.session_state.chip_values[color])
            
    st.info(f"**Total Call Value:** {call_amt}")

    if st.button("Calculate Move", type="primary"):
        temp_board = st.session_state.community_cards + new_cards
        all_cards = st.session_state.hole_cards + temp_board
        if len(all_cards) != len(set(all_cards)):
            st.error("Duplicate cards detected! Please make sure every card is unique.")
            return

        with st.spinner(f"Running {sim_iters} Monte Carlo simulations..."):
            equity = calculate_multiplayer_equity(st.session_state.hole_cards, temp_board, st.session_state.num_players, st.session_state.playstyle, iterations=sim_iters)
            
            actual_call = min(call_amt, st.session_state.total_chips)
            pot_odds = actual_call / (pot + actual_call) if (pot + actual_call) > 0 else 0
            
            # Positional Strategy Multiplier
            pos_buffer = 0.0
            if st.session_state.position == "Late Position / Button (Advantage)":
                pos_buffer = 0.04 # Can loosen up call requirements by 4% due to position
            elif st.session_state.position == "Early Position (Disadvantage)":
                pos_buffer = -0.03 # Must be 3% stricter when acting first
                
            ev = (equity * (pot + implied_odds)) - ((1 - equity) * actual_call)
            
            st.markdown("### Hand Analysis")
            st.write("Win Probability")
            st.progress(min(float(equity), 1.0))
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Win %", f"{equity * 100:.1f}%")
            m2.metric("Pot Odds Target", f"{pot_odds * 100:.1f}%")
            m3.metric("Expected Value (EV)", f"{ev:+.1f} Chips")
            
            # Display Draw Tracking if Flop or Turn
            if street_name in ['FLOP', 'TURN']:
                draw_type, outs = track_outs(st.session_state.hole_cards, temp_board)
                if outs > 0:
                    st.info(f"🔮 **Draw Detected:** {draw_type} with **{outs} Outs** remaining in the deck.")
            
            # Decision Engine incorporating Position
            if call_amt == 0:
                st.success("🎯 **ACTION: CHECK** (It costs nothing to see the next card)")
            elif ev > 0 or (equity + pos_buffer) > pot_odds:
                if ev > (pot * 0.4) and (st.session_state.total_chips / pot) < 3:
                    st.success("💥 **ACTION: RAISE / ALL-IN** (Extremely Profitable Play)")
                elif ev < 0 and (equity + pos_buffer) > pot_odds:
                    st.success(f"✅ **ACTION: CALL** (Backed by Positional Tactical Advantage)")
                else:
                    st.success(f"✅ **ACTION: CALL** (Mathematically profitable in the long run)")
            else:
                st.error("❌ **ACTION: FOLD** (Negative EV. Position cannot save this hand)")

    st.markdown("---")
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("I Folded (End Hand)", type="secondary", use_container_width=True):
            reset_hand()
            st.rerun()
    with bc2:
        if next_step == 'END':
            if st.button("Showdown! (Start New Hand)", type="primary", use_container_width=True):
                reset_hand()
                st.rerun()
        else:
            if st.button("I stayed in ➡️ Next Street", type="primary", use_container_width=True):
                st.session_state.community_cards.extend(new_cards)
                next_phase(next_step)
                st.rerun()

# --- ROUTER ---
if st.session_state.phase == 'PRE-FLOP': render_street_ui("PRE-FLOP", 0, 'FLOP', sim_iters=2000)
elif st.session_state.phase == 'FLOP': render_street_ui("FLOP", 3, 'TURN', sim_iters=1000)
elif st.session_state.phase == 'TURN': render_street_ui("TURN", 4, 'RIVER', sim_iters=500)
elif st.session_state.phase == 'RIVER': render_street_ui("RIVER", 5, 'END', sim_iters=100)
