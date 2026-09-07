export interface User {
  id: number;
  email: string;
  username?: string | null;
  full_name?: string | null;
  currency: string;
  timezone: string;
  monthly_salary?: number | null;
  phone_number?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  occupation?: string | null;
  country?: string | null;
  language?: string | null;
  theme?: string | null;
  profile_photo_path?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface Account {
  id: number;
  name: string;
  type: "bank" | "cash" | "credit_card" | "wallet" | "investment" | "loan";
  currency?: string;
  balance: number;
  credit_limit?: number | null;
  is_active?: number | boolean;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  parent_category_id?: number | null;
  is_system: boolean | number;
  is_active?: number | boolean;
}

export interface Transaction {
  id: number;
  account_id: number;
  amount: number;
  type: "income" | "expense" | "transfer";
  category_id?: number | null;
  merchant?: string | null;
  description?: string | null;
  transaction_date: string;
  payment_method?: "upi" | "card" | "cash" | "netbanking" | "other" | string;
  is_recurring?: number | boolean;
  is_transfer?: number | boolean;
  confidence_score?: number;
  created_at?: string;
}

export interface Budget {
  id: number;
  category_id?: number | null;
  amount: number;
  month: string;
  created_at?: string;
}

export interface BudgetSummary extends Budget {
  category_name: string;
  budget_amount: number;
  spent_amount: number;
  remaining: number;
  pct_used: number;
}

export interface SavingsGoal {
  id: number;
  name: string;
  target_amount: number;
  current_amount: number;
  deadline?: string | null;
  priority: "low" | "medium" | "high";
  monthly_contribution?: number | null;
  created_at?: string;
}

export interface GoalPlan {
  months_remaining?: number | null;
  required_monthly?: number | null;
  current_surplus: number;
  is_achievable: boolean;
  tradeoff_suggestions: string[];
}

export interface Subscription {
  id: number;
  merchant: string;
  expected_amount: number;
  interval_days: number;
  next_expected_date?: string | null;
  last_seen_date?: string | null;
  monthly_cost: number;
  annual_cost: number;
}

export interface RecurringRule {
  id: number;
  merchant_pattern?: string | null;
  category_id?: number | null;
  expected_amount?: number | null;
  interval_days?: number | null;
  next_expected_date?: string | null;
  is_subscription: boolean | number;
  last_seen_date?: string | null;
}

export interface Receipt {
  id: number;
  transaction_id?: number | null;
  file_path: string;
  merchant?: string | null;
  total_amount?: number | null;
  receipt_date?: string | null;
  tax_amount?: number | null;
  ocr_raw_text?: string | null;
  created_at?: string;
}

export interface HealthScore {
  total_score: number;
  grade: string;
  disclaimer: string;
  factors: { name: string; score: number; max_score: number; description: string; tip?: string | null }[];
}

export interface Anomaly {
  transaction_id: number;
  transaction_date: string;
  merchant?: string | null;
  amount?: number;
  category_name?: string | null;
  anomaly_type?: string;
  severity: "low" | "medium" | "high";
  message: string;
}

export interface SpendingTrend {
  month: string;
  category_name: string;
  total_spent: number;
}

export interface ChatResponse {
  answer_text: string;
  response?: string;
  data_summary?: Record<string, unknown>;
  suggestions: string[];
  mutations?: string[];
  ollama_offline?: boolean;
}

export interface DashboardSummary {
  total_balance: number;
  this_month_income: { total: number; change: number };
  this_month_expenses: { total: number; change: number };
  savings_rate: number;
}

export interface CashflowForecast {
  days: number;
  current_balance: number;
  forecast: { date: string; predicted_balance: number; is_low_balance: boolean; events: string[] }[];
  assumptions: string[];
}
