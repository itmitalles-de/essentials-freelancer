import { FormEvent, useEffect, useState } from "react";

import { api, ApiError } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Project } from "../types";

const empty = {
  client_id: "",
  name: "",
  description: "",
  hourly_rate: "",
  billing_rate_type_override: null as Project["billing_rate_type_override"],
  default_service_mode: "remote" as Project["default_service_mode"],
  is_individual_project: false,
  billing_profile_confirmed: false,
  active: true,
};

export function Projects() {
  const { t } = useLanguage();
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [form, setForm] = useState(empty);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.get<Project[]>("/projects").then(setProjects);

  useEffect(() => {
    api.get<Client[]>("/clients").then(setClients);
    load();
  }, []);

  const startEdit = (project: Project) => {
    setEditingId(project.id);
    setForm({
      client_id: String(project.client_id),
      name: project.name,
      description: project.description,
      hourly_rate: project.hourly_rate ?? "",
      billing_rate_type_override: project.billing_rate_type_override,
      default_service_mode: project.default_service_mode,
      is_individual_project: project.is_individual_project,
      billing_profile_confirmed: project.billing_profile_confirmed,
      active: project.active,
    });
    setShowForm(true);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    const payload = {
      ...form,
      client_id: Number(form.client_id),
      hourly_rate: form.hourly_rate || null,
    };
    try {
      if (editingId === null) await api.post("/projects", payload);
      else await api.put(`/projects/${editingId}`, payload);
      setForm(empty);
      setEditingId(null);
      setShowForm(false);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Project could not be saved");
    }
  };

  const remove = async (id: number) => {
    if (!confirm(t("projects.confirmDelete"))) return;
    setError(null);
    try {
      await api.delete(`/projects/${id}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Project could not be deleted");
    }
  };

  const clientName = (id: number) => clients.find((item) => item.id === id)?.name ?? "?";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>{t("projects.title")}</h2>
        <button onClick={() => { setShowForm((value) => !value); setEditingId(null); setForm(empty); }}>
          {showForm ? t("projects.cancel") : t("projects.new")}
        </button>
      </div>
      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}
      {showForm && (
        <form onSubmit={submit} className="card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
          <select required value={form.client_id} onChange={(event) => setForm({ ...form, client_id: event.target.value })}>
            <option value="">{t("projects.client")}</option>
            {clients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <input required placeholder={t("projects.name")} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <textarea style={{ gridColumn: "1 / -1" }} placeholder={t("projects.description")} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          <input type="number" min="0" step="0.01" placeholder={t("projects.hourlyRate")} value={form.hourly_rate} onChange={(event) => setForm({ ...form, hourly_rate: event.target.value })} />
          <label>{t("projects.billingRateOverride")}
            <select value={form.billing_rate_type_override ?? ""} onChange={(event) => setForm({ ...form, billing_rate_type_override: (event.target.value || null) as Project["billing_rate_type_override"] })}>
              <option value="">{t("billing.inherit")}</option>
              <option value="private">{t("billing.private")}</option>
              <option value="business">{t("billing.business")}</option>
              <option value="custom">{t("billing.custom")}</option>
            </select>
          </label>
          <label>{t("projects.serviceMode")}
            <select value={form.default_service_mode} onChange={(event) => setForm({ ...form, default_service_mode: event.target.value as Project["default_service_mode"] })}>
              <option value="remote">{t("billing.remote")}</option>
              <option value="onsite">{t("billing.onsite")}</option>
            </select>
          </label>
          <label><input type="checkbox" checked={form.is_individual_project} onChange={(event) => setForm({ ...form, is_individual_project: event.target.checked })} /> {t("projects.individual")}</label>
          <label><input type="checkbox" checked={form.billing_profile_confirmed} onChange={(event) => setForm({ ...form, billing_profile_confirmed: event.target.checked })} /> {t("billing.profileConfirmed")}</label>
          <label><input type="checkbox" checked={form.active} onChange={(event) => setForm({ ...form, active: event.target.checked })} /> {t("projects.active")}</label>
          <button type="submit" style={{ gridColumn: "1 / -1" }}>{editingId === null ? t("projects.create") : t("projects.save")}</button>
        </form>
      )}
      <table className="card">
        <thead><tr><th>{t("projects.name")}</th><th>{t("projects.colClient")}</th><th>{t("projects.colRate")}</th><th>{t("projects.colBillingType")}</th><th>{t("projects.colServiceMode")}</th><th>{t("billing.colConfirmed")}</th><th>{t("projects.colStatus")}</th><th></th></tr></thead>
        <tbody>{projects.map((project) => (
          <tr key={project.id}>
            <td>{project.name}</td><td>{clientName(project.client_id)}</td><td>{project.hourly_rate ?? t("billing.fromProfile")}</td><td>{project.billing_rate_type_override ? t(`billing.${project.billing_rate_type_override}`) : t("billing.inherit")}</td><td>{t(`billing.${project.default_service_mode}`)}</td><td>{project.billing_profile_confirmed ? t("common.yes") : t("common.no")}</td><td>{project.active ? t("clients.statusActive") : t("clients.statusInactive")}</td>
            <td style={{ display: "flex", gap: "0.4rem" }}><button className="secondary" onClick={() => startEdit(project)}>{t("projects.edit")}</button><button className="danger" onClick={() => remove(project.id)}>{t("projects.delete")}</button></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}
