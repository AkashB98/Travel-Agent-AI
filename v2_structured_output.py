import asyncio
import os
import re
from typing import List
from pydantic import BaseModel, Field, ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load .env vars
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
model = "gpt-4o-mini"

# Setup OpenAI client
client = AsyncOpenAI(api_key=api_key)

# --- Structured Output Class ---
class TravelPlan(BaseModel):
    destination: str
    duration_days: int
    budget: float
    activities: List[str] = Field(description="List of recommended activities")
    notes: str = Field(description="Additional notes or recommendations")

# --- Prompt Template ---
def build_prompt(query: str) -> str:
    return f"""
You are a helpful and enthusiastic travel planning assistant.

Based on the following user request, generate a JSON response matching this schema:
- destination: string
- duration_days: integer
- budget: float
- activities: list of strings
- notes: a helpful string with extra suggestions

Respond ONLY with JSON matching that structure. No markdown, no explanation.

User query:
"{query}"
"""

# --- Async Runner ---
async def main():
    queries = [
        "I'm planning a trip to Miami for 5 days with a budget of $2000. What should I do there?",
        "I want to visit Tokyo for a week with a budget of $3000. What activities do you recommend?"
    ]

    for query in queries:
        print("\n" + "="*60)
        print(f"QUERY: {query}")

        prompt = build_prompt(query)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw = response.choices[0].message.content.strip()

        # Remove markdown code fences like ```json ... ```
        cleaned = re.sub(r"^```json\n?|```$", "", raw.strip(), flags=re.IGNORECASE).strip()

        try:
            travel_plan = TravelPlan.model_validate_json(cleaned)

            # --- Pretty Output ---
            print(f"\n🌍 TRAVEL PLAN FOR {travel_plan.destination.upper()} 🌍")
            print(f"Duration: {travel_plan.duration_days} days")
            print(f"Budget: ${travel_plan.budget}")
            print("\n🎯 RECOMMENDED ACTIVITIES:")
            for i, activity in enumerate(travel_plan.activities, 1):
                print(f"  {i}. {activity}")
            print(f"\n📝 NOTES: {travel_plan.notes}")

        except ValidationError as e:
            print("\n❌ Error parsing structured output:")
            print(e)
            print("\nRaw Output:\n", raw)

if __name__ == "__main__":
    asyncio.run(main())
