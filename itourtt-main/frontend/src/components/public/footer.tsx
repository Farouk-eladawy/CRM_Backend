'use client';

import Link from 'next/link';
import { Mail, Phone } from 'lucide-react';

export function PublicFooter() {
  return (
    <footer className="bg-[#1a1a2e] text-white/70">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          {/* Column 1: Company */}
          <div>
            <h3 className="text-lg font-semibold text-white">iTour Transfers</h3>
            <p className="mt-3 text-sm leading-relaxed">
              Professional airport transfer and transportation services across Egypt.
              Safe, reliable, and comfortable rides for tourists and business travelers.
            </p>
          </div>

          {/* Column 2: Quick Links */}
          <div>
            <h3 className="text-lg font-semibold text-white">Quick Links</h3>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link href="/" className="hover:text-white transition-colors">
                  Home
                </Link>
              </li>
              <li>
                <Link href="/book" className="hover:text-white transition-colors">
                  Book Now
                </Link>
              </li>
              <li>
                <Link href="/booking/lookup" className="hover:text-white transition-colors">
                  Track Booking
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Contact */}
          <div>
            <h3 className="text-lg font-semibold text-white">Contact Us</h3>
            <ul className="mt-3 space-y-3 text-sm">
              <li className="flex items-center gap-2">
                <Mail className="h-4 w-4 shrink-0 text-blue-400" />
                <a href="mailto:info@itour-tt.com" className="hover:text-white transition-colors">
                  info@itour-tt.com
                </a>
              </li>
              <li className="flex items-center gap-2">
                <Phone className="h-4 w-4 shrink-0 text-blue-400" />
                <a href="tel:+201234567890" className="hover:text-white transition-colors">
                  +20 123 456 7890
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-10 border-t border-white/10 pt-6 text-center text-xs text-white/40">
          &copy; {new Date().getFullYear()} iTour Transport &amp; Traffic. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
