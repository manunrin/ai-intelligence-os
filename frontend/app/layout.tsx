import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Intelligence OS",
  description: "AI Agent Intelligence Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
