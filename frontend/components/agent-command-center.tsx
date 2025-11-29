"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Terminal, Zap } from "lucide-react"
import { useState } from "react"

interface Message {
  id: string
  type: "user" | "agent"
  content: string
  steps?: string[]
}

export function AgentCommandCenter({
  messages,
  onBuild,
  isThinking,
  messageRef,
  selectedItemsCount,
}: {
  messages: Message[]
  onBuild: (prompt: string) => void
  isThinking: boolean
  messageRef: React.RefObject<HTMLDivElement>
  selectedItemsCount: number
}) {
  const [inputValue, setInputValue] = useState("")

  const handleBuildClick = () => {
    if (inputValue.trim()) {
      onBuild(inputValue)
      setInputValue("")
    }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header */}
      <div className="border-b border-border pb-3">
        <h2 className="text-sm font-bold uppercase tracking-widest terminal text-orange-500 mb-2">
          Production Pipeline
        </h2>
        <div className="flex gap-2">
          <Badge variant="secondary" className="text-xs bg-slate-800 border-slate-700">
            <Zap className="w-3 h-3 mr-1" />
            Agent: Planner
          </Badge>
          {selectedItemsCount > 0 && (
            <Badge className="text-xs bg-orange-500/20 border-orange-500/30 text-orange-400">
              {selectedItemsCount} selected
            </Badge>
          )}
        </div>
      </div>

      {/* Messages Timeline */}
      <div ref={messageRef} className="flex-1 overflow-y-auto space-y-3">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-xs text-center">
            <div>
              <Terminal className="w-6 h-6 mx-auto mb-2 opacity-30" />
              Ready for commands
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
              {msg.type === "user" ? (
                /* User Message */
                <div className="bg-orange-500/20 border border-orange-500/50 rounded p-3 max-w-xs text-xs">
                  <p className="text-foreground">{msg.content}</p>
                </div>
              ) : (
                /* Agent Message with Steps */
                <div className="w-full">
                  <Accordion type="single" collapsible defaultValue="agent-log" className="w-full">
                    <AccordionItem value="agent-log" className="border-slate-800">
                      <AccordionTrigger className="py-2 text-xs hover:no-underline">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                          <span className="font-mono text-orange-400">Agent: Inventory Clerk</span>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent className="bg-slate-900/40 rounded border border-slate-800 p-3 mt-2 space-y-2">
                        {msg.steps?.map((step, idx) => (
                          <div key={idx} className="text-xs font-mono text-muted-foreground flex gap-2">
                            <span className="text-slate-600">[{idx + 1}]</span>
                            <span>{step}</span>
                          </div>
                        ))}
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </div>
              )}
            </div>
          ))
        )}

        {/* Thinking State */}
        {isThinking && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-700 rounded p-3 text-xs">
              <div className="flex gap-2 items-center">
                <div className="flex gap-1">
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-bounce"
                    style={{ animationDelay: "300ms" }}
                  />
                </div>
                <span className="text-muted-foreground">Thinking...</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border pt-3 space-y-2">
        <Input
          placeholder="Describe your assembly..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleBuildClick()}
          className="h-8 bg-slate-900 border-slate-800 text-xs"
        />
        <Button
          onClick={handleBuildClick}
          disabled={!inputValue.trim() || isThinking}
          className="w-full h-8 bg-orange-500 hover:bg-orange-600 text-slate-950 font-semibold text-xs"
        >
          Build
        </Button>
      </div>
    </div>
  )
}
