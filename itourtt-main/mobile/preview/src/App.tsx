import React, { useState } from 'react';
import { DriverApp } from './apps/DriverApp';
import { RepApp } from './apps/RepApp';
import { SupplierApp } from './apps/SupplierApp';
import { GuestApp } from './apps/GuestApp';

type AppType = 'driver' | 'rep' | 'supplier' | 'guest';

const APP_LABELS: Record<AppType, string> = {
  driver: 'Driver',
  rep: 'Rep',
  supplier: 'Supplier',
  guest: 'Guest Booking',
};

export function App() {
  const [activeApp, setActiveApp] = useState<AppType>('driver');
  const [dark, setDark] = useState(false);

  const apps: Record<AppType, React.ReactNode> = {
    driver: <DriverApp dark={dark} />,
    rep: <RepApp dark={dark} />,
    supplier: <SupplierApp dark={dark} />,
    guest: <GuestApp dark={dark} />,
  };

  return (
    <div className="preview-layout">
      <div className="preview-header">
        <img src="/itourtt-logo.svg" alt="iTour" style={{ height: 32, filter: 'brightness(2) saturate(0.8)' }} />
        <h1>iTour Mobile Apps Preview</h1>
        <div className="app-tabs">
          {(Object.keys(APP_LABELS) as AppType[]).map((key) => (
            <button
              key={key}
              className={`app-tab ${activeApp === key ? 'active' : ''}`}
              onClick={() => setActiveApp(key)}
            >
              {APP_LABELS[key]}
            </button>
          ))}
        </div>
        <button
          className="app-tab"
          onClick={() => setDark(!dark)}
          style={{ marginLeft: 16 }}
        >
          {dark ? 'Light Mode' : 'Dark Mode'}
        </button>
      </div>
      <div className="preview-content">
        {apps[activeApp]}
      </div>
    </div>
  );
}
