import type { Metadata } from "next";
import { DM_Sans, DM_Mono, Instrument_Serif} from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  weight: ['300', '400', '500'],
})

const dmMono = DM_Mono({
  subsets: ['latin'],
  variable: '--font-dm-mono',
  weight: ['400', '500'],
})

const instrumentSerif = Instrument_Serif({
  subsets: ['latin'],
  variable: '--font-instrument-serif',
  weight: ['400'],
  style: ['normal', 'italic'],
})


export const metadata: Metadata = {
 title: 'RetainIQ- Churn Intelligence',
  description: 'Automated churn analysis and marketing action engine',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${dmSans.variable} ${dmMono.variable} ${instrumentSerif.variable}`}>
      <body className="bg-ink text-mist font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
