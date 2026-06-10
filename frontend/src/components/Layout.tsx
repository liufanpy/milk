import { Outlet, NavLink } from 'react-router-dom';
import { useAppStore } from '../store/appStore';

const navItems = [
  { to: '/', label: '看板' },
  { to: '/products', label: '产品' },
  { to: '/customers', label: '客户' },
  { to: '/suppliers', label: '供应商' },
  { to: '/purchases', label: '进货' },
  { to: '/sales', label: '零售' },
  { to: '/distribution-orders', label: '铺货管理' },
  { to: '/returns', label: '退货' },
  { to: '/wastage', label: '损耗' },
  { to: '/subscriptions', label: '订奶' },
  { to: '/stores', label: '店铺管理' },
  { to: '/store-sales', label: '巡店记录' },
  { to: '/inventory', label: '库存' },
  { to: '/stock-ledger', label: '库存流水' },
  { to: '/transaction-ledger', label: '资金流水' },
  { to: '/logs', label: '日志' },
];

export default function Layout() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className={`${sidebarOpen ? 'w-48' : 'w-0'} overflow-hidden transition-all bg-gray-900 text-white flex-shrink-0`}>
        <div className="p-4 font-bold text-lg border-b border-gray-700">奶记</div>
        <nav className="p-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm ${isActive ? 'bg-blue-600 text-white' : 'text-gray-300 hover:bg-gray-800'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-12 bg-white border-b flex items-center px-4 flex-shrink-0">
          <button onClick={() => useAppStore.getState().toggleSidebar()} className="text-gray-500 mr-4">
            ☰
          </button>
          <span className="font-medium">奶记</span>
        </header>
        <main className="flex-1 overflow-auto p-4">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
