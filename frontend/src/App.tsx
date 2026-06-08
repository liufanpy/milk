import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';

const queryClient = new QueryClient();

// Lazy imports for pages
import DashboardPage from './pages/DashboardPage';
import ProductsPage from './pages/ProductsPage';
import CustomersPage from './pages/CustomersPage';
import SuppliersPage from './pages/SuppliersPage';
import PurchasesPage from './pages/PurchasesPage';
import SalesPage from './pages/SalesPage';
import DeliveriesPage from './pages/DeliveriesPage';
import ReturnsPage from './pages/ReturnsPage';
import WastagePage from './pages/WastagePage';
import SubscriptionsPage from './pages/SubscriptionsPage';
import SubscriptionDetailPage from './pages/SubscriptionDetailPage';
import InventoryPage from './pages/InventoryPage';
import OperationLogsPage from './pages/OperationLogsPage';
import StockLedgerPage from './pages/StockLedgerPage';
import TransactionLedgerPage from './pages/TransactionLedgerPage';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/products" element={<ProductsPage />} />
            <Route path="/customers" element={<CustomersPage />} />
            <Route path="/suppliers" element={<SuppliersPage />} />
            <Route path="/purchases" element={<PurchasesPage />} />
            <Route path="/sales" element={<SalesPage />} />
            <Route path="/deliveries" element={<DeliveriesPage />} />
            <Route path="/returns" element={<ReturnsPage />} />
            <Route path="/wastage" element={<WastagePage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/subscriptions/:id" element={<SubscriptionDetailPage />} />
            <Route path="/inventory" element={<InventoryPage />} />
            <Route path="/logs" element={<OperationLogsPage />} />
            <Route path="/stock-ledger" element={<StockLedgerPage />} />
            <Route path="/transaction-ledger" element={<TransactionLedgerPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
