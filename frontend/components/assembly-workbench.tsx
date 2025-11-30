"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { RotateCcw, FileDown, Cpu, ChevronDown, ChevronUp, History, BookOpen, Loader2, Package } from "lucide-react"
import { ImageCanvas } from "./image-canvas"

export function AssemblyWorkbench({
  generatedImage,
  constructionPlan,
  onRegenerate,
  imageHistory = [],
  onSelectHistoryImage,
  selectedParents = [],
  onParentSelect,
  assemblyManualImages = [],
  assemblyManualPrompts = [],
  partsOverviewImage = null,
  onGenerateAssemblyManual,
  isGeneratingManual = false,
  canGenerateManual = false,
}: {
  generatedImage: string | null
  constructionPlan: string | null
  onRegenerate: () => void
  imageHistory?: string[]
  onSelectHistoryImage?: (imageUrl: string) => void
  selectedParents?: number[]
  onParentSelect?: (indices: number[]) => void
  assemblyManualImages?: string[]
  assemblyManualPrompts?: any[]
  partsOverviewImage?: string | null
  onGenerateAssemblyManual?: () => void
  isGeneratingManual?: boolean
  canGenerateManual?: boolean
}) {
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("hero")

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-border bg-card p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="flex items-center justify-between mb-2">
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
            {activeTab === "guide" && canGenerateManual && assemblyManualImages.length === 0 && (
              <Button
                onClick={onGenerateAssemblyManual}
                disabled={isGeneratingManual}
                size="sm"
                className="ml-auto mr-16"
              >
                {isGeneratingManual ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <BookOpen className="w-4 h-4 mr-2" />
                    Generate Assembly Manual
                  </>
                )}
              </Button>
            )}
          </div>
        </Tabs>
      </div>

      {/* Main Canvas */}
      <div className="flex-1 relative overflow-hidden">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
          <TabsContent value="hero" className="h-full m-0">
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
          </TabsContent>

          <TabsContent value="schematic" className="h-full m-0">
            <div className="w-full h-full flex items-center justify-center dot-grid">
              <div className="flex flex-col items-center gap-4 text-muted-foreground">
                <div className="w-16 h-16 rounded border-2 border-dashed border-border flex items-center justify-center">
                  <Cpu className="w-8 h-8 text-muted-foreground" />
                </div>
                <p className="text-sm font-mono uppercase tracking-widest">SCHEMATIC VIEW</p>
                <p className="text-xs">Coming soon</p>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="guide" className="h-full m-0 overflow-auto">
            {isGeneratingManual ? (
              <div className="w-full h-full flex items-center justify-center">
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                  <Loader2 className="w-8 h-8 animate-spin" />
                  <p className="text-sm font-mono uppercase tracking-widest">GENERATING ASSEMBLY MANUAL...</p>
                </div>
              </div>
            ) : assemblyManualImages.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center dot-grid">
                <div className="flex flex-col items-center gap-4 text-muted-foreground">
                  <BookOpen className="w-16 h-16 text-muted-foreground" />
                  <p className="text-sm font-mono uppercase tracking-widest">NO ASSEMBLY MANUAL</p>
                  {canGenerateManual ? (
                    <p className="text-xs text-center max-w-md">
                      Confirm your product image is ready, then click "Generate Assembly Manual" to create step-by-step assembly instructions.
                    </p>
                  ) : (
                    <p className="text-xs text-center max-w-md">
                      Generate a product image first, then you can create the assembly manual.
                    </p>
                  )}
                </div>
              </div>
            ) : (
              <div className="p-6 space-y-6 max-w-4xl mx-auto">
                <div className="flex items-center justify-between">
                  <h2 className="text-lg font-semibold">Assembly Instructions</h2>
                  <span className="text-sm text-muted-foreground">
                    {assemblyManualImages.length} step{assemblyManualImages.length !== 1 ? "s" : ""}
                  </span>
                </div>

                {/* Parts Overview Card */}
                {partsOverviewImage && (
                  <Card className="p-4 border-primary/20 bg-primary/5">
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <Package className="w-5 h-5 text-primary" />
                        <h3 className="font-semibold text-primary">Box Contents & Parts List</h3>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Check that you have all components before starting assembly.
                      </p>
                      <div className="rounded-lg overflow-hidden border border-border bg-white">
                        <img
                          src={partsOverviewImage}
                          alt="Parts Overview"
                          className="w-full h-auto"
                        />
                      </div>
                    </div>
                  </Card>
                )}

                {/* Steps */}
                <div className="space-y-8">
                  {assemblyManualImages.map((imageUrl, index) => (
                    <Card key={index} className="p-4">
                      <div className="flex gap-4">
                        <div className="flex-shrink-0">
                          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                            <span className="text-primary font-bold">{index + 1}</span>
                          </div>
                        </div>
                        <div className="flex-1 space-y-2">
                          <h3 className="font-semibold">Step {index + 1}</h3>
                          {assemblyManualPrompts[index] && (
                            <p className="text-sm text-muted-foreground">
                              {typeof assemblyManualPrompts[index] === 'string'
                                ? assemblyManualPrompts[index]
                                : assemblyManualPrompts[index].instruction}
                            </p>
                          )}
                          <div className="mt-4 rounded-lg overflow-hidden border border-border">
                            <img
                              src={imageUrl}
                              alt={`Assembly step ${index + 1}`}
                              className="w-full h-auto"
                            />
                          </div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
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
