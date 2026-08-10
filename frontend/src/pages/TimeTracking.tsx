import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { Client, TimeEntry } from "../types";

function formatDuration(minutes: number) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

export function TimeTracking() {
  const [clients, setClients] = useState<Client[]>([]);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [running, setRunning] = useState<TimeEntry | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [timerClientId, setTimerClientId] = useState<number | "">("");
  const [timerDescription, setTimerDescription] = useState("");
  const [filterClientId, setFilterClientId] = useState<number | "">("");

  const [manual, setManual] = useState({
    client_id: "",
    date: new Date().toISOString().slice(0, 10),
    description: "",
    hours: "",
  });

  const loadClients = () => api.get<Client[]>("/clients").then(setClients);
  const loadEntries = () =>
    api
      .get<TimeEntry[]>(`/time-entries${filterClientId ? `?client_id=${filterClientId}` : ""}`)
      .then(setEntries);
  const loadRunning = () => api.get<TimeEntry | null>("/time-entries/running").then(setRunning);

  useEffect(() => {
    loadClients();
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
    const entry = await api.post<TimeEntry>("/time-entries/start", {
      client_id: timerClientId,
      description: timerDescription,
    });
    setRunning(entry);
  };

  const stopTimer = async () => {
    if (!running) return;
    await api.post(`/time-entries/${running.id}/stop`);
    setRunning(null);
    setTimerDescription("");
    loadEntries();
  };

  const onManualSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await api.post("/time-entries", {
      client_id: Number(manual.client_id),
      date: manual.date,
      description: manual.description,
      duration_minutes: Math.round(Number(manual.hours) * 60),
    });
    setManual({ ...manual, description: "", hours: "" });
    loadEntries();
  };

  const remove = async (id: number) => {
    if (!confirm("Eintrag löschen?")) return;
    await api.delete(`/time-entries/${id}`);
    loadEntries();
  };

  const clientName = (id: number) => clients.find((c) => c.id === id)?.name ?? "?";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      <h2 style={{ margin: 0 }}>Zeiterfassung</h2>

      <div className="card" style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
        {running ? (
          <>
            <div style={{ fontWeight: 700, fontSize: "1.2rem" }}>
              {clientName(running.client_id)} — {new Date(elapsed * 1000).toISOString().substring(11, 19)}
            </div>
            <div style={{ color: "var(--fg-muted)" }}>{running.description}</div>
            <div style={{ flex: 1 }} />
            <button className="danger" onClick={stopTimer}>Stopp</button>
          </>
        ) : (
          <>
            <select value={timerClientId} onChange={(e) => setTimerClientId(Number(e.target.value))}>
              <option value="">Kunde wählen…</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <input
              placeholder="Beschreibung"
              value={timerDescription}
              onChange={(e) => setTimerDescription(e.target.value)}
              style={{ flex: 1 }}
            />
            <button onClick={startTimer} disabled={!timerClientId}>Start</button>
          </>
        )}
      </div>

      <form onSubmit={onManualSubmit} className="card" style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap", alignItems: "center" }}>
        <strong>Manueller Eintrag:</strong>
        <select required value={manual.client_id} onChange={(e) => setManual({ ...manual, client_id: e.target.value })}>
          <option value="">Kunde…</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <input type="date" value={manual.date} onChange={(e) => setManual({ ...manual, date: e.target.value })} />
        <input placeholder="Beschreibung" value={manual.description} onChange={(e) => setManual({ ...manual, description: e.target.value })} />
        <input
          placeholder="Stunden"
          type="number"
          step="0.25"
          min="0"
          required
          value={manual.hours}
          onChange={(e) => setManual({ ...manual, hours: e.target.value })}
          style={{ width: 90 }}
        />
        <button type="submit">Hinzufügen</button>
      </form>

      <div>
        <select value={filterClientId} onChange={(e) => setFilterClientId(e.target.value ? Number(e.target.value) : "")}>
          <option value="">Alle Kunden</option>
          {clients.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      <table className="card">
        <thead>
          <tr>
            <th>Datum</th>
            <th>Kunde</th>
            <th>Beschreibung</th>
            <th>Dauer</th>
            <th>Satz</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.id}>
              <td>{e.date}</td>
              <td>{clientName(e.client_id)}</td>
              <td>{e.description}</td>
              <td>{formatDuration(e.duration_minutes)}</td>
              <td>{e.hourly_rate} €/h</td>
              <td>{e.billed ? "abgerechnet" : "offen"}</td>
              <td>
                {!e.billed && (
                  <button className="danger" onClick={() => remove(e.id)}>Löschen</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
