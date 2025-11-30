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

  const handleBuildWithStreaming = async (prompt: string) => {
    // Build the user query from conversation data if available
    let finalPrompt = prompt
    if (conversationData && Object.keys(conversationData).length > 0) {
      // Construct a detailed prompt from conversation data
      const parts = []
      if (conversationData.use_case) parts.push(`Use case: ${conversationData.use_case}`)
      if (conversationData.dimensions) parts.push(`Dimensions: ${conversationData.dimensions}`)
      if (conversationData.style_preferences) parts.push(`Style: ${conversationData.style_preferences}`)
      if (conversationData.material_preferences) parts.push(`Materials: ${conversationData.material_preferences}`)
      if (conversationData.personalization) parts.push(`Personalization: ${conversationData.personalization}`)
      if (conversationData.constraints) parts.push(`Constraints: ${conversationData.constraints}`)
      finalPrompt = parts.join(". ")
    }

    // Add user message
    const userMessageId = `user-${Date.now()}-${Math.random()}`
    setAgentMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        type: "user",
        content: prompt || "Building your design...",
      },
    ])

    setIsThinking(true)

    const thinkingMessageId = `agent-${Date.now()}-${Math.random()}`
    setAgentMessages((prev) => [
      ...prev,
      {
        id: thinkingMessageId,
        type: "agent",
        content: "Great! I have enough information. Now generating your design...",
        steps: [
          "⏳ Style Optimizer: Expanding design vision...",
          "⏳ Planner: Creating construction plan...",
          "⏳ Inventory Clerk: Searching for materials...",
          "⏳ Prompt Engineer: Optimizing image prompt...",
          "⏳ Flux Generator: Rendering image...",
        ],
      },
    ])

    try {
      const params = new URLSearchParams({
        user_query: finalPrompt,
        previous_style_description: styleDescription || "",
        previous_image_url: generatedImage || "",
      })
      const eventSource = new EventSource(
        `http://localhost:8000/api/v1/build-stream?${params.toString()}`
      )

      const stepMapping: Record<string, number> = {
        "style_optimizer": 0,
        "planner": 1,
        "inventory_clerk": 2,
        "prompt_engineer": 3,
        "flux_generator": 4,
      }

      const stepMessages = [
        "Style Optimizer: Expanding design vision...",
        "Planner: Creating construction plan...",
        "Inventory Clerk: Searching for materials...",
        "Prompt Engineer: Optimizing image prompt...",
        "Flux Generator: Rendering image...",
      ]

      const completedSteps = [
        "⏳ Style Optimizer: Expanding design vision...",
        "⏳ Planner: Creating construction plan...",
        "⏳ Inventory Clerk: Searching for materials...",
        "⏳ Prompt Engineer: Optimizing image prompt...",
        "⏳ Flux Generator: Rendering image...",
      ]

      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data)

        if (data.type === "progress") {
          // Update step progress - mark as complete
          const stepIndex = stepMapping[data.node]
          if (stepIndex !== undefined) {
            completedSteps[stepIndex] = `✓ ${stepMessages[stepIndex]}`
            setAgentMessages((prev) =>
              prev.map((msg) =>
                msg.id === thinkingMessageId
                  ? { ...msg, steps: [...completedSteps] }
                  : msg
              )
            )
          }
        } else if (data.type === "result") {
          // Update partial results
          if (data.field === "style_description") {
            setStyleDescription(data.value)
          } else if (data.field === "construction_plan") {
            setConstructionPlan(data.value)
          } else if (data.field === "selected_items") {
            setSelectedItems(data.value.ids)
            setSelectedItemsData(data.value.items)
          } else if (data.field === "final_image_url") {
            setImageHistory((prev) => [...prev, data.value])
            setGeneratedImage(data.value)
          }
        } else if (data.type === "complete") {
          eventSource.close()
          setIsThinking(false)
          
          // Mark all steps as complete
          const allComplete = stepMessages.map(msg => `✓ ${msg}`)
          setAgentMessages((prev) =>
            prev.map((msg) =>
              msg.id === thinkingMessageId
                ? {
                    ...msg,
                    content: data.success
                      ? "Build completed successfully!"
                      : `Build failed: ${data.error}`,
                    steps: allComplete,
                  }
                : msg
            )
          )
        } else if (data.type === "error") {
          eventSource.close()
          setIsThinking(false)
          setAgentMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}-${Math.random()}`,
              type: "agent",
              content: `Error: ${data.error}`,
            },
          ])
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
        setIsThinking(false)
        setAgentMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}-${Math.random()}`,
            type: "agent",
            content: "Connection error. Please try again.",
          },
        ])
      }
    } catch (error) {
      setIsThinking(false)
      setAgentMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}-${Math.random()}`,
          type: "agent",
          content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      ])
    }
  }

  const handleBuild = async (prompt: string, skipConversation: boolean = false) => {
    // If skipping conversation, use streaming
    if (skipConversation) {
      return handleBuildWithStreaming(prompt)
    }

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

    // In conversation mode, show a simple thinking message
    if (false) {
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
            // Proceed to workflow with streaming
            setIsInConversation(false)

            // Build final prompt from conversation data
            let workflowPrompt = prompt
            if (data.conversation_data && Object.keys(data.conversation_data).length > 0) {
              const parts = []
              if (data.conversation_data.use_case) parts.push(`Use case: ${data.conversation_data.use_case}`)
              if (data.conversation_data.dimensions) parts.push(`Dimensions: ${data.conversation_data.dimensions}`)
              if (data.conversation_data.style_preferences) parts.push(`Style: ${data.conversation_data.style_preferences}`)
              if (data.conversation_data.material_preferences) parts.push(`Materials: ${data.conversation_data.material_preferences}`)
              if (data.conversation_data.personalization) parts.push(`Personalization: ${data.conversation_data.personalization}`)
              if (data.conversation_data.constraints) parts.push(`Constraints: ${data.conversation_data.constraints}`)
              workflowPrompt = parts.join(". ")
            }

            // Update message to show workflow is starting with initial steps
            const workflowMessageId = generateMessageId()
            setAgentMessages((prev) => [
              ...prev,
              {
                id: workflowMessageId,
                type: "agent",
                content: "Great! I have enough information. Now generating your design...",
                steps: [
                  "⏳ Style Optimizer: Expanding design vision...",
                  "⏳ Planner: Creating construction plan...",
                  "⏳ Inventory Clerk: Searching for materials...",
                  "⏳ Prompt Engineer: Optimizing image prompt...",
                  "⏳ Flux Generator: Rendering image...",
                ],
              },
            ])

            // Now use streaming endpoint for workflow
            try {
              const params = new URLSearchParams({
                user_query: workflowPrompt,
                previous_style_description: styleDescription || "",
                previous_image_url: generatedImage || "",
              })
              const eventSource = new EventSource(
                `http://localhost:8000/api/v1/build-stream?${params.toString()}`
              )

              const stepMapping: Record<string, number> = {
                "style_optimizer": 0,
                "planner": 1,
                "inventory_clerk": 2,
                "prompt_engineer": 3,
                "flux_generator": 4,
              }

              const stepMessages = [
                "Style Optimizer: Expanding design vision...",
                "Planner: Creating construction plan...",
                "Inventory Clerk: Searching for materials...",
                "Prompt Engineer: Optimizing image prompt...",
                "Flux Generator: Rendering image...",
              ]

              const completedSteps = [
                "⏳ Style Optimizer: Expanding design vision...",
                "⏳ Planner: Creating construction plan...",
                "⏳ Inventory Clerk: Searching for materials...",
                "⏳ Prompt Engineer: Optimizing image prompt...",
                "⏳ Flux Generator: Rendering image...",
              ]

              eventSource.onmessage = (event) => {
                const streamData = JSON.parse(event.data)

                if (streamData.type === "progress") {
                  // Update step progress - mark as complete
                  const stepIndex = stepMapping[streamData.node]
                  if (stepIndex !== undefined) {
                    completedSteps[stepIndex] = `✓ ${stepMessages[stepIndex]}`
                    setAgentMessages((prev) =>
                      prev.map((msg) =>
                        msg.id === workflowMessageId
                          ? { ...msg, steps: [...completedSteps] }
                          : msg
                      )
                    )
                  }
                } else if (streamData.type === "result") {
                  // Update partial results
                  if (streamData.field === "style_description") {
                    setStyleDescription(streamData.value)
                  } else if (streamData.field === "construction_plan") {
                    setConstructionPlan(streamData.value)
                  } else if (streamData.field === "selected_items") {
                    setSelectedItems(streamData.value.ids)
                    setSelectedItemsData(streamData.value.items)
                  } else if (streamData.field === "final_image_url") {
                    setImageHistory((prev) => [...prev, streamData.value])
                    setGeneratedImage(streamData.value)
                  }
                } else if (streamData.type === "complete") {
                  eventSource.close()
                  
                  // Mark all steps as complete
                  const allComplete = stepMessages.map(msg => `✓ ${msg}`)
                  setAgentMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === workflowMessageId
                        ? {
                            ...msg,
                            content: streamData.success
                              ? "Build completed successfully!"
                              : `Build failed: ${streamData.error}`,
                            steps: allComplete,
                          }
                        : msg
                    )
                  )
                } else if (streamData.type === "error") {
                  eventSource.close()
                  setAgentMessages((prev) => [
                    ...prev,
                    {
                      id: generateMessageId(),
                      type: "agent",
                      content: `Error: ${streamData.error}`,
                    },
                  ])
                }
              }

              eventSource.onerror = () => {
                eventSource.close()
                setAgentMessages((prev) => [
                  ...prev,
                  {
                    id: generateMessageId(),
                    type: "agent",
                    content: "Connection error. Please try again.",
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
          onSkipConversation={() => {
            // Build prompt from conversation data if available
            let skipPrompt = ""
            if (conversationData && Object.keys(conversationData).length > 0) {
              const parts = []
              if (conversationData.use_case) parts.push(`Use case: ${conversationData.use_case}`)
              if (conversationData.dimensions) parts.push(`Dimensions: ${conversationData.dimensions}`)
              if (conversationData.style_preferences) parts.push(`Style: ${conversationData.style_preferences}`)
              if (conversationData.material_preferences) parts.push(`Materials: ${conversationData.material_preferences}`)
              if (conversationData.personalization) parts.push(`Personalization: ${conversationData.personalization}`)
              if (conversationData.constraints) parts.push(`Constraints: ${conversationData.constraints}`)
              skipPrompt = parts.join(". ")
            }
            handleBuild(skipPrompt, true)
          }}
          hasConversationData={Object.keys(conversationData).length > 0}
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
