import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CCM Console | Evidence Operations",
  description: "Tenant-scoped Continuous Control Monitoring executive console preview."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
