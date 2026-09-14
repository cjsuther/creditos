import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { useNivelActual } from "../../permisos";
import { confirmar, avisar, pedirTexto } from "../../ui/dialog";

const money = (n: number) => "$" + (n || 0).toLocaleString("es-AR", { maximumFractionDigits: 0 });
const ESTADO_CLASS: Record<string, string> = {
  BORRADOR: "", EN_EVALUACION: "warn", APROBADA: "ok", RECHAZADA: "crit", ORIGINADA: "brand", ANULADA: "",
};
const RELACIONES = ["ESTANDAR", "PREFERENCIAL", "PREMIUM"];
const TIPODOC: Record<string, string> = { DNI_FRENTE: "DNI (frente)", DNI_DORSO: "DNI (dorso)", RECIBO: "Recibo de sueldo", OTRO: "Otro" };
const DESTINO: Record<string, string> = {
  VIVIENDA: "Vivienda / refacción", VEHICULO: "Vehículo", CONSUMO: "Consumo / gastos personales",
  EDUCACION: "Educación", SALUD: "Salud", REFINANCIACION: "Refinanciación de deudas",
  EMPRENDIMIENTO: "Emprendimiento / negocio", OTRO: "Otro",
};
const kb = (n: number) => (n >= 1048576 ? (n / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(n / 1024)) + " KB");

export default function SolicitudesCredito() {
  const [items, setItems] = useState<any[]>([]);
  const [estados, setEstados] = useState<string[]>([]);
  const [permisos, setPermisos] = useState({ edita: false, aprueba: false });
  const { soloLectura } = useNivelActual();
  const [filtro, setFiltro] = useState("");
  const [q, setQ] = useState("");
  const [nueva, setNueva] = useState(false);
  const [paso, setPaso] = useState(1);          // wizard: 1 Solicitante · 2 Simulación · 3 Confirmación
  const [sim, setSim] = useState<any>(null);
  const [simulando, setSimulando] = useState(false);
  const [altaSol, setAltaSol] = useState<any>(null);   // solicitud en alta al maestro (modal de revisión)
  const [alta, setAlta] = useState({ apellido_nombre: "", dni: "", cuil: "" });
  const [altaErr, setAltaErr] = useState("");
  // Cliente de la solicitud: se ELIGE del maestro con un buscador (igual que Originar); no se carga a mano.
  const [cliQ, setCliQ] = useState("");
  const [clis, setClis] = useState<any[]>([]);
  const [buscandoCli, setBuscandoCli] = useState(false);
  const [cliSel, setCliSel] = useState<any>(null);
  const [sel, setSel] = useState<any>(null);
  const [docs, setDocs] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const [lineas, setLineas] = useState<any[]>([]);
  const [cat, setCat] = useState<{ segmentos: string[]; canales: string[] }>({ segmentos: [], canales: [] });

  const [form, setForm] = useState<any>({
    solicitante_tipo: "REGISTRADO", cliente_id: 0,
    cliente_datos: { apellido_nombre: "", cuil: "", dni: "" },
    producto_id: "", monto_solicitado: 1000000, plazo_solicitado: 24,
    segmento: "", canal: "SUCURSAL", edad: "", antiguedad_meses: "", relacion: "ESTANDAR",
    datos_adicionales: { destino: "", cbu: "", observaciones: "" },
  });

  const cargar = () => api.ppSolicitudes({ estado: filtro, q }).then((d) => {
    setItems(d.items); setEstados(d.estados); setPermisos(d.permisos);
  }).catch((e) => setErr(String(e)));
  useEffect(() => { cargar(); }, [filtro, q]);
  // Documentación que adjuntó el solicitante (la sube el ciudadano desde el portal).
  useEffect(() => {
    if (sel?.id) api.ppSolicitudDocs(sel.id).then((d: any) => setDocs(d.items)).catch(() => setDocs([]));
    else setDocs([]);
  }, [sel?.id]);
  useEffect(() => {
    api.ppOferta().then((d) => { setLineas(d.items); if (d.items[0]) setForm((f: any) => ({ ...f, producto_id: f.producto_id || d.items[0].id })); }).catch(() => {});
    api.ctoSegmentos().then(setCat).catch(() => {});
  }, []);

  // Buscador de clientes (typeahead) del wizard: el cliente se elige del maestro, no se carga a mano.
  useEffect(() => {
    const qq = cliQ.trim();
    if (form.cliente_id || qq.length < 2) { setClis([]); return; }
    let vivo = true; setBuscandoCli(true);
    const t = setTimeout(async () => {
      try { const r = await api.clientes({ q: qq, limit: 8 }); if (vivo) setClis(r.items); }
      catch { if (vivo) setClis([]); }
      finally { if (vivo) setBuscandoCli(false); }
    }, 300);
    return () => { vivo = false; clearTimeout(t); };
  }, [cliQ, form.cliente_id]);
  const elegirCliente = (c: any) => { setForm((f: any) => ({ ...f, solicitante_tipo: "REGISTRADO", cliente_id: c.id })); setCliSel(c); setCliQ(""); setClis([]); };
  const cambiarCliente = () => { setForm((f: any) => ({ ...f, cliente_id: "" })); setCliSel(null); setCliQ(""); setClis([]); };

  const abrirNueva = () => { setNueva(true); setSel(null); setPaso(1); setSim(null); setErr(""); setCliSel(null); setCliQ(""); setClis([]); setForm((f: any) => ({ ...f, cliente_id: "" })); };
  const cerrarNueva = () => { setNueva(false); setPaso(1); setSim(null); };

  const paso1OK = !!form.cliente_id;   // la solicitud es para un cliente REGISTRADO (elegido del maestro)
  const paso2OK = !!form.producto_id && Number(form.monto_solicitado) > 0 && Number(form.plazo_solicitado) > 0;

  const simular = async () => {
    if (!paso2OK) return;
    setSimulando(true); setErr("");
    try {
      setSim(await api.ppSimPreview(form.producto_id, {
        monto: Number(form.monto_solicitado), plazo: Number(form.plazo_solicitado),
        segmento: form.segmento || undefined, canal: form.canal || undefined,
        edad: form.edad ? Number(form.edad) : undefined,
        antiguedad_meses: form.antiguedad_meses ? Number(form.antiguedad_meses) : undefined,
      }));
    } catch (e: any) { setSim(null); setErr(e.message || String(e)); }
    finally { setSimulando(false); }
  };

  const crear = async () => {
    setErr("");
    try {
      const payload = {
        ...form,
        cliente_id: form.solicitante_tipo === "REGISTRADO" ? Number(form.cliente_id) || null : null,
        edad: form.edad ? Number(form.edad) : null,
        antiguedad_meses: form.antiguedad_meses ? Number(form.antiguedad_meses) : null,
      };
      const s = await api.ppSolicitudCrear(payload);
      cerrarNueva(); setSel(s); cargar();
    } catch (e: any) { setErr(e.message || String(e)); }
  };

  const accion = async (s: any, acc: string) => {
    let motivo = "";
    if (acc === "rechazar" || acc === "anular") { motivo = (await pedirTexto({ titulo: acc === "rechazar" ? "Rechazar solicitud" : "Anular solicitud", mensaje: `Motivo de ${acc}:`, requerido: acc === "rechazar" })) || ""; if (acc === "rechazar" && !motivo) return; }
    try { const r = await api.ppSolicitudEstado(s.id, acc, motivo); setSel(r); cargar(); }
    catch (e: any) { avisar({ tipo: "error", mensaje: e.message || String(e) }); }
  };
  // Alta en el maestro = mini-revisión: precarga nombre/DNI declarados y el asesor completa el CUIL (H-137).
  const abrirAlta = (s: any) => {
    const cd = s.clienteDatos || {};
    setAlta({ apellido_nombre: cd.apellido_nombre || s.clienteNombre || "", dni: cd.dni || "", cuil: cd.cuil || "" });
    setAltaSol(s); setAltaErr("");
  };
  const cuilDigits = (alta.cuil || "").replace(/\D/g, "");
  const altaOK = !!alta.apellido_nombre.trim() && (cuilDigits.length === 0 || cuilDigits.length === 11);
  const confirmarAlta = async () => {
    if (!altaSol) return;
    setAltaErr("");
    try {
      const r = await api.ppSolicitudPromover(altaSol.id, { apellido_nombre: alta.apellido_nombre.trim(), dni: alta.dni, cuil: cuilDigits });
      setAltaSol(null); setSel(r.solicitud); cargar();
      avisar(r.yaExistia ? "Cliente ya existía en el maestro; vinculado." : "Cliente dado de alta en el maestro.");
    } catch (e: any) { setAltaErr(e.message || String(e)); }
  };
  const originar = async (s: any) => {
    // La solicitud ya trae los datos (los ves en el panel de revisión): originar es revisar y confirmar.
    // El contrato queda A_LIQUIDAR y el desembolso pasa por la liquidación por lote (H-135).
    if (!(await confirmar({ titulo: "Originar contrato", confirmar: "Originar", mensaje: `Originar el contrato de ${s.clienteNombre} por ${money(s.monto)} a ${s.plazo} cuotas.\n\nQueda A LIQUIDAR (el desembolso se hace por lote). ¿Confirmás?` }))) return;
    try {
      const c = await api.ctoOriginar({
        producto_id: s.productoId, cliente_nombre: s.clienteNombre, monto: s.monto, plazo: s.plazo,
        segmento: s.segmento || undefined, canal: s.canal || undefined,
        edad: s.edad ?? undefined, antiguedad_meses: s.antiguedadMeses ?? undefined,
        relacion: s.relacion || undefined, solicitud_pp_id: s.id,
        datos_adicionales: { destino: s.datosAdicionales?.destino || "", cbu: s.datosAdicionales?.cbu || "" },
        desembolsar: false,
      });
      cargar();
      const rec = await api.ppSolicitudes({ estado: filtro, q }).then((d) => d.items.find((x: any) => x.id === s.id)).catch(() => null);
      setSel(rec || null);
      avisar(`Contrato originado: ${c.numeroContrato || c.numero_contrato || ""} · quedó A LIQUIDAR para el desembolso por lote.`);
    } catch (e: any) { avisar({ tipo: "error", mensaje: e.message || String(e) }); }
  };

  const acciones = (s: any) => {
    const a: { l: string; acc: string; can: boolean }[] = [];
    if (s.estado === "BORRADOR") a.push({ l: "Enviar a evaluación", acc: "enviar", can: (permisos.edita && !soloLectura) });
    if (s.estado === "EN_EVALUACION") { a.push({ l: "Aprobar", acc: "aprobar", can: (permisos.aprueba && !soloLectura) }); a.push({ l: "Rechazar", acc: "rechazar", can: (permisos.aprueba && !soloLectura) }); }
    if (!["ORIGINADA", "ANULADA"].includes(s.estado)) a.push({ l: "Anular", acc: "anular", can: (permisos.edita && !soloLectura) });
    return a;
  };

  const filtrados = useMemo(() => items, [items]);

  return (
    <div className="sol cfgc">
      <div className="sol-head">
        <div>
          <h1>Solicitudes de crédito</h1>
          <p className="muted">Carga y evaluación de solicitudes de la línea nueva. Cliente registrado o alta express. Una solicitud aprobada se puede originar como contrato.</p>
        </div>
        {(permisos.edita && !soloLectura) && <button className="btn primary" onClick={abrirNueva}>+ Nueva solicitud</button>}
      </div>

      <div className="sol-filtros">
        <button className={filtro === "" ? "on" : ""} onClick={() => setFiltro("")}>Todas</button>
        {estados.map((e) => <button key={e} className={filtro === e ? "on" : ""} onClick={() => setFiltro(e)}>{e}</button>)}
        <input placeholder="Buscar cliente o N°…" value={q} onChange={(e) => setQ(e.target.value)} style={{ marginLeft: "auto" }} />
      </div>

      {err && <div className="cfgc-err" style={{ margin: "8px 0" }}>{err}</div>}

      {nueva && (
        <div className="sol-modal-scrim" onClick={cerrarNueva}>
          <div className="sol-modal" onClick={(e) => e.stopPropagation()}>
            <div className="sol-modal-head">
              <h3>Nueva solicitud</h3>
              <button className="sol-modal-x" onClick={cerrarNueva} title="Cerrar">✕</button>
            </div>
            <ol className="sol-steps">
              {["Solicitante", "Simulación", "Confirmación"].map((t, i) => {
                const n = i + 1;
                return <li key={t} className={`sol-step ${paso === n ? "on" : paso > n ? "done" : ""}`}>
                  <span className="sol-step-n">{paso > n ? "✓" : n}</span>{t}</li>;
              })}
            </ol>
            <div className="sol-modal-body">
              {err && <div className="cfgc-err" style={{ marginBottom: 10 }}>{err}</div>}

              {paso === 1 && (
                <>
                  {!form.cliente_id ? (
                    <div style={{ background: "var(--surface-2)", borderRadius: 11, padding: 12, marginBottom: 12 }}>
                      <b style={{ fontSize: 13 }}>🔎 Buscar cliente <span className="req">*</span></b>
                      <span className="muted" style={{ fontSize: 11.5 }}> · elegí un cliente del maestro (el alta está en Clientes → Maestro)</span>
                      <input style={{ width: "100%", marginTop: 8 }} value={cliQ} placeholder="Buscar por apellido y nombre, CUIL o DNI…" onChange={(e) => setCliQ(e.target.value)} />
                      {buscandoCli && <div className="hint" style={{ marginTop: 6 }}>Buscando…</div>}
                      {clis.length > 0 && (
                        <div style={{ marginTop: 8, maxHeight: 200, overflowY: "auto", display: "flex", flexDirection: "column", gap: 4 }}>
                          {clis.map((c) => (
                            <button type="button" key={c.id} className="btn" style={{ justifyContent: "flex-start", textAlign: "left", fontWeight: 400 }} onClick={() => elegirCliente(c)}>
                              <b>{c.apellido_nombre}</b>&nbsp;— CUIL {c.cuil || "—"} · DNI {c.dni || "—"}
                            </button>
                          ))}
                        </div>
                      )}
                      {cliQ.trim().length >= 2 && !buscandoCli && clis.length === 0 && (
                        <div className="hint" style={{ marginTop: 6 }}>Sin resultados. Si es un cliente nuevo, dalo de alta en <a href="/clientes/maestro">Clientes → Maestro</a>.</div>
                      )}
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: 12, background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 11, padding: "12px 14px", marginBottom: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div className="eyebrow">Cliente</div>
                        <b style={{ fontSize: 15 }}>{cliSel?.apellido_nombre}</b>
                        <div className="muted" style={{ fontSize: 12 }}>CUIL {cliSel?.cuil || "—"} · DNI {cliSel?.dni || "—"}</div>
                      </div>
                      <button type="button" className="btn" onClick={cambiarCliente}>Cambiar cliente</button>
                    </div>
                  )}
                  <div className="sol-grid">
                  <label>Segmento
                    <select value={form.segmento} onChange={(e) => setForm({ ...form, segmento: e.target.value })}>
                      <option value="">(cualquiera)</option>
                      {cat.segmentos.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label>Canal
                    <select value={form.canal} onChange={(e) => setForm({ ...form, canal: e.target.value })}>
                      {cat.canales.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label>Edad<input type="number" value={form.edad} onChange={(e) => setForm({ ...form, edad: e.target.value })} /></label>
                  <label>Antigüedad (meses)<input type="number" value={form.antiguedad_meses} onChange={(e) => setForm({ ...form, antiguedad_meses: e.target.value })} /></label>
                  <label>Relación
                    <select value={form.relacion} onChange={(e) => setForm({ ...form, relacion: e.target.value })}>
                      {RELACIONES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  </label>
                  </div>
                </>
              )}

              {paso === 2 && (
                <>
                  <div className="sol-grid">
                    <label>Línea <span className="req">*</span>
                      <select value={form.producto_id} onChange={(e) => { setForm({ ...form, producto_id: e.target.value }); setSim(null); }}>
                        {lineas.map((l) => <option key={l.id} value={l.id}>{l.nombre} ({l.codigo})</option>)}
                      </select>
                    </label>
                    <label>Monto <span className="req">*</span><input type="number" min="1" value={form.monto_solicitado} onChange={(e) => { setForm({ ...form, monto_solicitado: Number(e.target.value) }); setSim(null); }} /></label>
                    <label>Plazo (cuotas) <span className="req">*</span><input type="number" min="1" value={form.plazo_solicitado} onChange={(e) => { setForm({ ...form, plazo_solicitado: Number(e.target.value) }); setSim(null); }} /></label>
                  </div>
                  <div style={{ marginTop: 10 }}>
                    <button className="btn" onClick={simular} disabled={!paso2OK || simulando}>{simulando ? "Simulando…" : "↻ Simular"}</button>
                  </div>
                  {sim && (
                    <div className="sol-sim">
                      <div className="sol-sim-kpis">
                        <div><small>Cuota promedio</small><b>{money(sim.cuotaPromedio)}</b></div>
                        <div><small>Total a pagar</small><b>{money(sim.totalCuotas)}</b></div>
                        <div><small>Cuotas</small><b>{sim.cantidadCuotas}</b></div>
                        <div><small>TNA</small><b>{sim.tna}%</b></div>
                      </div>
                      {sim.elegible === false
                        ? <p className="cfgc-err" style={{ marginTop: 8 }}>No elegible: {sim.motivos.join(" · ")} (podés registrarla igual; un asesor revisa).</p>
                        : <p className="muted" style={{ marginTop: 8 }}>✓ Elegible con estos datos.</p>}
                    </div>
                  )}
                </>
              )}

              {paso === 3 && (
                <>
                  <div className="sol-resumen">
                    <div><span>Cliente</span>{cliSel?.apellido_nombre || "—"}</div>
                    <div><span>Línea</span>{lineas.find((l) => l.id === form.producto_id)?.nombre || "—"}</div>
                    <div><span>Monto</span>{money(Number(form.monto_solicitado))}</div>
                    <div><span>Plazo</span>{form.plazo_solicitado} cuotas</div>
                    {sim && <div><span>Cuota estimada</span>{money(sim.cuotaPromedio)}</div>}
                    {sim && <div><span>Elegible</span>{sim.elegible === false ? "No (revisar)" : "Sí"}</div>}
                  </div>
                  <div className="sol-grid" style={{ marginTop: 12 }}>
                    <label>Destino
                      <select value={form.datos_adicionales.destino} onChange={(e) => setForm({ ...form, datos_adicionales: { ...form.datos_adicionales, destino: e.target.value } })}>
                        <option value="">(sin especificar)</option>
                        {Object.entries(DESTINO).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                      </select>
                    </label>
                    <label>Relación
                      <select value={form.relacion} onChange={(e) => setForm({ ...form, relacion: e.target.value })}>
                        {RELACIONES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </label>
                  </div>
                  <label style={{ display: "block", marginTop: 10 }}>Observaciones
                    <textarea value={form.datos_adicionales.observaciones} rows={2} style={{ width: "100%" }}
                      onChange={(e) => setForm({ ...form, datos_adicionales: { ...form.datos_adicionales, observaciones: e.target.value } })} />
                  </label>
                </>
              )}
            </div>

            <div className="sol-modal-foot">
              <button className="btn" onClick={cerrarNueva}>Cancelar</button>
              <div style={{ flex: 1 }} />
              {paso > 1 && <button className="btn" onClick={() => setPaso(paso - 1)}>← Volver</button>}
              {paso === 1 && <button className="btn primary" disabled={!paso1OK} onClick={() => { setPaso(2); if (!sim) simular(); }}>Continuar →</button>}
              {paso === 2 && <button className="btn primary" disabled={!paso2OK} onClick={() => setPaso(3)}>Continuar →</button>}
              {paso === 3 && <button className="btn primary" onClick={crear}>Crear (queda en borrador)</button>}
            </div>
          </div>
        </div>
      )}

      <table className="sol-table">
        <thead><tr><th>N°</th><th>Cliente</th><th>Monto</th><th>Plazo</th><th>Cuota est.</th><th>Estado</th><th>Elegible</th><th></th></tr></thead>
        <tbody>
          {filtrados.map((s) => (
            <tr key={s.id} className={sel?.id === s.id ? "on" : ""} onClick={() => { setSel(s); setNueva(false); }}>
              <td><b>{s.numero}</b></td>
              <td>{s.clienteNombre}{s.solicitanteTipo === "NO_REGISTRADO" && <span className="pill" style={{ marginLeft: 6, fontSize: 9 }}>express</span>}</td>
              <td className="num">{money(s.monto)}</td>
              <td className="num">{s.plazo}</td>
              <td className="num">{money(s.evaluacion?.cuota_estimada || 0)}</td>
              <td><span className={"pill " + (ESTADO_CLASS[s.estado] || "")}>{s.estado}</span></td>
              <td>{s.evaluacion?.elegible ? "✓" : "✕"}</td>
              <td>{s.estado === "APROBADA" && <span className="pill ok" style={{ fontSize: 9 }}>lista p/ originar</span>}</td>
            </tr>
          ))}
          {filtrados.length === 0 && <tr><td colSpan={8} className="muted" style={{ textAlign: "center", padding: 20 }}>Sin solicitudes.</td></tr>}
        </tbody>
      </table>

      {sel && (
        <div className="sol-detalle">
          <h3>{sel.numero} · {sel.clienteNombre} <span className={"pill " + (ESTADO_CLASS[sel.estado] || "")}>{sel.estado}</span></h3>
          <div className="sol-grid">
            <div><small>Línea</small><b>{lineas.find((l) => l.id === sel.productoId)?.nombre || sel.productoId}</b></div>
            <div><small>Monto</small><b>{money(sel.monto)}</b></div>
            <div><small>Plazo</small><b>{sel.plazo} cuotas</b></div>
            <div><small>TNA ofrecida</small><b>{sel.evaluacion?.tna_ofrecida ?? "—"}%</b></div>
            <div><small>Cuota estimada</small><b>{money(sel.evaluacion?.cuota_estimada || 0)}</b></div>
            <div><small>Relación</small><b>{sel.relacion}</b></div>
            {sel.datosAdicionales?.destino && <div><small>Destino</small><b>{DESTINO[sel.datosAdicionales.destino] || sel.datosAdicionales.destino}</b></div>}
          </div>
          {sel.datosAdicionales?.sueldo_declarado && (
            <p className="muted" style={{ marginTop: 6 }}>
              Sueldo {sel.datosAdicionales.haberes_fuente === "micatamarca" ? "verificado" : "declarado"}: {money(sel.datosAdicionales.sueldo_declarado)}
              {sel.datosAdicionales.afectacion != null && <> · afectación {sel.datosAdicionales.afectacion}%</>}
              {sel.datosAdicionales.haberes_fuente === "micatamarca" && <span className="pill ok" style={{ marginLeft: 8 }}>✓ Mi Catamarca</span>}
            </p>
          )}
          {sel.evaluacion?.motivos?.length > 0 && (
            <p className="cfgc-err" style={{ marginTop: 8 }}>No elegible: {sel.evaluacion.motivos.join(" · ")}</p>
          )}
          {sel.motivoRechazo && <p className="muted">Motivo: {sel.motivoRechazo}</p>}
          {docs.length > 0 && (
            <div className="sol-docs">
              <small>Documentación del solicitante</small>
              {docs.map((d) => (
                <div className="sol-doc" key={d.id}>
                  <span className="pill">{TIPODOC[d.tipo] || d.tipo}</span>
                  <button className="sol-doc-link" onClick={() => api.ppSolicitudDocAbrir(sel.id, d.id)}>{d.nombre}</button>
                  <span className="muted" style={{ fontSize: 12 }}>{kb(d.tamano)}</span>
                </div>
              ))}
            </div>
          )}
          {sel.datosLiquidacion?.aplica && (
            <div className="sol-revli">
              <small>Revisión para liquidar {sel.datosLiquidacion.lista
                ? <span className="pill ok" style={{ marginLeft: 6 }}>lista</span>
                : <span className="pill warn" style={{ marginLeft: 6 }}>faltan datos</span>}</small>
              <div className="sol-revli-items">
                {sel.datosLiquidacion.items.map((it: any) => (
                  <div className={`sol-revli-item ${it.ok ? "ok" : it.requerido ? "crit" : "warn"}`} key={it.campo}>
                    <span className="sol-revli-ck">{it.ok ? "✓" : it.requerido ? "✕" : "○"}</span>
                    <span className="sol-revli-lbl">{it.label}{!it.requerido && <em> (opcional)</em>}</span>
                    <span className="sol-revli-val">{it.ok ? (it.valor || "—") : (it.requerido ? "falta" : "—")}</span>
                  </div>
                ))}
              </div>
              {!sel.datosLiquidacion.lista && (
                <p className="cfgc-err" style={{ marginTop: 6 }}>No se puede originar: completá {sel.datosLiquidacion.faltantes.join(", ")}.</p>
              )}
            </div>
          )}
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            {acciones(sel).map((a) => (
              <button key={a.acc} className="btn" disabled={!a.can} onClick={() => accion(sel, a.acc)}>{a.l}</button>
            ))}
            {sel.solicitanteTipo === "NO_REGISTRADO" && (permisos.edita && !soloLectura) && <button className="btn" onClick={() => abrirAlta(sel)}>Dar de alta en maestro</button>}
            {sel.estado === "APROBADA" && <button className="btn primary" disabled={sel.datosLiquidacion?.aplica && !sel.datosLiquidacion?.lista}
              title={sel.datosLiquidacion?.aplica && !sel.datosLiquidacion?.lista ? "Faltan datos para liquidar" : ""}
              onClick={() => originar(sel)}>💸 Originar contrato</button>}
            {sel.estado === "ORIGINADA" && sel.contratoId && <span className="pill brand">Originada · contrato {sel.contratoId.slice(0, 8)}</span>}
          </div>
        </div>
      )}

      {altaSol && (
        <div className="sol-modal-scrim" onClick={() => setAltaSol(null)}>
          <div className="sol-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
            <div className="sol-modal-head">
              <h3>Dar de alta en el maestro</h3>
              <button className="sol-modal-x" onClick={() => setAltaSol(null)} title="Cerrar">✕</button>
            </div>
            <div className="sol-modal-body">
              <p className="muted" style={{ marginTop: 0 }}>Revisá los datos del solicitante y completá el CUIL antes de crear el cliente en el maestro.</p>
              {altaErr && <div className="cfgc-err" style={{ marginBottom: 10 }}>{altaErr}</div>}
              <div className="sol-grid">
                <label>Apellido y nombre<input value={alta.apellido_nombre} onChange={(e) => setAlta({ ...alta, apellido_nombre: e.target.value })} /></label>
                <label>DNI<input className="num" value={alta.dni} onChange={(e) => setAlta({ ...alta, dni: e.target.value.replace(/\D/g, "").slice(0, 9) })} /></label>
                <label>CUIL (11 dígitos)
                  <input className="num" inputMode="numeric" value={alta.cuil} onChange={(e) => setAlta({ ...alta, cuil: e.target.value.replace(/\D/g, "").slice(0, 11) })} placeholder="20304050607" />
                  {cuilDigits.length > 0 && cuilDigits.length !== 11 && <span className="hint" style={{ color: "var(--warn)" }}>Faltan {11 - cuilDigits.length} dígito(s).</span>}
                </label>
              </div>
            </div>
            <div className="sol-modal-foot">
              <button className="btn" onClick={() => setAltaSol(null)}>Cancelar</button>
              <div style={{ flex: 1 }} />
              <button className="btn primary" disabled={!altaOK} onClick={confirmarAlta}>Dar de alta</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
