import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import DataTable, { Col } from "../../components/DataTable";
import { useNivelActual } from "../../permisos";
import { MENU } from "../../menu";
import { avisar, pedirTexto } from "../../ui/dialog";

type Usuario = { id: number; username: string; nombre: string; perfil: string; activo: boolean; perfilesExtra?: number };
const VACIO = { id: 0, username: "", nombre: "", password: "", perfil: "" };
const NIV = ["CONSULTA", "ESCRITURA", "TOTAL"];
// Una fila por ruta única: el menú tiene alias (dos ítems → misma ruta, p.ej. reimpresiones), que
// deduplicamos para no repetir opciones ni romper las keys del <select>.
const PANTALLAS = Object.values(
  MENU.flatMap((m) => m.grupos.flatMap((g) => g.items.map((i) => ({ ruta: i.to, label: i.label, modulo: m.label }))))
    .reduce<Record<string, { ruta: string; label: string; modulo: string }>>((acc, p) => { if (!acc[p.ruta]) acc[p.ruta] = p; return acc; }, {})
);

export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [perfiles, setPerfiles] = useState<{ codigo: string }[]>([]);
  const [usados, setUsados] = useState<string[]>([]);
  const [busq, setBusq] = useState("");
  const [estado, setEstado] = useState("todos");
  const [form, setForm] = useState<any>(null);
  const [esAlta, setEsAlta] = useState(true);
  const [error, setError] = useState("");
  const [perfilUsr, setPerfilUsr] = useState<{ principal: string; perfiles: string[] }>({ principal: "", perfiles: [] });
  const [agregar, setAgregar] = useState("");
  const [accesos, setAccesos] = useState<any>(null);
  const [gruposCat, setGruposCat] = useState<{ codigo: string; nombre: string }[]>([]);
  const [nuevoGrupo, setNuevoGrupo] = useState({ grupo: "", desde: "", hasta: "" });
  const [nuevoPerm, setNuevoPerm] = useState({ ruta: "", nivel: "CONSULTA", desde: "", hasta: "" });
  const [tab, setTab] = useState("roles");
  const { soloLectura } = useNivelActual();

  const cargar = async () => {
    setUsuarios(await api.adminUsuarios());
    setUsados((await api.perfilesUsados()).map((x: any) => x.perfil));
  };
  useEffect(() => {
    cargar();
    api.perfilesMaestro().then((d) => setPerfiles(d.filter((p: any) => p.habilitado)));
  }, []);

  const opcionesPerfil = useMemo(() => {
    const s = new Set<string>([...perfiles.map((p) => p.codigo), ...usados]);
    return [...s].sort();
  }, [perfiles, usados]);

  const filtrados = useMemo(() => {
    const t = busq.trim().toLowerCase();
    return usuarios.filter((u) =>
      (estado === "todos" || (estado === "activos" ? u.activo : !u.activo)) &&
      (!t || u.username.toLowerCase().includes(t) || (u.nombre || "").toLowerCase().includes(t) || (u.perfil || "").toLowerCase().includes(t)));
  }, [usuarios, busq, estado]);

  const cols: Col[] = [
    { key: "username", label: "Usuario", sortable: true, render: (u) => <b>{u.username}</b> },
    { key: "nombre", label: "Nombre", sortable: true, render: (u) => u.nombre || "—" },
    { key: "perfil", label: "Perfil", sortable: true, render: (u) => (
      <span style={{ display: "inline-flex", gap: 4, alignItems: "center" }}>
        <span className="pill">{u.perfil}</span>
        {u.perfilesExtra > 0 && <span className="pill" title={`Tiene ${u.perfilesExtra} perfil(es) adicional(es)`} style={{ background: "var(--brand-2)", color: "#fff" }}>+{u.perfilesExtra}</span>}
      </span>
    ) },
    { key: "activo", label: "Estado", sortable: true, render: (u) => <span className={`pill ${u.activo ? "ok" : "crit"}`}>{u.activo ? "Activo" : "Baja"}</span> },
  ];
  const acciones = (u: Usuario) => soloLectura ? [] : [
    { label: "Editar", icon: "edit", onClick: () => abrirEdicion(u) },
    { label: "Restablecer clave", icon: "key", onClick: () => reset(u) },
    { label: "Dar de baja", icon: "ban", danger: true, onClick: () => guard(api.bajaUsuario(u.id)), hidden: !u.activo },
    { label: "Reactivar", icon: "rotate-ccw", onClick: () => guard(api.reactivarUsuario(u.id)), hidden: u.activo },
  ];

  const guard = (p: Promise<any>) => p.then(cargar).catch((e: any) => avisar({ tipo: "error", mensaje: e.message || String(e) }));
  function abrirAlta() { setForm({ ...VACIO }); setEsAlta(true); setError(""); setPerfilUsr({ principal: "", perfiles: [] }); setAgregar(""); }
  function abrirEdicion(u: Usuario) {
    setForm({ ...VACIO, ...u }); setEsAlta(false); setError(""); setAgregar(""); setNuevoGrupo({ grupo: "", desde: "", hasta: "" });
    setPerfilUsr({ principal: u.perfil, perfiles: [u.perfil] });     // provisorio hasta que llegue el detalle
    api.usuarioPerfiles(u.id).then((d) => setPerfilUsr({ principal: d.principal, perfiles: d.perfiles })).catch(() => {});
    recargarAccesos(u.id); setTab("roles");
    api.grupos().then((d: any[]) => setGruposCat(d.map((g) => ({ codigo: g.codigo, nombre: g.nombre })))).catch(() => {});
  }
  function recargarAccesos(id: number) { api.usuarioAccesos(id).then(setAccesos).catch(() => setAccesos(null)); }
  async function agregarGrupo() {
    if (!nuevoGrupo.grupo || !form) return;
    try {
      await api.asignarGrupoUsuario(form.id, nuevoGrupo.grupo, nuevoGrupo.desde || null, nuevoGrupo.hasta || null);
      setNuevoGrupo({ grupo: "", desde: "", hasta: "" }); recargarAccesos(form.id);
    } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }
  async function quitarGrupo(codigo: string) {
    if (!form) return;
    try { await api.quitarGrupoUsuario(form.id, codigo); recargarAccesos(form.id); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }
  async function agregarPermisoDir() {
    if (!nuevoPerm.ruta || !form) return;
    try {
      await api.asignarPermisoDirecto(form.id, nuevoPerm.ruta, nuevoPerm.nivel, nuevoPerm.desde || null, nuevoPerm.hasta || null);
      setNuevoPerm({ ruta: "", nivel: "CONSULTA", desde: "", hasta: "" }); recargarAccesos(form.id);
    } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }
  async function quitarPermisoDir(ruta: string) {
    if (!form) return;
    try { await api.quitarPermisoDirecto(form.id, ruta); recargarAccesos(form.id); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); }
  }
  const labelRuta = (ruta: string) => PANTALLAS.find((p) => p.ruta === ruta)?.label || ruta;
  function set(k: string, v: any) { setForm((f: any) => ({ ...f, [k]: v })); }
  function agregarPerfil() {
    const c = agregar.trim().toUpperCase();
    if (c && !perfilUsr.perfiles.includes(c)) setPerfilUsr((p) => ({ ...p, perfiles: [...p.perfiles, c] }));
    setAgregar("");
  }
  function quitarPerfil(c: string) {
    setPerfilUsr((p) => {
      const perfiles = p.perfiles.filter((x) => x !== c);
      const principal = p.principal === c ? (perfiles[0] || "") : p.principal;
      return { principal, perfiles };
    });
  }

  async function reset(u: Usuario) {
    const p = await pedirTexto({ titulo: "Restablecer clave", mensaje: `Nueva clave para ${u.username}:`, requerido: true });
    if (p) { try { await api.cambiarClave(u.id, p); avisar("Clave actualizada."); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); } }
  }
  async function guardarRoles() {
    if (!form) return; setError("");
    try {
      if (!perfilUsr.principal) throw new Error("El usuario debe tener un rol principal.");
      await api.setUsuarioPerfiles(form.id, perfilUsr.principal, perfilUsr.perfiles);
      recargarAccesos(form.id); avisar("Roles guardados.");
    } catch (err: any) { setError(err.message); }
  }
  async function guardar(e: React.FormEvent) {
    e.preventDefault(); setError("");
    try {
      if (esAlta) {
        await api.crearUsuario({ username: form.username, nombre: form.nombre, password: form.password, perfil: (form.perfil || "XCR").toUpperCase() });
      } else {
        await api.editarUsuario(form.id, { nombre: form.nombre });
        if (!perfilUsr.principal) throw new Error("El usuario debe tener un perfil principal.");
        await api.setUsuarioPerfiles(form.id, perfilUsr.principal, perfilUsr.perfiles);
      }
      setForm(null); cargar();
    } catch (err: any) { setError(err.message); }
  }

  const activos = usuarios.filter((u) => u.activo).length;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", marginBottom: 14, gap: 10 }}>
        <div>
          <h1 style={{ margin: 0 }}>Usuarios</h1>
          <p className="muted" style={{ margin: 0 }}>{activos} activos · {usuarios.length - activos} de baja · {usuarios.length} total · alta, baja y modificación</p>
        </div>
        <div style={{ flex: 1 }} />
        {!soloLectura && <button onClick={abrirAlta}>＋ Nuevo usuario</button>}
        {soloLectura && <span className="pill" style={{ fontSize: 12 }}>Sólo lectura</span>}
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div style={{ display: "flex", gap: 10, padding: "12px 14px", borderBottom: "1px solid var(--border)", flexWrap: "wrap" }}>
          <input value={busq} onChange={(e) => setBusq(e.target.value)} placeholder="Buscar por usuario, nombre o perfil…" style={{ marginBottom: 0, flex: 1, minWidth: 200 }} />
          <select value={estado} onChange={(e) => setEstado(e.target.value)} style={{ marginBottom: 0, maxWidth: 160 }}>
            <option value="todos">Todos</option><option value="activos">Activos</option><option value="baja">Dados de baja</option>
          </select>
        </div>
        <div style={{ padding: "4px 14px 14px" }}>
          <DataTable columns={cols} rows={filtrados} rowKey={(u) => u.id} actions={acciones}
                     clientSort pageSize={25} defaultSort="username" emptyText="Sin usuarios para el filtro." />
        </div>
      </div>

      <datalist id="perfiles-dl">{opcionesPerfil.map((c) => <option key={c} value={c} />)}</datalist>

      {form && esAlta && (
        <div className="abmu-ov" onClick={() => setForm(null)}>
          <form className="abmu-modal" onClick={(e) => e.stopPropagation()} onSubmit={guardar}>
            <h3 style={{ marginTop: 0 }}>Nuevo usuario</h3>
            <label>Usuario<input value={form.username} onChange={(e) => set("username", e.target.value)} required /></label>
            <label>Nombre<input value={form.nombre} onChange={(e) => set("nombre", e.target.value)} /></label>
            <label>Clave<input type="password" value={form.password} onChange={(e) => set("password", e.target.value)} required /></label>
            <label>Rol principal<input list="perfiles-dl" value={form.perfil} onChange={(e) => set("perfil", e.target.value)} placeholder="XCR" /></label>
            <div className="muted" style={{ fontSize: 11 }}>Después de crearlo podés sumarle roles, grupos y permisos.</div>
            {error && <div className="alert crit">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 8, justifyContent: "flex-end" }}>
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancelar</button>
              <button type="submit" className="btn primary">Alta</button>
            </div>
          </form>
        </div>
      )}

      {form && !esAlta && (
        <div className="abmu-ov" onClick={() => setForm(null)}>
          <div className="abmu-modal ue" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>Acceso de {form.username} <span className="muted" style={{ fontSize: ".6em", fontWeight: 400 }}>{form.nombre}</span></h3>
            <div className="ue-tabs">
              {[["roles", "Roles"], ["grupos", "Grupos"], ["permisos", "Permisos directos"], ["efectivo", "Acceso efectivo"], ["datos", "Datos"]].map(([k, l]) => (
                <button key={k} className={"ue-tab" + (tab === k ? " on" : "")} onClick={() => setTab(k)}>{l}</button>
              ))}
            </div>

            {tab === "roles" && (
              <div className="ue-body">
                <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>Roles asignados directamente al usuario. El ★ es el <b>principal</b> (se usa para JWT y aprobaciones).</p>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                  {perfilUsr.perfiles.map((c) => (
                    <span key={c} className={"pill" + (c === perfilUsr.principal ? " ok" : "")} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                      {c === perfilUsr.principal && <span title="Principal">★</span>}{c}
                      {!soloLectura && c !== perfilUsr.principal && <button type="button" title="Marcar principal" style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--ink-soft)" }} onClick={() => setPerfilUsr((p) => ({ ...p, principal: c }))}>☆</button>}
                      {!soloLectura && <button type="button" title="Quitar" style={{ border: "none", background: "transparent", cursor: "pointer", color: "var(--crit)" }} onClick={() => quitarPerfil(c)}>×</button>}
                    </span>
                  ))}
                  {perfilUsr.perfiles.length === 0 && <span className="muted" style={{ fontSize: 12 }}>Sin roles</span>}
                </div>
                {!soloLectura && (
                  <div style={{ display: "flex", gap: 6 }}>
                    <input list="perfiles-dl" placeholder="Agregar rol…" value={agregar} onChange={(e) => setAgregar(e.target.value)}
                           onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); agregarPerfil(); } }} style={{ flex: 1 }} />
                    <button type="button" className="btn sm" onClick={agregarPerfil}>+ Rol</button>
                    <button type="button" className="btn sm primary" onClick={guardarRoles}>Guardar roles</button>
                  </div>
                )}
              </div>
            )}

            {tab === "grupos" && (
              <div className="ue-body">
                <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>El usuario hereda los roles de sus grupos. Podés poner <b>vigencia</b> (para licencias/vacaciones).</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                  {(accesos?.grupos || []).map((g: any) => (
                    <div key={g.codigo} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
                      <span className="pill">{g.codigo}</span>
                      <span className="muted">{g.desde || g.hasta ? `vigencia ${g.desde || "—"} → ${g.hasta || "sin fin"}` : "sin vencimiento"}</span>
                      <span style={{ flex: 1 }} />
                      {!soloLectura && <button type="button" className="btn sm" style={{ color: "var(--crit)" }} onClick={() => quitarGrupo(g.codigo)}>Quitar</button>}
                    </div>
                  ))}
                  {(!accesos?.grupos || accesos.grupos.length === 0) && <span className="muted" style={{ fontSize: 12 }}>No pertenece a ningún grupo.</span>}
                </div>
                {!soloLectura && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "end" }}>
                    <label style={{ flex: 1, minWidth: 130 }}><span className="ue-lbl">Grupo</span>
                      <select value={nuevoGrupo.grupo} onChange={(e) => setNuevoGrupo({ ...nuevoGrupo, grupo: e.target.value })}>
                        <option value="">— elegir —</option>
                        {gruposCat.filter((g) => !(accesos?.grupos || []).some((x: any) => x.codigo === g.codigo)).map((g) => <option key={g.codigo} value={g.codigo}>{g.codigo} — {g.nombre}</option>)}
                      </select></label>
                    <label><span className="ue-lbl">Desde</span><input type="date" value={nuevoGrupo.desde} onChange={(e) => setNuevoGrupo({ ...nuevoGrupo, desde: e.target.value })} /></label>
                    <label><span className="ue-lbl">Hasta</span><input type="date" value={nuevoGrupo.hasta} onChange={(e) => setNuevoGrupo({ ...nuevoGrupo, hasta: e.target.value })} /></label>
                    <button type="button" className="btn sm primary" disabled={!nuevoGrupo.grupo} onClick={agregarGrupo}>+ Agregar</button>
                  </div>
                )}
              </div>
            )}

            {tab === "permisos" && (
              <div className="ue-body">
                <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>Permisos puntuales sobre una pantalla, directos al usuario (además de sus roles/grupos), con vigencia opcional.</p>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
                  {(accesos?.permisosDirectos || []).map((p: any) => (
                    <div key={p.ruta} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5 }}>
                      <span>{labelRuta(p.ruta)}</span><span className="pill">{p.nivel}</span>
                      <span className="muted">{p.desde || p.hasta ? `${p.desde || "—"} → ${p.hasta || "sin fin"}` : ""}</span>
                      <span style={{ flex: 1 }} />
                      {!soloLectura && <button type="button" className="btn sm" style={{ color: "var(--crit)" }} onClick={() => quitarPermisoDir(p.ruta)}>Quitar</button>}
                    </div>
                  ))}
                  {(!accesos?.permisosDirectos || accesos.permisosDirectos.length === 0) && <span className="muted" style={{ fontSize: 12 }}>Sin permisos directos.</span>}
                </div>
                {!soloLectura && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "end" }}>
                    <label style={{ flex: 1, minWidth: 150 }}><span className="ue-lbl">Pantalla</span>
                      <select value={nuevoPerm.ruta} onChange={(e) => setNuevoPerm({ ...nuevoPerm, ruta: e.target.value })}>
                        <option value="">— elegir —</option>
                        {PANTALLAS.map((p) => <option key={p.ruta} value={p.ruta}>{p.modulo} · {p.label}</option>)}
                      </select></label>
                    <label><span className="ue-lbl">Nivel</span>
                      <select value={nuevoPerm.nivel} onChange={(e) => setNuevoPerm({ ...nuevoPerm, nivel: e.target.value })}>
                        {NIV.map((n) => <option key={n} value={n}>{n}</option>)}
                      </select></label>
                    <label><span className="ue-lbl">Desde</span><input type="date" value={nuevoPerm.desde} onChange={(e) => setNuevoPerm({ ...nuevoPerm, desde: e.target.value })} /></label>
                    <label><span className="ue-lbl">Hasta</span><input type="date" value={nuevoPerm.hasta} onChange={(e) => setNuevoPerm({ ...nuevoPerm, hasta: e.target.value })} /></label>
                    <button type="button" className="btn sm primary" disabled={!nuevoPerm.ruta} onClick={agregarPermisoDir}>+ Agregar</button>
                  </div>
                )}
              </div>
            )}

            {tab === "efectivo" && (
              <div className="ue-body">
                <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>Lo que este usuario <b>puede ver/hacer hoy</b>, resultado de unir roles + grupos + permisos directos (vigentes).</p>
                {accesos?.sinRestricciones
                  ? <div className="pill ok">Sin restricciones — ve todo el sistema (rol ADMG o sin RBAC configurado).</div>
                  : (
                    <div style={{ maxHeight: 280, overflow: "auto", fontSize: 12.5 }}>
                      {Object.entries(accesos?.accesoEfectivo || {}).map(([ruta, niv]: any) => (
                        <div key={ruta} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
                          <span>{labelRuta(ruta)} <span className="muted" style={{ fontSize: 11 }}>{ruta}</span></span><span className="pill ok">{niv}</span>
                        </div>
                      ))}
                      {Object.keys(accesos?.accesoEfectivo || {}).length === 0 && <span className="muted">Sin acceso a ninguna pantalla.</span>}
                    </div>
                  )}
              </div>
            )}

            {tab === "datos" && (
              <div className="ue-body">
                <label className="ue-f">Nombre<input value={form.nombre} onChange={(e) => set("nombre", e.target.value)} /></label>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button type="button" className="btn sm" onClick={() => reset(form)}>Restablecer clave</button>
                  <button type="button" className="btn sm primary" onClick={async () => { try { await api.editarUsuario(form.id, { nombre: form.nombre }); cargar(); avisar("Guardado."); } catch (e: any) { avisar({ tipo: "error", mensaje: e.message }); } }}>Guardar nombre</button>
                </div>
              </div>
            )}

            {error && <div className="alert crit">{error}</div>}
            <div style={{ display: "flex", gap: 8, marginTop: 10, justifyContent: "flex-end", borderTop: "1px solid var(--border)", paddingTop: 10 }}>
              <button type="button" className="btn primary" onClick={() => { setForm(null); cargar(); }}>Cerrar</button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .abmu-ov { position:fixed; inset:0; background:rgba(0,0,0,.5); display:flex; align-items:center; justify-content:center; z-index:1000; }
        .abmu-modal { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px 20px; width:min(420px,92vw); display:flex; flex-direction:column; gap:6px; }
        .abmu-modal label { display:flex; flex-direction:column; gap:3px; font-size:.85rem; color:var(--ink-soft); }
        .abmu-modal.ue { width:min(560px,94vw); }
        .ue-tabs { display:flex; gap:2px; border-bottom:1px solid var(--border); margin-bottom:12px; flex-wrap:wrap; }
        .ue-tab { border:none; background:transparent; padding:7px 12px; cursor:pointer; font-size:.85rem; color:var(--ink-soft); border-bottom:2px solid transparent; }
        .ue-tab.on { color:var(--ink); border-bottom-color:var(--brand-2); font-weight:600; }
        .ue-body { min-height:120px; }
        .ue-body label { display:flex; flex-direction:column; gap:3px; }
        .ue-lbl { font-size:.72rem; color:var(--ink-soft); }
        .ue-f { display:flex; flex-direction:column; gap:3px; font-size:.85rem; color:var(--ink-soft); }
      `}</style>
    </div>
  );
}
