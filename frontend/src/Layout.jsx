import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTheme } from './ThemeContext'
import DevelopedByModal from './DevelopedByModal'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/debugger', label: 'Debugger' },
  { to: '/theory', label: 'Theory' },
  { to: '/history', label: 'History' },
  { to: '/quiz', label: 'Quiz' },
  { to: '/about', label: 'About' },
]

function Layout() {
  const { theme, toggleTheme } = useTheme()
  const [isDevelopedByOpen, setIsDevelopedByOpen] = useState(false)

  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <span className="site-brand">Stored Procedure Debugger</span>

          {/* Nav tabs and the theme/Developed-By cluster share one row,
              grouped as a single flex item -- see the .site-header-right
              comment in App.css for why this can't just be three direct
              children of .site-header-inner. */}
          <div className="site-header-right">
            <nav className="top-nav">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => (isActive ? 'top-nav-item top-nav-item-active' : 'top-nav-item')}
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="header-utility-cluster">
              <button
                type="button"
                className="theme-toggle"
                onClick={toggleTheme}
                aria-label={theme === 'dark' ? 'Switch to Day Mode' : 'Switch to Night Mode'}
                title={theme === 'dark' ? 'Switch to Day Mode' : 'Switch to Night Mode'}
              >
                {theme === 'dark' ? '🌙' : '☀️'}
              </button>
              <button type="button" className="developed-by-trigger" onClick={() => setIsDevelopedByOpen(true)}>
                Developed By
              </button>
            </div>
          </div>
        </div>
      </header>

      <main id="page-content">
        <Outlet />
      </main>

      {isDevelopedByOpen && <DevelopedByModal onClose={() => setIsDevelopedByOpen(false)} />}
    </>
  )
}

export default Layout
