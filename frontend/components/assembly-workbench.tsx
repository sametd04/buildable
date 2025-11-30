"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { RotateCcw, FileDown, Cpu, ChevronDown, ChevronUp, History } from "lucide-react"
import { ImageCanvas } from "./image-canvas"

export function AssemblyWorkbench({
  generatedImage,
  constructionPlan,
  onRegenerate,
  imageHistory = [],
  onSelectHistoryImage,
  selectedParents = [],
  onParentSelect,
}: {
  generatedImage: string | null
  constructionPlan: string | null
  onRegenerate: () => void
  imageHistory?: string[]
  onSelectHistoryImage?: (imageUrl: string) => void
  selectedParents?: number[]
  onParentSelect?: (indices: number[]) => void
}) {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-border bg-card p-4">
        <Tabs value="hero" className="w-full">
          <TabsList className="bg-muted border border-border">
            <TabsTrigger value="hero" className="text-xs">
              Hero Render
            </TabsTrigger>
            <TabsTrigger value="schematic" className="text-xs">
              Schematic View
            </TabsTrigger>
            <TabsTrigger value="guide" className="text-xs">
              Assembly Guide
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Main Canvas */}
      <div className="flex-1 relative overflow-hidden">
        {imageHistory.length > 0 ? (
          <ImageCanvas
            images={imageHistory}
            currentImageIndex={imageHistory.findIndex((img) => img === generatedImage)}
            onImageSelect={(index) => onSelectHistoryImage?.(imageHistory[index])}
            selectedParents={selectedParents}
            onParentSelect={onParentSelect}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center dot-grid">
            <div className="flex flex-col items-center gap-4 text-muted-foreground">
              <div className="w-16 h-16 rounded border-2 border-dashed border-border flex items-center justify-center">
                <Cpu className="w-8 h-8 text-muted-foreground" />
              </div>
              <p className="text-sm font-mono uppercase tracking-widest">AWAITING AGENT INPUT</p>
            </div>
          </div>
        )}
      </div>

      {/* Image History Gallery */}
      {imageHistory.length > 0 && (
        <div className="border-t border-border bg-card">
          {/* Toggle Button */}
          <button
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
            className="w-full p-3 flex items-center gap-2 hover:bg-muted transition-colors"
          >
            <History className="w-4 h-4 text-muted-foreground" />
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              History ({imageHistory.length})
            </p>
            <div className="flex-1 h-px bg-border" />
            {isHistoryOpen ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </button>

          {/* Collapsible Gallery */}
          {isHistoryOpen && (
            <div className="px-3 pb-3">
              <div className="flex gap-2 overflow-x-auto pb-2">
                {imageHistory.map((imageUrl, index) => (
                  <button
                    key={index}
                    onClick={() => onSelectHistoryImage?.(imageUrl)}
                    className={`flex-shrink-0 w-20 h-20 rounded border-2 overflow-hidden transition-all hover:border-primary ${imageUrl === generatedImage ? "border-primary ring-2 ring-primary/20" : "border-border"
                      }`}
                    title={`Version ${imageHistory.length - index}`}
                  >
                    <img src={imageUrl} alt={`History ${index}`} className="w-full h-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}


    </div>
  )
}
