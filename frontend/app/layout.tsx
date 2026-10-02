import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "@/components/auth";
import { AppShell } from "@/components/app";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI-Powered IT Helpdesk",
  description: "Enterprise IT helpdesk with AI-assisted triage, RAG knowledge base and analytics.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}