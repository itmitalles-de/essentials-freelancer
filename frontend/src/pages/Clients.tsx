import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client } from "../types";

const empty = {
  name: "",
  contact_person: "",
  address_line1: "",
  address_line2: "",
  zip_city: "",
  email: "",
  hourly_rate: "",
  notes: "",
  active: true,
};

export function Clients() {
  const { t } = useLanguage();
  const [clients, setClients] = useState<Client[]>([]);
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => api.get<Client[]>("/clients").then(setClients);

  useEffect(() => {
    load();
  }, []);

  const startEdit = (c: Client) => {
    setEditingId(c.id);
    setForm({
      name: c.name,
      contact_person: c.contact_person,
      address_line1: c.address_line1,
      address_line2: c.address_line2,
      zip_city: c.zip_city,
      email: c.email,
      hourly_rate: c.hourly_rate ?? "",
      notes: c.notes,
      active: c.active,
    });
    setShowForm(true);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      hourly_rate: form.hourly_rate === "" ? null : form.hourly_rate,
    };
    if (editingId) {
      await api.put(`/clients/${editingId}`, payload);
    } else {
      await api.post("/clients", payload);
    }
    setForm(empty);
    setEditingId(null);
    setShowForm(false);
    load();
  };

  const remove = async (id: number) => {
    if (!confirm(t("clients.confirmDelete"))) return;
    await api.delete(`/clients/${id}`);
    load();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("clients.title")}</h2>
        <button
          onClick={() => {
            setForm(empty);
            setEditingId(null);
            setShowForm((v) => !v);
          }}
        >
          {showForm ? t("clients.cancel") : t("clients.new")}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
          <input placeholder={t("clients.name")} required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder={t("clients.contactPerson")} value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
          <input placeholder={t("clients.address")} value={form.address_line1} onChange={(e) => setForm({ ...form, address_line1: e.target.value })} />
          <input placeholder={t("clients.addressLine2")} value={form.address_line2} onChange={(e) => setForm({ ...form, address_line2: e.target.value })} />
          <input placeholder={t("clients.zipCity")} value={form.zip_city} onChange={(e) => setForm({ ...form, zip_city: e.target.value })} />
          <input placeholder={t("clients.email")} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input placeholder={t("clients.hourlyRate")} value={form.hourly_rate} onChange={(e) => setForm({ ...form, hourly_rate: e.target.value })} />
          <label style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            {t("clients.active")}
          </label>
          <textarea
            placeholder={t("clients.notes")}
            style={{ gridColumn: "1 / -1" }}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
          <button type="submit" style={{ gridColumn: "1 / -1" }}>
            {editingId ? t("clients.save") : t("clients.create")}
          </button>
        </form>
      )}

      <table className="card">
        <thead>
          <tr>
            <th>{t("clients.name")}</th>
            <th>{t("clients.colContact")}</th>
            <th>{t("clients.colEmail")}</th>
            <th>{t("clients.colHourlyRate")}</th>
            <th>{t("clients.colStatus")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {clients.map((c) => (
            <tr key={c.id}>
              <td>{c.name}</td>
              <td>{c.contact_person}</td>
              <td>{c.email}</td>
              <td>{c.hourly_rate ?? "—"}</td>
              <td>{c.active ? t("clients.statusActive") : t("clients.statusInactive")}</td>
              <td style={{ display: "flex", gap: "0.4rem" }}>
                <button className="secondary" onClick={() => startEdit(c)}>{t("clients.edit")}</button>
                <button className="danger" onClick={() => remove(c.id)}>{t("clients.delete")}</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
