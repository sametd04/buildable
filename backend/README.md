# Buildable Backend

A FastAPI + LangGraph backend for the Buildable hackathon project. This service transforms vague user ideas into specific construction plans using inventory items and generates photorealistic hero shots.

## Architecture

The backend uses LangGraph to orchestrate a multi-agent workflow:

1. **Agent A (Planner)**: Generates a detailed construction plan from the user's vague idea
2. **Agent B (Inventory Clerk)**: Selects specific items from inventory using structured output
3. **Agent C (Prompt Engineer)**: Creates an optimized prompt for FLUX image generation
4. **Agent D (Flux Generator)**: Calls the FLUX API (currently mocked) to generate the image

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST `/api/v1/build`

Generate a construction plan and image from a user query.

**Request:**
```json
{
  "user_query": "Cyberpunk Throne"
}
```

**Response:**
```json
{
  "success": true,
  "user_query": "Cyberpunk Throne",
  "construction_plan": "...",
  "selected_item_ids": ["pipe-001", "light-001", ...],
  "selected_items": [...],
  "flux_prompt": "...",
  "final_image_url": "..."
}
```

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes.py      # API endpoints
│   │   └── schemas.py     # Pydantic models
│   ├── core/
│   │   ├── config.py      # Configuration
│   │   └── database.py    # Inventory loader
│   ├── graph/
│   │   ├── state.py       # AgentState definition
│   │   ├── nodes.py       # Agent logic
│   │   └── workflow.py    # Compiled StateGraph
│   ├── services/
│   │   └── flux_service.py # FLUX API mock
│   └── main.py            # FastAPI app
├── data/
│   └── inventory.json     # Inventory database
├── requirements.txt
└── .env.example
```

## Development

- API docs available at `/docs` (Swagger UI)
- Alternative docs at `/redoc`

