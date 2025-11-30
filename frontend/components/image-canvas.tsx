"use client"

import { useCallback, useEffect, useState } from "react"
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Panel,
  Handle,
  Position,
  MarkerType,
  useReactFlow,
} from "reactflow"
import "reactflow/dist/style.css"
import { Maximize2, Minimize2 } from "lucide-react"

interface ImageNode {
  id: string
  imageUrl: string
  isMinimized: boolean
  isSelected?: boolean
  onToggleSize?: () => void
  onSelect?: () => void
}

interface ImageCanvasProps {
  images: string[]
  currentImageIndex: number
  onImageSelect: (index: number) => void
  selectedParents?: number[]
  onParentSelect?: (indices: number[]) => void
}

// Custom Image Node Component
function ImageNodeComponent({ data }: { data: ImageNode }) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div
      className={`relative bg-card rounded-lg overflow-hidden cursor-pointer transition-all ${
        data.isSelected 
          ? "border-4 border-primary shadow-[0_0_30px_rgba(34,139,34,0.6)] ring-4 ring-primary/40" 
          : "border-2 border-border shadow-lg"
      }`}
      style={{
        width: data.isMinimized ? "150px" : "400px",
        height: data.isMinimized ? "150px" : "400px",
      }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={(e) => {
        if (!e.defaultPrevented) {
          data.onSelect?.()
        }
      }}
    >
      {/* Connection Handles - Hidden */}
      <Handle type="target" position={Position.Left} className="opacity-0" />
      <Handle type="source" position={Position.Right} className="opacity-0" />

      <img src={data.imageUrl} alt={`Node ${data.id}`} className="w-full h-full object-cover" />

      {/* Minimize/Maximize Button */}
      {isHovered && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            data.onToggleSize?.()
          }}
          className="absolute top-2 right-2 p-2 bg-background/80 hover:bg-background border border-border rounded transition-colors"
        >
          {data.isMinimized ? (
            <Maximize2 className="w-4 h-4 text-foreground" />
          ) : (
            <Minimize2 className="w-4 h-4 text-foreground" />
          )}
        </button>
      )}

      {/* Node Label */}
      <div className="absolute bottom-0 left-0 right-0 bg-background/95 border-t border-border p-2 backdrop-blur-sm">
        <p className="text-sm font-semibold text-foreground text-center tracking-wide">Version {data.id}</p>
      </div>
    </div>
  )
}

const nodeTypes = {
  imageNode: ImageNodeComponent,
}

export function ImageCanvas({ images, currentImageIndex, onImageSelect, selectedParents = [], onParentSelect }: ImageCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [showError, setShowError] = useState(false)
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null)
  const [manuallyMinimized, setManuallyMinimized] = useState<Record<number, boolean>>({})

  // Build nodes and edges from images
  useEffect(() => {
    if (images.length === 0) {
      setNodes([])
      setEdges([])
      return
    }

    const newNodes: Node[] = images.map((imageUrl, index) => {
      const isLatest = index === images.length - 1
      const isSelected = selectedParents.includes(index)
      
      // Check if manually toggled, otherwise use default (latest = maximized, others = minimized)
      const isMinimized = manuallyMinimized[index] !== undefined 
        ? manuallyMinimized[index] 
        : !isLatest
      
      return {
        id: `node-${index}`,
        type: "imageNode",
        position: { x: index * 500, y: 200 },
        data: {
          id: `${index + 1}`,
          imageUrl,
          isMinimized,
          isSelected,
          onToggleSize: () => toggleNodeSize(index),
          onSelect: () => handleNodeSelect(index),
        },
        selected: isSelected,
        draggable: true,
      }
    })

    const newEdges: Edge[] = []
    for (let i = 0; i < images.length - 1; i++) {
      newEdges.push({
        id: `edge-${i}-${i + 1}`,
        source: `node-${i}`,
        target: `node-${i + 1}`,
        type: "default",
        animated: true,
        style: { 
          stroke: "#228B22",
          strokeWidth: 3,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#228B22",
        },
      })
    }

    setNodes(newNodes)
    setEdges(newEdges)

    // Auto-center on new image
    if (images.length > 0 && reactFlowInstance) {
      setTimeout(() => {
        reactFlowInstance.fitView({ duration: 800, padding: 0.2 })
      }, 100)
    }
  }, [images, selectedParents, manuallyMinimized, setNodes, setEdges, reactFlowInstance])

  const handleNodeSelect = (index: number) => {
    if (!onParentSelect) return

    const isAlreadySelected = selectedParents.includes(index)
    
    if (isAlreadySelected) {
      // Deselect
      onParentSelect(selectedParents.filter((i) => i !== index))
    } else {
      // Select - check limit
      if (selectedParents.length >= 3) {
        setShowError(true)
        setTimeout(() => setShowError(false), 3000)
        return
      }
      onParentSelect([...selectedParents, index])
    }
  }

  const toggleNodeSize = (index: number) => {
    setManuallyMinimized((prev) => {
      const currentState = prev[index] !== undefined ? prev[index] : (index !== images.length - 1)
      return {
        ...prev,
        [index]: !currentState,
      }
    })
  }

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  )

  return (
    <div className="w-full h-full bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={setReactFlowInstance}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 0.8 }}
      >
        <Background color="hsl(var(--border))" gap={20} />
        <Controls className="bg-card border border-border rounded" showInteractive={false} />
        <Panel position="top-left" className="bg-card border border-border rounded p-2">
          <p className="text-xs font-mono text-muted-foreground">
            {images.length} {images.length === 1 ? "Version" : "Versions"}
          </p>
          {selectedParents.length > 0 && (
            <p className="text-xs font-mono text-primary mt-1">
              {selectedParents.length} selected as context
            </p>
          )}
        </Panel>
        {showError && (
          <Panel position="top-center" className="bg-red-500 text-white border border-red-600 rounded p-3 shadow-lg">
            <p className="text-sm font-semibold">⚠️ Maximum 3 images can be selected as context</p>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}
