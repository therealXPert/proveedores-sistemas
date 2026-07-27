export default function Home() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Control de Gasto - Sistemas</h1>
      <p>Aplicacion en construccion (Etapa 1: infraestructura y esqueleto).</p>
      <p>API configurada en: {apiUrl}</p>
    </main>
  );
}
