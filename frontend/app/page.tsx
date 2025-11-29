"use client"

import { useState, useRef, useEffect } from "react"
import { Warehouse } from "@/components/warehouse"
import { AssemblyWorkbench } from "@/components/assembly-workbench"
import { AgentCommandCenter } from "@/components/agent-command-center"
import { ResizableDivider } from "@/components/resizable-divider"

export default function BuildableDashboard() {
  const [selectedItems, setSelectedItems] = useState<string[]>([])
  const [agentMessages, setAgentMessages] = useState<
    Array<{ id: string; type: "user" | "agent"; content: string; steps?: string[] }>
  >([])
  const [isThinking, setIsThinking] = useState(false)
  const [generatedImage, setGeneratedImage] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [assemblyHeight, setAssemblyHeight] = useState(60) // percentage

  const handleSelectItem = (itemId: string) => {
    setSelectedItems((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]))
  }

  const handleBuild = (prompt: string) => {
    // Add user message
    setAgentMessages((prev) => [
      ...prev,
      {
        id: Date.now().toString(),
        type: "user",
        content: prompt,
      },
    ])

    // Simulate thinking
    setIsThinking(true)

    // Simulate agent response with steps
    setTimeout(() => {
      setAgentMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          type: "agent",
          content: "Processing assembly request...",
          steps: [
            "Analyzing material compatibility...",
            "Mapping selected components to inventory...",
            "Verifying structural integrity...",
            "Optimizing assembly sequence...",
            "Confidence Score: 98%",
          ],
        },
      ])
      setIsThinking(false)

      // Simulate image generation
      setTimeout(() => {
        setGeneratedImage("/industrial-manufactured-object-technical-schematic.jpg")
      }, 1500)
    }, 2000)
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
      <div className="w-1/4 border-r border-border bg-slate-950/50 flex flex-col">
        <AgentCommandCenter
          messages={agentMessages}
          onBuild={handleBuild}
          isThinking={isThinking}
          messageRef={scrollRef}
          selectedItemsCount={selectedItems.length}
        />
      </div>

      <div className="flex-1 bg-slate-950/30 flex flex-col center-panel">
        {/* Assembly Workbench - Dynamic height */}
        <div style={{ height: `${assemblyHeight}%` }} className="border-b border-border overflow-hidden">
          <AssemblyWorkbench generatedImage={generatedImage} onRegenerate={() => setGeneratedImage(null)} />
        </div>

        {/* Resizable Divider */}
        <ResizableDivider onResize={handleResize} />

        {/* Material Database - Dynamic height */}
        <div style={{ height: `${100 - assemblyHeight}%` }} className="border-t border-border overflow-hidden">
          <Warehouse selectedItems={selectedItems} onSelectItem={handleSelectItem} />
        </div>
      </div>
    </div>
  )
}
