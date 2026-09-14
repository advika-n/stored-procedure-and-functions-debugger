import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useTheme } from './ThemeContext'
import DevelopedByModal from './DevelopedByModal'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/debugger', label: 'Debugger' },
  { to: '/compare', label: 'Compare' },
  { to: '/tests', label: 'Tests' },
  { to: '/theory', label: 'Theory' },
  { to: '/history', label: 'History' },
  { to: '/quiz', label: 'Quiz' },
  { to: '/about', label: 'About' },
  // Course requirement: the Learn tab must be "prominent" and "positioned
  // top-right" -- rightmost of the main tabs (right next to the Help/theme/
  // Developed-By cluster, i.e. the far top-right of the header) plus its
  // own emphasized styling (see .top-nav-item-emphasize in App.css) so it
  // doesn't just blend in as one more muted tab like its neighbors.
  { to: '/learn', label: '🎓 Learn', emphasize: true },
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
                  className={({ isActive }) =>
                    [
                      'top-nav-item',
                      isActive && 'top-nav-item-active',
                      item.emphasize && 'top-nav-item-emphasize',
                    ]
                      .filter(Boolean)
                      .join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="header-utility-cluster">
              <NavLink
                to="/help"
                className={({ isActive }) => (isActive ? 'help-nav-trigger help-nav-trigger-active' : 'help-nav-trigger')}
              >
                Help
              </NavLink>
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
