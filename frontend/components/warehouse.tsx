"use client"

import { useState, useEffect } from "react"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Package, Check, Info, Trash2 } from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"

interface InventoryItem {
  id: string
  name: string
  category?: string
  description?: string
  image_url?: string
  src?: string
  text?: string
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
  const [isLoading, setIsLoading] = useState(true)
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>(INVENTORY_DATA)
  const [selectedItemForDetails, setSelectedItemForDetails] = useState<InventoryItem | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Fetch inventory from backend on mount
  useEffect(() => {
    fetchInventory()
  }, [])

  const fetchInventory = async () => {
    try {
      const response = await fetch("http://localhost:8000/api/v1/inventory")
      const data = await response.json()
      if (data.success && data.items) {
        setInventoryItems(data.items)
      }
    } catch (error) {
      console.error("Failed to fetch inventory:", error)
      // Fall back to hardcoded data on error
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteItem = async (itemId: string) => {
    if (!confirm("Are you sure you want to delete this item?")) {
      return
    }

    setIsDeleting(true)
    try {
      const response = await fetch(`http://localhost:8000/api/v1/inventory/${itemId}`, {
        method: "DELETE",
      })
      const data = await response.json()

      if (data.success) {
        // Remove from local state
        setInventoryItems((prev) => prev.filter((item) => item.id !== itemId))
        setSelectedItemForDetails(null)
        // Also deselect if it was selected
        if (selectedItems.includes(itemId)) {
          onSelectItem(itemId)
        }
      } else {
        alert("Failed to delete item")
      }
    } catch (error) {
      console.error("Failed to delete item:", error)
      alert("Failed to delete item")
    } finally {
      setIsDeleting(false)
    }
  }

  // Use selectedItemsData if available, otherwise fall back to fetched inventory
  const displayItems = selectedItemsData && selectedItemsData.length > 0 ? selectedItemsData : inventoryItems

  const [filteredItems, setFilteredItems] = useState(displayItems)

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilteredItems(
        displayItems.filter(
          (item) =>
            item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (item.category && item.category.toLowerCase().includes(searchQuery.toLowerCase())),
        ),
      )
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
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-4 gap-2 pb-2">
          {isLoading ? (
            <>
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="w-full h-24 bg-card rounded border border-border animate-pulse"
                />
              ))}
            </>
          ) : filteredItems.length > 0 ? (
            filteredItems.map((item) => {
              // Extract price from description
              const priceMatch = item.description?.match(/Price:\s*([\d.,]+)\s*â¬/)
              const price = priceMatch ? priceMatch[1] : null

              return (
                <Card
                  key={item.id}
                  className={`p-3 cursor-pointer transition-all border-2 relative group ${selectedItems.includes(item.id)
                      ? "border-primary bg-muted"
                      : "border-border bg-card hover:border-primary/50"
                    }`}
                >
                  <div className="flex flex-col gap-2 h-full" onClick={() => onSelectItem(item.id)}>
                    {/* Thumbnail */}
                    <div className="w-full h-20 bg-muted rounded border border-border flex items-center justify-center overflow-hidden">
                      {(item.src || item.image_url) ? (
                        <img
                          src={item.src || item.image_url}
                          alt={item.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Package className="w-6 h-6 text-muted-foreground" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 flex flex-col justify-between">
                      <div>
                        <p className="text-xs font-semibold text-foreground truncate leading-tight">{item.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{item.category || "Unknown"}</p>
                      </div>
                      <div className="flex items-center justify-between gap-1">
                        <p className="text-xs terminal text-foreground truncate flex-1">{item.id}</p>
                        {/* Price or Selection Badge */}
                        {selectedItems.includes(item.id) ? (
                          <div className="w-4 h-4 rounded-full bg-primary flex items-center justify-center flex-shrink-0">
                            <Check className="w-2.5 h-2.5 text-primary-foreground" />
                          </div>
                        ) : price ? (
                          <span className="text-xs font-bold text-primary">{price}â¬</span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  {/* Info Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedItemForDetails(item)
                    }}
                    className="absolute top-2 right-2 p-1.5 rounded bg-background/90 hover:bg-background border border-border opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Info className="w-4 h-4 text-foreground" />
                  </button>
                </Card>
              )
            })
          ) : (
            <div className="col-span-4 flex items-center justify-center text-muted-foreground text-xs py-8">No items found</div>
          )}
        </div>
      </div>

      {/* Item Details Dialog */}
      <Dialog open={!!selectedItemForDetails} onOpenChange={(open) => !open && setSelectedItemForDetails(null)}>
        <DialogContent onClose={() => setSelectedItemForDetails(null)}>
          {selectedItemForDetails && (() => {
            // Extract price from description
            const priceMatch = selectedItemForDetails.description?.match(/Price:\s*([\d.,]+)\s*â¬/)
            const price = priceMatch ? priceMatch[1] : null

            return (
              <>
                <DialogHeader>
                  <div className="pr-8">
                    <DialogTitle className="text-xl">{selectedItemForDetails.name}</DialogTitle>
                    <div className="flex items-center gap-2 mt-2">
                      <DialogDescription className="text-base">{selectedItemForDetails.category || "Uncategorized"}</DialogDescription>
                      {price && (
                        <span className="text-lg font-bold text-primary">{price} â¬</span>
                      )}
                    </div>
                  </div>
                </DialogHeader>
                <div className="p-6 space-y-4">
                  {/* Image */}
                  {(selectedItemForDetails.src || selectedItemForDetails.image_url) ? (
                    <img
                      src={selectedItemForDetails.src || selectedItemForDetails.image_url}
                      alt={selectedItemForDetails.name}
                      className="w-full h-80 object-cover rounded-lg border border-border shadow-md"
                    />
                  ) : (
                    <div className="w-full h-80 bg-muted rounded-lg border border-border flex items-center justify-center">
                      <Package className="w-20 h-20 text-muted-foreground" />
                    </div>
                  )}

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-4 p-4 bg-muted/30 rounded-lg border border-border">
                    <div>
                      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Item ID</p>
                      <p className="text-sm terminal text-foreground font-medium">{selectedItemForDetails.id}</p>
                    </div>
                    {selectedItemForDetails.category && (
                      <div>
                        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">Category</p>
                        <p className="text-sm text-foreground font-medium">{selectedItemForDetails.category}</p>
                      </div>
                    )}
                  </div>

                  {/* Description */}
                  {selectedItemForDetails.description && (
                    <div className="p-4 bg-card rounded-lg border border-border">
                      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2">Description</p>
                      <p className="text-sm text-foreground leading-relaxed whitespace-pre-line">{selectedItemForDetails.description}</p>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        onSelectItem(selectedItemForDetails.id)
                        setSelectedItemForDetails(null)
                      }}
                      className={`flex-1 py-3 px-4 rounded-lg font-semibold border-2 transition-all ${selectedItems.includes(selectedItemForDetails.id)
                          ? "border-primary bg-primary text-primary-foreground shadow-lg"
                          : "border-border bg-card hover:border-primary hover:shadow-md text-foreground"
                        }`}
                    >
                      {selectedItems.includes(selectedItemForDetails.id) ? "â Selected" : "Select Item"}
                    </button>
                    <button
                      onClick={() => handleDeleteItem(selectedItemForDetails.id)}
                      disabled={isDeleting}
                      className="py-3 px-4 rounded-lg font-semibold border-2 border-red-500/50 bg-card hover:bg-red-500 hover:text-white text-red-500 transition-all hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete item"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
