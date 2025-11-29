"use client"

import type React from "react"

interface ResizableDividerProps {
  onResize: (delta: number) => void
}

export function ResizableDivider({ onResize }: ResizableDividerProps) {
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    const startY = e.clientY

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - startY
      onResize(delta * 0.25)
    }

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove)
      document.removeEventListener("mouseup", handleMouseUp)
    }

    document.addEventListener("mousemove", handleMouseMove)
    document.addEventListener("mouseup", handleMouseUp)
  }

  return (
    <div
      onMouseDown={handleMouseDown}
      className="h-1 bg-slate-700 hover:bg-orange-500 cursor-row-resize transition-colors duration-200 group active:bg-orange-500"
      title="Drag to resize"
    />
  )
}
