import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import { Plus, Search, Upload, Pencil, Trash2 } from "lucide-react";
import toast from "react-hot-toast";
import api from "../lib/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { formatINR, formatDate, typeColor } from "../lib/utils";
import type { Transaction, Account, Category } from "../types";

export default function Transactions() {
  const qc = useQueryClient();

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const params = new URLSearchParams({
    page: String(page),
    page_size: "20",
  });

  if (search.trim()) {
    params.set("search", search.trim());
  }

  if (typeFilter) {
    params.set("type", typeFilter);
  }

  // =========================================================
  // TRANSACTIONS
  // =========================================================

  const {
    data: transactions = [],
    isLoading,
  } = useQuery<Transaction[]>({
    queryKey: ["transactions", page, search, typeFilter],
    queryFn: () =>
      api
        .get(`/transactions?${params.toString()}`)
        .then((r) => r.data),
  });

  // =========================================================
  // ACCOUNTS
  // =========================================================

  const {
    data: accounts = [],
  } = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: () =>
      api.get("/accounts").then((r) => r.data),
  });

  // =========================================================
  // CATEGORIES
  // =========================================================

  const {
    data: categories = [],
  } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () =>
      api.get("/categories").then((r) => r.data),
  });

  // =========================================================
  // FORM
  // =========================================================

  const {
    register,
    handleSubmit,
    reset,
  } = useForm<any>({
    defaultValues: {
      account_id: accounts[0]?.id ?? "",
      amount: "",
      type: "expense",
      merchant: "",
      description: "",
      transaction_date: "",
      payment_method: "other",
      category_id: "",
    },
  });

  // =========================================================
  // DATE HELPER
  // =========================================================

  const getDateInputValue = (value: any): string => {
    if (!value) return "";

    const text = String(value);

    // Backend may return:
    // 2026-08-27
    // 2026-08-27T20:06:00
    // 2026-08-27T20:06:00.000Z

    return text.substring(0, 10);
  };

  // =========================================================
  // OPEN CREATE
  // =========================================================

  const openCreate = () => {
    setEditing(null);

    reset({
      account_id: accounts[0]?.id ?? "",
      amount: "",
      type: "expense",
      merchant: "",
      description: "",
      transaction_date: new Date().toISOString().substring(0, 10),
      payment_method: "other",
      category_id: "",
    });

    setShowForm(true);
  };

  // =========================================================
  // OPEN EDIT
  // =========================================================

  const openEdit = (transaction: Transaction) => {
    setEditing(transaction);

    reset({
      account_id: transaction.account_id ?? "",
      amount: transaction.amount ?? "",
      type: transaction.type ?? "expense",
      merchant: transaction.merchant ?? "",
      description: transaction.description ?? "",
      transaction_date: getDateInputValue(
        transaction.transaction_date
      ),
      payment_method:
        transaction.payment_method ?? "other",
      category_id:
        transaction.category_id ?? "",
    });

    setShowForm(true);
  };

  // =========================================================
  // CLOSE FORM
  // =========================================================

  const closeForm = () => {
    if (saveMutation.isPending) return;

    setShowForm(false);
    setEditing(null);
    reset();
  };

  // =========================================================
  // SAVE / UPDATE TRANSACTION
  // =========================================================

  const saveMutation = useMutation({
    mutationFn: async (data: any) => {
      // -------------------------------------------------------
      // EDIT EXISTING TRANSACTION
      // -------------------------------------------------------

      if (editing) {
        /*
         * IMPORTANT:
         *
         * The backend TransactionUpdate schema currently accepts:
         *
         * account_id
         * amount
         * category_id
         * merchant
         * description
         * transaction_date
         *
         * It expects transaction_date as YYYY-MM-DD.
         *
         * Therefore we deliberately build a clean update payload
         * instead of sending the entire form object.
         */

        const updatePayload = {
          account_id:
            data.account_id !== "" &&
            data.account_id !== undefined
              ? Number(data.account_id)
              : undefined,

          amount:
            data.amount !== "" &&
            data.amount !== undefined
              ? Number(data.amount)
              : undefined,

          category_id:
            data.category_id !== "" &&
            data.category_id !== undefined &&
            !Number.isNaN(Number(data.category_id))
              ? Number(data.category_id)
              : null,

          merchant:
            data.merchant?.trim() || null,

          description:
            data.description?.trim() || null,

          transaction_date:
            data.transaction_date
              ? String(data.transaction_date).substring(0, 10)
              : undefined,
        };

        return api.put(
          `/transactions/${editing.id}`,
          updatePayload
        );
      }

      // -------------------------------------------------------
      // CREATE NEW TRANSACTION
      // -------------------------------------------------------

      const createPayload = {
        account_id: Number(data.account_id),

        amount: Number(data.amount),

        type: data.type,

        category_id:
          data.category_id !== "" &&
          data.category_id !== undefined &&
          !Number.isNaN(Number(data.category_id))
            ? Number(data.category_id)
            : null,

        merchant:
          data.merchant?.trim() || null,

        description:
          data.description?.trim() || null,

        transaction_date:
          data.transaction_date,

        /*
         * Keep payment_method for the existing create flow.
         * The current backend schema can safely ignore fields it
         * doesn't explicitly expose.
         */
        payment_method:
          data.payment_method || "other",
      };

      return api.post(
        "/transactions",
        createPayload
      );
    },

    onSuccess: async () => {
      /*
       * Refresh all financial data after a transaction changes.
       *
       * This is important because a transaction can affect:
       * - Transactions
       * - Accounts
       * - Dashboard
       * - Analytics
       * - Budgets
       * - Goals
       * - Savings plan
       * - Cash-flow forecast
       */

      await qc.invalidateQueries();

      toast.success(
        editing
          ? "Transaction updated successfully"
          : "Transaction added successfully"
      );

      setShowForm(false);
      setEditing(null);
      reset();
    },

    onError: (error: any) => {
      console.error(
        "Transaction save error:",
        error?.response?.data || error
      );

      const detail =
        error?.response?.data?.detail;

      if (Array.isArray(detail)) {
        const message = detail
          .map((item: any) =>
            item?.msg || "Validation error"
          )
          .join(", ");

        toast.error(message);
      } else if (typeof detail === "string") {
        toast.error(detail);
      } else {
        toast.error(
          editing
            ? "Failed to update transaction"
            : "Failed to add transaction"
        );
      }
    },
  });

  // =========================================================
  // DELETE
  // =========================================================

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      api.delete(`/transactions/${id}`),

    onSuccess: async () => {
      await qc.invalidateQueries();

      toast.success("Transaction deleted");

      setDeleteId(null);
    },

    onError: (error: any) => {
      console.error(
        "Delete transaction error:",
        error?.response?.data || error
      );

      toast.error(
        "Failed to delete transaction"
      );
    },
  });

  // =========================================================
  // SUBMIT
  // =========================================================

  const onSubmit = (data: any) => {
    if (
      !editing &&
      (!data.account_id ||
        Number.isNaN(Number(data.account_id)))
    ) {
      toast.error("Please select an account");
      return;
    }

    if (
      !data.amount ||
      Number.isNaN(Number(data.amount)) ||
      Number(data.amount) <= 0
    ) {
      toast.error("Please enter a valid amount");
      return;
    }

    if (!data.transaction_date) {
      toast.error("Please select a transaction date");
      return;
    }

    saveMutation.mutate(data);
  };

  // =========================================================
  // CSV IMPORT
  // =========================================================

  const handleCSV = async (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = e.target.files?.[0];

    if (!file) return;

    if (accounts.length === 0) {
      toast.error(
        "Please create an account before importing transactions"
      );

      e.target.value = "";
      return;
    }

    const fd = new FormData();

    fd.append("file", file);

    try {
      const { data } = await api.post(
        `/transactions/import-csv?account_id=${accounts[0].id}`,
        fd,
        {
          headers: {
            "Content-Type":
              "multipart/form-data",
          },
        }
      );

      await qc.invalidateQueries();

      toast.success(
        `Imported ${data.imported ?? 0} transactions`
      );
    } catch (error: any) {
      console.error(
        "CSV import error:",
        error?.response?.data || error
      );

      toast.error("CSV import failed");
    }

    e.target.value = "";
  };

  // =========================================================
  // RENDER
  // =========================================================

  return (
    <div className="space-y-6">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="flex items-center justify-between">

        <h1 className="text-2xl font-bold text-gray-900">
          Transactions
        </h1>

        <div className="flex gap-2">

          {/* CSV */}

          <label className="btn-secondary text-sm cursor-pointer flex items-center gap-2">

            <Upload size={16} />

            Import CSV

            <input
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleCSV}
            />

          </label>

          {/* ADD */}

          <button
            onClick={openCreate}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Plus size={16} />
            Add
          </button>

        </div>

      </div>

      {/* =====================================================
          FILTERS
      ===================================================== */}

      <div className="flex gap-3 flex-wrap">

        {/* SEARCH */}

        <div className="relative">

          <Search
            size={16}
            className="absolute left-3 top-2.5 text-gray-400"
          />

          <input
            className="input pl-9 w-64"
            placeholder="Search merchant or description..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />

        </div>

        {/* TYPE */}

        <select
          className="input w-40"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
        >

          <option value="">
            All types
          </option>

          <option value="income">
            Income
          </option>

          <option value="expense">
            Expense
          </option>

          <option value="transfer">
            Transfer
          </option>

        </select>

      </div>

      {/* =====================================================
          TABLE
      ===================================================== */}

      <div className="card p-0 overflow-hidden">

        <table className="w-full text-sm">

          <thead className="bg-gray-50 border-b border-gray-100">

            <tr>

              {[
                "Date",
                "Merchant",
                "Category",
                "Amount",
                "Method",
                "",
              ].map((heading) => (
                <th
                  key={heading}
                  className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide"
                >
                  {heading}
                </th>
              ))}

            </tr>

          </thead>

          <tbody className="divide-y divide-gray-50">

            {/* LOADING */}

            {isLoading && (
              <tr>
                <td
                  colSpan={6}
                  className="text-center py-8 text-gray-400"
                >
                  Loading...
                </td>
              </tr>
            )}

            {/* EMPTY */}

            {!isLoading &&
              transactions.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="text-center py-8 text-gray-400"
                  >
                    No transactions found
                  </td>
                </tr>
              )}

            {/* DATA */}

            {!isLoading &&
              transactions.map((transaction) => {

                const category =
                  categories.find(
                    (c) =>
                      c.id ===
                      transaction.category_id
                  );

                return (
                  <tr
                    key={transaction.id}
                    className="hover:bg-gray-50"
                  >

                    {/* DATE */}

                    <td className="px-4 py-3 text-gray-500">
                      {formatDate(
                        transaction.transaction_date
                      )}
                    </td>

                    {/* MERCHANT */}

                    <td className="px-4 py-3 font-medium text-gray-800">
                      {transaction.merchant || "—"}
                    </td>

                    {/* CATEGORY */}

                    <td className="px-4 py-3 text-gray-500">
                      {category?.name || "—"}
                    </td>

                    {/* AMOUNT */}

                    <td
                      className={`px-4 py-3 font-semibold ${typeColor(
                        transaction.type
                      )}`}
                    >

                      {transaction.type ===
                      "income"
                        ? "+"
                        : "-"}

                      {formatINR(
                        Number(
                          transaction.amount
                        )
                      )}

                    </td>

                    {/* METHOD */}

                    <td className="px-4 py-3 text-gray-400 capitalize">
                      {transaction.payment_method ||
                        "other"}
                    </td>

                    {/* ACTIONS */}

                    <td className="px-4 py-3">

                      <div className="flex gap-2">

                        {/* EDIT */}

                        <button
                          type="button"
                          onClick={() =>
                            openEdit(transaction)
                          }
                          className="text-gray-400 hover:text-blue-600"
                          title="Edit transaction"
                        >
                          <Pencil size={15} />
                        </button>

                        {/* DELETE */}

                        <button
                          type="button"
                          onClick={() =>
                            setDeleteId(
                              transaction.id
                            )
                          }
                          className="text-gray-400 hover:text-red-600"
                          title="Delete transaction"
                        >
                          <Trash2 size={15} />
                        </button>

                      </div>

                    </td>

                  </tr>
                );
              })}

          </tbody>

        </table>

        {/* =================================================
            PAGINATION
        ================================================= */}

        <div className="flex justify-between items-center px-4 py-3 border-t border-gray-100">

          <button
            disabled={page === 1}
            onClick={() =>
              setPage((current) =>
                current - 1
              )
            }
            className="btn-secondary text-xs disabled:opacity-40"
          >
            Previous
          </button>

          <span className="text-xs text-gray-500">
            Page {page}
          </span>

          <button
            disabled={
              transactions.length < 20
            }
            onClick={() =>
              setPage((current) =>
                current + 1
              )
            }
            className="btn-secondary text-xs disabled:opacity-40"
          >
            Next
          </button>

        </div>

      </div>

      {/* =====================================================
          ADD / EDIT DIALOG
      ===================================================== */}

      <Dialog
        open={showForm}
        onClose={closeForm}
        className="relative z-50"
      >

        <div className="fixed inset-0 bg-black/30" />

        <div className="fixed inset-0 flex items-center justify-center p-4">

          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-lg">

            {/* TITLE */}

            <Dialog.Title className="font-semibold text-gray-900 mb-4">

              {editing
                ? "Edit Transaction"
                : "Add Transaction"}

            </Dialog.Title>

            <form
              onSubmit={handleSubmit(
                onSubmit
              )}
              className="space-y-3"
            >

              {/* ACCOUNT + TYPE */}

              <div className="grid grid-cols-2 gap-3">

                {/* ACCOUNT */}

                <div>

                  <label className="label">
                    Account
                  </label>

                  <select
                    {...register(
                      "account_id",
                      {
                        required: true,
                      }
                    )}
                    className="input"
                  >

                    <option value="">
                      Select account
                    </option>

                    {accounts.map(
                      (account) => (
                        <option
                          key={account.id}
                          value={account.id}
                        >
                          {account.name}
                        </option>
                      )
                    )}

                  </select>

                </div>

                {/* TYPE */}

                <div>

                  <label className="label">
                    Type
                  </label>

                  <select
                    {...register("type")}
                    className="input"
                    disabled={!!editing}
                  >

                    <option value="expense">
                      Expense
                    </option>

                    <option value="income">
                      Income
                    </option>

                    <option value="transfer">
                      Transfer
                    </option>

                  </select>

                  {editing && (
                    <p className="text-[10px] text-gray-400 mt-1">
                      Transaction type cannot be changed
                      while editing.
                    </p>
                  )}

                </div>

              </div>

              {/* AMOUNT + DATE */}

              <div className="grid grid-cols-2 gap-3">

                {/* AMOUNT */}

                <div>

                  <label className="label">
                    Amount (INR)
                  </label>

                  <input
                    {...register(
                      "amount",
                      {
                        required: true,
                        valueAsNumber: true,
                      }
                    )}
                    type="number"
                    min="0"
                    step="0.01"
                    className="input"
                    placeholder="0.00"
                  />

                </div>

                {/* DATE */}

                <div>

                  <label className="label">
                    Date
                  </label>

                  <input
                    {...register(
                      "transaction_date",
                      {
                        required: true,
                      }
                    )}
                    type="date"
                    className="input"
                  />

                </div>

              </div>

              {/* MERCHANT + PAYMENT */}

              <div className="grid grid-cols-2 gap-3">

                {/* MERCHANT */}

                <div>

                  <label className="label">
                    Merchant
                  </label>

                  <input
                    {...register("merchant")}
                    className="input"
                    placeholder="e.g. Swiggy"
                  />

                </div>

                {/* PAYMENT METHOD */}

                <div>

                  <label className="label">
                    Payment Method
                  </label>

                  <select
                    {...register(
                      "payment_method"
                    )}
                    className="input"
                    disabled={!!editing}
                  >

                    <option value="upi">
                      UPI
                    </option>

                    <option value="card">
                      Card
                    </option>

                    <option value="cash">
                      Cash
                    </option>

                    <option value="netbanking">
                      Net Banking
                    </option>

                    <option value="other">
                      Other
                    </option>

                  </select>

                  {editing && (
                    <p className="text-[10px] text-gray-400 mt-1">
                      Payment method cannot be changed
                      while editing.
                    </p>
                  )}

                </div>

              </div>

              {/* CATEGORY */}

              <div>

                <label className="label">
                  Category
                </label>

                <select
                  {...register(
                    "category_id"
                  )}
                  className="input"
                >

                  <option value="">
                    Auto-detect / No category
                  </option>

                  {categories.map(
                    (category) => (
                      <option
                        key={category.id}
                        value={category.id}
                      >
                        {category.name}
                      </option>
                    )
                  )}

                </select>

              </div>

              {/* DESCRIPTION */}

              <div>

                <label className="label">
                  Description
                </label>

                <input
                  {...register(
                    "description"
                  )}
                  className="input"
                  placeholder="Optional description"
                />

              </div>

              {/* BUTTONS */}

              <div className="flex gap-3 justify-end pt-2">

                <button
                  type="button"
                  onClick={closeForm}
                  disabled={
                    saveMutation.isPending
                  }
                  className="btn-secondary text-sm"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={
                    saveMutation.isPending
                  }
                  className="btn-primary text-sm"
                >

                  {saveMutation.isPending
                    ? "Saving..."
                    : editing
                    ? "Update"
                    : "Save"}

                </button>

              </div>

            </form>

          </Dialog.Panel>

        </div>

      </Dialog>

      {/* =====================================================
          DELETE CONFIRMATION
      ===================================================== */}

      <ConfirmDialog
        open={deleteId !== null}
        title="Delete Transaction"
        message="This action cannot be undone."
        onConfirm={() => {
          if (
            deleteId !== null &&
            !deleteMutation.isPending
          ) {
            deleteMutation.mutate(
              deleteId
            );
          }
        }}
        onCancel={() =>
          setDeleteId(null)
        }
        loading={
          deleteMutation.isPending
        }
      />

    </div>
  );
}