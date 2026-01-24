import streamlit as st
import requests


# Page config
st.set_page_config(
    page_title="Travia",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>

/* ===== Global Typography & Base ===== */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Roboto, Helvetica, Arial, sans-serif;
    color: #E0E0E0;
}

/* ===== Main Header ===== */
.main-header {
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    text-align: center;
    color: #42A5F5;
    margin-bottom: 2.5rem;
}

/* ===== Chat Message Base ===== */
.chat-message {
    padding: 1.2rem 1.4rem;
    border-radius: 16px;
    margin-bottom: 1.4rem;
    line-height: 1.65;
    box-shadow: 0 8px 24px rgba(0,0,0,0.35);
    opacity: 1;
}

/* ===== User Message ===== */
.user-message {
    background: linear-gradient(135deg, #E3F2FD, #F1F8FF);
    border-left: 5px solid #1E88E5;
    color: #0D47A1;
    font-weight: 500;
}

/* ===== Assistant Message (FIXED) ===== */
.assistant-message {
    background: #FFFFFF;
    border-left: 5px solid #2E7D32;
    color: #1B1F23;              /* CRITICAL FIX */
    font-weight: 400;
}

/* Force visibility for all nested elements */
.assistant-message * {
    color: #1B1F23 !important;
    opacity: 1 !important;
}

/* ===== Metric Cards ===== */
.metric-card {
    background-color: #FFFFFF;
    padding: 1.3rem;
    border-radius: 14px;
    border: 1px solid rgba(0,0,0,0.08);
    box-shadow: 0 10px 28px rgba(0,0,0,0.35);
    color: #263238;
}

/* Hover elevation */
.metric-card:hover {
    transform: translateY(-2px);
    transition: all 0.2s ease-in-out;
}

/* ===== Small Text / Captions ===== */
small, .caption {
    color: #90A4AE;
    font-size: 0.85rem;
}

/* ===== Icons ===== */
.chat-message svg,
.chat-message img {
    opacity: 1;
}

</style>
""", unsafe_allow_html=True)



# Backend API URL
API_URL = "http://127.0.0.1:8000"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None

# Sidebar
with st.sidebar:
    st.title("Travel Assistant")
    st.markdown("---")
    
    st.subheader("📊 Session Info")
    if st.session_state.session_id:
        st.info(f"Session ID: `{st.session_state.session_id[:8]}...`")
    else:
        st.warning("No active session")
    
    st.markdown("---")
    
    st.subheader("💡 Quick Examples")
    
    examples = [
        "Book a flight from BOM to DEL tomorrow",
        "Find hotels in bombay for 3 nights",
        "I need a flight from bombay to delhi next week and a hotel for 2 nights",
    ]
    
    for example in examples:
        if st.button(example, key=f"ex_{example}", use_container_width=True):
            st.session_state.input_query = example
    
    st.markdown("---")
    
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        if st.session_state.session_id:
            try:
                requests.delete(f"{API_URL}/session/{st.session_state.session_id}")
            except:  # noqa: E722
                pass
        st.session_state.session_id = None
        st.session_state.messages = []
        st.session_state.last_response = None
        st.rerun()
    
    st.markdown("---")
    st.caption("Powered by Amadeus API & Local LLM")

# Main content
st.markdown('<div class="main-header">✈️ Travia</div>', unsafe_allow_html=True)

# Display conversation history
chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        role_class = "user-message" if message["role"] == "user" else "assistant-message"
        role_icon = "👤" if message["role"] == "user" else "🤖"
        
        st.markdown(f"""
        <div class="chat-message {role_class}">
            <strong>{role_icon} {message["role"].capitalize()}:</strong><br>
            {message["content"]}
        """, unsafe_allow_html=True)

# Display last response details
if st.session_state.last_response:
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Intent",
            st.session_state.last_response.get("intent", {}).get("intent", "N/A").replace("_", " ").title()
        )
    
    with col2:
        st.metric(
            "Flight API",
            "✅ Used" if st.session_state.last_response.get("used_flight_api") else "❌ Not Used"
        )
    
    with col3:
        st.metric(
            "Hotel API",
            "✅ Used" if st.session_state.last_response.get("used_hotel_api") else "❌ Not Used"
        )
    
    with col4:
        st.metric(
            "Messages",
            len(st.session_state.messages)
        )
    
    # Show intent details in expander
    with st.expander("🔍 View Intent Details"):
        intent_data = st.session_state.last_response.get("intent", {})
        if intent_data:
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.write("**Origin:**", intent_data.get("origin", "N/A"))
                st.write("**Destination:**", intent_data.get("destination", "N/A"))
                st.write("**Travelers:**", intent_data.get("travelers", "N/A"))
            
            with col_b:
                st.write("**Check-in:**", intent_data.get("check_in", "N/A"))
                st.write("**Check-out:**", intent_data.get("check_out", "N/A"))
                st.write("**Reasoning:**", intent_data.get("reasoning", "N/A"))

# Input area
st.markdown("---")

# Use session state for input if example was clicked
query = st.text_input(
    "💬 Ask me anything about flights, hotels, or travel plans:",
    placeholder="e.g., Book a flight from BOM to DEL tomorrow",
    key="user_input",
    value=st.session_state.get("input_query", "")
)

# Clear the input_query after using it
if "input_query" in st.session_state:
    del st.session_state.input_query

col1, col2, col3 = st.columns([3, 1, 1])

with col2:
    submit_button = st.button("🚀 Send", use_container_width=True, type="primary")

with col3:
    health_button = st.button("💚 Health Check", use_container_width=True)

# Handle health check
if health_button:
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            st.success("✅ Backend is healthy!")
        else:
            st.error("❌ Backend unhealthy")
    except Exception as e:
        st.error(f"❌ Cannot reach backend: {str(e)}")

# Handle query submission
if submit_button and query:
    with st.spinner("🔍 Processing your request..."):
        try:
            # Make API request
            response = requests.post(
                f"{API_URL}/query",
                json={
                    "query": query,
                    "session_id": st.session_state.session_id
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Update session
                st.session_state.session_id = data["session_id"]
                st.session_state.messages = data["conversation_history"]
                st.session_state.last_response = data
                
                # Show success
                st.success("✅ Response received!")
                st.rerun()
            else:
                st.error(f"❌ Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to backend. Make sure the FastAPI server is running on http://127.0.0.1:8000")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Instructions
if not st.session_state.messages:
    st.markdown("---")
    st.info("""
    ### 🎯 How to use:
    1. Type your travel query in the input box above
    2. Click "Send" or press Enter
    3. The AI will understand your request and search for flights/hotels
    4. You can ask follow-up questions to refine your search
    5. Use the sidebar examples for quick queries
    
    ### ✨ Features:
    - **Multi-turn conversations**: Context is maintained across messages
    - **Natural language**: Ask in plain English
    - **Real-time search**: Uses Amadeus API for live data
    """)