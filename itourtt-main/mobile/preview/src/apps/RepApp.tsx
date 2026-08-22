import React, { useState } from 'react';

interface Props {
  dark: boolean;
}

type Screen = 'login' | 'jobs' | 'detail' | 'noshow' | 'history' | 'notifications' | 'profile';

const SCREENS: { key: Screen; label: string }[] = [
  { key: 'login', label: 'Login' },
  { key: 'jobs', label: 'Jobs List' },
  { key: 'detail', label: 'Job Detail' },
  { key: 'noshow', label: 'No Show' },
  { key: 'history', label: 'History' },
  { key: 'notifications', label: 'Notifications' },
  { key: 'profile', label: 'Profile' },
];

const MOCK_JOBS = [
  {
    id: '1',
    internalRef: 'IT-2026-001847',
    serviceType: 'ARR' as const,
    repStatus: 'PENDING' as const,
    route: 'Cairo Airport (T2) \u2192 Pyramids Zone',
    pax: 4,
    time: '14:30',
    flight: 'MS-721',
    clientName: 'Ahmed Hassan',
    clientMobile: '+20 123 456 7890',
    meetingPoint: 'Terminal 2 - Gate 3 Exit',
    driverName: 'Mohamed Khalil',
    driverMobile: '+20 100 234 5678',
    vehiclePlate: 'ABC 1234',
  },
  {
    id: '2',
    internalRef: 'IT-2026-001852',
    serviceType: 'DEP' as const,
    repStatus: 'PENDING' as const,
    route: 'Le Meridien Hotel \u2192 Cairo Airport (T3)',
    pax: 2,
    time: '16:00',
    flight: 'EK-924',
    clientName: 'Sarah Williams',
    clientMobile: '+44 777 123 456',
    meetingPoint: 'Hotel Lobby',
    driverName: 'Hassan Ali',
    driverMobile: '+20 101 345 6789',
    vehiclePlate: 'DEF 5678',
  },
  {
    id: '3',
    internalRef: 'IT-2026-001860',
    serviceType: 'CITY' as const,
    repStatus: 'COMPLETED' as const,
    route: 'Four Seasons Nile \u2192 Khan el-Khalili',
    pax: 6,
    time: '09:00',
    clientName: 'Marco Rossi',
    meetingPoint: 'Hotel Main Entrance',
    driverName: 'Youssef Magdy',
    driverMobile: '+20 102 456 7890',
    vehiclePlate: 'GHI 9012',
  },
];

const MOCK_NOTIFICATIONS = [
  { id: '1', title: 'New Assignment', body: 'You have been assigned to IT-2026-001847 at Cairo Airport T2', time: '5 min ago', read: false },
  { id: '2', title: 'Flight Delayed', body: 'MS-721 delayed by 45 min. New ETA: 15:15', time: '20 min ago', read: false },
  { id: '3', title: 'Job Completed', body: 'IT-2026-001860 marked as completed. Fee: 75 EGP', time: '2 hours ago', read: true },
  { id: '4', title: 'Schedule Change', body: 'Tomorrow\'s first assignment moved to 07:00', time: '5 hours ago', read: true },
];

const MOCK_HISTORY = [
  { ref: 'IT-2026-001830', route: 'Airport (T1) \u2192 Maadi Zone', flight: 'MS-802', status: 'COMPLETED', fee: '75 EGP', date: 'Feb 19' },
  { ref: 'IT-2026-001815', route: 'Heliopolis \u2192 Airport (T2)', flight: 'QR-310', status: 'COMPLETED', fee: '75 EGP', date: 'Feb 19' },
  { ref: 'IT-2026-001801', route: 'Airport (T3) \u2192 Zamalek', flight: 'LH-580', status: 'NO_SHOW', fee: '0 EGP', date: 'Feb 18' },
  { ref: 'IT-2026-001790', route: 'Giza \u2192 Cairo Airport (T1)', flight: 'MS-912', status: 'COMPLETED', fee: '75 EGP', date: 'Feb 18' },
];

function getBorderColor(status: string) {
  switch (status) {
    case 'PENDING': return '#eab308';
    case 'IN_PROGRESS': return '#3b82f6';
    case 'COMPLETED': return '#22c55e';
    default: return '#eab308';
  }
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'PENDING': return <span className="badge badge-pending">Pending</span>;
    case 'IN_PROGRESS': return <span className="badge badge-progress">In Progress</span>;
    case 'COMPLETED': return <span className="badge badge-completed">Completed</span>;
    case 'NO_SHOW': return <span className="badge badge-noshow">No Show</span>;
    default: return null;
  }
}

function getServiceBadge(type: string) {
  switch (type) {
    case 'ARR': return <span className="badge badge-arr">ARR</span>;
    case 'DEP': return <span className="badge badge-dep">DEP</span>;
    case 'CITY': return <span className="badge badge-city">CITY</span>;
    default: return null;
  }
}

export function RepApp({ dark }: Props) {
  const [screen, setScreen] = useState<Screen>('jobs');
  const [activeTab, setActiveTab] = useState(0);

  const tabForScreen = (s: Screen) => {
    if (s === 'jobs' || s === 'detail' || s === 'noshow') return 0;
    if (s === 'history') return 1;
    if (s === 'notifications') return 2;
    if (s === 'profile') return 3;
    return -1;
  };

  const renderLogin = () => (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-title">iTour Rep</div>
        <input className="login-input" placeholder="Mobile Number" defaultValue="+20" />
        <input className="login-input" type="password" placeholder="PIN Code" />
        <button className="login-btn">Sign In</button>
        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>
          Forgot PIN? Contact dispatch
        </div>
      </div>
    </div>
  );

  const renderJobs = () => (
    <>
      <div className="screen-header">Today's Assignments</div>
      <div className="date-nav">
        <button>&larr;</button>
        <span>Thu, Feb 20, 2026</span>
        <button>&rarr;</button>
      </div>
      {MOCK_JOBS.map((job) => (
        <div
          key={job.id}
          className="job-card"
          style={{ borderLeftColor: getBorderColor(job.repStatus), cursor: 'pointer' }}
          onClick={() => setScreen('detail')}
        >
          <div className="job-card-header">
            <div style={{ display: 'flex', gap: 6 }}>
              {getServiceBadge(job.serviceType)}
              {getStatusBadge(job.repStatus)}
            </div>
            <span style={{ fontSize: 13, color: '#737373' }}>{job.time}</span>
          </div>
          <div className="job-ref">{job.internalRef}</div>
          <div className="job-route">{job.route}</div>
          <div className="job-footer">
            <span>{job.pax} pax</span>
            {job.flight && <span>Flight: {job.flight}</span>}
          </div>
          <div style={{ fontSize: 12, color: '#737373', marginTop: 6 }}>
            Meeting: {job.meetingPoint}
          </div>
          {job.repStatus === 'PENDING' && (
            <div className="btn-row">
              <button className="btn btn-primary btn-sm" style={{ flex: 1 }}>Complete</button>
              <button className="btn btn-destructive btn-sm" style={{ flex: 1 }} onClick={(e) => { e.stopPropagation(); setScreen('noshow'); }}>No Show</button>
            </div>
          )}
        </div>
      ))}
      <div style={{ height: 80 }} />
    </>
  );

  const renderDetail = () => {
    const job = MOCK_JOBS[0];
    return (
      <>
        <div className="screen-header" style={{ position: 'relative' }}>
          <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('jobs')}>&larr;</span>
          Job Detail
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            {getServiceBadge(job.serviceType)}
            {getStatusBadge(job.repStatus)}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{job.internalRef}</div>
          <div style={{ fontSize: 14, color: '#737373', marginBottom: 16 }}>{job.route}</div>

          <div className="card" style={{ margin: '0 0 12px' }}>
            <div className="card-title">Trip Info</div>
            <div className="info-row"><span className="info-label">Service</span><span className="info-value">{job.serviceType}</span></div>
            <div className="info-row"><span className="info-label">Time</span><span className="info-value">{job.time}</span></div>
            <div className="info-row"><span className="info-label">Flight</span><span className="info-value">{job.flight}</span></div>
            <div className="info-row"><span className="info-label">Pax</span><span className="info-value">{job.pax} passengers</span></div>
            <div className="info-row"><span className="info-label">Meeting Point</span><span className="info-value">{job.meetingPoint}</span></div>
          </div>

          <div className="card" style={{ margin: '0 0 12px' }}>
            <div className="card-title">Client</div>
            <div className="info-row"><span className="info-label">Name</span><span className="info-value">{job.clientName}</span></div>
            <div className="info-row"><span className="info-label">Mobile</span><span className="info-value">{job.clientMobile}</span></div>
            <div className="btn-row">
              <button className="btn btn-outline btn-sm" style={{ flex: 1 }}>Call</button>
              <button className="btn btn-outline btn-sm" style={{ flex: 1, background: '#25d366', color: '#fff', borderColor: '#25d366' }}>WhatsApp</button>
            </div>
          </div>

          <div className="card" style={{ margin: '0 0 12px' }}>
            <div className="card-title">Driver & Vehicle</div>
            <div className="info-row"><span className="info-label">Driver</span><span className="info-value">{job.driverName}</span></div>
            <div className="info-row"><span className="info-label">Driver Mobile</span><span className="info-value">{job.driverMobile}</span></div>
            <div className="info-row"><span className="info-label">Vehicle</span><span className="info-value">{job.vehiclePlate}</span></div>
            <div className="btn-row">
              <button className="btn btn-outline btn-sm" style={{ flex: 1 }}>Call Driver</button>
            </div>
          </div>

          <div className="btn-row">
            <button className="btn btn-primary" style={{ flex: 1 }}>Mark Complete</button>
            <button className="btn btn-destructive" style={{ flex: 1 }} onClick={() => setScreen('noshow')}>No Show</button>
          </div>
        </div>
        <div style={{ height: 80 }} />
      </>
    );
  };

  const renderNoShow = () => (
    <>
      <div className="screen-header" style={{ position: 'relative' }}>
        <span style={{ cursor: 'pointer', position: 'absolute', left: 16 }} onClick={() => setScreen('detail')}>&larr;</span>
        Report No Show
      </div>
      <div style={{ padding: 16 }}>
        <div className="card" style={{ margin: '0 0 16px' }}>
          <div className="card-title">IT-2026-001847</div>
          <div style={{ fontSize: 13, color: '#737373' }}>Cairo Airport (T2) &rarr; Pyramids Zone</div>
          <div style={{ fontSize: 13, color: '#737373', marginTop: 4 }}>Client: Ahmed Hassan</div>
        </div>

        <div className="card" style={{ margin: '0 0 16px' }}>
          <div className="card-title">Photo Evidence</div>
          <div style={{ fontSize: 12, color: '#737373', marginBottom: 8 }}>Take photos of the meeting point</div>
          <div className="photo-grid">
            <div className="photo-placeholder">+</div>
            <div className="photo-placeholder">+</div>
          </div>
        </div>

        <div className="card" style={{ margin: '0 0 16px' }}>
          <div className="card-title">GPS Location</div>
          <div style={{ fontSize: 13, color: '#737373', marginBottom: 8 }}>Capture your current location</div>
          <button className="btn btn-outline btn-sm">Capture GPS Location</button>
          <div style={{ marginTop: 8, fontSize: 12, color: '#22c55e' }}>
            30.1219, 31.4056 - Captured (Airport T2)
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Notes (optional)</label>
          <input className="form-input" placeholder="Waited 30 minutes at gate..." />
        </div>

        <button className="btn btn-destructive">Submit No Show Report</button>
      </div>
      <div style={{ height: 80 }} />
    </>
  );

  const renderHistory = () => (
    <>
      <div className="screen-header">Assignment History</div>
      <div style={{ padding: '12px 16px', display: 'flex', gap: 8 }}>
        <input className="form-input" type="date" defaultValue="2026-02-17" style={{ flex: 1 }} />
        <input className="form-input" type="date" defaultValue="2026-02-20" style={{ flex: 1 }} />
      </div>
      <div className="card" style={{ background: dark ? '#171717' : '#f0fdf4', borderColor: dark ? '#262626' : '#bbf7d0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ fontSize: 12, color: '#737373' }}>Total Earnings (4 days)</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#16a34a' }}>225 EGP</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, color: '#737373' }}>Flights</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>4</div>
          </div>
        </div>
        <div style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>Fee per flight: 75 EGP</div>
      </div>
      {MOCK_HISTORY.map((h, i) => (
        <div key={i} className="job-card" style={{ borderLeftColor: h.status === 'COMPLETED' ? '#22c55e' : '#ec4899' }}>
          <div className="job-card-header">
            {getStatusBadge(h.status)}
            <span style={{ fontSize: 12, color: '#737373' }}>{h.date}</span>
          </div>
          <div className="job-ref">{h.ref}</div>
          <div className="job-route">{h.route}</div>
          <div className="job-footer">
            <span>Flight: {h.flight}</span>
            <span>Fee: {h.fee}</span>
          </div>
        </div>
      ))}
      <div style={{ height: 80 }} />
    </>
  );

  const renderNotifications = () => (
    <>
      <div className="screen-header">Notifications</div>
      {MOCK_NOTIFICATIONS.map((n) => (
        <div key={n.id} className="notif-item">
          <div className={`notif-dot ${n.read ? 'read' : ''}`} />
          <div>
            <div className="notif-title">{n.title}</div>
            <div className="notif-body">{n.body}</div>
            <div className="notif-time">{n.time}</div>
          </div>
        </div>
      ))}
      <div style={{ height: 80 }} />
    </>
  );

  const renderProfile = () => (
    <>
      <div className="screen-header">Profile</div>
      <div style={{ padding: 16 }}>
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <div style={{ width: 72, height: 72, borderRadius: '50%', background: dark ? '#262626' : '#e5e5e5', margin: '0 auto 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>
            FA
          </div>
          <div className="profile-name">Fatma Ahmed</div>
          <span className="badge badge-completed">Active Rep</span>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Personal Info</div>
          <div className="profile-field">
            <div className="profile-field-label">Mobile</div>
            <div className="profile-field-value">+20 100 987 6543</div>
          </div>
          <div className="profile-field">
            <div className="profile-field-label">Employee ID</div>
            <div className="profile-field-value">REP-0042</div>
          </div>
          <div className="profile-field">
            <div className="profile-field-label">Assigned Area</div>
            <div className="profile-field-value">Cairo Airport - All Terminals</div>
          </div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">This Month</div>
          <div style={{ display: 'flex', justifyContent: 'space-around', padding: '8px 0' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700 }}>48</div>
              <div style={{ fontSize: 11, color: '#737373' }}>Flights</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700 }}>3,600</div>
              <div style={{ fontSize: 11, color: '#737373' }}>EGP Earned</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700 }}>2</div>
              <div style={{ fontSize: 11, color: '#737373' }}>No Shows</div>
            </div>
          </div>
        </div>

        <div className="card" style={{ margin: '0 0 12px' }}>
          <div className="card-title">Appearance</div>
          <div className="theme-row">
            <button className={`theme-btn ${!dark ? 'active' : ''}`}>Light</button>
            <button className={`theme-btn ${dark ? 'active' : ''}`}>Dark</button>
          </div>
        </div>

        <button className="btn btn-destructive" style={{ marginTop: 8 }}>Sign Out</button>
      </div>
      <div style={{ height: 80 }} />
    </>
  );

  const renderScreen = () => {
    switch (screen) {
      case 'login': return renderLogin();
      case 'jobs': return renderJobs();
      case 'detail': return renderDetail();
      case 'noshow': return renderNoShow();
      case 'history': return renderHistory();
      case 'notifications': return renderNotifications();
      case 'profile': return renderProfile();
    }
  };

  return (
    <div>
      <div className="screen-nav">
        {SCREENS.map((s) => (
          <button
            key={s.key}
            className={`screen-pill ${screen === s.key ? 'active' : ''}`}
            onClick={() => { setScreen(s.key); setActiveTab(tabForScreen(s.key)); }}
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
        {screen !== 'login' && (
          <div className="tab-bar">
            <div className={`tab-item ${activeTab === 0 ? 'active' : ''}`} onClick={() => { setActiveTab(0); setScreen('jobs'); }}>
              <div className="tab-icon">&#128203;</div>
              <span>Jobs</span>
            </div>
            <div className={`tab-item ${activeTab === 1 ? 'active' : ''}`} onClick={() => { setActiveTab(1); setScreen('history'); }}>
              <div className="tab-icon">&#128337;</div>
              <span>History</span>
            </div>
            <div className={`tab-item ${activeTab === 2 ? 'active' : ''}`} onClick={() => { setActiveTab(2); setScreen('notifications'); }}>
              <div className="tab-icon">&#128276;</div>
              <span>Alerts</span>
            </div>
            <div className={`tab-item ${activeTab === 3 ? 'active' : ''}`} onClick={() => { setActiveTab(3); setScreen('profile'); }}>
              <div className="tab-icon">&#128100;</div>
              <span>Profile</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
