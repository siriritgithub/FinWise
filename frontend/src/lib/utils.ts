export const formatINR = (amount: number): string => {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

export const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
  });
};

export const currentMonth = (): string => {
  return new Date().toISOString().slice(0, 7);
};
export const typeColor = (type: "income" | "expense" | "transfer"): string => {
  if (type === "income") return "text-green-600";
  if (type === "expense") return "text-red-600";
  return "text-blue-600";
};
