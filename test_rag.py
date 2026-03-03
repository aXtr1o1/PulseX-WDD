import asyncio
import httpx
import json

API_URL = "http://localhost:8081/api/chat/stream"

TEST_QUERIES = [
    "I'm looking for a chalet under 8 million near the beach. Preferably finishing in the next 2 years.", 
    "What's the difference between Ojo and Waterside?",
    "Tell me about the payments for ClubTown, can I spread it over 6 years?",
    "I want to invest strictly in East Cairo. Show me only luxury villas.",
    "Do you have anything in Sahel? I don't want an apartment."
]

async def test_query(client, query, idx):
    print(f"\n--- Test {idx} ---")
    print(f"User: {query}")
    
    response_text = ""
    res = await client.post(API_URL, json={"message": query, "session_id": f"test_rag_{idx}"})
    
    print("\n[AI Response]:")
    payload_split = res.text.split("<payload>")
    print(payload_split[0].strip())
    
    if len(payload_split) > 1:
        print("\n[Extracted CRM Payload]:")
        try:
            payload = json.loads(payload_split[1].replace("</payload>", "").strip())
            print(f"   Purpose: {payload.get('lead_suggestions', {}).get('purpose')}")
            print(f"   Budget: {payload.get('lead_suggestions', {}).get('budget_min')} - {payload.get('lead_suggestions', {}).get('budget_max')}")
            print(f"   Unit Type: {payload.get('lead_suggestions', {}).get('unit_type')}")
            print(f"   Region: {payload.get('lead_suggestions', {}).get('region')}")
            print(f"   Score: {payload.get('lead_suggestions', {}).get('qualification_score')} ({payload.get('lead_suggestions', {}).get('qualification_reason')})")
        except Exception as e:
             print("   [Raw Payload Parser Error]:", e)

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, q in enumerate(TEST_QUERIES):
            await test_query(client, q, i+1)

if __name__ == "__main__":
    asyncio.run(main())
