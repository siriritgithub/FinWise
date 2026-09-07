// Accounts.tsx

import { useState } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Dialog } from "@headlessui/react";
import {
  Plus,
  Pencil,
  Trash2,
} from "lucide-react";
import toast from "react-hot-toast";

import api from "../lib/api";
import ConfirmDialog from "../components/ConfirmDialog";
import { formatINR } from "../lib/utils";
import type { Account } from "../types";


// ============================================================
// TYPES
// ============================================================

type AccountFormData = {
  name: string;
  type:
    | "bank"
    | "cash"
    | "credit_card"
    | "wallet"
    | "investment"
    | "loan";
  balance: number | string;
  credit_limit?: number | string;
};


// ============================================================
// COMPONENT
// ============================================================

export function Accounts() {
  const qc = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
  } = useForm<AccountFormData>({
    defaultValues: {
      name: "",
      type: "bank",
      balance: "",
      credit_limit: "",
    },
  });


  // ==========================================================
  // ACCOUNT TYPES
  // ==========================================================

  const ACCOUNT_TYPES = [
    "bank",
    "cash",
    "credit_card",
    "wallet",
    "investment",
    "loan",
  ] as const;


  // ==========================================================
  // TYPE COLORS
  // ==========================================================

  const typeColors: Record<string, string> = {
    bank:
      "bg-blue-100 text-blue-700",

    cash:
      "bg-green-100 text-green-700",

    credit_card:
      "bg-purple-100 text-purple-700",

    wallet:
      "bg-yellow-100 text-yellow-700",

    investment:
      "bg-indigo-100 text-indigo-700",

    loan:
      "bg-red-100 text-red-700",
  };


  // ==========================================================
  // FETCH ACCOUNTS
  // ==========================================================

  const {
    data: accounts = [],
    isLoading,
    isError,
  } = useQuery<Account[]>({
    queryKey: ["accounts"],

    queryFn: async () => {
      const response = await api.get("/accounts");

      return response.data;
    },
  });


  // ==========================================================
  // REFRESH RELATED FINWISE DATA
  // ==========================================================

  const refreshFinancialData = () => {

    qc.invalidateQueries({
      queryKey: ["accounts"],
    });

    qc.invalidateQueries({
      queryKey: ["dashboard"],
    });

    qc.invalidateQueries({
      queryKey: ["analytics"],
    });

    qc.invalidateQueries({
      queryKey: ["transactions"],
    });

    qc.invalidateQueries({
      queryKey: ["goals"],
    });

    qc.invalidateQueries({
      queryKey: ["budgets"],
    });
  };


  // ==========================================================
  // SAVE ACCOUNT
  // ==========================================================

  const saveMutation = useMutation({

    mutationFn: async (
      data: AccountFormData
    ) => {

      const payload = {
        name: data.name,

        type: data.type,

        balance:
          data.balance === ""
            ? 0
            : Number(data.balance),

        credit_limit:
          data.credit_limit === "" ||
          data.credit_limit === undefined
            ? null
            : Number(data.credit_limit),
      };


      // EDIT ACCOUNT

      if (editing) {

        return api.put(
          `/accounts/${editing.id}`,
          payload
        );
      }


      // CREATE ACCOUNT

      return api.post(
        "/accounts",
        payload
      );
    },


    // ========================================================
    // SUCCESS
    // ========================================================

    onSuccess: () => {

      refreshFinancialData();

      toast.success(
        editing
          ? "Account updated successfully"
          : "Account created successfully"
      );

      setShowForm(false);

      setEditing(null);

      reset({
        name: "",
        type: "bank",
        balance: "",
        credit_limit: "",
      });
    },


    // ========================================================
    // ERROR
    // ========================================================

    onError: (error: any) => {

      console.error(
        "Account save error:",
        error
      );

      const message =
        error?.response?.data?.detail ||
        "Unable to save account";

      toast.error(
        typeof message === "string"
          ? message
          : "Unable to save account"
      );
    },
  });


  // ==========================================================
  // DELETE ACCOUNT
  // ==========================================================

  const deleteMutation = useMutation({

    mutationFn: async (
      id: number
    ) => {

      return api.delete(
        `/accounts/${id}`
      );
    },


    // ========================================================
    // SUCCESS
    // ========================================================

    onSuccess: () => {

      refreshFinancialData();

      toast.success(
        "Account deleted successfully"
      );

      setDeleteId(null);
    },


    // ========================================================
    // ERROR
    // ========================================================

    onError: (error: any) => {

      console.error(
        "Account delete error:",
        error
      );

      const message =
        error?.response?.data?.detail ||
        "Unable to delete account";

      toast.error(
        typeof message === "string"
          ? message
          : "Unable to delete account"
      );
    },
  });


  // ==========================================================
  // OPEN EDIT
  // ==========================================================

  const openEdit = (
    account: Account
  ) => {

    setEditing(account);

    setValue(
      "name",
      account.name || ""
    );

    setValue(
      "type",
      account.type
    );

    setValue(
      "balance",
      account.balance ?? ""
    );

    setValue(
      "credit_limit",
      account.credit_limit ?? ""
    );

    setShowForm(true);
  };


  // ==========================================================
  // OPEN ADD
  // ==========================================================

  const openAdd = () => {

    setEditing(null);

    reset({
      name: "",
      type: "bank",
      balance: "",
      credit_limit: "",
    });

    setShowForm(true);
  };


  // ==========================================================
  // CLOSE FORM
  // ==========================================================

  const closeForm = () => {

    setShowForm(false);

    setEditing(null);

    reset({
      name: "",
      type: "bank",
      balance: "",
      credit_limit: "",
    });
  };


  // ==========================================================
  // SUBMIT
  // ==========================================================

  const onSubmit = (
    data: AccountFormData
  ) => {

    saveMutation.mutate(data);
  };


  // ==========================================================
  // LOADING
  // ==========================================================

  if (isLoading) {

    return (
      <div className="space-y-6">

        <div className="flex items-center justify-between">

          <h1 className="text-2xl font-bold text-gray-900">
            Accounts
          </h1>

        </div>


        <div className="card">

          <p className="text-sm text-gray-500">
            Loading accounts...
          </p>

        </div>

      </div>
    );
  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (isError) {

    return (
      <div className="space-y-6">

        <div className="flex items-center justify-between">

          <h1 className="text-2xl font-bold text-gray-900">
            Accounts
          </h1>


          <button
            onClick={openAdd}
            className="btn-primary flex items-center gap-2 text-sm"
          >
            <Plus size={16} />
            Add Account
          </button>

        </div>


        <div className="card">

          <p className="text-sm text-red-600">
            Unable to load accounts.
          </p>

        </div>

      </div>
    );
  }


  // ==========================================================
  // MAIN UI
  // ==========================================================

  return (
    <div className="space-y-6">


      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="flex items-center justify-between">

        <h1 className="text-2xl font-bold text-gray-900">
          Accounts
        </h1>


        <button
          onClick={openAdd}
          className="btn-primary flex items-center gap-2 text-sm"
        >

          <Plus size={16} />

          Add Account

        </button>

      </div>


      {/* ======================================================
          EMPTY STATE
      ====================================================== */}

      {accounts.length === 0 && (

        <div className="card text-center py-12">

          <div className="flex justify-center mb-4">

            <div className="rounded-full bg-blue-100 p-3">

              <Plus
                size={22}
                className="text-blue-600"
              />

            </div>

          </div>


          <h2 className="text-lg font-semibold text-gray-800">
            No accounts yet
          </h2>


          <p className="text-sm text-gray-500 mt-1">
            Add your first bank, cash, wallet, or
            investment account.
          </p>


          <button
            onClick={openAdd}
            className="btn-primary mt-5 text-sm"
          >
            Add Account
          </button>

        </div>
      )}


      {/* ======================================================
          ACCOUNT CARDS
      ====================================================== */}

      {accounts.length > 0 && (

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">

          {accounts.map((account) => {

            const balance =
              Number(account.balance) || 0;


            const hasCreditLimit =
              account.credit_limit !== null &&
              account.credit_limit !== undefined &&
              Number(account.credit_limit) > 0;


            return (

              <div
                key={account.id}
                className="card"
              >


                {/* =================================================
                    CARD HEADER
                ================================================= */}

                <div className="flex items-start justify-between mb-3">

                  <div>

                    <p className="font-semibold text-gray-800">
                      {account.name}
                    </p>


                    <span
                      className={`
                        text-xs
                        px-2
                        py-0.5
                        rounded-full
                        font-medium
                        ${
                          typeColors[account.type] ||
                          "bg-gray-100 text-gray-600"
                        }
                      `}
                    >

                      {String(account.type)
                        .replace(/_/g, " ")}

                    </span>

                  </div>


                  {/* =================================================
                      ACTION BUTTONS
                  ================================================= */}

                  <div className="flex gap-2">

                    <button
                      type="button"
                      onClick={() =>
                        openEdit(account)
                      }
                      title="Edit account"
                      className="text-gray-400 hover:text-blue-600 transition"
                    >

                      <Pencil size={15} />

                    </button>


                    <button
                      type="button"
                      onClick={() =>
                        setDeleteId(account.id)
                      }
                      title="Delete account"
                      className="text-gray-400 hover:text-red-600 transition"
                    >

                      <Trash2 size={15} />

                    </button>

                  </div>

                </div>


                {/* =================================================
                    BALANCE
                ================================================= */}

                <p
                  className={`
                    text-2xl
                    font-bold
                    ${
                      balance < 0
                        ? "text-red-600"
                        : "text-gray-900"
                    }
                  `}
                >

                  {formatINR(balance)}

                </p>


                {/* =================================================
                    CREDIT LIMIT
                ================================================= */}

                {hasCreditLimit && (

                  <p className="text-xs text-gray-400 mt-1">

                    Limit:{" "}

                    {formatINR(
                      Number(account.credit_limit)
                    )}

                  </p>

                )}

              </div>

            );
          })}

        </div>

      )}


      {/* ========================================================
          ADD / EDIT ACCOUNT DIALOG
      ======================================================== */}

      <Dialog
        open={showForm}
        onClose={closeForm}
        className="relative z-50"
      >


        {/* BACKDROP */}

        <div
          className="fixed inset-0 bg-black/30"
          aria-hidden="true"
        />


        {/* CENTER */}

        <div className="fixed inset-0 flex items-center justify-center p-4">

          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">


            {/* =================================================
                TITLE
            ================================================= */}

            <Dialog.Title className="font-semibold text-gray-900 mb-4">

              {editing
                ? "Edit Account"
                : "Add Account"}

            </Dialog.Title>


            {/* =================================================
                FORM
            ================================================= */}

            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-3"
            >


              {/* =================================================
                  ACCOUNT NAME
              ================================================= */}

              <div>

                <label className="label">
                  Account Name
                </label>


                <input
                  {...register("name", {
                    required:
                      "Account name is required",
                  })}
                  className="input"
                  placeholder="e.g. HDFC Savings"
                />

              </div>


              {/* =================================================
                  TYPE
              ================================================= */}

              <div>

                <label className="label">
                  Type
                </label>


                <select
                  {...register("type", {
                    required: true,
                  })}
                  className="input"
                >

                  {ACCOUNT_TYPES.map(
                    (type) => (

                      <option
                        key={type}
                        value={type}
                      >

                        {type.replace(
                          /_/g,
                          " "
                        )}

                      </option>

                    )
                  )}

                </select>

              </div>


              {/* =================================================
                  BALANCE
              ================================================= */}

              <div>

                <label className="label">
                  Current Balance (INR)
                </label>


                <input
                  {...register("balance", {
                    valueAsNumber: true,
                  })}
                  type="number"
                  step="0.01"
                  className="input"
                  placeholder="0.00"
                />

              </div>


              {/* =================================================
                  CREDIT LIMIT
              ================================================= */}

              <div>

                <label className="label">
                  Credit Limit (for credit cards)
                </label>


                <input
                  {...register(
                    "credit_limit",
                    {
                      valueAsNumber: true,
                    }
                  )}
                  type="number"
                  step="0.01"
                  className="input"
                  placeholder="Optional"
                />

              </div>


              {/* =================================================
                  BUTTONS
              ================================================= */}

              <div className="flex gap-3 justify-end pt-2">

                <button
                  type="button"
                  onClick={closeForm}
                  className="btn-secondary text-sm"
                  disabled={
                    saveMutation.isPending
                  }
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
                    : "Save"}

                </button>

              </div>

            </form>

          </Dialog.Panel>

        </div>

      </Dialog>


      {/* ========================================================
          DELETE CONFIRMATION
      ======================================================== */}

      <ConfirmDialog

        open={
          deleteId !== null
        }

        title="Delete Account"

        message="All transactions in this account will also be deleted."

        onConfirm={() => {

          if (deleteId !== null) {

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