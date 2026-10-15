import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpenRelief | Emergency Command",
  description: "Real-time emergency triage and responder dispatch dashboard.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
