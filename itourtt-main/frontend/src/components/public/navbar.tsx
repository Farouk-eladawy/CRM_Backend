'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

export function PublicNavbar() {
  const [lang, setLang] = useState<'EN' | 'AR'>('EN');
  const [open, setOpen] = useState(false);

  const toggleLang = () => setLang((l) => (l === 'EN' ? 'AR' : 'EN'));

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-white/10 bg-[#1a1a2e] shadow-lg">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Logo + Brand */}
        <Link href="/" className="flex items-center gap-2.5">
          <Image
            src="/favicon.svg"
            alt="iTour"
            width={32}
            height={32}
            className="shrink-0"
          />
          <span className="text-lg font-semibold tracking-tight text-white">
            iTour Transfers
          </span>
        </Link>

        {/* Right: Desktop nav */}
        <div className="hidden items-center gap-3 md:flex">
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleLang}
            className="text-white/80 hover:bg-white/10 hover:text-white"
          >
            {lang}
          </Button>
          <Button asChild size="sm" className="bg-blue-600 hover:bg-blue-700 text-white">
            <Link href="/book">Book Now</Link>
          </Button>
        </div>

        {/* Right: Mobile hamburger */}
        <div className="flex items-center gap-2 md:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="sm" className="text-white hover:bg-white/10">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-64 bg-[#1a1a2e] border-white/10">
              <SheetHeader>
                <SheetTitle className="text-white">Menu</SheetTitle>
              </SheetHeader>
              <div className="mt-6 flex flex-col gap-4 px-2">
                <Link
                  href="/"
                  onClick={() => setOpen(false)}
                  className="text-sm font-medium text-white/80 hover:text-white"
                >
                  Home
                </Link>
                <Link
                  href="/book"
                  onClick={() => setOpen(false)}
                  className="text-sm font-medium text-white/80 hover:text-white"
                >
                  Book Now
                </Link>
                <Link
                  href="/booking/lookup"
                  onClick={() => setOpen(false)}
                  className="text-sm font-medium text-white/80 hover:text-white"
                >
                  Track Booking
                </Link>
                <button
                  onClick={() => {
                    toggleLang();
                  }}
                  className="mt-4 w-full rounded-md border border-white/20 px-3 py-2 text-sm text-white/80 hover:bg-white/10 hover:text-white"
                >
                  Language: {lang}
                </button>
                <Button asChild size="sm" className="mt-2 bg-blue-600 hover:bg-blue-700 text-white">
                  <Link href="/book" onClick={() => setOpen(false)}>
                    Book Now
                  </Link>
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </nav>
  );
}
