import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ENSO Macro Risk Desk",
  description:
    "ENSO Macro Risk Desk — when the ENSO cycle shifts, which commodity & sector exposures to reposition, and which links are causally real vs. spurious.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
