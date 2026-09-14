import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import DataTable, { Col } from "../../components/DataTable";
import { MENU, items as itemsDe } from "../../menu";
import { useNivelActual } from "../../permisos";
import { confirmar, avisar } from "../../ui/dialog";

type Perfil = { id: number; codigo: string; denominacion: string; habilitado: boolean; usuarios: number };
const VACIO = { id: 0, codigo: "", denominacion: "", habilitado: true, usuarios: 0 };
const NIVELES = ["NINGUNO", "CONSULTA", "ESCRITURA", "TOTAL"];
const NIV_LBL: Record<string, string> = { NINGUNO: "Sin acceso", CONSULTA: "Consulta", ESCRITURA: "Escritura", TOTAL: "Total" };

export default function Perfiles() {
  const [rows, setRows] = useState<Perfil[]>([]);
  const [busq, setBusq] = useState("");
  const [form, setForm] = useState<any>(null);
  const [esAlta, setEsAlta] = useState(true);
  const [acceso, setAcceso] = useState<Perfil | null>(null);
  const [error, setError] = useState("");
  const { soloLectura } = useNivelActual();

  const cargar = () => api.perfilesMaestro().then(setRows).catch((e) => setError(String(e)));
  useEffect(() => { cargar(); }, []);
  const guard = (p: Promise<any>) => p.then(cargar).catch((e: any) => avisar({ tipo: "error", mensaje: e.message || String(e) }));

  const filtrados = useMemo(() => {
    const t = busq.trim().toLowerCase();
    return rows.filter((p) => !t || p.codigo.toLowerCase().includes(t) || (p.denominacion || "").toLowerCase().includes(t));
  }, [rows, busq]);

  const cols: Col[] = [
    { key: "codigo", label: "Código", sortable: true, render: (p) => <b>{p.codigo}</b> },
    { key: "denominacion", label: "Denominación", sortable: true, render: (p) => p.denominacion || "—" },
    { key: "usuarios", label: "Usuarios", sortable: true, align: "right", render: (p) => <span className="num">{p.usuarios}</span> },
    { key: "habilitado", label: "Estado", sortable: true, render: (p) => <span className={`pill ${p.habilitado ? "ok" : "crit"}`}>{p.habilitado ? "Habilitado" : "Deshabilitado"}</span> },
  ];
  const acciones = (p: Perfil) => [
    { label: "Acceso (permisos y usuarios)", icon: "lock", onClick: () => setAcceso(p) },
    ...(soloLectura ? [] : [
      { label: "Editar", icon: "edit", onClick: () => { setForm({ ...p }); setEsAlta(false); setError(""); } },
      { label: p.habilitado ? "Deshabilitar" : "Habilitar", icon: p.habilitado ? "eye-off" : "eye", onClick: () => guard(api.editarPerfil(p.id, { denominacion: p.denominacion, habilitado: !p.habilitado })) },
      { label: "Borrar", icon: "trash", danger: true, hidden: p.usuarios > 0, onClick: async () => { if (await confirmar({ titulo: "Borrar rol", mensaje: `¿Borrar el rol ${p.codigo}?`, danger: true })) guard(api.borrarPerfil(p.id)); } },
    ]),
  ];

  function set(k: string, v: any) { setForm((f: any) => ({ ...f, [k]: v })); }
  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try {
      if (esAlta) await api.crearPerfil({ codigo: form.codigo, denominacion: form.denominacion, habilitado: form.habilitado });
      else await api.editarPerfil(form.id, { denominacion: form.denominacion, habilitado: form.habilitado });
      setForm(null); cargar();
    } catch (err: any) { setError(err.message); }
  }

  const hab = rows.filter((p) => p.habilitado).length;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", marginBottom: 14, gap: 10 }}>
        <div>
          <h1 style={{ margin: 0 }}>Roles <span className="muted" style={{ fontSize: ".55em", fontWeight: 400 }}>(perfiles)</span></h1>
          <p className="muted" style={{ margin: 0 }}>Cada rol es un conjunto de permisos por pantalla. {hab} habilitados de {rows.length} · alta, baja y modificación</p>
        </div>
        <div style={{ flex: 1 }} />
        {!soloLectura && <button onClick={() => { setForm({ ...VACIO }); setEsAlta(true); setError(""); }}>＋ Nuevo rol</button>}
        {soloLectura && <span className="pill" style={{ fontSize: 12 }}>Sólo lectura</span>}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: "flex", gap: 10, padding: "12px 14px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
          <input value={busq} onChange={(e) => setBusq(e.target.value)} placeholder="Buscar por código o denominación…" style={{ marginBottom: 0, flex: 1, minWidth: 200 }} />
        </div>
        <div style={{ padding: "4px 14px 14px" }}>
          <DataTable columns={cols} rows={filtrados} rowKey={(p) => p.id} actions={acciones}
                     clientSort pageSize={25} defaultSort="codigo" emptyText="Sin perfiles." />
        </div>
      </div>

      {form && (
        <div className="abmu-ov" onClick={() => setForm(null)}>
          <form className="abmu-modal" onClick={(e) => e.stopPropagation()} onSubmit={guardar}>
            <h3 style={{ marginTop: 0 }}>{esAlta ? "Nuevo rol" : `Editar rol ${form.codigo}`}</h3>
            {esAlta && <label>Código<input value={form.codigo} maxLength={6} onChange={(e) => set("codigo", e.target.value.toUpperCase())} required /></label>}
            <label>Denominación<input value={form.denominacion} onChange={(e) => set("denominacion", e.target.value)} /></label>
            <label style={{ flexDirection: "row", alignItems: "center", gap: 8 }}><input type="checkbox" checked={form.habilitado} onChange={(e) => set("habilitado", e.target.checked)} style={{ width: "auto" }} /> Habilitado</label>
            {error && <div className="alert crit">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancelar</button>
              <button type="submit" className="btn primary">{esAlta ? "Alta" : "Guardar"}</button>
            </div>
          </form>
        </div>
      )}

      {acceso && <PerfilAcceso perfil={acceso} soloLectura={soloLectura} onClose={() => { setAcceso(null); cargar(); }} />}

      <style>{`
        .abmu-ov { position:fixed; inset:0; background:rgba(0,0,0,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
        .abmu-modal { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px 20px; width:min(420px,92vw); display:flex; flex-direction:column; gap:6px; }
        .abmu-modal label { display:flex; flex-direction:column; gap:3px; font-size:.85rem; color:var(--ink-soft); }
      `}</style>
    </div>
  );
}

// Panel de acceso del perfil: permisos por pantalla (matriz desde el MENU) + usuarios asignados.
function PerfilAcceso({ perfil, soloLectura, onClose }: { perfil: Perfil; soloLectura: boolean; onClose: () => void }) {
  const [tab, setTab] = useState<"permisos" | "usuarios">("permisos");
  const [permisos, setPermisos] = useState<Record<string, string>>({});
  const [miembros, setMiembros] = useState<any[]>([]);
  const [todos, setTodos] = useState<any[]>([]);
  const [aAsignar, setAAsignar] = useState<number[]>([]);
  const [q, setQ] = useState("");
  const [abierto, setAbierto] = useState<string | null>(MENU[0]?.label ?? null);

  const cargarPerm = () => api.perfilPermisos(perfil.id).then((d) => setPermisos(d.permisos || {}));
  const cargarUsr = () => api.perfilUsuarios(perfil.id).then((d) => setMiembros(d.usuarios || []));
  useEffect(() => { cargarPerm(); cargarUsr(); api.adminUsuarios().then(setTodos); }, []);

  const nivelDe = (ruta: string) => permisos[ruta] || "NINGUNO";
  async function setNivel(ruta: string, nivel: string) {
    setPermisos((p) => ({ ...p, [ruta]: nivel }));            // optimista
    try { await api.setPerfilPermiso(perfil.id, ruta, nivel); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); cargarPerm(); }
  }
  async function setModulo(rutas: string[], nivel: string) {
    setPermisos((p) => { const n = { ...p }; rutas.forEach((r) => (n[r] = nivel)); return n; });
    try { await api.setPerfilPermisosBulk(perfil.id, rutas, nivel); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); cargarPerm(); }
  }
  async function asignar() {
    if (!aAsignar.length) return;
    try { await api.asignarUsuariosPerfil(perfil.id, aAsignar); setAAsignar([]); cargarUsr(); }
    catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }

  const miembrosIds = new Set(miembros.map((u) => u.id));
  const disponibles = todos.filter((u) => !miembrosIds.has(u.id) &&
    (!q.trim() || u.username.toLowerCase().includes(q.toLowerCase()) || (u.nombre || "").toLowerCase().includes(q.toLowerCase())));
  const conAcceso = Object.values(permisos).filter((n) => n && n !== "NINGUNO").length;

  return (
    <div className="abmu-ov" onClick={onClose}>
      <div className="pa" onClick={(e) => e.stopPropagation()}>
        <div className="pa-head">
          <div><b>Acceso · {perfil.codigo}</b> <span className="muted" style={{ fontSize: 12 }}>{perfil.denominacion}</span></div>
          <span style={{ flex: 1 }} />
          <button className="btn sm" onClick={onClose}>✕ Cerrar</button>
        </div>
        <div className="pa-tabs">
          <button className={"pa-tab" + (tab === "permisos" ? " on" : "")} onClick={() => setTab("permisos")}>Permisos por pantalla <span className="pa-badge">{conAcceso}</span></button>
          <button className={"pa-tab" + (tab === "usuarios" ? " on" : "")} onClick={() => setTab("usuarios")}>Usuarios <span className="pa-badge">{miembros.length}</span></button>
        </div>

        {tab === "permisos" && (
          <div className="pa-body">
            {perfil.codigo === "ADMG" && (
              <div className="alert" style={{ marginBottom: 8, fontSize: 12.5 }}>
                <b>Acceso irrestricto.</b> El rol <b>ADMG</b> ve y opera todo el sistema por diseño, sin importar esta grilla.
              </div>
            )}
            {MENU.map((m) => {
              const rutas = itemsDe(m).map((i) => i.to);
              const conAccModulo = rutas.filter((r) => nivelDe(r) !== "NINGUNO").length;
              const exp = abierto === m.label;
              return (
                <div key={m.label} className="pa-mod">
                  <div className="pa-modhead" onClick={() => setAbierto(exp ? null : m.label)}>
                    <span className="pa-chev">{exp ? "▾" : "▸"}</span>
                    <b>{m.label}</b>
                    <span className="muted" style={{ fontSize: 11.5 }}>{conAccModulo}/{rutas.length} con acceso</span>
                    <span style={{ flex: 1 }} />
                    <select className="pa-sel" disabled={soloLectura} onClick={(e) => e.stopPropagation()} value="" onChange={(e) => { if (e.target.value) setModulo(rutas, e.target.value); e.currentTarget.value = ""; }}>
                      <option value="">Aplicar a todo…</option>
                      {NIVELES.map((n) => <option key={n} value={n}>{NIV_LBL[n]}</option>)}
                    </select>
                  </div>
                  {exp && (
                    <div className="pa-rows">
                      {m.grupos.map((g) => g.items.map((i) => (
                        <div key={i.to} className="pa-row">
                          <span className="pa-scr">{i.label}{i.nuevo && <span className="pa-new">new</span>}</span>
                          <span className="pa-ruta">{i.to}</span>
                          <select className={"pa-sel niv-" + nivelDe(i.to).toLowerCase()} disabled={soloLectura} value={nivelDe(i.to)} onChange={(e) => setNivel(i.to, e.target.value)}>
                            {NIVELES.map((n) => <option key={n} value={n}>{NIV_LBL[n]}</option>)}
                          </select>
                        </div>
                      )))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {tab === "usuarios" && (
          <div className="pa-body">
            <div className="pa-usrhead">
              <b style={{ fontSize: 13 }}>Miembros ({miembros.length})</b>
            </div>
            <div className="pa-miembros">
              {miembros.length === 0 && <div className="muted" style={{ fontSize: 12, padding: 6 }}>Sin usuarios con este rol.</div>}
              {miembros.map((u) => (
                <div key={u.id} className="pa-mrow">
                  <b>{u.username}</b> <span className="muted">{u.nombre}</span>
                  <span className="pill" style={{ marginLeft: 6, fontSize: 11 }}>{u.principal ? "★ principal" : "adicional"}</span>
                  {!u.activo && <span className="pill crit" style={{ marginLeft: 6 }}>baja</span>}
                </div>
              ))}
            </div>
            {!soloLectura && <div className="pa-asignar">
              <b style={{ fontSize: 13 }}>Sumar el rol {perfil.codigo} a usuarios</b>
              <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>Se agrega como rol adicional; no reemplaza el rol principal del usuario.</div>
              <input className="inp" placeholder="Buscar usuario…" value={q} onChange={(e) => setQ(e.target.value)} style={{ margin: "8px 0" }} />
              <div className="pa-disp">
                {disponibles.slice(0, 200).map((u) => (
                  <label key={u.id} className="pa-chk">
                    <input type="checkbox" checked={aAsignar.includes(u.id)} onChange={(e) => setAAsignar((s) => e.target.checked ? [...s, u.id] : s.filter((x) => x !== u.id))} />
                    <b>{u.username}</b> <span className="muted">{u.nombre} · {u.perfil}</span>
                  </label>
                ))}
              </div>
              <button className="btn primary" disabled={!aAsignar.length} onClick={asignar} style={{ marginTop: 8 }}>Asignar {aAsignar.length || ""} usuario(s)</button>
            </div>}
          </div>
        )}
      </div>

      <style>{`
        .pa { background:var(--surface); border:1px solid var(--border); border-radius:12px; width:min(760px,95vw); max-height:88vh; display:flex; flex-direction:column; overflow:hidden; }
        .pa-head { display:flex; align-items:center; gap:8px; padding:14px 16px; border-bottom:1px solid var(--border); }
        .pa-tabs { display:flex; gap:6px; padding:10px 16px 0; }
        .pa-tab { padding:7px 12px; border:1px solid var(--border); border-bottom:none; border-radius:8px 8px 0 0; background:var(--surface-2); color:var(--ink-soft); font:inherit; font-size:13px; cursor:pointer; }
        .pa-tab.on { background:var(--surface); color:var(--ink); font-weight:600; }
        .pa-badge { font-size:11px; background:var(--brand-2); color:#fff; border-radius:999px; padding:0 7px; margin-left:4px; }
        .pa-body { padding:12px 16px; overflow:auto; }
        .pa-mod { border:1px solid var(--border); border-radius:10px; margin-bottom:8px; }
        .pa-modhead { display:flex; align-items:center; gap:8px; padding:9px 12px; cursor:pointer; }
        .pa-chev { opacity:.6; width:14px; }
        .pa-rows { border-top:1px solid var(--border); }
        .pa-row { display:flex; align-items:center; gap:10px; padding:6px 12px; border-bottom:1px solid var(--border); }
        .pa-row:last-child { border-bottom:none; }
        .pa-scr { flex:1; font-size:13px; }
        .pa-new { font-size:9px; background:var(--ok-soft); color:var(--ok); border-radius:6px; padding:1px 5px; margin-left:6px; text-transform:uppercase; }
        .pa-ruta { font-size:11px; color:var(--ink-faint); font-family:var(--font-mono,monospace); }
        .pa-sel { padding:4px 8px; border:1px solid var(--border); border-radius:6px; background:var(--surface-2); color:var(--ink); font:inherit; font-size:12.5px; }
        .pa-sel.niv-consulta { border-color:var(--brand-2); } .pa-sel.niv-escritura { border-color:var(--warn); } .pa-sel.niv-total { border-color:var(--ok); }
        .pa-miembros { display:flex; flex-direction:column; gap:2px; margin:8px 0 14px; max-height:180px; overflow:auto; }
        .pa-mrow { padding:5px 8px; border-bottom:1px solid var(--border); font-size:13px; }
        .pa-asignar { border-top:1px solid var(--border); padding-top:12px; }
        .pa-disp { max-height:220px; overflow:auto; display:flex; flex-direction:column; gap:2px; }
        .pa-chk { display:flex; align-items:center; gap:8px; padding:4px 6px; font-size:13px; cursor:pointer; }
      `}</style>
    </div>
  );
}
