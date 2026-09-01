import type { Metadata } from "next";
import "./globals.css";

// The description below is the canonical one-liner from docs/ABOUT.md, gated by
// tests/test_core.py::test_about_copy_is_single_sourced. Edit it there, not here.
export const metadata: Metadata = {
  title: "ENSO Macro Risk Desk",
  description:
    "When the ENSO cycle shifts, which commodity and sector exposures to reposition, and which of those links are causally real rather than spurious.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
