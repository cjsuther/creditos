import { useEffect, useMemo, useState } from "react";
import { api } from "../../api";
import { avisar } from "../../ui/dialog";

const money = (n: any) => "$" + Number(n || 0).toLocaleString("es-AR", { maximumFractionDigits: 0 });
const ESTADO_CLR: Record<string, string> = {
  ACTIVO: "var(--dv-green)", A_LIQUIDAR: "var(--dv-amber)", EN_MORA: "var(--dv-orange)", CERRADO: "var(--dv-slate)",
  REFINANCIADO: "var(--dv-blue)", ANULADO: "var(--dv-red)", CANCELADO: "var(--dv-slate)", CASTIGADO: "var(--dv-red)",
};
const DIMS = [
  { key: "estado", label: "Estado" },
  { key: "sistema", label: "Sistema" },
  { key: "producto", label: "Línea / producto" },
  { key: "saldoRango", label: "Rango de saldo" },
] as const;
type DimKey = typeof DIMS[number]["key"];

const RANGOS: [string, (v: number) => boolean][] = [
  ["$0", (v) => v <= 0],
  ["$0–500k", (v) => v > 0 && v <= 500_000],
  ["$500k–1M", (v) => v > 500_000 && v <= 1_000_000],
  ["$1M–2M", (v) => v > 1_000_000 && v <= 2_000_000],
  ["> $2M", (v) => v > 2_000_000],
];

function claveDim(c: any, dim: DimKey): string {
  if (dim === "estado") return c.estado;
  if (dim === "sistema") return c.sistema;
  if (dim === "producto") return c.snapshot?.producto || c.producto_id || "—";
  const s = Number(c.saldo_capital || 0);
  return (RANGOS.find(([, f]) => f(s)) || ["—", () => false])[0];
}

export default function TableroCartera() {
  const [tablero, setTablero] = useState<any>(null);
  const [contratos, setContratos] = useState<any[]>([]);
  const [dim, setDim] = useState<DimKey>("estado");
  const [err, setErr] = useState("");
  const [cargando, setCargando] = useState(true);

  const cargar = async () => {
    setErr(""); setCargando(true);
    try {
      const [tb, cs] = await Promise.all([api.ctoTablero(), api.ctoListar()]);
      setTablero(tb); setContratos(cs.items);
    } catch (e: any) { setErr(e.message || String(e)); }
    finally { setCargando(false); }
  };
  useEffect(() => { cargar(); }, []);

  // Agrupación por la dimensión elegida (contratos, capital colocado, saldo vigente).
  const grupos = useMemo(() => {
    const m = new Map<string, { n: number; capital: number; saldo: number }>();
    for (const c of contratos) {
      const k = claveDim(c, dim);
      const g = m.get(k) || { n: 0, capital: 0, saldo: 0 };
      g.n += 1;
      g.capital += Number(c.monto_original || 0);
      g.saldo += c.estado === "ACTIVO" ? Number(c.saldo_capital || 0) : 0;
      m.set(k, g);
    }
    const arr = [...m.entries()].map(([k, v]) => ({ k, ...v }));
    arr.sort((a, b) => b.capital - a.capital);
    return arr;
  }, [contratos, dim]);
  const maxCap = Math.max(1, ...grupos.map((g) => g.capital));

  return (
    <div className="tcar">
      <div className="tcar-head">
        <div>
          <h1 style={{ margin: 0 }}>📊 Tablero de cartera</h1>
          <p className="muted" style={{ margin: "2px 0 0" }}>Análisis de los contratos originados en Configurar Créditos.</p>
        </div>
        <span style={{ flex: 1 }} />
        <button className="btn sm" title="Actualizar" onClick={cargar} disabled={cargando}>{cargando ? "…" : "↻ Refrescar"}</button>
        {contratos.length > 0 && <button className="btn sm" onClick={() => api.ctoCarteraExcel().catch((e: any) => avisar({ tipo: "error", mensaje: e.message }))}>⬇ Exportar cartera (Excel)</button>}
      </div>
      {err && <div className="alert crit">{err}</div>}

      {tablero && (
        <div className="tcar-kpis">
          <Kpi label="Contratos" v={tablero.contratos} />
          <Kpi label="Saldo vigente" v={money(tablero.saldoVigente)} hl />
          <Kpi label="Capital colocado" v={money(tablero.capitalColocado)} />
          <Kpi label="Cobrado" v={money(tablero.cobrado)} />
          <Kpi label="Cuotas pagadas" v={`${tablero.cuotasPagadas}/${tablero.cuotasPagadas + tablero.cuotasPendientes}`} />
          <Kpi label="En mora" v={tablero.contratosEnMora} crit={tablero.contratosEnMora > 0} />
        </div>
      )}

      <div className="card tcar-analisis">
        <div className="tcar-analhead">
          <b>Analizar por</b>
          <div className="tcar-tabs">
            {DIMS.map((d) => (
              <button key={d.key} className={"tcar-tab" + (dim === d.key ? " on" : "")} onClick={() => setDim(d.key)}>{d.label}</button>
            ))}
          </div>
        </div>
        <table className="tcar-tbl">
          <thead>
            <tr>
              <th>{DIMS.find((d) => d.key === dim)?.label}</th>
              <th className="n">Contratos</th>
              <th className="n">Capital colocado</th>
              <th className="n">Saldo vigente</th>
              <th style={{ width: "34%" }}>Participación (capital)</th>
            </tr>
          </thead>
          <tbody>
            {grupos.length === 0 && <tr><td colSpan={5} style={{ textAlign: "center", opacity: .6, padding: 20 }}>Sin contratos.</td></tr>}
            {grupos.map((g) => (
              <tr key={g.k}>
                <td><span className="tcar-dot" style={{ background: ESTADO_CLR[g.k] || "var(--dv-slate)" }} />{g.k}</td>
                <td className="n">{g.n}</td>
                <td className="n">{money(g.capital)}</td>
                <td className="n">{money(g.saldo)}</td>
                <td>
                  <div className="tcar-bar"><div className="tcar-bar-fill" style={{ width: `${(g.capital / maxCap) * 100}%`, background: ESTADO_CLR[g.k] || "var(--dv-blue)" }} /></div>
                  <small className="muted">{((g.capital / (tablero?.capitalColocado || maxCap)) * 100).toFixed(1)}%</small>
                </td>
              </tr>
            ))}
          </tbody>
          {grupos.length > 0 && (
            <tfoot>
              <tr>
                <td><b>Total</b></td>
                <td className="n"><b>{grupos.reduce((a, g) => a + g.n, 0)}</b></td>
                <td className="n"><b>{money(grupos.reduce((a, g) => a + g.capital, 0))}</b></td>
                <td className="n"><b>{money(grupos.reduce((a, g) => a + g.saldo, 0))}</b></td>
                <td />
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      <style>{`
        .tcar-head{display:flex;align-items:center;gap:10px;margin-bottom:14px}
        .tcar-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
        .tcar-kpi{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:4px}
        .tcar-kpi.hl{border-color:var(--brand-2);box-shadow:0 0 0 1px var(--brand-2) inset}
        .tcar-kpi small{font-size:.7rem;text-transform:uppercase;letter-spacing:.4px;color:var(--ink-soft)}
        .tcar-kpi b{font-size:1.3rem;font-variant-numeric:tabular-nums;color:var(--ink)}
        .tcar-kpi b.crit{color:var(--crit)}
        .tcar-analisis{padding:14px 16px}
        .tcar-analhead{display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}
        .tcar-tabs{display:flex;gap:6px;flex-wrap:wrap}
        .tcar-tab{padding:5px 12px;border:1px solid var(--border);background:var(--surface);color:var(--ink-soft);border-radius:999px;font:inherit;font-size:12.5px;cursor:pointer}
        .tcar-tab.on{background:var(--brand-2);border-color:var(--brand-2);color:#fff;font-weight:600}
        .tcar-tbl{width:100%;border-collapse:collapse;font-size:.86rem;color:var(--ink)}
        .tcar-tbl th,.tcar-tbl td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left}
        .tcar-tbl th{font-size:.72rem;text-transform:uppercase;letter-spacing:.3px;color:var(--ink-soft)}
        .tcar-tbl .n{text-align:right;font-variant-numeric:tabular-nums}
        .tcar-tbl tfoot td{border-top:2px solid var(--border);border-bottom:none}
        .tcar-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:8px;vertical-align:middle}
        .tcar-bar{height:8px;border-radius:999px;background:var(--surface-2);overflow:hidden}
        .tcar-bar-fill{height:100%;border-radius:999px;transition:width .3s}
      `}</style>
    </div>
  );
}

function Kpi({ label, v, hl, crit }: { label: string; v: any; hl?: boolean; crit?: boolean }) {
  return (
    <div className={"tcar-kpi" + (hl ? " hl" : "")}>
      <small>{label}</small>
      <b className={crit ? "crit" : ""}>{v}</b>
    </div>
  );
}
