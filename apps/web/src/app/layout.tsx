import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata = {
  title: "Control de Gasto — Sistemas",
  description: "Control de presupuesto y facturación del área de Sistemas — Autocity",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
