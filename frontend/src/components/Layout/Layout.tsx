import { NavLink, Outlet } from 'react-router'

const links = [
  { to: '/', label: 'Indicadores' },
  { to: '/receita', label: 'Receita' },
  { to: '/visao-360', label: 'Visão 360' },
  { to: '/inspecoes', label: 'Fila de inspeção' },
  { to: '/continuidade', label: 'Continuidade' },
]

function Layout() {
  return (
    <div>
      <header>
        <strong>V-Energy Grid 360</strong>
      </header>

      <nav>
        <ul>
          {links.map((link) => (
            <li key={link.to}>
              <NavLink to={link.to} end={link.to === '/'}>
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <main>
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
