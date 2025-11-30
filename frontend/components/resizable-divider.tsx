"use client"

import type React from "react"

interface ResizableDividerProps {
  onResize: (delta: number) => void
}

export function ResizableDivider({ onResize }: ResizableDividerProps) {
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    const startY = e.clientY
    let lastY = startY

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const delta = moveEvent.clientY - lastY
      lastY = moveEvent.clientY
      onResize(delta)
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
      className="h-1 bg-border hover:bg-primary cursor-row-resize transition-colors duration-200 group active:bg-primary"
      title="Drag to resize"
    />
  )
}
