# Buildable Frontend

Next.js frontend for the Buildable hackathon project. Connects to the FastAPI backend to transform user ideas into construction plans and generated images.

## Overview

The frontend provides a dashboard interface where users can:
- Enter vague design ideas (e.g., "Cyberpunk Throne")
- View the AI-generated construction plan
- See selected materials from the inventory
- View the generated photorealistic image

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   # or
   pnpm install
   ```

2. **Configure backend URL (optional):**
   Create a `.env.local` file:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
   ```
   Default is `http://localhost:8000/api/v1`

3. **Run the development server:**
   ```bash
   npm run dev
   # or
   pnpm dev
   ```

4. **Make sure the backend is running:**
   The frontend expects the backend API to be available at `http://localhost:8000` (or your configured URL).

## Features

- **Agent Command Center**: Input field to submit design requests
- **Assembly Workbench**: Displays generated images and construction plans
- **Material Database (Warehouse)**: Shows selected inventory items
- **Real-time Updates**: Shows agent processing steps and results

## Project Structure

```
frontend/
├── app/
│   └── page.tsx              # Main dashboard page
├── components/
│   ├── agent-command-center.tsx  # Input and message display
│   ├── assembly-workbench.tsx     # Image and plan display
│   └── warehouse.tsx              # Material inventory display
├── lib/
│   └── api.ts                # Backend API client
└── ...
```

## API Integration

The frontend calls the backend `/api/v1/build` endpoint with:
```json
{
  "user_query": "Cyberpunk Throne"
}
```

And receives:
```json
{
  "success": true,
  "user_query": "Cyberpunk Throne",
  "construction_plan": "...",
  "selected_item_ids": ["pipe-001", "light-001"],
  "selected_items": [...],
  "flux_prompt": "...",
  "final_image_url": "..."
}
```

## Development

- Frontend runs on `http://localhost:3000` (default Next.js port)
- Backend should run on `http://localhost:8000`
- CORS is enabled on the backend to allow frontend requests