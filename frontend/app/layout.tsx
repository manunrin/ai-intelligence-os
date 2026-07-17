import type { Metadata } from "next";
import { Providers } from "@/lib/providers";

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
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
