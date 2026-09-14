import { useEffect, useState } from "react";
import { api } from "../../api";
import DataTable, { Col } from "../../components/DataTable";

const COLS: Col[] = [
  { key: "clave", label: "Clave", sortable: true },
  { key: "valor", label: "Valor", sortable: true },
  { key: "descripcion", label: "Descripción", sortable: true, render: (p) => p.descripcion || "-" },
];

export default function Parametros() {
  const [parametros, setParametros] = useState<any[]>([]);
  const [par, setPar] = useState({ clave: "", valor: "", descripcion: "" });
  const [error, setError] = useState("");

  async function cargar() { setParametros(await api.adminParametros()); }
  useEffect(() => { cargar(); }, []);

  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try { await api.upsertParametro(par); setPar({ clave: "", valor: "", descripcion: "" }); cargar(); }
    catch (err: any) { setError(err.message); }
  }

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>Parámetros generales ({parametros.length})</h2>
      <form onSubmit={guardar} style={{ display: "flex", gap: "0.5rem", alignItems: "end", marginBottom: "1rem", flexWrap: "wrap" }}>
        <div><label>Clave</label><input value={par.clave} onChange={(e) => setPar({ ...par, clave: e.target.value })} style={{ marginBottom: 0 }} required /></div>
        <div><label>Valor</label><input value={par.valor} onChange={(e) => setPar({ ...par, valor: e.target.value })} style={{ marginBottom: 0 }} required /></div>
        <div style={{ flex: 1 }}><label>Descripción</label><input value={par.descripcion} onChange={(e) => setPar({ ...par, descripcion: e.target.value })} style={{ marginBottom: 0 }} /></div>
        <button type="submit">Guardar</button>
      </form>
      {error && <p className="error">{error}</p>}
      <DataTable columns={COLS} rows={parametros} rowKey={(p) => p.id}
                 clientSort pageSize={25} defaultSort="clave" emptyText="Sin parámetros" />
    </div>
  );
}
