import streamlit as st
import asyncio
import uuid
from datetime import datetime
from typing import List
from v5_guardrails_and_context import (
    handle_query,
    UserContext,
    TravelPlan,
    FlightRecommendation,
    HotelRecommendation
)

# Page config
st.set_page_config(
    page_title="Travel Planner Assistant",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Styling
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem; 
        border-radius: 0.5rem; 
        margin-bottom: 1rem; 
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #e6f7ff;
        border-left: 5px solid #2196F3;
    }
    .chat-message.assistant {
        background-color: #f0f0f0;
        border-left: 5px solid #4CAF50;
    }
    .chat-message .content {
        display: flex;
        margin-top: 0.5rem;
    }
    .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 1rem;
    }
    .message {
        flex: 1;
        color: #000000;
    }
    .timestamp {
        font-size: 0.8rem;
        color: #888;
        margin-top: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# Session state setup
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "user_context" not in st.session_state:
    st.session_state.user_context = UserContext(
        user_id=str(uuid.uuid4()),
        preferred_airlines=["SkyWays", "OceanAir"],
        hotel_amenities=["WiFi", "Pool"],
        budget_level="mid-range",
        session_start=datetime.now().isoformat()
    )

if "processing_message" not in st.session_state:
    st.session_state.processing_message = None

if "user_input_value" not in st.session_state:
    st.session_state.user_input_value = ""

# Format agent responses
def format_agent_response(response_dict):
    if not isinstance(response_dict, dict):
        if hasattr(response_dict, "model_dump"):
            response_dict = {"result": response_dict.model_dump()}
        else:
            return str(response_dict)

    if response_dict.get("type") == "guardrail":
        return f"""
        <div style='color:#b30000;font-weight:bold;'>⚠️ GUARDRAIL TRIGGERED</div>
        <p><strong>Reason:</strong> {response_dict.get("reasoning")}</p>
        <p><strong>Suggested Budget:</strong> ${response_dict.get("suggested_budget")}</p>
        """

    result = response_dict.get("result")
    if hasattr(result, "model_dump"):
        result = result.model_dump()

    if isinstance(result, dict):
        if "destination" in result:
            html = f"""
            <h3>Travel Plan for {result.get('destination')}</h3>
            <p><strong>Duration:</strong> {result.get('duration_days')} days</p>
            <p><strong>Budget:</strong> ${result.get('budget')}</p>
            <h4>Recommended Activities:</h4>
            <ul>"""
            for activity in result.get("activities", []):
                html += f"<li>{activity}</li>"
            html += f"</ul><p><strong>Notes:</strong> {result.get('notes')}</p>"
            return html

        elif "airline" in result:
            return f"""
            <h3>Flight Recommendation</h3>
            <p><strong>Airline:</strong> {result.get('airline')}</p>
            <p><strong>Departure:</strong> {result.get('departure_time')}</p>
            <p><strong>Arrival:</strong> {result.get('arrival_time')}</p>
            <p><strong>Price:</strong> ${result.get('price')}</p>
            <p><strong>Direct Flight:</strong> {'Yes' if result.get('direct_flight') else 'No'}</p>
            <p><strong>Why this flight:</strong> {result.get('recommendation_reason')}</p>
            """

        elif "name" in result and "amenities" in result:
            html = f"""
            <h3>Hotel Recommendation: {result.get('name')}</h3>
            <p><strong>Location:</strong> {result.get('location')}</p>
            <p><strong>Price per night:</strong> ${result.get('price_per_night')}</p>
            <h4>Amenities:</h4>
            <ul>"""
            for amenity in result.get("amenities", []):
                html += f"<li>{amenity}</li>"
            html += f"</ul><p><strong>Why this hotel:</strong> {result.get('recommendation_reason')}</p>"
            return html

    return str(result)

# Handle user input
def handle_user_message(user_input: str):
    timestamp = datetime.now().strftime("%I:%M %p")
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": timestamp
    })
    st.session_state.processing_message = user_input
    st.session_state.user_input_value = ""

# Sidebar UI
with st.sidebar:
    st.title("Travel Preferences")
    st.subheader("About You")
    st.text_input("Your Name", value="Traveler")

    st.subheader("Travel Preferences")
    preferred_airlines = st.multiselect(
        "Preferred Airlines",
        ["SkyWays", "OceanAir", "MountainJet", "Delta", "United", "American", "Southwest"],
        default=st.session_state.user_context.preferred_airlines
    )
    preferred_amenities = st.multiselect(
        "Must-have Hotel Amenities",
        ["WiFi", "Pool", "Gym", "Free Breakfast", "Restaurant", "Spa", "Parking"],
        default=st.session_state.user_context.hotel_amenities
    )
    budget_level = st.select_slider(
        "Budget Level",
        options=["budget", "mid-range", "luxury"],
        value=st.session_state.user_context.budget_level
    )

    if st.button("Save Preferences"):
        st.session_state.user_context.preferred_airlines = preferred_airlines
        st.session_state.user_context.hotel_amenities = preferred_amenities
        st.session_state.user_context.budget_level = budget_level
        st.success("Preferences saved!")

    if st.button("Start New Conversation"):
        st.session_state.chat_history = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.processing_message = None
        st.success("New conversation started!")

# Main app interface
st.title("✈️ Travel Planner Assistant")
st.caption("Ask me about travel destinations, flight options, hotel recommendations, and more!")

# Input field
user_input = st.text_input("Ask about travel plans...", key="chat_input", value=st.session_state.user_input_value)
if user_input and st.session_state.processing_message is None:
    handle_user_message(user_input)

# AI agent execution
if st.session_state.processing_message:
    query = st.session_state.processing_message
    st.session_state.processing_message = None

    with st.spinner("Thinking..."):
        try:
            print("🧠 DEBUG - UserContext:", st.session_state.user_context)
            result = asyncio.run(handle_query(query, st.session_state.user_context))
            response_content = format_agent_response(result)
            print("🧪 DEBUG - Formatted HTML:", response_content)
        except Exception as e:
            response_content = f"\u274c Error: {str(e)}"

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response_content,
            "timestamp": datetime.now().strftime("%I:%M %p")
        })

# Render chat history
for message in st.session_state.chat_history:
    role_class = "user" if message["role"] == "user" else "assistant"
    avatar_url = (
        f"https://api.dicebear.com/7.x/avataaars/svg?seed={st.session_state.user_context.user_id}"
        if role_class == "user"
        else "https://api.dicebear.com/7.x/bottts/svg?seed=travel-agent"
    )

    if role_class == "user":
        st.markdown(f"""
        <div class="chat-message user">
            <div class="content">
                <img src="{avatar_url}" class="avatar" />
                <div class="message">
                    {message["content"]}
                    <div class="timestamp">{message["timestamp"]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant">
            <div class="content">
                <img src="{avatar_url}" class="avatar" />
                <div class="message">
        """, unsafe_allow_html=True)

        # 👇 Properly rendered assistant HTML output, wrapped safely
        st.markdown(message["content"], unsafe_allow_html=True)

        st.markdown(f"""
                    <div class="timestamp">{message["timestamp"]}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Powered by OpenAI Agents SDK | Built with Streamlit")

