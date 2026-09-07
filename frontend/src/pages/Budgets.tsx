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
  Trash2,
  Target,
  CalendarDays,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
} from "lucide-react";
import toast from "react-hot-toast";

import api from "../lib/api";
import BudgetProgress from "../components/BudgetProgress";
import ConfirmDialog from "../components/ConfirmDialog";
import { currentMonth } from "../lib/utils";

import type {
  Budget,
  BudgetSummary,
  Category,
} from "../types";


/* =========================================================
   TYPES
   ========================================================= */

type BudgetFormData = {
  name: string;
  category_id: number | undefined;
  amount: number;
  priority: "low" | "medium" | "high";
  planning_day: number;
};


type ExtendedBudgetSummary = BudgetSummary & {
  budget_name?: string;
  priority?: "low" | "medium" | "high";
  planning_day?: number;
  daily_target?: number;
  projected_monthly_spending?: number;
  projected_overage?: number;
  savings_impact?: number;
};


/* =========================================================
   HELPERS
   ========================================================= */

function formatCurrency(value: number) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })}`;
}


function priorityLabel(
  priority?: string
) {
  switch (priority) {
    case "high":
      return "High";

    case "low":
      return "Low";

    default:
      return "Medium";
  }
}


function getPriorityClasses(
  priority?: string
) {
  switch (priority) {
    case "high":
      return "bg-red-50 text-red-700 border-red-200";

    case "low":
      return "bg-green-50 text-green-700 border-green-200";

    default:
      return "bg-yellow-50 text-yellow-700 border-yellow-200";
  }
}


function getBudgetStatus(
  item: ExtendedBudgetSummary
) {
  if (
    item.projected_overage &&
    item.projected_overage > 0
  ) {
    return "over_budget";
  }

  if (
    item.pct_used >= 90
  ) {
    return "near_limit";
  }

  return "on_track";
}


/* =========================================================
   COMPONENT
   ========================================================= */

export default function Budgets() {

  const qc = useQueryClient();

  const [month, setMonth] =
    useState(currentMonth());

  const [showForm, setShowForm] =
    useState(false);

  const [deleteId, setDeleteId] =
    useState<number | null>(null);

  const {
    register,
    handleSubmit,
    reset,
  } = useForm<BudgetFormData>({
    defaultValues: {
      name: "",
      category_id: undefined,
      amount: undefined,
      priority: "medium",
      planning_day: 1,
    },
  });


  /* =======================================================
     BUDGET SUMMARY
     ======================================================= */

  const {
    data: summary = [],
    isLoading: _summaryLoading,
  } = useQuery<ExtendedBudgetSummary[]>({
    queryKey: [
      "budget-summary",
      month,
    ],

    queryFn: () =>
      api
        .get(
          `/budgets/summary?month=${month}`
        )
        .then(
          (r) => r.data
        ),
  });


  /* =======================================================
     BUDGETS
     ======================================================= */

  const {
    data: budgets = [],
    isLoading: _budgetsLoading,
  } = useQuery<Budget[]>({
    queryKey: [
      "budgets",
      month,
    ],

    queryFn: () =>
      api
        .get(
          `/budgets?month=${month}`
        )
        .then(
          (r) => r.data
        ),
  });


  /* =======================================================
     CATEGORIES
     ======================================================= */

  const {
    data: categories = [],
  } = useQuery<Category[]>({
    queryKey: [
      "categories",
    ],

    queryFn: () =>
      api
        .get("/categories")
        .then(
          (r) => r.data
        ),
  });


  /* =======================================================
     SAVE BUDGET
     ======================================================= */

  const saveMutation =
    useMutation({

      mutationFn: (
        data: BudgetFormData
      ) => {

        return api.post(
          "/budgets",
          {
            name:
              data.name.trim() ||
              "Monthly Budget",

            category_id:
              data.category_id || null,

            amount:
              Number(data.amount),

            month,

            priority:
              data.priority,

            planning_day:
              Number(
                data.planning_day
              ),
          }
        );
      },

      onSuccess: () => {

        qc.invalidateQueries({
          queryKey: [
            "budgets",
          ],
        });

        qc.invalidateQueries({
          queryKey: [
            "budget-summary",
          ],
        });

        toast.success(
          "Budget saved successfully"
        );

        setShowForm(false);

        reset();
      },

      onError: (
        error: any
      ) => {

        const message =
          error?.response?.data
            ?.detail ||
          "Unable to save budget";

        toast.error(message);
      },
    });


  /* =======================================================
     DELETE BUDGET
     ======================================================= */

  const deleteMutation =
    useMutation({

      mutationFn: (
        id: number
      ) =>
        api.delete(
          `/budgets/${id}`
        ),

      onSuccess: () => {

        qc.invalidateQueries({
          queryKey: [
            "budgets",
          ],
        });

        qc.invalidateQueries({
          queryKey: [
            "budget-summary",
          ],
        });

        toast.success(
          "Budget deleted"
        );

        setDeleteId(null);
      },

      onError: () => {

        toast.error(
          "Unable to delete budget"
        );
      },
    });


  /* =======================================================
     FORM SUBMIT
     ======================================================= */

  const onSubmit = (
    data: BudgetFormData
  ) => {

    if (!data.name.trim()) {

      toast.error(
        "Please enter a budget name"
      );

      return;
    }

    if (
      !data.amount ||
      Number(data.amount) <= 0
    ) {

      toast.error(
        "Budget amount must be greater than zero"
      );

      return;
    }

    saveMutation.mutate(
      data
    );
  };


  /* =======================================================
     SUMMARY CALCULATIONS
     ======================================================= */

  const totalBudget =
    summary.reduce(
      (
        total,
        item
      ) =>
        total +
        Number(
          item.budget_amount || 0
        ),
      0
    );


  const totalSpent =
    summary.reduce(
      (
        total,
        item
      ) =>
        total +
        Number(
          item.spent_amount || 0
        ),
      0
    );


  const totalRemaining =
    summary.reduce(
      (
        total,
        item
      ) =>
        total +
        Number(
          item.remaining || 0
        ),
      0
    );


  const projectedOverage =
    summary.reduce(
      (
        total,
        item
      ) =>
        total +
        Number(
          item.projected_overage || 0
        ),
      0
    );


  const savingsImpact =
    summary.reduce(
      (
        total,
        item
      ) =>
        total +
        Number(
          item.savings_impact || 0
        ),
      0
    );


  const overallUsage =
    totalBudget > 0
      ? (
          totalSpent /
          totalBudget
        ) *
        100
      : 0;


  /* =======================================================
     UI
     ======================================================= */

  return (

    <div className="space-y-6">

      {/* ===================================================
          HEADER
      =================================================== */}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">

        <div>

          <h1 className="text-2xl font-bold text-gray-900">
            Budgets
          </h1>

          <p className="text-sm text-gray-500 mt-1">
            Plan your spending and protect your savings.
          </p>

        </div>


        <div className="flex gap-3">

          <input
            type="month"
            value={month}
            onChange={(
              e
            ) =>
              setMonth(
                e.target.value
              )
            }
            className="input w-40"
          />


          <button
            onClick={() => {

              reset({
                name: "",
                category_id:
                  undefined,
                amount:
                  undefined,
                priority:
                  "medium",
                planning_day:
                  1,
              });

              setShowForm(
                true
              );
            }}
            className="btn-primary flex items-center gap-2 text-sm"
          >

            <Plus size={16} />

            Add Budget

          </button>

        </div>

      </div>


      {/* ===================================================
          OVERVIEW CARDS
      =================================================== */}

      {summary.length > 0 && (

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">


          {/* Budget */}

          <div className="card">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-sm text-gray-500">
                  Total Budget
                </p>

                <p className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(
                    totalBudget
                  )}
                </p>

              </div>

              <div className="p-2 rounded-lg bg-blue-50">
                <Target
                  size={20}
                  className="text-blue-600"
                />
              </div>

            </div>

          </div>


          {/* Spent */}

          <div className="card">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-sm text-gray-500">
                  Spent
                </p>

                <p className="text-xl font-bold text-gray-900 mt-1">
                  {formatCurrency(
                    totalSpent
                  )}
                </p>

              </div>

              <div className="p-2 rounded-lg bg-orange-50">
                <TrendingUp
                  size={20}
                  className="text-orange-600"
                />
              </div>

            </div>

            <p className="text-xs text-gray-500 mt-2">
              {overallUsage.toFixed(1)}% of total budget
            </p>

          </div>


          {/* Remaining */}

          <div className="card">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-sm text-gray-500">
                  Remaining
                </p>

                <p
                  className={`text-xl font-bold mt-1 ${
                    totalRemaining >= 0
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  {formatCurrency(
                    totalRemaining
                  )}
                </p>

              </div>

              <div className="p-2 rounded-lg bg-green-50">
                <CheckCircle2
                  size={20}
                  className="text-green-600"
                />
              </div>

            </div>

          </div>


          {/* Projected Overage */}

          <div className="card">

            <div className="flex items-center justify-between">

              <div>

                <p className="text-sm text-gray-500">
                  Projected Overage
                </p>

                <p
                  className={`text-xl font-bold mt-1 ${
                    projectedOverage > 0
                      ? "text-red-600"
                      : "text-green-600"
                  }`}
                >
                  {formatCurrency(
                    projectedOverage
                  )}
                </p>

              </div>

              <div className="p-2 rounded-lg bg-red-50">
                <AlertTriangle
                  size={20}
                  className="text-red-600"
                />
              </div>

            </div>

            <p className="text-xs text-gray-500 mt-2">
              Based on current spending pace
            </p>

          </div>

        </div>

      )}


      {/* ===================================================
          BUDGET PROGRESS
      =================================================== */}

      {summary.length > 0 ? (

        <div className="card">

          <div className="flex items-center justify-between mb-5">

            <div>

              <h2 className="font-semibold text-gray-800">
                Spending vs Budget — {month}
              </h2>

              <p className="text-xs text-gray-500 mt-1">
                Track your spending against planned limits.
              </p>

            </div>

          </div>

          <BudgetProgress
            items={summary}
          />

        </div>

      ) : (

        <div className="card text-center py-12">

          <Target
            size={38}
            className="mx-auto text-gray-300 mb-3"
          />

          <p className="text-gray-500">
            No budgets set for {month}.
          </p>

          <p className="text-sm text-gray-400 mt-1">
            Create a budget to start planning your spending.
          </p>

        </div>

      )}


      {/* ===================================================
          DETAILED BUDGET PLANNING
      =================================================== */}

      {summary.length > 0 && (

        <div className="card">

          <div className="mb-5">

            <h2 className="font-semibold text-gray-800">
              Budget Planning
            </h2>

            <p className="text-xs text-gray-500 mt-1">
              Projected spending and savings impact based on your current pace.
            </p>

          </div>


          <div className="space-y-4">

            {summary.map(
              (
                item,
                index
              ) => {

                const status =
                  getBudgetStatus(
                    item
                  );

                const budgetAmount =
                  Number(
                    item.budget_amount ||
                    0
                  );

                const spent =
                  Number(
                    item.spent_amount ||
                    0
                  );

                const percentage =
                  budgetAmount > 0
                    ? Math.min(
                        (
                          spent /
                          budgetAmount
                        ) *
                          100,
                        100
                      )
                    : 0;

                return (

                  <div
                    key={`${item.category_id}-${index}`}
                    className="border border-gray-100 rounded-xl p-4"
                  >

                    {/* Header */}

                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">

                      <div>

                        <div className="flex items-center gap-2">

                          <h3 className="font-semibold text-gray-800">
                            {item.budget_name ||
                              item.category_name}
                          </h3>

                          {item.priority && (

                            <span
                              className={`text-xs px-2 py-1 rounded-full border ${getPriorityClasses(
                                item.priority
                              )}`}
                            >
                              {priorityLabel(
                                item.priority
                              )}
                            </span>

                          )}

                        </div>

                        <p className="text-xs text-gray-500 mt-1">
                          {item.category_name}
                        </p>

                      </div>


                      <div className="text-right">

                        <p className="text-sm font-semibold text-gray-800">
                          {formatCurrency(
                            spent
                          )}
                          {" / "}
                          {formatCurrency(
                            budgetAmount
                          )}
                        </p>

                        <p className="text-xs text-gray-500">
                          {Number(
                            item.pct_used || 0
                          ).toFixed(1)}
                          % used
                        </p>

                      </div>

                    </div>


                    {/* Progress */}

                    <div className="mt-4">

                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">

                        <div
                          className={`h-full rounded-full transition-all ${
                            status ===
                            "over_budget"
                              ? "bg-red-500"
                              : status ===
                                "near_limit"
                              ? "bg-yellow-500"
                              : "bg-green-500"
                          }`}
                          style={{
                            width: `${percentage}%`,
                          }}
                        />

                      </div>

                    </div>


                    {/* Metrics */}

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">

                      <div className="bg-gray-50 rounded-lg p-3">

                        <p className="text-xs text-gray-500">
                          Remaining
                        </p>

                        <p
                          className={`text-sm font-semibold mt-1 ${
                            Number(
                              item.remaining
                            ) >= 0
                              ? "text-gray-800"
                              : "text-red-600"
                          }`}
                        >
                          {formatCurrency(
                            Number(
                              item.remaining
                            )
                          )}
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-lg p-3">

                        <p className="text-xs text-gray-500">
                          Daily Target
                        </p>

                        <p className="text-sm font-semibold text-gray-800 mt-1">
                          {formatCurrency(
                            Number(
                              item.daily_target ||
                              0
                            )
                          )}
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-lg p-3">

                        <p className="text-xs text-gray-500">
                          Projected
                        </p>

                        <p className="text-sm font-semibold text-gray-800 mt-1">
                          {formatCurrency(
                            Number(
                              item.projected_monthly_spending ||
                              0
                            )
                          )}
                        </p>

                      </div>


                      <div className="bg-gray-50 rounded-lg p-3">

                        <p className="text-xs text-gray-500">
                          Savings Impact
                        </p>

                        <p className="text-sm font-semibold text-green-600 mt-1">
                          {formatCurrency(
                            Number(
                              item.savings_impact ||
                              0
                            )
                          )}
                        </p>

                      </div>

                    </div>


                    {/* Status message */}

                    <div className="mt-4 flex items-center justify-between gap-3">

                      <div className="flex items-center gap-2 text-xs">

                        {status ===
                        "over_budget" ? (

                          <>
                            <AlertTriangle
                              size={15}
                              className="text-red-500"
                            />

                            <span className="text-red-600">
                              Projected to exceed this budget by{" "}
                              {formatCurrency(
                                Number(
                                  item.projected_overage ||
                                  0
                                )
                              )}
                            </span>
                          </>

                        ) : status ===
                          "near_limit" ? (

                          <>
                            <AlertTriangle
                              size={15}
                              className="text-yellow-500"
                            />

                            <span className="text-yellow-700">
                              Spending is approaching the budget limit.
                            </span>
                          </>

                        ) : (

                          <>
                            <CheckCircle2
                              size={15}
                              className="text-green-500"
                            />

                            <span className="text-green-600">
                              Spending is currently on track.
                            </span>
                          </>

                        )}

                      </div>


                      {item.planning_day && (

                        <div className="flex items-center gap-1 text-xs text-gray-500">

                          <CalendarDays
                            size={14}
                          />

                          Plan on day{" "}
                          {item.planning_day}

                        </div>

                      )}

                    </div>

                  </div>

                );
              }
            )}

          </div>


          {/* Savings message */}

          {savingsImpact > 0 && (

            <div className="mt-5 rounded-xl border border-green-100 bg-green-50 p-4">

              <div className="flex gap-3">

                <TrendingUp
                  size={20}
                  className="text-green-600 mt-0.5"
                />

                <div>

                  <p className="text-sm font-semibold text-green-800">
                    Savings opportunity
                  </p>

                  <p className="text-xs text-green-700 mt-1">
                    Staying within your planned budgets could preserve approximately{" "}
                    <strong>
                      {formatCurrency(
                        savingsImpact
                      )}
                    </strong>{" "}
                    for savings.
                  </p>

                </div>

              </div>

            </div>

          )}

        </div>

      )}


      {/* ===================================================
          BUDGET LIMITS
      =================================================== */}

      {budgets.length > 0 && (

        <div className="card">

          <h2 className="font-semibold text-gray-800 mb-4">
            Budget Limits
          </h2>

          <div className="space-y-2">

            {budgets.map(
              (budget) => {

                const category =
                  categories.find(
                    (
                      c
                    ) =>
                      c.id ===
                      budget.category_id
                  );

                return (

                  <div
                    key={budget.id}
                    className="flex items-center justify-between py-3 border-b border-gray-50 last:border-0"
                  >

                    <div>

                      <div className="flex items-center gap-2">

                        <span className="text-sm font-medium text-gray-700">
                          {(budget as any).name ||
                            "Monthly Budget"}
                        </span>

                        <span
                          className={`text-xs px-2 py-0.5 rounded-full border ${getPriorityClasses(
                            (budget as any).priority
                          )}`}
                        >
                          {priorityLabel(
                            (budget as any).priority
                          )}
                        </span>

                      </div>

                      <div className="flex items-center gap-2 mt-1">

                        <span className="text-xs text-gray-400">
                          {category?.name ||
                            "Total"}
                        </span>

                        <span className="text-xs text-gray-300">
                          •
                        </span>

                        <span className="text-xs text-gray-400">
                          Planning day{" "}
                          {(budget as any).planning_day}
                        </span>

                      </div>

                    </div>


                    <div className="flex items-center gap-3">

                      <span className="text-sm font-semibold text-gray-800">
                        {formatCurrency(
                          Number(
                            budget.amount
                          )
                        )}
                      </span>

                      <button
                        onClick={() =>
                          setDeleteId(
                            budget.id
                          )
                        }
                        className="text-gray-400 hover:text-red-600 transition"
                        title="Delete budget"
                      >

                        <Trash2
                          size={15}
                        />

                      </button>

                    </div>

                  </div>

                );
              }
            )}

          </div>

        </div>

      )}


      {/* ===================================================
          ADD BUDGET DIALOG
      =================================================== */}

      <Dialog
        open={showForm}
        onClose={() =>
          setShowForm(false)
        }
        className="relative z-50"
      >

        <div className="fixed inset-0 bg-black/30" />


        <div className="fixed inset-0 flex items-center justify-center p-4">

          <Dialog.Panel className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">

            <Dialog.Title className="text-lg font-semibold text-gray-900 mb-1">
              Add Budget
            </Dialog.Title>

            <p className="text-xs text-gray-500 mb-5">
              Create a spending plan for {month}.
            </p>


            <form
              onSubmit={handleSubmit(
                onSubmit
              )}
              className="space-y-4"
            >

              {/* Budget Name */}

              <div>

                <label className="label">
                  Budget Name
                </label>

                <input
                  {...register(
                    "name",
                    {
                      required:
                        true,
                      maxLength:
                        100,
                    }
                  )}
                  type="text"
                  placeholder="e.g. Food & Dining"
                  className="input"
                />

                <p className="text-xs text-gray-400 mt-1">
                  Give this spending plan a name.
                </p>

              </div>


              {/* Category */}

              <div>

                <label className="label">
                  Category
                </label>

                <select
                  {...register(
                    "category_id",
                    {
                      setValueAs:
                        (
                          value
                        ) =>
                          value
                            ? Number(
                                value
                              )
                            : undefined,
                    }
                  )}
                  className="input"
                >

                  <option value="">
                    Total — all categories
                  </option>

                  {categories.map(
                    (
                      category
                    ) => (

                      <option
                        key={
                          category.id
                        }
                        value={
                          category.id
                        }
                      >
                        {
                          category.name
                        }
                      </option>

                    )
                  )}

                </select>

              </div>


              {/* Amount */}

              <div>

                <label className="label">
                  Budget Amount (INR)
                </label>

                <input
                  {...register(
                    "amount",
                    {
                      required:
                        true,
                      valueAsNumber:
                        true,
                      min: 1,
                    }
                  )}
                  type="number"
                  min="1"
                  step="0.01"
                  placeholder="5000"
                  className="input"
                />

              </div>


              {/* Priority */}

              <div>

                <label className="label">
                  Priority
                </label>

                <select
                  {...register(
                    "priority"
                  )}
                  className="input"
                >

                  <option value="high">
                    High — Essential
                  </option>

                  <option value="medium">
                    Medium — Important
                  </option>

                  <option value="low">
                    Low — Flexible
                  </option>

                </select>

                <p className="text-xs text-gray-400 mt-1">
                  Helps FinWise prioritize spending decisions.
                </p>

              </div>


              {/* Planning Day */}

              <div>

                <label className="label">
                  Planning / Review Day
                </label>

                <input
                  {...register(
                    "planning_day",
                    {
                      required:
                        true,
                      valueAsNumber:
                        true,
                      min: 1,
                      max: 31,
                    }
                  )}
                  type="number"
                  min="1"
                  max="31"
                  placeholder="1"
                  className="input"
                />

                <p className="text-xs text-gray-400 mt-1">
                  Choose the day of the month to review this budget.
                </p>

              </div>


              {/* Buttons */}

              <div className="flex gap-3 justify-end pt-3">

                <button
                  type="button"
                  onClick={() =>
                    setShowForm(
                      false
                    )
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
                    : "Save Budget"}

                </button>

              </div>

            </form>

          </Dialog.Panel>

        </div>

      </Dialog>


      {/* ===================================================
          DELETE CONFIRMATION
      =================================================== */}

      <ConfirmDialog
        open={
          deleteId !== null
        }
        title="Delete Budget"
        message="Remove this budget limit?"
        onConfirm={() =>
          deleteId &&
          deleteMutation.mutate(
            deleteId
          )
        }
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