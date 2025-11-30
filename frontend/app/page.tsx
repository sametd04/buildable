"use client"

import { useState, useRef, useEffect } from "react"
import { Warehouse } from "@/components/warehouse"
import { AssemblyWorkbench } from "@/components/assembly-workbench"
import { AgentCommandCenter } from "@/components/agent-command-center"
import { ResizableDivider } from "@/components/resizable-divider"
import { ThemeToggle } from "@/components/theme-toggle"
import { buildProject, streamBuildProject, generateAssemblyManual, type BuildResponse, type InventoryItem, type GenerateAssemblyManualResponse } from "@/lib/api"

// Generate unique IDs for messages
let messageIdCounter = 0
function generateMessageId(): string {
  messageIdCounter++
  return `${Date.now()}-${messageIdCounter}-${Math.random().toString(36).substr(2, 9)}`
}

export default function BuildableDashboard() {
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [selectedItemsData, setSelectedItemsData] = useState<InventoryItem[]>([])
  const [agentMessages, setAgentMessages] = useState<
    Array<{ id: string; type: "user" | "agent"; content: string; steps?: string[] }>
  >([])
  const [isThinking, setIsThinking] = useState(false)
  const [generatedImage, setGeneratedImage] = useState<string | null>(null)
  const [constructionPlan, setConstructionPlan] = useState<string | null>(null)
  const [styleDescription, setStyleDescription] = useState<string | null>(null)
  const [imageHistory, setImageHistory] = useState<string[]>([])
  const [selectedParentIndices, setSelectedParentIndices] = useState<number[]>([])
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const [assemblyHeight, setAssemblyHeight] = useState(70) // percentage
  const [assemblyManualImages, setAssemblyManualImages] = useState<string[]>([])
  const [assemblyManualPrompts, setAssemblyManualPrompts] = useState<string[]>([])
  const [isGeneratingManual, setIsGeneratingManual] = useState(false)
  const [conversationHistory, setConversationHistory] = useState<Array<{ role: string; content: string }>>([])
  const [conversationData, setConversationData] = useState<Record<string, any>>({})
  const [isInConversation, setIsInConversation] = useState(false)

  const handleSelectItem = (itemId: string) => {
    setSelectedItems((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]))
  }

  const handleBuild = async (prompt: string, skipConversation: boolean = false) => {
    // Add user message to conversation
    const newUserMessage = { role: "user", content: prompt }
    const updatedHistory = [...conversationHistory, newUserMessage]
    setConversationHistory(updatedHistory)

    // Add user message to agent messages
    const userMessageId = generateMessageId()
    setAgentMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        type: "user",
        content: prompt,
      },
    ])

    setIsThinking(true)

    // Add initial agent message
    const thinkingMessageId = generateMessageId()

    // Only show workflow steps if we're explicitly skipping conversation
    // Otherwise, we're in conversation mode and should show a simple thinking message
    if (skipConversation) {
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
    } else {
      // During conversation, create an empty message that we'll stream into
      setAgentMessages((prev) => [
        ...prev,
        {
          id: thinkingMessageId,
          type: "agent",
          content: "",
        },
      ])
    }

    try {
      // If skipping conversation, use regular endpoint
      if (skipConversation) {
        const response: BuildResponse = await buildProject({
          user_query: prompt,
          previous_style_description: styleDescription || undefined,
          previous_image_url: generatedImage || undefined,
          conversation_history: updatedHistory,
          conversation_data: conversationData,
          skip_conversation: skipConversation,
        })

        // Handle response (same as existing logic below)
        // Update conversation state
        if (response.conversation_history) {
          setConversationHistory(response.conversation_history)
        }
        if (response.conversation_data) {
          setConversationData(response.conversation_data)
        }

        // Proceeding to workflow
        setIsInConversation(false)

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

        if (response.success && response.status === "success") {
          setStyleDescription(response.style_description || null)
          setConstructionPlan(response.construction_plan || null)
          setSelectedItems(response.selected_item_ids)
          setSelectedItemsData(response.selected_items)

          if (response.final_image_url) {
            setImageHistory((prev) => [...prev, response.final_image_url!])
            setGeneratedImage(response.final_image_url)
          }

          setAgentMessages((prev) => [
            ...prev,
            {
              id: generateMessageId(),
              type: "agent",
              content: `Found ${response.selected_item_ids.length} matching materials in inventory.`,
            },
          ])
        } else {
          setAgentMessages((prev) => [
            ...prev,
            {
              id: generateMessageId(),
              type: "agent",
              content: response.error || "Build failed. Please try a different design.",
            },
          ])
          setConstructionPlan(null)
          setSelectedItems([])
          setSelectedItemsData([])
          setGeneratedImage(null)
        }

        setIsThinking(false)
        return
      }

      // For conversation, use streaming endpoint
      let streamedContent = ""

      await streamBuildProject(
        {
          user_query: prompt,
          previous_style_description: styleDescription || undefined,
          previous_image_url: generatedImage || undefined,
          conversation_history: updatedHistory,
          conversation_data: conversationData,
          skip_conversation: skipConversation,
        },
        // onChunk - update message content as chunks arrive
        (chunk: string) => {
          streamedContent += chunk
          setAgentMessages((prev) =>
            prev.map((msg) =>
              msg.id === thinkingMessageId
                ? { ...msg, content: streamedContent }
                : msg
            )
          )
        },
        // onComplete - handle completion
        async (data) => {
          setIsThinking(false)

          // Update conversation state
          const finalHistory = [...updatedHistory]
          if (streamedContent) {
            finalHistory.push({
              role: "assistant",
              content: streamedContent,
            })
          }
          setConversationHistory(finalHistory)

          if (data.conversation_data) {
            setConversationData(data.conversation_data)
          }

          if (data.ready_for_workflow) {
            // Proceed to workflow
            setIsInConversation(false)

            // Update message to show workflow is starting
            setAgentMessages((prev) =>
              prev.map((msg) =>
                msg.id === thinkingMessageId
                  ? {
                    ...msg,
                    content: "Great! I have enough information. Now generating your design...",
                    steps: [
                      "Style Optimizer: Expanding design vision...",
                      "Planner: Creating construction plan...",
                      "Inventory Clerk: Searching for materials...",
                      "Prompt Engineer: Optimizing image prompt...",
                      "Flux Generator: Rendering image...",
                    ],
                  }
                  : msg
              )
            )

            // Now call the regular build endpoint to proceed with workflow
            try {
              const workflowResponse: BuildResponse = await buildProject({
                user_query: prompt,
                previous_style_description: styleDescription || undefined,
                previous_image_url: generatedImage || undefined,
                conversation_history: finalHistory,
                conversation_data: data.conversation_data || conversationData,
                skip_conversation: false, // We're ready now
              })

              // Handle workflow response
              if (workflowResponse.status === "success") {
                setStyleDescription(workflowResponse.style_description || null)
                setConstructionPlan(workflowResponse.construction_plan || null)
                setSelectedItems(workflowResponse.selected_item_ids)
                setSelectedItemsData(workflowResponse.selected_items)

                if (workflowResponse.final_image_url) {
                  setImageHistory((prev) => [...prev, workflowResponse.final_image_url!])
                  setGeneratedImage(workflowResponse.final_image_url)
                }

                setAgentMessages((prev) => [
                  ...prev,
                  {
                    id: generateMessageId(),
                    type: "agent",
                    content: `Found ${workflowResponse.selected_item_ids.length} matching materials in inventory.`,
                  },
                ])
              }
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : "Failed to generate design"
              setAgentMessages((prev) => [
                ...prev,
                {
                  id: generateMessageId(),
                  type: "agent",
                  content: `Error: ${errorMessage}`,
                },
              ])
            }
          } else {
            // Still in conversation
            setIsInConversation(true)
          }
        },
        // onError
        (error: string) => {
          setIsThinking(false)
          setAgentMessages((prev) => [
            ...prev,
            {
              id: generateMessageId(),
              type: "agent",
              content: `Error: ${error}`,
            },
          ])
        }
      )
    } catch (error) {
      // Handle API error
      const errorMessage = error instanceof Error ? error.message : "Failed to connect to backend"
      setAgentMessages((prev) => [
        ...prev,
        {
          id: generateMessageId(),
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

  const handleGenerateAssemblyManual = async () => {
    if (!constructionPlan || !generatedImage || selectedItems.length === 0) {
      return
    }

    setIsGeneratingManual(true)

    try {
      const response: GenerateAssemblyManualResponse = await generateAssemblyManual({
        construction_plan: constructionPlan,
        selected_item_ids: selectedItems,
        final_image_url: generatedImage,
      })

      if (response.success) {
        setAssemblyManualImages(response.assembly_manual_images)
        setAssemblyManualPrompts(response.assembly_manual_prompts)

        // Add success message
        setAgentMessages((prev) => [
          ...prev,
          {
            id: generateMessageId(),
            type: "agent",
            content: `Assembly manual generated successfully with ${response.assembly_manual_images.length} steps!`,
          },
        ])
      } else {
        setAgentMessages((prev) => [
          ...prev,
          {
            id: generateMessageId(),
            type: "agent",
            content: response.error || "Failed to generate assembly manual. Please try again.",
          },
        ])
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Failed to generate assembly manual"
      setAgentMessages((prev) => [
        ...prev,
        {
          id: generateMessageId(),
          type: "agent",
          content: `Error: ${errorMessage}`,
        },
      ])
    } finally {
      setIsGeneratingManual(false)
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
      <ThemeToggle />
      <div className="w-[30%] border-r border-border bg-card flex flex-col">
        <AgentCommandCenter
          messages={agentMessages}
          onBuild={handleBuild}
          isThinking={isThinking}
          messageRef={scrollRef}
          selectedItemsCount={selectedItems.length}
          isInConversation={isInConversation}
          onSkipConversation={() => handleBuild("", true)}
        />
      </div>

      <div className="flex-1 bg-background flex flex-col center-panel">
        {/* Assembly Workbench - Dynamic height */}
        <div style={{ height: `${assemblyHeight}%` }} className="border-b border-border overflow-hidden">
          <AssemblyWorkbench
            generatedImage={generatedImage}
            constructionPlan={constructionPlan}
            onRegenerate={() => setGeneratedImage(null)}
            imageHistory={imageHistory}
            onSelectHistoryImage={(imageUrl) => setGeneratedImage(imageUrl)}
            selectedParents={selectedParentIndices}
            onParentSelect={setSelectedParentIndices}
            assemblyManualImages={assemblyManualImages}
            assemblyManualPrompts={assemblyManualPrompts}
            onGenerateAssemblyManual={handleGenerateAssemblyManual}
            isGeneratingManual={isGeneratingManual}
            canGenerateManual={!!constructionPlan && !!generatedImage && selectedItems.length > 0}
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
