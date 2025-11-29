"use client"

import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { RotateCcw, FileDown, Cpu } from "lucide-react"

export function AssemblyWorkbench({
  generatedImage,
  onRegenerate,
}: { generatedImage: string | null; onRegenerate: () => void }) {
  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-border bg-slate-950/70 p-4">
        <Tabs defaultValue="hero" className="w-full">
          <TabsList className="bg-slate-900 border border-slate-800">
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

          <TabsContent value="hero" className="mt-4">
            <div className="text-xs text-muted-foreground">Hero render mode active</div>
          </TabsContent>
          <TabsContent value="schematic" className="mt-4">
            <div className="text-xs text-muted-foreground">Schematic view mode active</div>
          </TabsContent>
          <TabsContent value="guide" className="mt-4">
            <div className="text-xs text-muted-foreground">Assembly guide mode active</div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Main Canvas */}
      <div className="flex-1 flex items-center justify-center dot-grid relative overflow-hidden p-6">
        {generatedImage ? (
          <Card className="bg-slate-900/80 border-slate-800 p-4 shadow-2xl max-w-lg max-h-full">
            <img
              src={generatedImage || "/placeholder.svg"}
              alt="Generated assembly"
              className="w-full h-full object-contain rounded"
            />
          </Card>
        ) : (
          <div className="flex flex-col items-center gap-4 text-muted-foreground">
            <div className="w-16 h-16 rounded border-2 border-dashed border-slate-700 flex items-center justify-center">
              <Cpu className="w-8 h-8 text-orange-500/30" />
            </div>
            <p className="text-sm font-mono uppercase tracking-widest">AWAITING AGENT INPUT</p>
          </div>
        )}
      </div>

      {/* Bottom Controls - Removed "Edit Prompt" button */}
      <div className="border-t border-border bg-slate-950/70 p-4 flex justify-center gap-3">
        <Button
          variant="outline"
          size="sm"
          className="bg-slate-900 border-slate-700 hover:border-orange-500 h-8"
          onClick={onRegenerate}
          disabled={!generatedImage}
        >
          <RotateCcw className="w-3 h-3 mr-2" />
          Regenerate
        </Button>
        <Button variant="outline" size="sm" className="bg-slate-900 border-slate-700 hover:border-orange-500 h-8">
          <FileDown className="w-3 h-3 mr-2" />
          Export PDF
        </Button>
      </div>
    </div>
  )
}
