import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import ProtectedLayout from "./components/ProtectedLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import { Accounts } from "./pages/Accounts";
import Budgets from "./pages/Budgets";
import Goals from "./pages/Goals";
import Analytics from "./pages/Analytics";
import { Chat } from "./pages/Chat";
import { Subscriptions, Receipts, Categories } from "./pages/OtherPages";
import Settings from "./pages/Settings";
import Landing from "./pages/Landing";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Protected */}
          <Route path="/dashboard"     element={<ProtectedLayout><Dashboard /></ProtectedLayout>} />
          <Route path="/transactions"  element={<ProtectedLayout><Transactions /></ProtectedLayout>} />
          <Route path="/accounts"      element={<ProtectedLayout><Accounts /></ProtectedLayout>} />
          <Route path="/categories"    element={<ProtectedLayout><Categories /></ProtectedLayout>} />
          <Route path="/budgets"       element={<ProtectedLayout><Budgets /></ProtectedLayout>} />
          <Route path="/subscriptions" element={<ProtectedLayout><Subscriptions /></ProtectedLayout>} />
          <Route path="/goals"         element={<ProtectedLayout><Goals /></ProtectedLayout>} />
          <Route path="/receipts"      element={<ProtectedLayout><Receipts /></ProtectedLayout>} />
          <Route path="/analytics"     element={<ProtectedLayout><Analytics /></ProtectedLayout>} />
          <Route path="/chat"          element={<ProtectedLayout><Chat /></ProtectedLayout>} />
          <Route path="/settings"      element={<ProtectedLayout><Settings /></ProtectedLayout>} />

          {/* Default */}
          <Route path="/" element={<Landing />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" toastOptions={{ duration: 3000 }} />
    </QueryClientProvider>
  );
}

export default App;
