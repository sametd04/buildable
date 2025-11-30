"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { RotateCcw, FileDown, Cpu, ChevronLeft, ChevronRight } from "lucide-react"

export function AssemblyWorkbench({
  generatedImage,
  constructionPlan,
  assemblyManualImages,
  onRegenerate,
}: {
  generatedImage: string | null
  constructionPlan: string | null
  assemblyManualImages: string[]
  onRegenerate: () => void
}) {
  const [activeTab, setActiveTab] = useState("hero")
  const [currentStep, setCurrentStep] = useState(0)

  // Reset step when assembly images change
  useEffect(() => {
    if (assemblyManualImages.length > 0 && currentStep >= assemblyManualImages.length) {
      setCurrentStep(0)
    }
  }, [assemblyManualImages.length, currentStep])

  // Keyboard navigation for assembly guide
  useEffect(() => {
    if (activeTab !== "guide" || assemblyManualImages.length === 0) return

    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft" && currentStep > 0) {
        setCurrentStep(currentStep - 1)
      } else if (e.key === "ArrowRight" && currentStep < assemblyManualImages.length - 1) {
        setCurrentStep(currentStep + 1)
      }
    }

    window.addEventListener("keydown", handleKeyPress)
    return () => window.removeEventListener("keydown", handleKeyPress)
  }, [activeTab, currentStep, assemblyManualImages.length])

  const renderHeroView = () => {
    if (!generatedImage) {
      return (
        <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground h-full">
          <div className="w-16 h-16 rounded border-2 border-dashed border-border flex items-center justify-center">
            <Cpu className="w-8 h-8 text-muted-foreground" />
          </div>
          <p className="text-sm font-mono uppercase tracking-widest">AWAITING AGENT INPUT</p>
        </div>
      )
    }

    return (
      <div className="flex items-center justify-center h-full p-6">
        <Card className="bg-card border-border p-4 shadow-2xl max-w-2xl w-full">
          <img
            src={generatedImage}
            alt="Generated assembly"
            className="w-full h-auto object-contain rounded"
            style={{ maxHeight: "calc(100vh - 300px)" }}
          />
        </Card>
      </div>
    )
  }

  const renderSchematicView = () => {
    return (
      <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground h-full">
        <div className="w-16 h-16 rounded border-2 border-dashed border-border flex items-center justify-center">
          <Cpu className="w-8 h-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-mono uppercase tracking-widest">SCHEMATIC VIEW COMING SOON</p>
      </div>
    )
  }

  const renderAssemblyGuide = () => {
    if (assemblyManualImages && assemblyManualImages.length > 0) {
      const hasNext = currentStep < assemblyManualImages.length - 1
      const hasPrev = currentStep > 0

      return (
        <div className="flex flex-col h-full">
          {/* Step Navigation */}
          <div className="border-b border-border bg-card p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                disabled={!hasPrev}
                className="h-8"
              >
                <ChevronLeft className="w-4 h-4 mr-1" />
                Previous
              </Button>
              <div className="text-sm font-medium">
                Step {currentStep + 1} of {assemblyManualImages.length}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(Math.min(assemblyManualImages.length - 1, currentStep + 1))}
                disabled={!hasNext}
                className="h-8"
              >
                Next
                <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
            {/* Step Indicators */}
            <div className="flex gap-2">
              {assemblyManualImages.map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentStep(index)}
                  className={`w-2 h-2 rounded-full transition-colors ${index === currentStep
                    ? "bg-primary"
                    : index < currentStep
                      ? "bg-primary/50"
                      : "bg-muted"
                    }`}
                  aria-label={`Go to step ${index + 1}`}
                />
              ))}
            </div>
          </div>

          {/* Current Step Image */}
          <div className="flex-1 flex items-center justify-center p-6 overflow-auto">
            <Card className="bg-card border-border p-6 shadow-xl max-w-4xl w-full">
              <div className="mb-4 text-center">
                <h3 className="text-lg font-semibold mb-1">
                  Assembly Step {currentStep + 1}
                </h3>
                <p className="text-sm text-muted-foreground">
                  Follow this step to continue building your project
                </p>
              </div>
              <div className="flex justify-center">
                <img
                  src={assemblyManualImages[currentStep]}
                  alt={`Assembly step ${currentStep + 1}`}
                  className="max-w-full h-auto rounded-lg border border-border shadow-lg"
                  style={{ maxHeight: "calc(100vh - 400px)" }}
                />
              </div>
            </Card>
          </div>

          {/* Step Grid View (Optional - can be toggled) */}
          {assemblyManualImages.length > 1 && (
            <div className="border-t border-border bg-card p-4">
              <div className="text-xs text-muted-foreground mb-2">All Steps:</div>
              <div className="grid grid-cols-4 gap-2 max-h-32 overflow-y-auto">
                {assemblyManualImages.map((imageUrl, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentStep(index)}
                    className={`relative rounded border-2 transition-all ${index === currentStep
                      ? "border-primary ring-2 ring-primary/20"
                      : "border-border hover:border-primary/50"
                      }`}
                  >
                    <img
                      src={imageUrl}
                      alt={`Step ${index + 1} thumbnail`}
                      className="w-full h-full object-cover rounded"
                    />
                    <div className="absolute top-1 left-1 bg-background/80 text-xs font-semibold px-1.5 py-0.5 rounded">
                      {index + 1}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )
    }

    if (constructionPlan) {
      return (
        <div className="flex flex-col h-full p-6 overflow-auto">
          <Card className="bg-card border-border p-6 max-w-4xl mx-auto w-full">
            <h3 className="text-lg font-semibold mb-4">Construction Plan</h3>
            <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">
              {constructionPlan}
            </div>
          </Card>
        </div>
      )
    }

    return (
      <div className="flex flex-col items-center justify-center gap-4 text-muted-foreground h-full">
        <div className="w-16 h-16 rounded border-2 border-dashed border-border flex items-center justify-center">
          <Cpu className="w-8 h-8 text-muted-foreground" />
        </div>
        <p className="text-sm font-mono uppercase tracking-widest">NO ASSEMBLY MANUAL AVAILABLE</p>
        <p className="text-xs">Assembly manual will appear here once generated</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-border bg-card p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
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

      {/* Main Canvas - Content changes based on active tab */}
      <div className="flex-1 dot-grid relative overflow-hidden">
        {activeTab === "hero" && renderHeroView()}
        {activeTab === "schematic" && renderSchematicView()}
        {activeTab === "guide" && renderAssemblyGuide()}
      </div>

      {/* Bottom Controls */}
      <div className="border-t border-border bg-card p-4 flex justify-center gap-3">
        {activeTab === "hero" && (
          <>
            <Button
              variant="outline"
              size="sm"
              className="bg-muted border-border hover:border-primary h-8"
              onClick={onRegenerate}
              disabled={!generatedImage}
            >
              <RotateCcw className="w-3 h-3 mr-2" />
              Regenerate
            </Button>
            <Button variant="outline" size="sm" className="bg-muted border-border hover:border-primary h-8">
              <FileDown className="w-3 h-3 mr-2" />
              Export PDF
            </Button>
          </>
        )}
        {activeTab === "guide" && assemblyManualImages.length > 0 && (
          <Button variant="outline" size="sm" className="bg-muted border-border hover:border-primary h-8">
            <FileDown className="w-3 h-3 mr-2" />
            Export Manual PDF
          </Button>
        )}
      </div>
    </div>
  )
}
