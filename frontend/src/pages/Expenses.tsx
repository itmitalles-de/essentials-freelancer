import { FormEvent, useEffect, useRef, useState } from "react";
import { api, ApiError, openExpenseReceipt, uploadExpenseReceipt } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Expense } from "../types";

const empty = {
  date: new Date().toISOString().slice(0, 10),
  description: "",
  category: "",
  amount: "",
};

const CATEGORY_SUGGESTIONS = ["Software", "Hardware", "Büro", "Reisen", "Fortbildung", "Sonstiges"];

export function Expenses() {
  const { t } = useLanguage();
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [form, setForm] = useState(empty);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingId, setUploadingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = () => api.get<Expense[]>("/expenses").then(setExpenses);

  useEffect(() => {
    load();
  }, []);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/expenses", { ...form, amount: form.amount });
      setForm(empty);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("expenses.errUpload"));
    }
  };

  const remove = async (id: number) => {
    if (!confirm(t("expenses.confirmDelete"))) return;
    await api.delete(`/expenses/${id}`);
    load();
  };

  const triggerUpload = (id: number) => {
    setUploadingId(id);
    fileInputRef.current?.click();
  };

  const onFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || uploadingId === null) return;
    setError(null);
    try {
      await uploadExpenseReceipt(uploadingId, file);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("expenses.errUpload"));
    } finally {
      setUploadingId(null);
    }
  };

  const total = expenses.reduce((sum, e) => sum + Number(e.amount), 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("expenses.title")}</h2>
        <button onClick={() => setShowForm((v) => !v)}>
          {showForm ? t("expenses.cancel") : t("expenses.new")}
        </button>
      </div>

      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      <input
        ref={fileInputRef}
        type="file"
        accept="image/png,image/jpeg,application/pdf"
        style={{ display: "none" }}
        onChange={onFileSelected}
      />

      {showForm && (
        <form onSubmit={onSubmit} className="card" style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
          <input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          <input
            placeholder={t("expenses.description")}
            required
            style={{ flex: 1, minWidth: 160 }}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <input
            placeholder={t("expenses.category")}
            list="expense-categories"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            style={{ width: 140 }}
          />
          <datalist id="expense-categories">
            {CATEGORY_SUGGESTIONS.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          <input
            placeholder={t("expenses.amount")}
            type="number"
            step="0.01"
            min="0"
            required
            value={form.amount}
            onChange={(e) => setForm({ ...form, amount: e.target.value })}
            style={{ width: 110 }}
          />
          <button type="submit">{t("expenses.create")}</button>
        </form>
      )}

      <table className="card">
        <thead>
          <tr>
            <th>{t("expenses.colDate")}</th>
            <th>{t("expenses.colDescription")}</th>
            <th>{t("expenses.colCategory")}</th>
            <th>{t("expenses.colAmount")}</th>
            <th>{t("expenses.colReceipt")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((e) => (
            <tr key={e.id}>
              <td>{e.date}</td>
              <td>{e.description}</td>
              <td>{e.category || "—"}</td>
              <td>{Number(e.amount).toFixed(2)} €</td>
              <td>
                {e.has_receipt ? (
                  <button className="secondary" onClick={() => openExpenseReceipt(e.id)}>{t("expenses.receiptOpen")}</button>
                ) : (
                  <button className="secondary" onClick={() => triggerUpload(e.id)}>{t("expenses.receiptUpload")}</button>
                )}
              </td>
              <td>
                <button className="danger" onClick={() => remove(e.id)}>{t("expenses.delete")}</button>
              </td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3} style={{ textAlign: "right", fontWeight: 600 }}>{t("expenses.total")}</td>
            <td style={{ fontWeight: 600 }}>{total.toFixed(2)} €</td>
            <td></td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
