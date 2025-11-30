# Buildable

**Transform vague ideas into detailed construction plans and photorealistic images using AI agents.**

Buildable is a full-stack application that uses a multi-agent AI system to help users create custom DIY furniture and structures. Simply describe what you want to build (e.g., "Cyberpunk Throne"), and the system will generate a detailed construction plan, select materials from inventory, and create photorealistic visualizations.

## 🎯 Features

- **Conversational Design Assistant**: Interactive conversation to gather requirements (use case, dimensions, style, materials, etc.)
- **AI-Powered Planning**: Multi-agent workflow that transforms vague ideas into detailed construction plans
- **Intelligent Material Selection**: Automatically selects appropriate materials from inventory using vector search
- **Photorealistic Image Generation**: Uses FLUX API to generate high-quality images of the final product
- **Assembly Manual Generation**: Creates step-by-step assembly instructions with images
- **Modern Web Interface**: Beautiful Next.js dashboard with real-time updates

## 🏗️ Architecture

Buildable consists of two main components:

### Backend (`/backend`)
- **FastAPI** REST API server
- **LangGraph** for orchestrating multi-agent workflows
- **MongoDB** for inventory management
- **FLUX API** integration for image generation
- **Langfuse** for observability and tracing

### Frontend (`/frontend`)
- **Next.js 16** with React 19
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** components
- Real-time updates via Server-Sent Events (SSE)

## 🤖 Multi-Agent Workflow

The system uses a LangGraph-based workflow with specialized AI agents:

1. **Conversation Agent**: Gathers requirements through natural conversation
2. **Style Optimizer**: Refines style preferences and aesthetic direction
3. **Planner (Agent A)**: Generates detailed construction plans from user requirements
4. **Inventory Clerk (Agent B)**: Selects specific materials from inventory using vector search
5. **Prompt Engineer (Agent C)**: Creates optimized prompts for image generation
6. **Flux Generator (Agent D)**: Generates photorealistic images using FLUX API

The workflow includes feedback loops - if materials can't be found, the Planner revises the plan and tries again.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **MongoDB** (local or Atlas)
- **API Keys**:
  - OpenAI API key (for LLM)
  - Black Forest Labs API key (for FLUX image generation)
  - Langfuse keys (optional, for observability)

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python -m venv ../buildable-env
   source ../buildable-env/bin/activate  # On Windows: ..\buildable-env\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env and add your API keys and MongoDB connection string
   ```

5. **Start MongoDB:**
   ```bash
   # Local MongoDB
   mongod
   
   # Or use MongoDB Atlas and update MONGO_URI in .env
   ```

6. **Seed the database:**
   ```bash
   python scripts/seed_db.py
   ```

7. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   # or
   pnpm install
   ```

3. **Configure backend URL (optional):**
   Create `.env.local`:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
   Default is `http://localhost:8000/api/v1`

4. **Run the development server:**
   ```bash
   npm run dev
   # or
   pnpm dev
   ```

The frontend will be available at `http://localhost:3000`

## 📖 API Documentation

### Main Endpoints

#### `POST /api/v1/build`
Generate a construction plan and image from a user query.

**Request:**
```json
{
  "user_query": "Cyberpunk Throne",
  "skip_conversation": false,
  "conversation_history": [],
  "conversation_data": {},
  "previous_image_url": null,
  "previous_image_urls": []
}
```

**Response:**
```json
{
  "success": true,
  "user_query": "Cyberpunk Throne",
  "status": "success",
  "style_description": "...",
  "construction_plan": "...",
  "selected_item_ids": ["pipe-001", "light-001", ...],
  "selected_items": [...],
  "flux_prompt": "...",
  "final_image_url": "..."
}
```

#### `POST /api/v1/build/stream`
Stream conversation agent responses in real-time using Server-Sent Events (SSE).

#### `POST /api/v1/generate-assembly-manual`
Generate step-by-step assembly instructions with images.

#### `GET /api/v1/inventory`
Get all inventory items.

#### `POST /api/v1/test-flux`
Test FLUX image generation directly.

See the [Backend README](backend/README.md) for detailed API documentation.

## 🗂️ Project Structure

```
buildable/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes and schemas
│   │   ├── core/           # Configuration and database
│   │   ├── graph/          # LangGraph workflow and nodes
│   │   ├── services/       # External service integrations
│   │   ├── utils/          # Utility functions
│   │   └── main.py         # FastAPI app entry point
│   ├── data/               # Seed data
│   ├── scripts/            # Utility scripts
│   └── requirements.txt    # Python dependencies
│
├── frontend/               # Next.js frontend
│   ├── app/                # Next.js app directory
│   ├── components/         # React components
│   ├── lib/                # Utilities and API client
│   └── package.json        # Node dependencies
│
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

**Backend** (`.env`):
- `OPENAI_API_KEY`: Your OpenAI API key
- `BFL_API_KEY`: Your Black Forest Labs API key for FLUX
- `MONGO_URI`: MongoDB connection string
- `MONGO_DB_NAME`: Database name
- `LLM_MODEL`: LLM model to use (default: `gpt-4o-mini`)
- `FLUX_MODEL`: FLUX model to use (default: `flux-pro-1.1`)
- `LANGFUSE_PUBLIC_KEY` & `LANGFUSE_SECRET_KEY`: Optional, for observability

**Frontend** (`.env.local`):
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8000/api/v1`)

See `backend/env.example` for all available options.

## 🧪 Development

### Backend Development
- API docs available at `/docs` (Swagger UI) or `/redoc`
- Enable debug mode by setting `DEBUG=True` in `.env`
- Langfuse tracing is automatically enabled if credentials are provided

### Frontend Development
- Hot reload enabled by default
- TypeScript for type safety
- ESLint for code quality

## 📝 License

This project was created for a hackathon. See individual component READMEs for more details.

## 📚 Additional Documentation

- [Backend README](backend/README.md) - Detailed backend documentation
- [Frontend README](frontend/README.md) - Detailed frontend documentation

## 🤝 Contributing

This is a hackathon project. Contributions and improvements are welcome!

## 🐛 Troubleshooting

### Backend Issues
- **MongoDB connection errors**: Ensure MongoDB is running and `MONGO_URI` is correct
- **API key errors**: Verify all API keys are set in `.env`
- **Import errors**: Make sure virtual environment is activated and dependencies are installed

### Frontend Issues
- **API connection errors**: Ensure backend is running on `http://localhost:8000`
- **CORS errors**: Backend CORS is configured to allow all origins in development
- **Build errors**: Clear `.next` directory and `node_modules`, then reinstall

---

**Built with ❤️ for the hackathon**

