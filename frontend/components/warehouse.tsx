"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Package, Check } from "lucide-react"

interface InventoryItem {
  id: string
  name: string
  type: string
  itemId: string
}

const INVENTORY_DATA: InventoryItem[] = [
  { id: "1", name: "Galvanized Pipe", type: "Metal", itemId: "#P-9921" },
  { id: "2", name: "Cinder Block", type: "Concrete", itemId: "#M-4421" },
  { id: "3", name: "Neon Tube", type: "Glass", itemId: "#E-1847" },
  { id: "4", name: "Oak Slab", type: "Wood", itemId: "#W-5523" },
]

export function Warehouse({
  selectedItems,
  onSelectItem,
}: { selectedItems: string[]; onSelectItem: (id: string) => void }) {
  const [searchQuery, setSearchQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [filteredItems, setFilteredItems] = useState(INVENTORY_DATA)

  useEffect(() => {
    setIsLoading(true)
    const timer = setTimeout(() => {
      setFilteredItems(
        INVENTORY_DATA.filter(
          (item) =>
            item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.type.toLowerCase().includes(searchQuery.toLowerCase()),
        ),
      )
      setIsLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  return (
    <div className="flex flex-col h-full p-4 gap-4">
      {/* Header */}
      <div className="flex flex-col gap-3 pb-2 border-b border-border">
        <h2 className="text-sm font-bold uppercase tracking-widest terminal text-orange-500">Material Database</h2>
        <Input
          placeholder="Search Catalog..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-8 bg-slate-900 border-slate-800 text-xs"
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
                  className="w-40 h-24 bg-slate-900 rounded border border-slate-800 animate-pulse flex-shrink-0"
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
                    ? "border-orange-500 bg-slate-800/50"
                    : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
                }`}
              >
                <div className="flex flex-col gap-2 h-full">
                  {/* Thumbnail */}
                  <div className="w-full h-12 bg-gradient-to-br from-slate-700 to-slate-900 rounded border border-slate-700 flex items-center justify-center">
                    <Package className="w-5 h-5 text-orange-500/50" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 flex flex-col justify-between">
                    <div>
                      <p className="text-xs font-semibold text-foreground truncate">{item.name}</p>
                      <p className="text-xs text-muted-foreground truncate">{item.type}</p>
                    </div>
                    <div className="flex items-center justify-between gap-1">
                      <p className="text-xs terminal text-orange-400 truncate flex-1">{item.itemId}</p>
                      {/* Selection Badge */}
                      {selectedItems.includes(item.id) && (
                        <div className="w-4 h-4 rounded-full bg-orange-500 flex items-center justify-center flex-shrink-0">
                          <Check className="w-2.5 h-2.5 text-slate-950" />
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
