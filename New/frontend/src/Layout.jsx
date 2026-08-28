import { NavLink, Outlet } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Home', end: true },
  { to: '/debugger', label: 'Debugger' },
  { to: '/theory', label: 'Theory' },
  { to: '/history', label: 'History' },
  { to: '/about', label: 'About' },
]

function Layout() {
  return (
    <>
      <header className="site-header">
        <div className="site-header-inner">
          <span className="site-brand">Stored Procedure Debugger</span>
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
        </div>
      </header>
      <main id="page-content">
        <Outlet />
      </main>
    </>
  )
}

export default Layout
