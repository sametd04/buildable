/**
 * API client for Buildable backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"

export interface BuildRequest {
  user_query: string
  previous_style_description?: string
  previous_image_url?: string
  conversation_history?: Array<{ role: string; content: string }>
  conversation_data?: Record<string, any>
  skip_conversation?: boolean
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
  status: "conversation" | "processing" | "success" | "failed_no_parts"
  conversation_history?: Array<{ role: string; content: string }>
  conversation_data?: Record<string, any>
  ready_for_workflow?: boolean
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
 * Stream conversation responses from the /build/stream endpoint
 */
export async function streamBuildProject(
  request: BuildRequest,
  onChunk: (chunk: string) => void,
  onComplete: (data: {
    content: string
    ready_for_workflow: boolean
    conversation_data?: Record<string, any>
  }) => void,
  onError: (error: string) => void
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/build/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Unknown error" }))
    onError(errorData.detail || `HTTP error! status: ${response.status}`)
    return
  }

  if (!response.body) {
    onError("No response body")
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      
      // Process complete lines (SSE format: "data: {...}\n\n")
      const lines = buffer.split("\n\n")
      buffer = lines.pop() || "" // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6)) // Remove "data: " prefix
            
            if (data.type === "chunk" && data.content) {
              onChunk(data.content)
            } else if (data.type === "complete") {
              onComplete({
                content: data.content || "",
                ready_for_workflow: data.ready_for_workflow || false,
                conversation_data: data.conversation_data,
              })
            } else if (data.type === "error") {
              onError(data.error || "Unknown error")
            } else if (data.type === "skip") {
              onComplete({
                content: "",
                ready_for_workflow: true,
              })
            }
          } catch (e) {
            console.error("Failed to parse SSE data:", e, line)
          }
        }
      }
    }
  } catch (error) {
    onError(error instanceof Error ? error.message : "Streaming error")
  } finally {
    reader.releaseLock()
  }
}

/**
 * Get inventory items from backend (if needed in future)
 */
export async function getInventory(): Promise<InventoryItem[]> {
  // This endpoint doesn't exist yet, but could be added
  // For now, we'll use the selected_items from the build response
  return []
}

export interface GenerateAssemblyManualRequest {
  construction_plan: string
  selected_item_ids: string[]
  final_image_url: string
}

export interface GenerateAssemblyManualResponse {
  success: boolean
  assembly_manual_prompts: string[]
  assembly_manual_images: string[]
  error?: string
}

/**
 * Call the /generate-assembly-manual endpoint to generate assembly instructions
 * after the user confirms they're happy with the final product image
 */
export async function generateAssemblyManual(
  request: GenerateAssemblyManualRequest
): Promise<GenerateAssemblyManualResponse> {
  const response = await fetch(`${API_BASE_URL}/generate-assembly-manual`, {
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

