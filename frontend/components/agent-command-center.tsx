"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Terminal, Zap, Palette, FileText, Package, Wand2, Image, CheckCircle2, Loader2 } from "lucide-react"
import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

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
  isInConversation = false,
  onSkipConversation,
  hasConversationData = false,
}: {
  messages: Message[]
  onBuild: (prompt: string, skipConversation?: boolean) => void
  isThinking: boolean
  messageRef: React.RefObject<HTMLDivElement | null>
  selectedItemsCount: number
  isInConversation?: boolean
  onSkipConversation?: () => void
  hasConversationData?: boolean
}) {
  const [inputValue, setInputValue] = useState("")

  const handleBuildClick = () => {
    if (inputValue.trim()) {
      onBuild(inputValue, false)
      setInputValue("")
    }
  }

  const handleSkipConversation = () => {
    if (onSkipConversation) {
      onSkipConversation()
    } else {
      // If no handler provided, call onBuild with skip flag
      onBuild(inputValue || "", true)
      setInputValue("")
    }
  }

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header */}
      <div className="border-b border-border pb-3">
        <h2 className="text-sm font-bold uppercase tracking-widest terminal text-foreground mb-2">
          Production Pipeline
        </h2>
        <div className="flex gap-2">
          <Badge variant="secondary" className="text-xs bg-muted border-border">
            <Zap className="w-3 h-3 mr-1" />
            Agent: Planner
          </Badge>
          {selectedItemsCount > 0 && (
            <Badge className="text-xs bg-primary/20 border-primary/30 text-primary">
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
          messages.map((msg, index) => {
            const isLatest = index === messages.length - 1
            return (
              <div key={msg.id} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
                {msg.type === "user" ? (
                  /* User Message */
                  <div className="bg-muted border border-border rounded p-3 max-w-xs text-xs">
                    <div className="text-foreground prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-code:text-foreground prose-pre:bg-muted prose-pre:text-foreground">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                ) : msg.steps && msg.steps.length > 0 ? (
                  /* Agent Message with Steps */
                  <div className="w-full">
                    <Accordion type="single" collapsible defaultValue={isLatest ? `agent-${msg.id}` : undefined} className="w-full">
                      <AccordionItem value={`agent-${msg.id}`} className="border-border">
                        <AccordionTrigger className="py-2 text-xs hover:no-underline">
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                            <div className="font-mono text-foreground prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-code:text-foreground prose-p:inline">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content || "Agent Processing"}</ReactMarkdown>
                            </div>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent className="bg-card rounded border border-border p-4 mt-2 space-y-3">
                          {/* Progress Bar */}
                          {msg.steps && msg.steps.length > 0 && (() => {
                            const completedCount = msg.steps.filter(s =>
                              s.startsWith('✓') || s.includes('completed') || s.includes('generated') || s.includes('created') || s.includes('selected')
                            ).length
                            const failedCount = msg.steps.filter(s => s.startsWith('✗') || s.toLowerCase().includes('error')).length

                            return (
                              <div className="mb-4">
                                <div className="flex justify-between text-xs mb-2">
                                  <span className="text-muted-foreground">Progress</span>
                                  <span className="text-foreground font-semibold">
                                    {completedCount} / {msg.steps.length}
                                    {failedCount > 0 && <span className="text-red-500 ml-1">({failedCount} failed)</span>}
                                  </span>
                                </div>
                                <div className="h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className={`h-full transition-all duration-500 ease-out ${failedCount > 0 ? 'bg-red-500' : 'bg-primary'
                                      }`}
                                    style={{
                                      width: `${(completedCount / msg.steps.length) * 100}%`
                                    }}
                                  />
                                </div>
                              </div>
                            )
                          })()}

                          {/* Steps */}
                          {msg.steps?.map((step, idx) => {
                            const isComplete = step.startsWith('✓') ||
                              step.includes('completed') ||
                              step.includes('generated') ||
                              step.includes('created') ||
                              step.includes('selected')
                            const isFailed = step.startsWith('✗') || step.toLowerCase().includes('error')
                            const isInProgress = step.startsWith('⏳') || step.includes('...')

                            // Determine icon based on step content
                            let StepIcon = Terminal
                            if (step.includes('Style')) StepIcon = Palette
                            else if (step.includes('Planner') || step.includes('plan')) StepIcon = FileText
                            else if (step.includes('Inventory') || step.includes('materials')) StepIcon = Package
                            else if (step.includes('Prompt')) StepIcon = Wand2
                            else if (step.includes('Image') || step.includes('Flux')) StepIcon = Image

                            return (
                              <div
                                key={idx}
                                className={`flex items-start gap-3 p-2 rounded transition-all ${isComplete ? 'bg-primary/10' : isFailed ? 'bg-red-500/10' : 'bg-muted/50'
                                  }`}
                              >
                                {/* Icon/Status */}
                                <div className="flex-shrink-0 mt-0.5">
                                  {isComplete ? (
                                    <CheckCircle2 className="w-4 h-4 text-primary animate-in zoom-in duration-300" />
                                  ) : isFailed ? (
                                    <div className="w-4 h-4 rounded-full bg-red-500 flex items-center justify-center">
                                      <span className="text-white text-xs">✗</span>
                                    </div>
                                  ) : isInProgress ? (
                                    <Loader2 className="w-4 h-4 text-primary animate-spin" />
                                  ) : (
                                    <StepIcon className="w-4 h-4 text-muted-foreground" />
                                  )}
                                </div>

                                {/* Step Content */}
                                <div className="flex-1 min-w-0">
                                  <p className={`text-xs leading-relaxed ${isComplete ? 'text-foreground font-medium' :
                                    isFailed ? 'text-red-500' :
                                      'text-muted-foreground'
                                    }`}>
                                    {step.replace(/^[✓✗⏳]\s*/, '')}
                                  </p>
                                </div>
                              </div>
                            )
                          })}
                        </AccordionContent>
                      </AccordionItem>
                    </Accordion>
                  </div>
                ) : (
                  /* Agent Message without Steps - just show content */
                  <div className="bg-muted border border-border rounded p-3 text-xs w-full">
                    <div className="text-foreground prose prose-sm dark:prose-invert max-w-none prose-headings:text-foreground prose-p:text-foreground prose-strong:text-foreground prose-code:text-foreground prose-pre:bg-muted prose-pre:text-foreground prose-ul:text-foreground prose-ol:text-foreground prose-li:text-foreground prose-a:text-primary prose-blockquote:text-foreground">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}

        {/* Thinking State */}
        {isThinking && (
          <div className="flex justify-start">
            <div className="bg-muted border border-border rounded p-3 text-xs">
              <div className="flex gap-2 items-center">
                <div className="flex gap-1">
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
                    style={{ animationDelay: "0ms" }}
                  />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
                    style={{ animationDelay: "150ms" }}
                  />
                  <div
                    className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
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
          placeholder={isInConversation ? "Answer the question..." : "Describe your assembly..."}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleBuildClick()}
          className="h-8 bg-input border-border text-xs"
        />
        <div className="flex gap-2">
          {isInConversation && (
            <Button
              onClick={handleSkipConversation}
              disabled={isThinking || !hasConversationData}
              variant="outline"
              className="flex-1 h-8 font-semibold text-xs"
              title={!hasConversationData ? "Please answer at least one question first" : "Skip to design generation"}
            >
              Skip Conversation
            </Button>
          )}
          <Button
            onClick={handleBuildClick}
            disabled={!inputValue.trim() || isThinking}
            className={isInConversation ? "flex-1 h-8 font-semibold text-xs" : "w-full h-8 font-semibold text-xs"}
          >
            {isInConversation ? "Send" : "Build"}
          </Button>
        </div>
      </div>
    </div>
  )
}
