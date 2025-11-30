/**
 * API client for Buildable backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

export interface BuildRequest {
  user_query: string
  previous_style_description?: string
  previous_image_url?: string
}

export interface InventoryItem {
  id: string
  name: string
  category?: string
  description?: string
  image_url?: string
}

export interface BuildResponse {
  success: boolean
  user_query: string
  style_description?: string
  construction_plan?: string
  selected_item_ids: string[]
  selected_items: InventoryItem[]
  flux_prompt?: string
  final_image_url?: string
  assembly_manual_prompts?: string[]
  assembly_manual_images?: string[]
  error?: string
}

/**
 * Call the /build endpoint to generate a construction plan and image
 */
export async function buildProject(request: BuildRequest): Promise<BuildResponse> {
  const response = await fetch(`${API_BASE_URL}/build`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
  }

  return response.json()
}

/**
 * Get inventory items from backend (if needed in future)
 */
export async function getInventory(): Promise<InventoryItem[]> {
  // This endpoint doesn't exist yet, but could be added
  // For now, we'll use the selected_items from the build response
  return []
}

