import asyncio
import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
model = os.getenv('MODEL_CHOICE', 'gpt-4o-mini')

# Setup OpenAI client
client = AsyncOpenAI(api_key=api_key)

# --- Structured Output Models ---

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

# --- Prompt Builder ---

def build_prompt(task_type: str, query: str) -> str:
    if task_type == "flight":
        schema = json.dumps(FlightRecommendation.model_json_schema(), indent=2)
        return f"""
You are a flight booking assistant.
Use the following query to return a flight recommendation in this JSON format:
{schema}

Only return valid JSON.
User: {query}
"""
    elif task_type == "hotel":
        schema = json.dumps(HotelRecommendation.model_json_schema(), indent=2)
        return f"""
You are a hotel booking assistant.
Use the following query to return a hotel recommendation in this JSON format:
{schema}

Only return valid JSON.
User: {query}
"""
    else:
        schema = json.dumps(TravelPlan.model_json_schema(), indent=2)
        return f"""
You are a travel planner.
Use the following query to return a travel plan in this JSON format:
{schema}

Only return valid JSON.
User: {query}
"""

# --- Main Logic ---

async def handle_query(query: str):
    # Heuristics to detect intent
    if "flight" in query.lower():
        task_type = "flight"
        output_model = FlightRecommendation
    elif "hotel" in query.lower():
        task_type = "hotel"
        output_model = HotelRecommendation
    else:
        task_type = "plan"
        output_model = TravelPlan

    prompt = build_prompt(task_type, query)

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = output_model.model_validate_json(raw)
        return parsed
    except ValidationError as e:
        print("\n❌ Error parsing structured output:")
        print(e)
        print("\nRaw Output:\n", raw)
        return None

# --- Runner ---

async def main():
    queries = [
        "I need a flight from New York to Chicago tomorrow",
        "Find me a hotel in Paris with a pool for under $300 per night",
        "Plan a trip to Miami for 5 days with a $2000 budget"
    ]

    for query in queries:
        print("\n" + "="*60)
        print(f"QUERY: {query}")

        result = await handle_query(query)

        if isinstance(result, FlightRecommendation):
            print("\n✈️ FLIGHT RECOMMENDATION ✈️")
            print(f"Airline: {result.airline}")
            print(f"Departure: {result.departure_time}")
            print(f"Arrival: {result.arrival_time}")
            print(f"Price: ${result.price}")
            print(f"Direct Flight: {'Yes' if result.direct_flight else 'No'}")
            print(f"Why: {result.recommendation_reason}")

        elif isinstance(result, HotelRecommendation):
            print("\n🏨 HOTEL RECOMMENDATION 🏨")
            print(f"Name: {result.name}")
            print(f"Location: {result.location}")
            print(f"Price per night: ${result.price_per_night}")
            print("Amenities:")
            for i, amenity in enumerate(result.amenities, 1):
                print(f"  {i}. {amenity}")
            print(f"Why: {result.recommendation_reason}")

        elif isinstance(result, TravelPlan):
            print(f"\n🌍 TRAVEL PLAN FOR {result.destination.upper()} 🌍")
            print(f"Duration: {result.duration_days} days")
            print(f"Budget: ${result.budget}")
            print("Activities:")
            for i, act in enumerate(result.activities, 1):
                print(f"  {i}. {act}")
            print(f"Notes: {result.notes}")

        else:
            print("🤷‍♂️ Could not parse output")

if __name__ == "__main__":
    asyncio.run(main())
