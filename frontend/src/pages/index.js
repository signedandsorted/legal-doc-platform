import { useState } from "react";
import axios from "axios";

export default function Home() {
  const [service, setService] = useState("will");
  const [jsonData, setJsonData] = useState("{}\n");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = { service, data: JSON.parse(jsonData) };
      const resp = await axios.post(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/draft/${service}", payload);
      setResult(resp.data);
    } catch (err) {
      setResult({ error: err.response?.data?.detail || err.message });
    }
    setLoading(false);
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "Arial, sans-serif" }}>
      <h1>Legal‑Doc AI Platform</h1>
      <form onSubmit={handleSubmit} style={{ marginBottom: "1rem" }}>
        <label>
          Service:
          <select value={service} onChange={(e) => setService(e.target.value)} style={{ marginLeft: "0.5rem" }}>
            <option value="will">Will</option>
            <option value="poa">Power of Attorney</option>
            <option value="probate">Probate</option>
          </select>
        </label>
        <br />
        <label>
          Client data (JSON):
          <br />
          <textarea
            rows={10}
            cols={60}
            value={jsonData}
            onChange={(e) => setJsonData(e.target.value)}
            style={{ fontFamily: "monospace" }}
          />
        </label>
        <br />
        <button type="submit" disabled={loading} style={{ marginTop: "0.5rem" }}>
          {loading ? "Generating…" : "Create Draft"}
        </button>
      </form>
      {result && (
        <pre style={{ background: "#f0f0f0", padding: "1rem" }}>{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  );
}
