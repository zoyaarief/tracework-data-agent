import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://tracework-data-agent.zoya-arief.chatgpt.site'),
  title: 'Tracework — Data Investigation Agent',
  description: 'Ask natural-language business questions and follow every answer back to its data evidence.',
  openGraph: {
    title: 'Tracework — Data Investigation Agent',
    description: 'Ask the data. Follow the evidence.',
    images: [{ url: '/og.png', width: 1734, height: 907, alt: 'Tracework data investigation flow' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Tracework — Data Investigation Agent',
    description: 'Ask the data. Follow the evidence.',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
