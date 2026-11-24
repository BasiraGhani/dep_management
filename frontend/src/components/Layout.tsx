import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router';

import { useAuth } from '../auth/useAuth';
import { ROLE_LABEL } from '../lib/labels';
import { navItemsFor } from './navItems';

/** Sidebar (filtered by role), top bar (name, role, logout) and the page content. */
export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  if (user === null) return null; // only rendered inside ProtectedRoute

  const linked = user.teacher ?? user.student;
  const name = linked ? `${linked.first_name} ${linked.last_name}` : user.username;
  const onLogout = () => {
    logout();
    void navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-50 lg:flex">
      <aside
        className={`${menuOpen ? 'block' : 'hidden'} w-full bg-slate-900 text-slate-200 lg:block lg:min-h-screen lg:w-60 lg:shrink-0`}
      >
        <div className="hidden px-5 py-4 text-lg font-semibold text-white lg:block">
          Department System
        </div>
        <nav aria-label="Main">
          <ul className="space-y-1 px-3 py-2">
            {navItemsFor(user.role).map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => {
                    setMenuOpen(false);
                  }}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 ${
                      isActive ? 'bg-slate-700 text-white' : 'hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b bg-white px-4 py-3">
          <button
            type="button"
            aria-expanded={menuOpen}
            onClick={() => {
              setMenuOpen((open) => !open);
            }}
            className="rounded border px-3 py-1 lg:hidden"
          >
            Menu
          </button>
          <div className="ml-auto flex items-center gap-4">
            <div className="text-right">
              <div className="font-medium text-slate-800">{name}</div>
              <div className="text-xs text-slate-500">{ROLE_LABEL[user.role]}</div>
            </div>
            <button
              type="button"
              onClick={onLogout}
              className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
            >
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
