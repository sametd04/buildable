"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Package, Check } from "lucide-react"

interface InventoryItem {
  id: string
  name: string
  category?: string
  description?: string
  image_url?: string
}

const INVENTORY_DATA: InventoryItem[] = [
  { id: "1", name: "Galvanized Pipe", category: "Metal" },
  { id: "2", name: "Cinder Block", category: "Concrete" },
  { id: "3", name: "Neon Tube", category: "Glass" },
  { id: "4", name: "Oak Slab", category: "Wood" },
]

export function Warehouse({
  selectedItems,
  selectedItemsData,
  onSelectItem,
}: {
  selectedItems: string[]
  selectedItemsData?: InventoryItem[]
  onSelectItem: (id: string) => void
}) {
  const [searchQuery, setSearchQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  // Use selectedItemsData if available, otherwise fall back to INVENTORY_DATA
  const displayItems = selectedItemsData && selectedItemsData.length > 0 ? selectedItemsData : INVENTORY_DATA

  const [filteredItems, setFilteredItems] = useState(displayItems)

  useEffect(() => {
    setIsLoading(true)
    const timer = setTimeout(() => {
      setFilteredItems(
        displayItems.filter(
          (item) =>
            item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (item.category && item.category.toLowerCase().includes(searchQuery.toLowerCase())),
        ),
      )
      setIsLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery, displayItems])

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header */}
      <div className="flex flex-col gap-3 pb-2 border-b border-border">
        <h2 className="text-sm font-bold uppercase tracking-widest terminal text-foreground">Material Database</h2>
        <Input
          placeholder="Search Catalog..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-8 bg-input border-border text-xs"
        />
      </div>

      {/* Inventory Grid */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        <div className="flex gap-2 pb-2 w-max">
          {isLoading ? (
            <>
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-40 h-24 bg-card rounded border border-border animate-pulse flex-shrink-0"
                />
              ))}
            </>
          ) : filteredItems.length > 0 ? (
            filteredItems.map((item) => (
              <Card
                key={item.id}
                onClick={() => onSelectItem(item.id)}
                className={`p-3 cursor-pointer transition-all border-2 flex-shrink-0 w-40 ${
                  selectedItems.includes(item.id)
                    ? "border-primary bg-muted"
                    : "border-border bg-card hover:border-primary/50"
                }`}
              >
                <div className="flex flex-col gap-2 h-full">
                  {/* Thumbnail */}
                  <div className="w-full h-12 bg-muted rounded border border-border flex items-center justify-center">
                    <Package className="w-5 h-5 text-muted-foreground" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <p className="text-xs font-semibold text-foreground truncate">{item.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{item.category || "Unknown"}</p>
                    </div>
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs terminal text-foreground truncate flex-1">{item.id}</p>
                      {/* Selection Badge */}
                      {selectedItems.includes(item.id) && (
                        <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                          <Check className="w-2.5 h-2.5 text-primary-foreground" />
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))
          ) : (
            <div className="flex items-center justify-center w-full text-muted-foreground text-xs">No items found</div>
          )}
        </div>
      </div>
    </div>
  )
}
