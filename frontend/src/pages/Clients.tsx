import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
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
    if (!confirm("Kunden wirklich löschen?")) return;
    await api.delete(`/clients/${id}`);
    load();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Kunden</h2>
        <button
          onClick={() => {
            setForm(empty);
            setEditingId(null);
            setShowForm((v) => !v);
          }}
        >
          {showForm ? "Abbrechen" : "Neuer Kunde"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
          <input placeholder="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Ansprechpartner" value={form.contact_person} onChange={(e) => setForm({ ...form, contact_person: e.target.value })} />
          <input placeholder="Adresse" value={form.address_line1} onChange={(e) => setForm({ ...form, address_line1: e.target.value })} />
          <input placeholder="Adresszusatz" value={form.address_line2} onChange={(e) => setForm({ ...form, address_line2: e.target.value })} />
          <input placeholder="PLZ Ort" value={form.zip_city} onChange={(e) => setForm({ ...form, zip_city: e.target.value })} />
          <input placeholder="E-Mail" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input placeholder="Stundensatz (leer = Standard)" value={form.hourly_rate} onChange={(e) => setForm({ ...form, hourly_rate: e.target.value })} />
          <label style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Aktiv
          </label>
          <textarea
            placeholder="Notizen"
            style={{ gridColumn: "1 / -1" }}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
          <button type="submit" style={{ gridColumn: "1 / -1" }}>
            {editingId ? "Speichern" : "Anlegen"}
          </button>
        </form>
      )}

      <table className="card">
        <thead>
          <tr>
            <th>Name</th>
            <th>Kontakt</th>
            <th>E-Mail</th>
            <th>Stundensatz</th>
            <th>Status</th>
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
              <td>{c.active ? "aktiv" : "inaktiv"}</td>
              <td style={{ display: "flex", gap: "0.4rem" }}>
                <button className="secondary" onClick={() => startEdit(c)}>Bearbeiten</button>
                <button className="danger" onClick={() => remove(c.id)}>Löschen</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
