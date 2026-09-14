import { useEffect, useState } from "react";
import { api } from "../../api";
import DataTable, { Col } from "../../components/DataTable";
import LimpiarFiltros from "../../components/LimpiarFiltros";

const COLS: Col[] = [
  { key: "codigo", label: "Código", sortable: true },
  { key: "descripcion", label: "Descripción", sortable: true },
  { key: "tipo", label: "Tipo", sortable: true },
  { key: "seguros", label: "Seguros", sortable: true, render: (m) => (m.seguros ? "Sí" : "—") },
  { key: "tiene_plantilla", label: "Plantilla", sortable: true, render: (m) => (m.tiene_plantilla ? "Sí" : "—") },
];

export default function Modelos() {
  const [rows, setRows] = useState<any[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => { api.modelosResolucion().then(setRows); }, []);

  const filtradas = rows.filter((m) => !q || m.descripcion.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
        <h2 style={{ margin: 0 }}>Modelos de resoluciones / disposiciones</h2>
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar modelo" style={{ marginBottom: 0, width: 240 }} />
          <LimpiarFiltros activo={!!q} onClear={() => setQ("")} />
        </div>
      </div>
      <p className="muted" style={{ marginTop: "0.5rem" }}>Catálogo de plantillas para generar resoluciones y disposiciones. Fuente: rtf. {rows.length} modelos.</p>
      <DataTable columns={COLS} rows={filtradas} rowKey={(m) => m.codigo}
                 clientSort pageSize={25} defaultSort="codigo" emptyText="Sin modelos" />
    </div>
  );
}
