import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { avisar, pedirTexto } from "../../ui/dialog";

type Tarea = {
  tipo: string; id: string; titulo: string; estado: string; accion: string;
  solicitante: string; fecha: string; detalle: string; ruta: string;
  deepLink?: { clave: string; valor: string };
};

const TIPO_LBL: Record<string, string> = { LINEA: "Línea de crédito", SOLICITUD: "Solicitud", DESEMBOLSO: "Desembolso", REFINANCIACION: "Refinanciación" };
const ACCION_LBL: Record<string, string> = { aprobar: "Aprobar", publicar: "Publicar", resolver: "Resolver" };

export default function InboxAprobaciones() {
  const nav = useNavigate();
  const [items, setItems] = useState<Tarea[]>([]);
  const [err, setErr] = useState("");
  const [cargando, setCargando] = useState(true);

  const cargar = async () => {
    setErr(""); setCargando(true);
    try { setItems((await api.inboxAprobaciones()).items); }
    catch (e: any) { setErr(e.message || String(e)); }
    finally { setCargando(false); }
  };
  useEffect(() => { cargar(); }, []);

  function abrir(t: Tarea) {
    if (t.deepLink) sessionStorage.setItem(t.deepLink.clave, t.deepLink.valor);
    nav(t.ruta);
  }
  async function aprobarInline(t: Tarea) {
    try {
      const r = await api.inboxAprobarPendiente(t.id);
      avisar(r.ejecutado ? "Aprobado y ejecutado." : `Aprobado. Falta${r.faltan === 1 ? "" : "n"} ${r.faltan} nivel(es).`);
      cargar();
    } catch (e: any) { avisar({ tipo: "error", mensaje: e.message || String(e) }); }
  }
  async function rechazarInline(t: Tarea) {
    const motivo = (await pedirTexto({ titulo: "Rechazar", mensaje: "Motivo del rechazo:" })) || "";
    try { await api.inboxRechazarPendiente(t.id, motivo); cargar(); }
    catch (e: any) { avisar({ tipo: "error", mensaje: e.message || String(e) }); }
  }

  return (
    <div className="inbx">
      <div className="inbx-head">
        <div>
          <h1 style={{ margin: 0 }}>📥 Inbox de aprobaciones</h1>
          <p className="muted" style={{ margin: "2px 0 0" }}>Tareas que esperan tu aprobación (cuatro-ojos: no ves lo que vos mismo enviaste).</p>
        </div>
        <span style={{ flex: 1 }} />
        <span className="inbx-count">{items.length} pendiente{items.length === 1 ? "" : "s"}</span>
        <button className="btn sm" onClick={cargar} disabled={cargando}>{cargando ? "…" : "↻ Refrescar"}</button>
      </div>
      {err && <div className="alert crit">{err}</div>}

      {!cargando && items.length === 0 && (
        <div className="inbx-empty">✓ No tenés tareas pendientes de aprobación.</div>
      )}

      <div className="inbx-list">
        {items.map((t) => (
          <div className="inbx-card" key={`${t.tipo}-${t.id}-${t.estado}`}>
            <span className={"inbx-tipo " + t.tipo.toLowerCase()}>{TIPO_LBL[t.tipo] || t.tipo}</span>
            <div className="inbx-body">
              <b className="inbx-titulo">{t.titulo}</b>
              <div className="inbx-detalle">{t.detalle}</div>
              <div className="inbx-meta">
                <span title="Quién lo pidió">👤 Pedido por <b>{t.solicitante}</b></span>
                {t.fecha && <span>· {t.fecha}</span>}
                <span className="inbx-estado">{t.estado}</span>
              </div>
            </div>
            {t.accion === "aprobar-inline" ? (
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn sm" style={{ color: "var(--crit)", borderColor: "var(--crit)" }} onClick={() => rechazarInline(t)}>Rechazar</button>
                <button className="btn primary sm" onClick={() => aprobarInline(t)}>Aprobar</button>
              </div>
            ) : (
              <button className="btn primary sm" onClick={() => abrir(t)}>{ACCION_LBL[t.accion] || t.accion} →</button>
            )}
          </div>
        ))}
      </div>

      <style>{`
        .inbx-head { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
        .inbx-count { font-size:.72rem; text-transform:uppercase; letter-spacing:.4px; color:var(--ink-soft);
          border:1px solid var(--border); border-radius:999px; padding:3px 10px; }
        .inbx-empty { background:var(--surface); border:1px solid var(--border); border-radius:12px;
          padding:28px; text-align:center; color:var(--ink-soft); }
        .inbx-list { display:flex; flex-direction:column; gap:10px; }
        .inbx-card { display:flex; align-items:center; gap:14px; background:var(--surface); border:1px solid var(--border);
          border-radius:12px; padding:12px 16px; }
        .inbx-tipo { font-size:.64rem; font-weight:700; text-transform:uppercase; letter-spacing:.4px; border-radius:6px;
          padding:4px 8px; white-space:nowrap; }
        .inbx-tipo.linea { color:var(--brand-2); background:var(--accent-soft); }
        .inbx-tipo.solicitud { color:var(--warn); background:var(--warn-soft); }
        .inbx-body { flex:1; min-width:0; }
        .inbx-titulo { font-size:.95rem; }
        .inbx-detalle { color:var(--ink-soft); font-size:.85rem; margin-top:2px; }
        .inbx-meta { display:flex; gap:8px; flex-wrap:wrap; align-items:center; font-size:.78rem; color:var(--ink-faint); margin-top:5px; }
        .inbx-estado { border:1px solid var(--border); border-radius:999px; padding:1px 8px; color:var(--ink-soft); }
      `}</style>
    </div>
  );
}
