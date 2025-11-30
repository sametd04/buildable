"use client"

import { Moon, Sun, Monitor } from "lucide-react"
import { useTheme } from "./theme-provider"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()

  const cycleTheme = () => {
    if (theme === "system") {
      setTheme("light")
    } else if (theme === "light") {
      setTheme("dark")
    } else {
      setTheme("system")
    }
  }

  return (
    <button
      onClick={cycleTheme}
      className="fixed top-4 right-4 z-50 p-2 rounded-lg border border-border bg-card hover:bg-muted transition-colors"
      title={`Current: ${theme} (click to cycle)`}
    >
      {theme === "system" && <Monitor className="w-5 h-5 text-foreground" />}
      {theme === "light" && <Sun className="w-5 h-5 text-foreground" />}
      {theme === "dark" && <Moon className="w-5 h-5 text-foreground" />}
    </button>
  )
}
