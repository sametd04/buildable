"use client"

import { useState, useRef, useEffect } from "react"
import { Warehouse } from "@/components/warehouse"
import { AssemblyWorkbench } from "@/components/assembly-workbench"
import { AgentCommandCenter } from "@/components/agent-command-center"
import { ResizableDivider } from "@/components/resizable-divider"
import { buildProject, type BuildResponse, type InventoryItem } from "@/lib/api"

export default function BuildableDashboard() {
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [selectedItemsData, setSelectedItemsData] = useState<InventoryItem[]>([])
  const [agentMessages, setAgentMessages] = useState<
    Array<{ id: string; type: "user" | "agent"; content: string; steps?: string[] }>
  >([])
  const [isThinking, setIsThinking] = useState(false)
  const [generatedImage, setGeneratedImage] = useState<string | null>(null)
  const [constructionPlan, setConstructionPlan] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [assemblyHeight, setAssemblyHeight] = useState(60) // percentage

  const handleSelectItem = (itemId: string) => {
    setSelectedItems((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]))
  }

  const handleBuild = async (prompt: string) => {
    // Add user message
    setAgentMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        type: "user",
        content: prompt,
      },
    ])

    // Show thinking state
    setIsThinking(true)

    // Add initial agent message
    const thinkingMessageId = (Date.now() + 1).toString()
    setAgentMessages((prev) => [
      ...prev,
      {
        id: thinkingMessageId,
        type: "agent",
        content: "Processing your request...",
        steps: [
          "Style Optimizer: Expanding design vision...",
          "Planner: Creating construction plan...",
          "Inventory Clerk: Searching for materials...",
          "Prompt Engineer: Optimizing image prompt...",
          "Flux Generator: Rendering image...",
        ],
      },
    ])

    try {
      // Call backend API
      const response: BuildResponse = await buildProject({ user_query: prompt })

      // Update messages
      setAgentMessages((prev) => {
        const updated = prev.map((msg) =>
          msg.id === thinkingMessageId
            ? {
                ...msg,
                content: response.success
                  ? "Build completed successfully!"
                  : "Build failed - see details below",
                steps: response.success
                  ? [
                      "✓ Style description generated",
                      "✓ Construction plan created",
                      `✓ ${response.selected_item_ids.length} materials selected`,
                      "✓ Image prompt optimized",
                      response.final_image_url ? "✓ Image generated" : "⏳ Image generation in progress",
                    ]
                  : [`✗ Error: ${response.error || "Unknown error"}`],
              }
            : msg,
        )
        return updated
      })

      if (response.success) {
        // Update state with results
        setConstructionPlan(response.construction_plan || null)
        setSelectedItems(response.selected_item_ids)
        setSelectedItemsData(response.selected_items)
        setGeneratedImage(response.final_image_url || null)

        // Add success message
        setAgentMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 2).toString(),
            type: "agent",
            content: `Found ${response.selected_item_ids.length} matching materials in inventory.`,
          },
        ])
      } else {
        // Handle error
        setAgentMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 2).toString(),
            type: "agent",
            content: response.error || "Build failed. Please try a different design.",
          },
        ])
        setConstructionPlan(null)
        setSelectedItems([])
        setSelectedItemsData([])
        setGeneratedImage(null)
      }
    } catch (error) {
      // Handle API error
      const errorMessage = error instanceof Error ? error.message : "Failed to connect to backend"
      setAgentMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          type: "agent",
          content: `Error: ${errorMessage}. Please check your backend connection.`,
        },
      ])
      setConstructionPlan(null)
      setSelectedItems([])
      setSelectedItemsData([])
      setGeneratedImage(null)
    } finally {
      setIsThinking(false)
    }
  }

  const handleResize = (delta: number) => {
    const centerPanel = document.querySelector(".center-panel")
    if (!centerPanel) return

    const containerHeight = centerPanel.clientHeight
    const deltaPercent = (delta / containerHeight) * 100

    setAssemblyHeight((prev) => {
      const newHeight = prev + deltaPercent
      // Constrain between 30% and 70%
      return Math.max(30, Math.min(70, newHeight))
    })
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [agentMessages])

  return (
    <div className="h-screen w-full bg-background text-foreground flex overflow-hidden">
      <div className="w-1/4 border-r border-border bg-card flex flex-col">
        <AgentCommandCenter
          messages={agentMessages}
          onBuild={handleBuild}
          isThinking={isThinking}
          messageRef={scrollRef}
          selectedItemsCount={selectedItems.length}
        />
      </div>

      <div className="flex-1 bg-background flex flex-col center-panel">
        {/* Assembly Workbench - Dynamic height */}
        <div style={{ height: `${assemblyHeight}%` }} className="border-b border-border overflow-hidden">
          <AssemblyWorkbench
            generatedImage={generatedImage}
            constructionPlan={constructionPlan}
            onRegenerate={() => setGeneratedImage(null)}
          />
        </div>

        {/* Resizable Divider */}
        <ResizableDivider onResize={handleResize} />

        {/* Material Database - Dynamic height */}
        <div style={{ height: `${100 - assemblyHeight}%` }} className="border-t border-border overflow-hidden">
          <Warehouse
            selectedItems={selectedItems}
            selectedItemsData={selectedItemsData}
            onSelectItem={handleSelectItem}
          />
        </div>
      </div>
    </div>
  )
}
