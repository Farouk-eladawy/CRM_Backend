import React, { useState } from 'react';

interface Props {
  dark: boolean;
}

type Screen = 'home' | 'search' | 'vehicles' | 'details' | 'payment' | 'confirmation' | 'lookup' | 'bookingDetail';

const SCREENS: { key: Screen; label: string }[] = [
  { key: 'home', label: 'Home' },
  { key: 'search', label: 'Search' },
  { key: 'vehicles', label: 'Vehicles' },
  { key: 'details', label: 'Guest Details' },
  { key: 'payment', label: 'Payment' },
  { key: 'confirmation', label: 'Confirmation' },
  { key: 'lookup', label: 'Lookup' },
  { key: 'bookingDetail', label: 'Booking Detail' },
];

const VEHICLES = [
  { name: 'Sedan', description: 'Toyota Corolla or similar', capacity: 3, luggage: 2, price: '$45' },
  { name: 'SUV', description: 'Toyota Fortuner or similar', capacity: 5, luggage: 4, price: '$65' },
  { name: 'Van', description: 'Toyota Hiace or similar', capacity: 10, luggage: 8, price: '$85' },
];

const STEP_LABELS = ['Route', 'Vehicle', 'Details', 'Payment'];

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="step-indicator">
      {STEP_LABELS.map((label, i) => (
        <React.Fragment key={i}>
          {i > 0 && <div className={`step-line ${i <= current ? 'done' : ''}`} />}
          <div
            className={`step-dot ${i === current ? 'active' : i < current ? 'done' : ''}`}
            title={label}
          >
            {i < current ? '\u2713' : i + 1}
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}

export function GuestApp({ dark }: Props) {
  const [screen, setScreen] = useState<Screen>('home');
  const [selectedVehicle, setSelectedVehicle] = useState(0);
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'cash'>('card');

  const renderHome = () => (
    <>
      <div className="screen-header">iTour Transfer</div>
      <div className="guest-hero">
        <img src="/itourtt-logo.svg" alt="iTour" style={{ height: 72, marginBottom: 16 }} />
        <h2>Airport Transfers</h2>
        <p>Safe, reliable transfers across Egypt</p>
      </div>
      <div style={{ padding: '0 16px' }}>
        <button className="btn btn-primary" style={{ marginBottom: 12 }} onClick={() => setScreen('search')}>
          Book a Transfer
        </button>
        <button className="btn btn-outline" onClick={() => setScreen('lookup')}>
          Track My Booking
        </button>
      </div>

      <div style={{ padding: '32px 16px 16px' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>Why Choose iTour?</div>
        {[
          { icon: '\u2705', title: 'Fixed Prices', desc: 'No hidden charges or surge pricing' },
          { icon: '\u23F0', title: 'Flight Monitoring', desc: 'We track your flight for delays' },
          { icon: '\uD83D\uDE97', title: 'Meet & Greet', desc: 'Driver meets you at arrivals' },
        ].map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ fontSize: 20, flexShrink: 0 }}>{item.icon}</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{item.title}</div>
              <div style={{ fontSize: 12, color: '#737373' }}>{item.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  );

  const renderSearch = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('home')}>&larr;</span>
        Book Transfer
      </div>
      <StepIndicator current={0} />
      <div style={{ padding: '0 16px' }}>
        <div className="form-group">
          <label className="form-label">Service Type</label>
          <div style={{ display: 'flex', gap: 8 }}>
            {['Arrival', 'Departure', 'City Tour'].map((t, i) => (
              <button key={i} className={`screen-pill ${i === 0 ? 'active' : ''}`} style={{ flex: 1, textAlign: 'center' }}>{t}</button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Pickup Location</label>
          <select className="form-input" defaultValue="airport-t2">
            <option value="" disabled>Select location...</option>
            <optgroup label="Cairo Airport">
              <option value="airport-t1">Terminal 1</option>
              <option value="airport-t2">Terminal 2</option>
              <option value="airport-t3">Terminal 3</option>
            </optgroup>
            <optgroup label="Hurghada Airport">
              <option value="hrg">Hurghada International</option>
            </optgroup>
            <optgroup label="Sharm Airport">
              <option value="ssh">Sharm el-Sheikh International</option>
            </optgroup>
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Dropoff Location</label>
          <select className="form-input" defaultValue="pyramids">
            <option value="" disabled>Select destination...</option>
            <optgroup label="Giza">
              <option value="pyramids">Pyramids Zone</option>
              <option value="haram">Haram Zone</option>
              <option value="dokki">Dokki Zone</option>
            </optgroup>
            <optgroup label="Cairo">
              <option value="zamalek">Zamalek</option>
              <option value="maadi">Maadi</option>
              <option value="heliopolis">Heliopolis</option>
              <option value="nasr-city">Nasr City</option>
            </optgroup>
            <optgroup label="New Cairo">
              <option value="fifth-settlement">5th Settlement</option>
              <option value="rehab">Rehab City</option>
            </optgroup>
          </select>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Date</label>
            <input className="form-input" type="date" defaultValue="2026-02-22" />
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Time</label>
            <input className="form-input" type="time" defaultValue="14:30" />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Passengers</label>
            <select className="form-input" defaultValue="2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1 }}>
            <label className="form-label">Luggage</label>
            <select className="form-input" defaultValue="2">
              {[0, 1, 2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Flight Number (optional)</label>
          <input className="form-input" placeholder="e.g. MS-721" defaultValue="MS-721" />
        </div>

        <button className="btn btn-primary" onClick={() => setScreen('vehicles')}>
          Search Vehicles
        </button>
      </div>
      <div style={{ height: 20 }} />
    </>
  );

  const renderVehicles = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('search')}>&larr;</span>
        Select Vehicle
      </div>
      <StepIndicator current={1} />
      <div style={{ padding: '0 16px 8px', fontSize: 13, color: '#737373' }}>
        Cairo Airport (T2) &rarr; Pyramids Zone
      </div>
      <div style={{ padding: '0 16px 4px', fontSize: 12, color: '#a3a3a3' }}>
        Feb 22, 2026 at 14:30 &middot; 2 passengers
      </div>
      {VEHICLES.map((v, i) => (
        <div
          key={i}
          className="vehicle-card"
          style={{
            borderColor: selectedVehicle === i ? '#1a1a2e' : undefined,
            background: selectedVehicle === i ? (dark ? '#1a1a2e' : '#f8f7ff') : undefined,
          }}
          onClick={() => setSelectedVehicle(i)}
        >
          <div>
            <div className="vehicle-name">{v.name}</div>
            <div className="vehicle-capacity">{v.description}</div>
            <div style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>
              Up to {v.capacity} pax &middot; {v.luggage} bags
            </div>
          </div>
          <div className="vehicle-price" style={{ color: dark ? '#c4b5fd' : '#1a1a2e' }}>{v.price}</div>
        </div>
      ))}
      <div style={{ padding: '12px 16px' }}>
        <button className="btn btn-primary" onClick={() => setScreen('details')}>
          Continue with {VEHICLES[selectedVehicle].name}
        </button>
      </div>
    </>
  );

  const renderDetails = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('vehicles')}>&larr;</span>
        Guest Details
      </div>
      <StepIndicator current={2} />
      <div style={{ padding: '0 16px' }}>
        <div className="form-group">
          <label className="form-label">Full Name *</label>
          <input className="form-input" placeholder="John Smith" defaultValue="John Smith" />
        </div>
        <div className="form-group">
          <label className="form-label">Email *</label>
          <input className="form-input" type="email" placeholder="john@example.com" defaultValue="john@example.com" />
        </div>
        <div className="form-group">
          <label className="form-label">Phone Number *</label>
          <input className="form-input" type="tel" placeholder="+1 234 567 8900" defaultValue="+1 234 567 8900" />
        </div>
        <div className="form-group">
          <label className="form-label">Nationality</label>
          <select className="form-input" defaultValue="US">
            <option value="US">United States</option>
            <option value="GB">United Kingdom</option>
            <option value="DE">Germany</option>
            <option value="FR">France</option>
            <option value="IT">Italy</option>
            <option value="ES">Spain</option>
            <option value="EG">Egypt</option>
            <option value="SA">Saudi Arabia</option>
            <option value="AE">UAE</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Special Requests (optional)</label>
          <input className="form-input" placeholder="Child seat, wheelchair, etc." />
        </div>

        <div className="card" style={{ margin: '0 0 16px', background: dark ? '#171717' : '#fafafa' }}>
          <div className="card-title">Booking Summary</div>
          <div className="price-row"><span>Route</span><span>Airport T2 &rarr; Pyramids</span></div>
          <div className="price-row"><span>Date</span><span>Feb 22, 2026</span></div>
          <div className="price-row"><span>Vehicle</span><span>{VEHICLES[selectedVehicle].name}</span></div>
          <div className="price-row"><span>Passengers</span><span>2</span></div>
          <div className="price-row price-total"><span>Total</span><span>{VEHICLES[selectedVehicle].price}</span></div>
        </div>

        <button className="btn btn-primary" onClick={() => setScreen('payment')}>
          Continue to Payment
        </button>
      </div>
      <div style={{ height: 20 }} />
    </>
  );

  const renderPayment = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('details')}>&larr;</span>
        Payment
      </div>
      <StepIndicator current={3} />
      <div style={{ padding: '0 16px' }}>
        <div className="form-group">
          <label className="form-label">Payment Method</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              className={`screen-pill ${paymentMethod === 'card' ? 'active' : ''}`}
              style={{ flex: 1, textAlign: 'center', padding: '12px' }}
              onClick={() => setPaymentMethod('card')}
            >
              Credit Card
            </button>
            <button
              className={`screen-pill ${paymentMethod === 'cash' ? 'active' : ''}`}
              style={{ flex: 1, textAlign: 'center', padding: '12px' }}
              onClick={() => setPaymentMethod('cash')}
            >
              Cash on Arrival
            </button>
          </div>
        </div>

        {paymentMethod === 'card' && (
          <>
            <div className="form-group">
              <label className="form-label">Card Number</label>
              <input className="form-input" placeholder="4242 4242 4242 4242" />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">Expiry</label>
                <input className="form-input" placeholder="MM/YY" />
              </div>
              <div className="form-group" style={{ flex: 1 }}>
                <label className="form-label">CVC</label>
                <input className="form-input" placeholder="123" />
              </div>
            </div>
          </>
        )}

        {paymentMethod === 'cash' && (
          <div className="card" style={{ margin: '0 0 16px', background: dark ? '#422006' : '#fef3c7' }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Cash Payment</div>
            <div style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>
              Pay the driver in cash upon arrival. Amount will be converted to EGP at the current exchange rate.
            </div>
          </div>
        )}

        <div className="card" style={{ margin: '0 0 16px', background: dark ? '#171717' : '#fafafa' }}>
          <div className="card-title">Order Summary</div>
          <div className="price-row"><span>{VEHICLES[selectedVehicle].name}</span><span>{VEHICLES[selectedVehicle].price}</span></div>
          <div className="price-row"><span>Service Fee</span><span>$5</span></div>
          <div className="price-row price-total">
            <span>Total</span>
            <span>${parseInt(VEHICLES[selectedVehicle].price.slice(1)) + 5}</span>
          </div>
        </div>

        <button className="btn btn-primary" onClick={() => setScreen('confirmation')}>
          {paymentMethod === 'card' ? 'Pay & Confirm' : 'Confirm Booking'}
        </button>

        <div style={{ textAlign: 'center', marginTop: 12, fontSize: 11, color: '#a3a3a3' }}>
          By confirming, you agree to our Terms of Service
        </div>
      </div>
      <div style={{ height: 20 }} />
    </>
  );

  const renderConfirmation = () => (
    <>
      <div className="screen-header">Booking Confirmed</div>
      <div style={{ textAlign: 'center', padding: '40px 16px 24px' }}>
        <div style={{
          width: 80, height: 80, borderRadius: '50%', background: '#d1fae5',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          margin: '0 auto 16px', fontSize: 40
        }}>
          &#10003;
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Thank You!</div>
        <div style={{ fontSize: 14, color: '#737373', marginBottom: 4 }}>Your transfer has been booked</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: dark ? '#c4b5fd' : '#1a1a2e', marginTop: 16 }}>
          BK-2026-004521
        </div>
        <div style={{ fontSize: 12, color: '#a3a3a3', marginTop: 4 }}>Booking Reference</div>
      </div>

      <div className="card" style={{ margin: '0 16px 12px' }}>
        <div className="card-title">Booking Details</div>
        <div className="info-row"><span className="info-label">Route</span><span className="info-value">Airport T2 &rarr; Pyramids Zone</span></div>
        <div className="info-row"><span className="info-label">Date</span><span className="info-value">Feb 22, 2026</span></div>
        <div className="info-row"><span className="info-label">Time</span><span className="info-value">14:30</span></div>
        <div className="info-row"><span className="info-label">Flight</span><span className="info-value">MS-721</span></div>
        <div className="info-row"><span className="info-label">Vehicle</span><span className="info-value">{VEHICLES[selectedVehicle].name}</span></div>
        <div className="info-row"><span className="info-label">Passengers</span><span className="info-value">2</span></div>
        <div className="info-row"><span className="info-label">Payment</span><span className="info-value">{paymentMethod === 'card' ? 'Credit Card' : 'Cash'}</span></div>
        <div className="info-row" style={{ fontWeight: 600 }}>
          <span className="info-label" style={{ fontWeight: 600 }}>Total</span>
          <span className="info-value">${parseInt(VEHICLES[selectedVehicle].price.slice(1)) + 5}</span>
        </div>
      </div>

      <div style={{ padding: '0 16px' }}>
        <div style={{ fontSize: 12, color: '#737373', textAlign: 'center', marginBottom: 16 }}>
          A confirmation email has been sent to john@example.com
        </div>
        <button className="btn btn-primary" style={{ marginBottom: 8 }} onClick={() => setScreen('home')}>
          Book Another Transfer
        </button>
        <button className="btn btn-outline" onClick={() => setScreen('bookingDetail')}>
          View Booking Details
        </button>
      </div>
    </>
  );

  const renderLookup = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('home')}>&larr;</span>
        Track Booking
      </div>
      <div className="lookup-card">
        <div style={{ fontSize: 48, marginBottom: 16 }}>&#128269;</div>
        <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>Find Your Booking</div>
        <div style={{ fontSize: 13, color: '#737373', marginBottom: 20 }}>
          Enter your booking reference number
        </div>
        <div className="form-group">
          <input className="form-input" placeholder="BK-2026-XXXXXX" defaultValue="BK-2026-004521" style={{ textAlign: 'center', fontSize: 16, fontWeight: 600 }} />
        </div>
        <button className="btn btn-primary" onClick={() => setScreen('bookingDetail')}>
          Track Booking
        </button>
      </div>
      <div style={{ padding: '0 16px', textAlign: 'center' }}>
        <div style={{ fontSize: 12, color: '#a3a3a3' }}>
          You can find your reference number in your confirmation email
        </div>
      </div>
    </>
  );

  const renderBookingDetail = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('home')}>&larr;</span>
        Booking Details
      </div>
      <div style={{ padding: 16 }}>
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>BK-2026-004521</div>
          <span className="badge badge-progress" style={{ marginTop: 8 }}>Confirmed</span>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Transfer Details</div>
          <div className="info-row"><span className="info-label">Service</span><span className="info-value">Airport Arrival</span></div>
          <div className="info-row"><span className="info-label">From</span><span className="info-value">Cairo Airport (Terminal 2)</span></div>
          <div className="info-row"><span className="info-label">To</span><span className="info-value">Pyramids Zone</span></div>
          <div className="info-row"><span className="info-label">Date</span><span className="info-value">Feb 22, 2026</span></div>
          <div className="info-row"><span className="info-label">Time</span><span className="info-value">14:30</span></div>
          <div className="info-row"><span className="info-label">Flight</span><span className="info-value">MS-721</span></div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Vehicle & Passengers</div>
          <div className="info-row"><span className="info-label">Vehicle</span><span className="info-value">{VEHICLES[selectedVehicle].name}</span></div>
          <div className="info-row"><span className="info-label">Passengers</span><span className="info-value">2</span></div>
          <div className="info-row"><span className="info-label">Luggage</span><span className="info-value">2 bags</span></div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Guest Info</div>
          <div className="info-row"><span className="info-label">Name</span><span className="info-value">John Smith</span></div>
          <div className="info-row"><span className="info-label">Email</span><span className="info-value">john@example.com</span></div>
          <div className="info-row"><span className="info-label">Phone</span><span className="info-value">+1 234 567 8900</span></div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Payment</div>
          <div className="price-row"><span>Transfer</span><span>{VEHICLES[selectedVehicle].price}</span></div>
          <div className="price-row"><span>Service Fee</span><span>$5</span></div>
          <div className="price-row price-total">
            <span>Total Paid</span>
            <span>${parseInt(VEHICLES[selectedVehicle].price.slice(1)) + 5}</span>
          </div>
        </div>

        <button className="btn btn-destructive">Cancel Booking</button>
        <div style={{ textAlign: 'center', marginTop: 8, fontSize: 11, color: '#a3a3a3' }}>
          Free cancellation up to 24 hours before pickup
        </div>
      </div>
    </>
  );

  const renderScreen = () => {
    switch (screen) {
      case 'home': return renderHome();
      case 'search': return renderSearch();
      case 'vehicles': return renderVehicles();
      case 'details': return renderDetails();
      case 'payment': return renderPayment();
      case 'confirmation': return renderConfirmation();
      case 'lookup': return renderLookup();
      case 'bookingDetail': return renderBookingDetail();
    }
  };

  return (
    <div>
      <div className="screen-nav">
        {SCREENS.map((s) => (
          <button
            key={s.key}
            className={`screen-pill ${screen === s.key ? 'active' : ''}`}
            onClick={() => setScreen(s.key)}
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className={`phone-frame ${dark ? 'dark' : ''}`}>
        <div className="phone-notch" />
        <div className="phone-screen">
          {renderScreen()}
        </div>
        {/* Guest app has no tab bar - uses stack navigation */}
      </div>
    </div>
  );
}
