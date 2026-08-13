import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { useLanguage } from "../contexts/LanguageContext";
import { Client, Project, TimeEntry } from "../types";

function formatDuration(minutes: number) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

export function TimeTracking() {
  const { t } = useLanguage();
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [running, setRunning] = useState<TimeEntry | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [timerClientId, setTimerClientId] = useState<number | "">("");
  const [timerProjectId, setTimerProjectId] = useState<number | "">("");
  const [timerDescription, setTimerDescription] = useState("");
  const [filterClientId, setFilterClientId] = useState<number | "">("");
  const [error, setError] = useState<string | null>(null);

  const [manual, setManual] = useState({
    client_id: "",
    project_id: "",
    date: new Date().toISOString().slice(0, 10),
    description: "",
    hours: "",
  });

  const loadClients = () => api.get<Client[]>("/clients").then(setClients);
  const loadProjects = () => api.get<Project[]>("/projects").then(setProjects);
  const loadEntries = () =>
    api
      .get<TimeEntry[]>(`/time-entries${filterClientId ? `?client_id=${filterClientId}` : ""}`)
      .then(setEntries);
  const loadRunning = () => api.get<TimeEntry | null>("/time-entries/running").then(setRunning);

  useEffect(() => {
    loadClients();
    loadProjects();
    loadRunning();
  }, []);

  useEffect(() => {
    loadEntries();
  }, [filterClientId]);

  useEffect(() => {
    if (!running) return;
    const tick = () => {
      const started = new Date(running.running_started_at + "Z").getTime();
      setElapsed(Math.max(0, Math.floor((Date.now() - started) / 1000)));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [running]);

  const startTimer = async () => {
    if (!timerClientId) return;
    setError(null);
    try {
      const entry = await api.post<TimeEntry>("/time-entries/start", {
        client_id: timerClientId,
        project_id: timerProjectId || null,
        description: timerDescription,
      });
      setRunning(entry);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("time.errStart"));
    }
  };

  const stopTimer = async () => {
    if (!running) return;
    setError(null);
    try {
      await api.post(`/time-entries/${running.id}/stop`);
      setRunning(null);
      setTimerDescription("");
      loadEntries();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("time.errStop"));
    }
  };

  const onManualSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.post("/time-entries", {
        client_id: Number(manual.client_id),
        project_id: manual.project_id ? Number(manual.project_id) : null,
        date: manual.date,
        description: manual.description,
        duration_minutes: Math.round(Number(manual.hours) * 60),
      });
      setManual({ ...manual, description: "", hours: "" });
      loadEntries();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("time.errSave"));
    }
  };

  const remove = async (id: number) => {
    if (!confirm(t("time.confirmDelete"))) return;
    setError(null);
    try {
      await api.delete(`/time-entries/${id}`);
      loadEntries();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t("time.errDelete"));
    }
  };

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";
  const projectName = (id: number | null) => projects.find((project) => project.id === id)?.name ?? "—";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ margin: 0 }}>{t("time.title")}</h2>

      {error && <div style={{ color: "var(--danger)" }}>{error}</div>}

      <div className="card" style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
        {running ? (
          <>
            <div style={{ fontWeight: 700, fontSize: "1.2rem" }}>
              {clientName(running.client_id)} — {new Date(elapsed * 1000).toISOString().substring(11, 19)}
            </div>
            <div style={{ color: "var(--fg-muted)" }}>{running.description}</div>
            <div style={{ flex: 1 }} />
            <button className="danger" onClick={stopTimer}>{t("time.stop")}</button>
          </>
        ) : (
          <>
            <select value={timerClientId} onChange={(e) => { setTimerClientId(e.target.value ? Number(e.target.value) : ""); setTimerProjectId(""); }}>
              <option value="">{t("time.chooseClient")}</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <select value={timerProjectId} onChange={(e) => setTimerProjectId(e.target.value ? Number(e.target.value) : "")}>
              <option value="">{t("time.project")}</option>
              {projects.filter((project) => project.active && project.client_id === timerClientId).map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
            <input
              placeholder={t("time.description")}
              value={timerDescription}
              onChange={(e) => setTimerDescription(e.target.value)}
              style={{ flex: 1 }}
            />
            <button onClick={startTimer} disabled={!timerClientId}>{t("time.start")}</button>
          </>
        )}
      </div>

      <form onSubmit={onManualSubmit} className="card" style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
        <strong>{t("time.manualEntry")}</strong>
        <select required value={manual.client_id} onChange={(e) => setManual({ ...manual, client_id: e.target.value, project_id: "" })}>
          <option value="">{t("time.client")}</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select value={manual.project_id} onChange={(e) => setManual({ ...manual, project_id: e.target.value })}>
          <option value="">{t("time.project")}</option>
          {projects.filter((project) => project.active && String(project.client_id) === manual.client_id).map((project) => (
            <option key={project.id} value={project.id}>{project.name}</option>
          ))}
        </select>
        <input type="date" value={manual.date} onChange={(e) => setManual({ ...manual, date: e.target.value })} />
        <input placeholder={t("time.description")} value={manual.description} onChange={(e) => setManual({ ...manual, description: e.target.value })} />
        <input
          placeholder={t("time.hours")}
          type="number"
          step="0.25"
          min="0"
          required
          value={manual.hours}
          onChange={(e) => setManual({ ...manual, hours: e.target.value })}
          style={{ width: 90 }}
        />
        <button type="submit">{t("time.add")}</button>
      </form>

      <div>
        <select value={filterClientId} onChange={(e) => setFilterClientId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">{t("time.allClients")}</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>{t("time.colDate")}</th>
            <th>{t("time.colClient")}</th>
            <th>{t("time.colProject")}</th>
            <th>{t("time.colDescription")}</th>
            <th>{t("time.colDuration")}</th>
            <th>{t("time.colRate")}</th>
            <th>{t("time.colStatus")}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id}>
              <td>{e.date}</td>
              <td>{clientName(e.client_id)}</td>
              <td>{projectName(e.project_id)}</td>
              <td>{e.description}</td>
              <td>{formatDuration(e.duration_minutes)}</td>
              <td>{e.hourly_rate} €/h</td>
              <td>{e.billed ? t("time.statusBilled") : t("time.statusOpen")}</td>
              <td>
                {!e.billed && (
                  <button className="danger" onClick={() => remove(e.id)}>{t("time.delete")}</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
