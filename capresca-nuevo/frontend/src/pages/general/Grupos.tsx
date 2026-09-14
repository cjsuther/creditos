import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import DataTable, { Col } from "../../components/DataTable";
import { useNivelActual } from "../../permisos";
import { confirmar, avisar } from "../../ui/dialog";

type Grupo = { id: number; codigo: string; nombre: string; activo: boolean; roles: string[]; miembros: number };

export default function Grupos() {
  const [rows, setRows] = useState<Grupo[]>([]);
  const [roles, setRoles] = useState<string[]>([]);
  const [busq, setBusq] = useState("");
  const [form, setForm] = useState<any>(null);          // alta/edición
  const [esAlta, setEsAlta] = useState(true);
  const [rolesDe, setRolesDe] = useState<Grupo | null>(null);   // panel de roles
  const [error, setError] = useState("");
  const { soloLectura } = useNivelActual();

  const cargar = () => api.grupos().then(setRows).catch((e) => setError(String(e)));
  useEffect(() => {
    cargar();
    api.perfilesMaestro().then((d: any[]) => setRoles(d.filter((p) => p.habilitado).map((p) => p.codigo))).catch(() => {});
  }, []);
  const guard = (p: Promise<any>) => p.then(cargar).catch((e: any) => avisar({ tipo: "error", mensaje: e.message || String(e) }));

  const filtrados = useMemo(() => {
    const t = busq.trim().toLowerCase();
    return rows.filter((g) => !t || g.codigo.toLowerCase().includes(t) || (g.nombre || "").toLowerCase().includes(t));
  }, [rows, busq]);

  const cols: Col[] = [
    { key: "codigo", label: "Código", sortable: true, render: (g) => <b>{g.codigo}</b> },
    { key: "nombre", label: "Nombre", sortable: true, render: (g) => g.nombre || "—" },
    { key: "roles", label: "Roles", render: (g) => g.roles.length ? g.roles.map((r: string) => <span key={r} className="pill" style={{ marginRight: 4 }}>{r}</span>) : <span className="muted">—</span> },
    { key: "miembros", label: "Miembros", sortable: true, align: "right" },
    { key: "activo", label: "Estado", sortable: true, render: (g) => <span className={`pill ${g.activo ? "ok" : "crit"}`}>{g.activo ? "Activo" : "Inactivo"}</span> },
  ];
  const acciones = (g: Grupo) => soloLectura ? [] : [
    { label: "Roles del grupo", icon: "shield", onClick: () => setRolesDe(g) },
    { label: "Editar", icon: "edit", onClick: () => { setForm({ ...g }); setEsAlta(false); setError(""); } },
    { label: g.activo ? "Desactivar" : "Activar", icon: g.activo ? "eye-off" : "eye", onClick: () => guard(api.editarGrupo(g.id, { nombre: g.nombre, activo: !g.activo })) },
    { label: "Borrar", icon: "trash", danger: true, hidden: g.miembros > 0, onClick: async () => { if (await confirmar({ titulo: "Borrar grupo", mensaje: `¿Borrar el grupo ${g.codigo}?`, danger: true })) guard(api.borrarGrupo(g.id)); } },
  ];

  function set(k: string, v: any) { setForm((f: any) => ({ ...f, [k]: v })); }
  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try {
      if (esAlta) await api.crearGrupo({ codigo: form.codigo, nombre: form.nombre });
      else await api.editarGrupo(form.id, { nombre: form.nombre, activo: form.activo });
      setForm(null); cargar();
    } catch (err: any) { setError(err.message); }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", marginBottom: 14, gap: 10 }}>
        <div>
          <h1 style={{ margin: 0 }}>Grupos</h1>
          <p className="muted" style={{ margin: 0 }}>Conjuntos de roles. Un usuario miembro hereda los roles del grupo. {rows.length} {rows.length === 1 ? "grupo" : "grupos"}.</p>
        </div>
        <div style={{ flex: 1 }} />
        {!soloLectura && <button onClick={() => { setForm({ codigo: "", nombre: "", activo: true }); setEsAlta(true); setError(""); }}>＋ Nuevo grupo</button>}
        {soloLectura && <span className="pill" style={{ fontSize: 12 }}>Sólo lectura</span>}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: "flex", gap: 10, padding: "12px 14px", borderBottom: "1px solid var(--border)" }}>
          <input value={busq} onChange={(e) => setBusq(e.target.value)} placeholder="Buscar por código o nombre…" style={{ marginBottom: 0, flex: 1 }} />
        </div>
        <div style={{ padding: "4px 14px 14px" }}>
          <DataTable columns={cols} rows={filtrados} rowKey={(g) => g.id} actions={acciones}
                     clientSort pageSize={25} defaultSort="codigo" emptyText="Sin grupos. Creá el primero." />
        </div>
      </div>

      {form && (
        <div className="abmu-ov" onClick={() => setForm(null)}>
          <form className="abmu-modal" onClick={(e) => e.stopPropagation()} onSubmit={guardar}>
            <h3 style={{ marginTop: 0 }}>{esAlta ? "Nuevo grupo" : `Editar grupo ${form.codigo}`}</h3>
            {esAlta && <label>Código<input value={form.codigo} maxLength={12} onChange={(e) => set("codigo", e.target.value.toUpperCase())} required /></label>}
            <label>Nombre<input value={form.nombre} onChange={(e) => set("nombre", e.target.value)} /></label>
            {!esAlta && <label className="abmu-chk" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}><input type="checkbox" checked={form.activo} onChange={(e) => set("activo", e.target.checked)} style={{ width: "auto" }} /> Activo</label>}
            {error && <div className="alert crit">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancelar</button>
              <button type="submit" className="btn primary">{esAlta ? "Alta" : "Guardar"}</button>
            </div>
          </form>
        </div>
      )}

      {rolesDe && <RolesDelGrupo grupo={rolesDe} roles={roles} soloLectura={soloLectura} onClose={() => { setRolesDe(null); cargar(); }} />}

      <style>{`
        .abmu-ov { position:fixed; inset:0; background:rgba(0,0,0,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
        .abmu-modal { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px 20px; width:min(440px,92vw); display:flex; flex-direction:column; gap:6px; }
        .abmu-modal label { display:flex; flex-direction:column; gap:3px; font-size:.85rem; color:var(--ink-soft); }
        .abmu-chk { display:flex; align-items:center; gap:5px; font-size:.85rem; color:var(--ink-soft); }
        .rg-chip { display:inline-flex; align-items:center; gap:6px; font-size:.78rem; background:var(--surface-2); border:1px solid var(--border); border-radius:999px; padding:3px 10px; }
      `}</style>
    </div>
  );
}

function RolesDelGrupo({ grupo, roles, soloLectura, onClose }: { grupo: Grupo; roles: string[]; soloLectura: boolean; onClose: () => void }) {
  const [sel, setSel] = useState<string[]>(grupo.roles);
  const [agregar, setAgregar] = useState("");
  const opciones = roles.filter((r) => !sel.includes(r));

  async function guardar() {
    try { await api.setGrupoRoles(grupo.id, sel); onClose(); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }
  return (
    <div className="abmu-ov" onClick={onClose}>
      <div className="abmu-modal" onClick={(e) => e.stopPropagation()} style={{ width: "min(480px,94vw)" }}>
        <h3 style={{ marginTop: 0 }}>Roles del grupo {grupo.codigo}</h3>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
          {sel.map((r) => (
            <span key={r} className="rg-chip">{r}{!soloLectura && <button type="button" style={{ border: "none", background: "transparent", color: "var(--crit)", cursor: "pointer" }} onClick={() => setSel((s) => s.filter((x) => x !== r))}>×</button>}</span>
          ))}
          {sel.length === 0 && <span className="muted" style={{ fontSize: 12 }}>Sin roles</span>}
        </div>
        {!soloLectura && (
          <div style={{ display: "flex", gap: 6 }}>
            <select value={agregar} onChange={(e) => setAgregar(e.target.value)} style={{ flex: 1 }}>
              <option value="">— agregar rol —</option>
              {opciones.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <button type="button" className="btn sm" disabled={!agregar} onClick={() => { setSel((s) => [...s, agregar]); setAgregar(""); }}>+ Agregar</button>
          </div>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
          <button type="button" className="btn" onClick={onClose}>Cerrar</button>
          {!soloLectura && <button type="button" className="btn primary" onClick={guardar}>Guardar roles</button>}
        </div>
      </div>
    </div>
  );
}
