import { useEffect, useState } from "react";
import { api } from "../api/client";
type O = { id: number; ticket_code: string; garment_name: string; length_cm: number; status: string; due_at: string };

function defaultDue(): string {
  const d = new Date(Date.now() + 24 * 3600 * 1000);
  d.setSeconds(0, 0);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function OrdersPage() {
  const [rows, setRows] = useState<O[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const [form, setForm] = useState({ ticket_code: "", garment_name: "", length_cm: "", due_at: defaultDue() });
  const [saving, setSaving] = useState(false);
  const reload = () => api<O[]>("/orders").then(setRows);
  useEffect(() => { reload(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setMsg(""); setErr("");
    const length = Number(form.length_cm);
    if (!form.ticket_code.trim()) { setErr("票号不能为空"); return; }
    if (!form.garment_name.trim()) { setErr("衣名不能为空"); return; }
    if (!(length > 0)) { setErr("衣长须为正数"); return; }
    if (!form.due_at) { setErr("请选择到期时间"); return; }
    if (new Date(form.due_at).getTime() < Date.now()) { setErr("到期时间不得早于当前时刻"); return; }
    setSaving(true);
    try {
      const o = await api<O>("/orders", {
        method: "POST",
        body: JSON.stringify({
          ticket_code: form.ticket_code.trim(),
          garment_name: form.garment_name.trim(),
          length_cm: length,
          due_at: new Date(form.due_at).toISOString(),
        }),
      });
      setMsg(`${o.ticket_code} 已录入，状态 ready，可上杆`);
      setForm({ ticket_code: "", garment_name: "", length_cm: "", due_at: defaultDue() });
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  }

  async function hang(id: number) {
    setMsg(""); setErr("");
    try {
      const o = await api<O>("/hang", { method: "POST", body: JSON.stringify({ order_id: id }) });
      setMsg(`${o.ticket_code} 已上杆`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>工单</h2>
    <form className="toolbar" onSubmit={submit}>
      <input value={form.ticket_code} onChange={e => setForm({ ...form, ticket_code: e.target.value })} placeholder="票号（全局唯一）" />
      <input value={form.garment_name} onChange={e => setForm({ ...form, garment_name: e.target.value })} placeholder="衣名" />
      <input type="number" step="0.1" min="0" value={form.length_cm} onChange={e => setForm({ ...form, length_cm: e.target.value })} placeholder="衣长 cm" style={{ width: "7rem" }} />
      <input type="datetime-local" value={form.due_at} onChange={e => setForm({ ...form, due_at: e.target.value })} />
      <button type="submit" disabled={saving}>{saving ? "录入中…" : "录入取衣工单"}</button>
    </form>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr><th>票号</th><th>衣物</th><th>衣长</th><th>状态</th><th>到期</th><th></th></tr></thead>
    <tbody>{rows.map(o => <tr key={o.id}><td className="mono">{o.ticket_code}</td><td>{o.garment_name}</td><td className="mono">{o.length_cm}cm</td><td>{o.status}</td>
      <td className="mono">{new Date(o.due_at).toLocaleString()}</td>
      <td>{(o.status === "ready" || o.status === "overdue") && <button onClick={() => hang(o.id)}>上杆</button>}</td>
    </tr>)}</tbody></table>
  </>);
}
