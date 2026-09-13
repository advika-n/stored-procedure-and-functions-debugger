import { createContext, useContext, useEffect, useState } from 'react'

// Day/Night Mode. Two themes ("dark" = Night Mode, the original/default
// look; "light" = Day Mode), applied purely via a `data-theme` attribute
// on <html> -- theme.css's `:root` (dark) and `:root[data-theme="light"]`
// (light) blocks hold the actual color values, so this context only
// tracks *which* one is active and persists that choice. index.html has
// a tiny inline script that applies the stored value before first paint
// (same storage key), so there's no flash of the wrong theme on load.
const STORAGE_KEY = 'spdebugger:theme'

const ThemeContext = createContext(null)

function readStoredTheme() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === 'light' ? 'light' : 'dark' // default: dark, same as index.html's inline script
  } catch {
    return 'dark'
  }
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(readStoredTheme)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try {
      localStorage.setItem(STORAGE_KEY, theme)
    } catch {
      // Storage can throw (privacy mode, disabled storage, ...) -- the
      // toggle still works for the rest of this session, it just won't
      // survive a refresh.
    }
  }, [theme])

  function toggleTheme() {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }

  return <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>{children}</ThemeContext.Provider>
}

/** { theme: "dark" | "light", setTheme, toggleTheme } */
export function useTheme() {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme must be used within a ThemeProvider')
  return context
}
