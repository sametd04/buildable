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

2. **Start MongoDB:**
   ```bash
   # Make sure MongoDB is running locally or update MONGO_URI in .env
   # For local MongoDB: mongod
   # Or use MongoDB Atlas and update MONGO_URI with your connection string
   ```

3. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env and add your API keys and MongoDB connection string
   ```

4. **Seed the database:**
   ```bash
   python scripts/seed_db.py
   ```
   This will load `data/inventory.json` into MongoDB. You can run this anytime to reset the database.

5. **Run the server:**
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
âââ app/
â   âââ api/
â   â   âââ routes.py      # API endpoints
â   â   âââ schemas.py     # Pydantic models
â   âââ core/
â   â   âââ config.py      # Configuration
â   â   âââ database.py    # MongoDB connection and inventory operations
â   âââ graph/
â   â   âââ state.py       # AgentState definition
â   â   âââ nodes.py       # Agent logic
â   â   âââ workflow.py    # Compiled StateGraph
â   âââ services/
â   â   âââ flux_service.py # FLUX API mock
â   âââ main.py            # FastAPI app
âââ data/
â   âââ inventory.json     # Inventory seed data
âââ scripts/
â   âââ seed_db.py         # Database seeding script
âââ requirements.txt
âââ env.example
```

## Development

- API docs available at `/docs` (Swagger UI)
- Alternative docs at `/redoc`

