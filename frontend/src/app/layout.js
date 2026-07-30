import "./globals.css";

export const metadata = {
  title: "Sales AI Agent — IKSATECH",
  description: "Agent IA Commercial Intelligent de prospection et de vente",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="fr"
      className="h-full antialiased"
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
