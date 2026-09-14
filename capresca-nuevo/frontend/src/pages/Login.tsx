import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, setToken } from "../api";
import { invalidarPermisos } from "../permisos";

export default function Login() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const r = await login(username, password);
      setToken(r.access_token);
      invalidarPermisos();        // releer permisos del nuevo usuario (no reusar la caché anterior)
      nav("/simulador");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <div className="login-wrap">
      <div className="card">
        <h2 style={{ marginTop: 0, color: "var(--azul)" }}>Ingreso al Sistema</h2>
        <form onSubmit={submit}>
          <label>Usuario</label>
          <input value={username} onChange={(e) => setUsername(e.target.value)} />
          <label>Contraseña</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          {error && <p className="error">{error}</p>}
          <button type="submit">Ingresar</button>
        </form>
        <p className="muted" style={{ marginTop: "1rem" }}>
          Demo: admin / admin123
        </p>
      </div>
    </div>
  );
}
