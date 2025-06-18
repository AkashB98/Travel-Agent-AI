import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional, Union
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv
import logfire

# Load environment variables
load_dotenv()

# ✅ LOGFIRE TRACING CONFIG
logfire.configure()

# OpenAI client setup
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv("MODEL_CHOICE", "gpt-4o-mini")
client = AsyncOpenAI(api_key=api_key)

# --- Models ---
class FlightRecommendation(BaseModel):
    airline: str
    departure_time: str
    arrival_time: str
    price: float
    direct_flight: bool
    recommendation_reason: str

class HotelRecommendation(BaseModel):
    name: str
    location: str
    price_per_night: float
    amenities: List[str]
    recommendation_reason: str

class TravelPlan(BaseModel):
    destination: str
    duration_days: int
    budget: float
    activities: List[str]
    notes: str

class BudgetAnalysis(BaseModel):
    is_realistic: bool
    reasoning: str
    suggested_budget: Optional[float] = None

# --- Context ---
@dataclass
class UserContext:
    user_id: str
    preferred_airlines: List[str]
    hotel_amenities: List[str]
    budget_level: str
    session_start: str

# --- Prompt Builders ---
def build_prompt(task_type: str, query: str, context: UserContext) -> str:
    schemas = {
        "flight": json.dumps(FlightRecommendation.model_json_schema(), indent=2),
        "hotel": json.dumps(HotelRecommendation.model_json_schema(), indent=2),
        "plan": json.dumps(TravelPlan.model_json_schema(), indent=2)
    }
    context_str = (
        f"Preferred Airlines: {context.preferred_airlines}\n"
        f"Hotel Amenities: {context.hotel_amenities}\n"
        f"Budget Level: {context.budget_level}\nSession Start: {context.session_start}"
    )
    return f"""
You are a helpful travel assistant.
User Preferences:
{context_str}

Respond ONLY with a JSON object that matches this schema:
{schemas[task_type]}

User Query: {query}
"""

def build_budget_check_prompt(query: str) -> str:
    schema = json.dumps(BudgetAnalysis.model_json_schema(), indent=2)
    return f"""
You are a budget check assistant.
Evaluate if this travel budget is realistic.
Respond ONLY with JSON that matches:
{schema}

Query: {query}
"""

# --- Main Handler ---
async def handle_query(query: str, context: UserContext) -> Union[dict, FlightRecommendation, HotelRecommendation, TravelPlan]:
    # Guardrail check
    try:
        guardrail_prompt = build_budget_check_prompt(query)
        guardrail_response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": guardrail_prompt}],
            temperature=0.2
        )
        guardrail_json = guardrail_response.choices[0].message.content.strip().strip('`').strip()
        if guardrail_json.startswith("json"):
            guardrail_json = guardrail_json.split("\n", 1)[1]
        budget_info = BudgetAnalysis.model_validate_json(guardrail_json)
        if not budget_info.is_realistic:
            return {
                "type": "guardrail",
                "reasoning": budget_info.reasoning,
                "suggested_budget": budget_info.suggested_budget
            }
    except Exception as e:
        print("Budget check failed:", e)

    # Intent Routing
    if "flight" in query.lower():
        task_type = "flight"
        model_type = FlightRecommendation
    elif "hotel" in query.lower():
        task_type = "hotel"
        model_type = HotelRecommendation
    else:
        task_type = "plan"
        model_type = TravelPlan

    try:
        main_prompt = build_prompt(task_type, query, context)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": main_prompt}],
            temperature=0.7
        )
        output_raw = response.choices[0].message.content.strip().strip('`').strip()
        if output_raw.startswith("json"):
            output_raw = output_raw.split("\n", 1)[1]
        return model_type.model_validate_json(output_raw)
    except ValidationError as e:
        print("\n🤖 Failed to parse structured output.")
        print(e)
        print("\nRaw Output:\n", output_raw)
        return {"type": "error", "error": str(e)}

# CLI runner to test manually
if __name__ == "__main__":
    async def main():
        context = UserContext(
            user_id="user123",
            preferred_airlines=["SkyWays", "OceanAir"],
            hotel_amenities=["WiFi", "Pool"],
            budget_level="mid-range",
            session_start=datetime.today().isoformat()
        )

        queries = [
            "I want to go to India for 500 dollars",
            "I need a flight from NYC to LA",
            "Find a hotel in Paris with a pool"
        ]

        for query in queries:
            print("\n" + "=" * 60)
            print(f"QUERY: {query}")
            print("=" * 60)
            result = await handle_query(query, context)
            print("RESULT:", result)

    asyncio.run(main())
