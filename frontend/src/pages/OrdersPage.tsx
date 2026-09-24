import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api/client";
type O = { id: number; ticket_code: string; garment_name: string; length_cm: number; status: string; due_at: string };
type S = { id: number; name: string };

function nowLocalInput(): string {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
}

export default function OrdersPage() {
  const [rows, setRows] = useState<O[]>([]);
  const [stores, setStores] = useState<S[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const [form, setForm] = useState({ store_id: "", ticket_code: "", garment_name: "", length_cm: "", due_at: "" });
  const [submitting, setSubmitting] = useState(false);
  const reload = () => api<O[]>("/orders").then(setRows);
  useEffect(() => {
    reload();
    api<S[]>("/stores").then((ss) => {
      setStores(ss);
      setForm((f) => ({ ...f, store_id: f.store_id || String(ss[0]?.id ?? "") }));
    });
  }, []);
  async function hang(id: number) {
    setMsg(""); setErr("");
    try {
      const o = await api<O>("/hang", { method: "POST", body: JSON.stringify({ order_id: id }) });
      setMsg(`${o.ticket_code} 已上杆`);
      reload();
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  async function submit(e: FormEvent) {
    e.preventDefault();
    setMsg(""); setErr("");
    setSubmitting(true);
    try {
      const created = await api<O>("/orders", {
        method: "POST",
        body: JSON.stringify({
          store_id: Number(form.store_id),
          ticket_code: form.ticket_code,
          garment_name: form.garment_name,
          length_cm: Number(form.length_cm),
          // datetime-local 按本地时区解释，转成带时区的 UTC 时间发送
          due_at: new Date(form.due_at).toISOString(),
        }),
      });
      setMsg(`${created.ticket_code} 已创建，状态 ready，可上杆`);
      setForm({ store_id: form.store_id, ticket_code: "", garment_name: "", length_cm: "", due_at: "" });
      reload();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSubmitting(false);
    }
  }
  return (<>
    <h2>工单</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <form className="toolbar" onSubmit={submit}>
      <select value={form.store_id} onChange={(e) => setForm({ ...form, store_id: e.target.value })} required>
        {stores.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <input placeholder="票号" value={form.ticket_code} required
        onChange={(e) => setForm({ ...form, ticket_code: e.target.value })} />
      <input placeholder="衣名" value={form.garment_name} required
        onChange={(e) => setForm({ ...form, garment_name: e.target.value })} />
      <input placeholder="衣长 cm" type="number" step="0.1" min="0" value={form.length_cm} required
        onChange={(e) => setForm({ ...form, length_cm: e.target.value })} />
      <input type="datetime-local" min={nowLocalInput()} value={form.due_at} required
        onChange={(e) => setForm({ ...form, due_at: e.target.value })} />
      <button type="submit" disabled={submitting}>{submitting ? "提交中…" : "新建工单"}</button>
    </form>
    <table className="table"><thead><tr><th>票号</th><th>衣物</th><th>衣长</th><th>状态</th><th>到期</th><th></th></tr></thead>
    <tbody>{rows.map(o => <tr key={o.id}><td className="mono">{o.ticket_code}</td><td>{o.garment_name}</td><td className="mono">{o.length_cm}cm</td><td>{o.status}</td>
      <td className="mono">{new Date(o.due_at).toLocaleString()}</td>
      <td>{(o.status === "ready" || o.status === "overdue") && <button onClick={() => hang(o.id)}>上杆</button>}</td>
    </tr>)}</tbody></table>
  </>);
}
