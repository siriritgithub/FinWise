import { useQuery } from "@tanstack/react-query";
import { Loader2, ArrowRight, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { Link } from "react-router-dom";
import api from "../lib/api";
import type { Transaction } from "../types";
import { formatINR, formatDate } from "../lib/utils";

const fetchRecentTransactions = async (): Promise<Transaction[]> => {
  const { data } = await api.get("/transactions", {
    params: { page: 1, page_size: 7 },
  });
  return data;
};

const TransactionIcon = ({ type }: { type: Transaction["type"] }) => {
  const iconClass = "h-5 w-5";
  if (type === "income") {
    return (
      <div className="p-2 bg-green-100 rounded-full">
        <ArrowUpRight className={`${iconClass} text-green-600`} />
      </div>
    );
  }
  return (
    <div className="p-2 bg-red-100 rounded-full">
      <ArrowDownRight className={`${iconClass} text-red-600`} />
    </div>
  );
};

export const RecentTransactions = () => {
  const { data: transactions, isLoading } = useQuery<Transaction[]>({
    queryKey: ["recentTransactions"],
    queryFn: fetchRecentTransactions,
  });

  if (isLoading) {
    return <Loader2 className="h-6 w-6 animate-spin text-blue-600" />;
  }

  return (
    <div className="legacy-dark-card p-4 rounded-2xl border shadow-xl shadow-black/10 h-full">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Recent Transactions</h2>
        <Link to="/transactions" className="text-sm text-blue-600 hover:underline flex items-center">
          View All <ArrowRight className="h-4 w-4 ml-1" />
        </Link>
      </div>
      <div className="space-y-4">
        {transactions?.map((txn) => (
          <div key={txn.id} className="flex items-center">
            <TransactionIcon type={txn.type} />
            <div className="ml-4 flex-grow">
              <p className="font-medium">{txn.merchant || txn.description || "Transaction"}</p>
              <p className="text-sm legacy-muted">{formatDate(txn.transaction_date)}</p>
            </div>
            <p
              className={`font-semibold ${
                txn.type === "income" ? "text-green-600" : "text-slate-200"
              }`}
            >
              {txn.type === "income" ? "+" : "-"}
              {formatINR(txn.amount)}
            </p>
          </div>
        ))}
        {!transactions || transactions.length === 0 && (
          <p className="legacy-muted text-center py-8">No recent transactions found.</p>
        )}
      </div>
    </div>
  );
};